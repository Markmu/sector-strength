"""涨跌停专题数据采集服务

负责从 Tushare 拉取涨停专题三接口数据并写入数据库。仿
``EtfDataInitService``（progress/cancel 回调 + 按交易日删旧插新）范式。

- ``sync_limit_data(trade_date)``：一次同步三张表
  - limit_list_d：每日涨跌停/炸板个股明细（约 200 条/日）
  - limit_step：涨停连板天梯（约 10 条/日）
  - limit_cpt_list：涨停最强概念板块（约 20 条/日）
- ``sync_limit_data_range(start_date, end_date)``：按日期范围逐交易日复用
  ``sync_limit_data``（仿 ``backfill_etf_history``），范围级进度 + 单日失败不中断。

三表同属一日、数据量小，合并为一个同步任务，按 trade_date 删除当日旧数据
+ 批量插入，保证幂等可重跑。
"""

import logging
import asyncio
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.limit import LimitListD, LimitStep, LimitCptList
from src.services.data_acquisition import DataSourceFactory
from src.services.trading_calendar import TradingCalendar

logger = logging.getLogger(__name__)


class LimitDataInitService:
    """涨跌停专题数据采集服务

    提供按交易日的涨停专题三表同步（sync_limit_data），以及按日期范围
    逐交易日复用单日同步的范围同步（sync_limit_data_range）。
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        """
        初始化服务

        Args:
            session: 数据库异步会话。为 None 时由调用方（如 collector）传入。
        """
        self.session = session
        self._progress_callback: Optional[callable] = None
        self._cancel_check: Optional[callable] = None

    def set_session(self, session: AsyncSession):
        """设置数据库会话（collector 模式下由外部注入）"""
        self.session = session

    def set_progress_callback(self, callback: callable):
        """设置进度回调，签名 (current: int, total: int, message: str)"""
        self._progress_callback = callback

    def set_cancel_check(self, check: callable):
        """设置取消检查回调，返回 bool（True = 已取消）"""
        self._cancel_check = check

    async def _check_cancelled(self):
        if self._cancel_check:
            if asyncio.iscoroutinefunction(self._cancel_check):
                cancelled = await self._cancel_check()
            else:
                cancelled = self._cancel_check()
            if cancelled:
                raise asyncio.CancelledError("任务已被用户取消")

    async def _update_progress(self, current: int, total: int, message: str):
        if self._progress_callback:
            try:
                if asyncio.iscoroutinefunction(self._progress_callback):
                    await self._progress_callback(current, total, message)
                else:
                    self._progress_callback(current, total, message)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

    # ------------------------------------------------------------------
    # sync_limit_data：涨停专题三表同步（删旧插新，幂等可重跑）
    # ------------------------------------------------------------------

    async def sync_limit_data(self, trade_date: str) -> dict:
        """同步指定交易日的涨停专题三表数据。

        一次调用同步 limit_list_d / limit_step / limit_cpt_list 三张表。
        按 trade_date 删除当日旧数据后批量插入，保证幂等可重跑。

        Args:
            trade_date: 交易日，格式 'YYYYMMDD' 或 'YYYY-MM-DD'（如 '20260731'）。

        Returns:
            {
                "trade_date": str,
                "limit_list_d": int,   # 入库条数
                "limit_step": int,
                "limit_cpt_list": int,
            }
        """
        if self.session is None:
            raise RuntimeError("LimitDataInitService.session 未设置")

        tushare = DataSourceFactory.create()
        target_date = self._parse_trade_date(trade_date)
        target_date_str = trade_date.replace("-", "")
        result = {
            "trade_date": target_date.isoformat(),
            "limit_list_d": 0,
            "limit_step": 0,
            "limit_cpt_list": 0,
        }

        await self._update_progress(0, 3, f"开始同步涨停专题 (trade_date={trade_date})")

        # 1. limit_list_d — 涨跌停/炸板个股明细
        await self._check_cancelled()
        await self._update_progress(1, 3, "正在拉取涨跌停明细 (limit_list_d)...")
        try:
            ll_records = tushare.get_limit_list_d(target_date_str)
        except Exception as e:
            logger.error(f"拉取 limit_list_d 失败 (trade_date={trade_date}): {e}")
            raise

        # 删旧 + 批量插新
        await self.session.execute(
            delete(LimitListD).where(LimitListD.trade_date == target_date)
        )
        ll_count = 0
        for record in ll_records:
            ts_code = record.get("ts_code")
            if not ts_code:
                continue
            self.session.add(
                LimitListD(
                    trade_date=target_date,
                    ts_code=ts_code,
                    name=record.get("name"),
                    industry=record.get("industry"),
                    close=self._to_decimal(record.get("close")),
                    pct_chg=self._to_decimal(record.get("pct_chg")),
                    amount=self._to_decimal(record.get("amount")),
                    fd_amount=self._to_decimal(record.get("fd_amount")),
                    first_time=self._to_str(record.get("first_time")),
                    last_time=self._to_str(record.get("last_time")),
                    open_times=self._to_int(record.get("open_times")),
                    up_stat=self._to_str(record.get("up_stat")),
                    limit_times=self._to_int(record.get("limit_times")),
                    limit_type=self._to_str(record.get("limit")),
                )
            )
            ll_count += 1
        result["limit_list_d"] = ll_count

        # 2. limit_step — 连板天梯
        await self._check_cancelled()
        await self._update_progress(2, 3, "正在拉取连板天梯 (limit_step)...")
        try:
            ls_records = tushare.get_limit_step(target_date_str)
        except Exception as e:
            logger.error(f"拉取 limit_step 失败 (trade_date={trade_date}): {e}")
            raise

        await self.session.execute(
            delete(LimitStep).where(LimitStep.trade_date == target_date)
        )
        ls_count = 0
        for record in ls_records:
            ts_code = record.get("ts_code")
            if not ts_code:
                continue
            self.session.add(
                LimitStep(
                    trade_date=target_date,
                    ts_code=ts_code,
                    name=record.get("name"),
                    nums=self._to_int(record.get("nums")),
                )
            )
            ls_count += 1
        result["limit_step"] = ls_count

        # 3. limit_cpt_list — 涨停最强板块
        await self._check_cancelled()
        await self._update_progress(3, 3, "正在拉取涨停最强板块 (limit_cpt_list)...")
        try:
            lc_records = tushare.get_limit_cpt_list(target_date_str)
        except Exception as e:
            logger.error(
                f"拉取 limit_cpt_list 失败 (trade_date={trade_date}): {e}"
            )
            raise

        await self.session.execute(
            delete(LimitCptList).where(LimitCptList.trade_date == target_date)
        )
        lc_count = 0
        for record in lc_records:
            ts_code = record.get("ts_code")
            if not ts_code:
                continue
            self.session.add(
                LimitCptList(
                    trade_date=target_date,
                    ts_code=ts_code,
                    name=record.get("name"),
                    days=self._to_int(record.get("days")),
                    up_stat=self._to_str(record.get("up_stat")),
                    cons_nums=self._to_int(record.get("cons_nums")),
                    up_nums=self._to_int(record.get("up_nums")),
                    pct_chg=self._to_decimal(record.get("pct_chg")),
                    rank=self._to_int(record.get("rank")),
                )
            )
            lc_count += 1
        result["limit_cpt_list"] = lc_count

        await self.session.commit()

        logger.info(
            f"[Limit] 涨停专题同步完成 (trade_date={trade_date}): "
            f"limit_list_d={ll_count}, limit_step={ls_count}, "
            f"limit_cpt_list={lc_count}"
        )
        await self._update_progress(
            3, 3,
            f"涨停专题同步完成: 涨跌停 {ll_count} 条, 连板 {ls_count} 条, "
            f"板块 {lc_count} 条",
        )

        return result

    # ------------------------------------------------------------------
    # sync_limit_data_range：按日期范围逐交易日同步（复用 sync_limit_data）
    # ------------------------------------------------------------------

    async def sync_limit_data_range(self, start_date: str, end_date: str) -> dict:
        """按日期范围逐交易日同步涨停专题三表（仿 ``backfill_etf_history``）。

        用 TradingCalendar 筛选范围内交易日（按日期升序），逐日复用
        ``sync_limit_data``（删旧插新，幂等可重跑）。范围级进度对外暴露
        ``(i, total_days)``，单日同步内部的三表粒度进度被临时屏蔽避免噪音。

        某日失败计入 ``failed_days`` 并继续下一日（不中断整体）；仅
        ``CancelledError`` 向上抛出。

        Args:
            start_date: 起始日期，'YYYYMMDD' 或 'YYYY-MM-DD'。
            end_date: 结束日期，'YYYYMMDD' 或 'YYYY-MM-DD'。

        Returns:
            {
                "start_date": str,
                "end_date": str,
                "total_days": int,    # 范围内交易日数
                "processed_days": int,  # 成功日数
                "failed_days": int,     # 失败日数
            }
        """
        if self.session is None:
            raise RuntimeError("LimitDataInitService.session 未设置")

        # 1. 日期校验（start <= end，范围上限 10 年）
        start = self._parse_trade_date(start_date)
        end = self._parse_trade_date(end_date)
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")
        if (end - start).days > 3650:
            raise ValueError("日期范围不能超过 10 年")

        # 2. 用交易日历筛选范围内交易日（按日期升序）
        calendar = TradingCalendar()
        trading_days: List[date] = await calendar.get_trading_days_between(start, end)
        total_days = len(trading_days)

        logger.info(
            f"[Limit] 范围同步开始: {start} ~ {end}, 交易日 {total_days} 天"
        )

        # 3. 屏蔽内层三表粒度进度（置 None 让 sync_limit_data 内部的
        #    _update_progress 短路），范围级 (i, total_days) 进度由本地
        #    helper 直接调用保存的原始回调发出（不能用 _update_progress，
        #    否则同样被短路）。
        saved_cb = self._progress_callback
        self._progress_callback = None

        async def _emit_range_progress(current: int, msg: str):
            """范围级进度：直接走 saved_cb，不受 self._progress_callback=None 影响。"""
            if saved_cb is None:
                return
            try:
                if asyncio.iscoroutinefunction(saved_cb):
                    await saved_cb(current, max(total_days, 1), msg)
                else:
                    saved_cb(current, max(total_days, 1), msg)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

        processed_days = 0
        failed_days = 0
        try:
            await _emit_range_progress(
                0, f"涨停专题范围同步 {start} ~ {end}，共 {total_days} 个交易日"
            )

            if total_days == 0:
                logger.info(f"[Limit] 范围 {start} ~ {end} 内无交易日，跳过")
                return {
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "total_days": 0,
                    "processed_days": 0,
                    "failed_days": 0,
                }

            # 4. 按日期升序逐日复用 sync_limit_data（删旧插新，幂等可重跑）
            for i, td in enumerate(trading_days, 1):
                await self._check_cancelled()
                td_str = td.isoformat()
                try:
                    await self.sync_limit_data(td_str)
                    processed_days += 1
                except asyncio.CancelledError:
                    logger.warning(f"[Limit] 范围同步在 {td_str} 被取消")
                    raise
                except Exception as e:
                    failed_days += 1
                    logger.warning(
                        f"[Limit] 范围同步 {td_str} 失败，跳过该日: {e}"
                    )

                await _emit_range_progress(
                    i, f"涨停专题范围同步进度 {i}/{total_days}（{td_str}）"
                )

            logger.info(
                f"[Limit] 范围同步完成: 总计 {total_days}, "
                f"成功 {processed_days}, 失败 {failed_days}"
            )
            await _emit_range_progress(
                total_days,
                f"涨停专题范围同步完成: 成功 {processed_days}, "
                f"失败 {failed_days}"
            )

            return {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "total_days": total_days,
                "processed_days": processed_days,
                "failed_days": failed_days,
            }
        finally:
            # 恢复原进度回调
            self._progress_callback = saved_cb

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_trade_date(trade_date: str) -> date:
        """解析交易日字符串（兼容 YYYYMMDD / YYYY-MM-DD）"""
        s = trade_date.replace("-", "")
        return datetime.strptime(s, "%Y%m%d").date()

    @staticmethod
    def _to_decimal(val):
        """安全转 Decimal，None/NaN 返回 None"""
        from decimal import Decimal, InvalidOperation

        if val is None:
            return None
        try:
            d = Decimal(str(val))
            return d if d == d else None  # NaN check
        except (InvalidOperation, ValueError, TypeError):
            return None

    @staticmethod
    def _to_int(val):
        """安全转 int，None/NaN 返回 None"""
        if val is None:
            return None
        try:
            f = float(val)
            return int(f) if f == f else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_str(val):
        """安全转 str，None 保留为 None（不转成 'None'）"""
        if val is None:
            return None
        s = str(val).strip()
        return s if s and s.lower() != "nan" else None
