"""指数数据采集服务（第 15 期 plan-02）

负责从 Tushare 拉取关键指数的基础信息、日线行情、估值指标与成分权重，
写入 index_basic / index_daily / index_dailybasic / index_weight 四张表。

仿 ``EtfDataInitService``（progress/cancel 回调 + pg upsert）范式：
- ``sync_index_basic()``：全量拉 index_basic → upsert（排除 is_watched 字段）→
  预置 14 只关注指数置 true（仅首次同步，不覆盖已关注记录）。
- ``backfill_index_history(start, end)``：逐交易日升序，逐关注指数采集
  daily/dailybasic/weight；权重数据按月缓存，同月只拉一次。
- ``sync_index_daily(trade_date)``：当日增量，逐关注指数采集 daily/dailybasic/
  weight（weight 当月未入库则拉取）。

数据特性：
- ``index_weight`` 数据仅在月末/调整日刷新，回填时用包含月末的宽窗口（当月 1 日至月末）
  拉取，同一月份只拉一次，避免重复请求。
- ``index_dailybasic`` 仅宽基指数有估值数据，无估值指数返回空列表，跳过 upsert。
"""

import asyncio
import calendar
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Set

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.index_monitor import (
    IndexBasic,
    IndexDaily,
    IndexDailyBasic,
    IndexWeight,
)
from src.services.data_acquisition import DataSourceFactory
from src.services.trading_calendar import TradingCalendar

logger = logging.getLogger(__name__)

# 预置 14 只关注指数（plan-02 §sync_index_basic 验收）
PRESET_WATCHED = [
    "000001.SH",  # 上证指数
    "000300.SH",  # 沪深300
    "000016.SH",  # 上证50
    "000905.SH",  # 中证500
    "000852.SH",  # 中证1000
    "399001.SZ",  # 深证成指
    "399006.SZ",  # 创业板指
    "399102.SZ",  # 创业板综合
    "399673.SZ",  # 创业板50
    "000688.SH",  # 科创50
    "000698.SH",  # 科创材料
    "000699.SH",  # 科创芯片
    "931643.CSI",  # 中证A50
    "899050.BJ",  # 北证50
]


class IndexDataInitService:
    """指数数据采集服务

    提供指数基础信息同步（sync_index_basic）、历史回填（backfill_index_history）
    与当日增量采集（sync_index_daily）。
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
        # 单个同步任务复用同一数据源实例，使客户端级限流在请求间持续生效。
        self._data_source = None

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

    def _get_data_source(self):
        """延迟创建并复用当前同步任务的数据源客户端。"""
        if self._data_source is None:
            self._data_source = DataSourceFactory.create()
        return self._data_source

    # ------------------------------------------------------------------
    # sync_index_basic：指数基础信息（index_basic 接口，全量拉取）
    # ------------------------------------------------------------------

    async def sync_index_basic(self) -> dict:
        """同步指数基础信息（index_basic 接口，全量拉取约 1 万条）。

        流程：
        1. 调 get_index_basic() 拉全量指数基础信息。
        2. 字段映射（ts_code/name/market/publisher/category/base_date/base_point/list_date 直取）。
        3. upsert index_basic（冲突键 ts_code，on_conflict_do_update 覆盖除
           is_watched 外的字段——**注意：不能覆盖 is_watched**，否则会重置用户关注配置）。
        4. 预置 14 只关注指数置 true（仅首次同步，用 WHERE is_watched IS NULL 兜底）。

        Returns:
            {"added": int, "updated": int, "failed": int}
            （added=成功 upsert 条数；updated 固定 0；failed=失败条数）
        """
        if self.session is None:
            raise RuntimeError("IndexDataInitService.session 未设置")

        tushare = self._get_data_source()
        added = 0
        failed = 0

        await self._update_progress(0, 1, "正在从 Tushare 拉取指数基础信息...")

        try:
            records = tushare.get_index_basic()
        except Exception as e:
            logger.error(f"拉取指数基础信息失败: {e}")
            raise

        if not records:
            raise RuntimeError("指数基础信息接口返回 0 条数据，拒绝将任务标记为成功")

        total = len(records)
        logger.info(f"拉取到 {total} 条指数基础信息")
        await self._update_progress(0, total, f"共 {total} 条指数待入库")

        for i, record in enumerate(records, 1):
            try:
                ts_code = record.get("ts_code")

                if not ts_code:
                    failed += 1
                    continue

                base_date = self._parse_date(record.get("base_date"))
                list_date = self._parse_date(record.get("list_date"))
                base_point = self._to_decimal(record.get("base_point"))

                stmt = pg_insert(IndexBasic).values(
                    ts_code=ts_code,
                    name=record.get("name"),
                    market=record.get("market"),
                    publisher=record.get("publisher"),
                    category=record.get("category"),
                    base_date=base_date,
                    base_point=base_point,
                    list_date=list_date,
                )
                # on_conflict_do_update 排除 is_watched 字段——保留用户关注配置
                update_cols = {
                    "name": stmt.excluded.name,
                    "market": stmt.excluded.market,
                    "publisher": stmt.excluded.publisher,
                    "category": stmt.excluded.category,
                    "base_date": stmt.excluded.base_date,
                    "base_point": stmt.excluded.base_point,
                    "list_date": stmt.excluded.list_date,
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=["ts_code"],
                    set_=update_cols,
                )
                await self.session.execute(stmt)
                added += 1

            except Exception as e:
                failed += 1
                logger.warning(f"写入指数基础信息 {record.get('ts_code')} 失败: {e}")
                continue

            if i % 500 == 0 or i == total:
                await self._update_progress(i, total, f"已处理 {i}/{total} 条指数基础信息")

        # 4. 预置 14 只关注指数置 true（仅首次同步：WHERE is_watched IS NULL 兜底，
        #    避免覆盖已关注记录；用 ts_code IN 预置清单限定范围）
        from sqlalchemy import update

        preset_result = await self.session.execute(
            update(IndexBasic)
            .where(
                IndexBasic.ts_code.in_(PRESET_WATCHED),
                IndexBasic.is_watched.is_(None),
            )
            .values(is_watched=True)
        )
        preset_rows = preset_result.rowcount or 0
        # 再次兜底：预置清单中 ts_code 已存在但 is_watched=False 的也置为 true
        # （仅针对预置清单 14 只，不触碰用户主动取消关注的记录）
        # 说明：AC 要求首次同步后 14 只 must be true，故对预置清单强制置 true。
        await self.session.execute(
            update(IndexBasic)
            .where(IndexBasic.ts_code.in_(PRESET_WATCHED))
            .values(is_watched=True)
        )

        await self.session.commit()

        logger.info(
            f"[INDEX] 基础信息同步完成: 总计 {total}, 入库 {added}, 失败 {failed}, "
            f"预置关注 {len(PRESET_WATCHED)} 只"
        )
        await self._update_progress(
            total, total,
            f"指数基础信息同步完成: 入库 {added}, 失败 {failed}, 预置关注已设置"
        )

        return {
            "added": added,
            "updated": 0,
            "failed": failed,
            "preset_watched": len(PRESET_WATCHED),
        }

    # ------------------------------------------------------------------
    # backfill_index_history：按日期范围回填历史行情/估值/权重
    # ------------------------------------------------------------------

    async def backfill_index_history(self, start_date: str, end_date: str) -> dict:
        """按日期范围回填历史指数数据。

        仿 ``EtfDataInitService.backfill_etf_history`` 范式：
        日期校验 + 范围上限 + 交易日历筛选 + 按日期升序逐日循环。

        流程：
        1. 日期校验：start <= end，范围上限 10 年（3650 天）。
        2. 查 index_basic WHERE is_watched=true 获取关注指数清单。
        3. 用 TradingCalendar 筛选范围内交易日（升序）。
        4. 逐交易日循环：对每个交易日，逐关注指数采集 daily/dailybasic；
           权重数据按月缓存，同月只拉一次（用当月 1 日至月末宽窗口拉取）。
        5. 单指数单日失败不中断，记 error 继续。
        6. 每个交易日完成后 upsert 入库 + progress_callback。

        Args:
            start_date: 起始日期，'YYYY-MM-DD' 或 'YYYYMMDD'。
            end_date: 结束日期，'YYYY-MM-DD' 或 'YYYYMMDD'。

        Returns:
            {
                "trading_days": int,
                "daily_records": int,
                "basic_records": int,
                "weight_records": int,
                "errors": [...],
            }
        """
        if self.session is None:
            raise RuntimeError("IndexDataInitService.session 未设置")

        # 1. 日期校验（仿 backfill_etf_history）
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)
        if start is None or end is None:
            raise ValueError(f"无效的日期范围: start_date={start_date}, end_date={end_date}")
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")

        # 范围上限 10 年（3650 天）
        if (end - start).days > 3650:
            raise ValueError("日期范围不能超过 10 年")

        # 2. 查关注指数清单（依赖 sync_index_basic 已设置 is_watched）
        watched_codes = await self._get_watched_codes()
        if not watched_codes:
            message = "关注指数清单为空，请先同步指数基础信息并设置关注指数"
            logger.error("[INDEX] %s", message)
            await self._update_progress(0, 1, message)
            raise RuntimeError(message)

        # 3. 用交易日历筛选范围内交易日（按日期升序）
        cal = TradingCalendar()
        trading_days: List[date] = await cal.get_trading_days_between(start, end)
        total_days = len(trading_days)

        logger.info(
            f"[INDEX] 开始历史回填: {start} ~ {end}, 交易日 {total_days} 天, "
            f"关注指数 {len(watched_codes)} 只"
        )
        await self._update_progress(
            0, max(total_days, 1),
            f"历史回填范围 {start} ~ {end}，共 {total_days} 个交易日，"
            f"{len(watched_codes)} 只关注指数"
        )

        daily_records = 0
        basic_records = 0
        weight_records = 0
        errors: List[str] = []
        # 已拉取权重的月份集合（YYYY-MM），同月不重复拉取
        weight_months_done: Set[str] = set()

        if total_days == 0:
            logger.info(f"[INDEX] 回填范围 {start} ~ {end} 内无交易日，跳过")
            return {
                "trading_days": 0,
                "daily_records": 0,
                "basic_records": 0,
                "weight_records": 0,
                "errors": errors,
            }

        # 4. 逐交易日循环
        for i, trade_date in enumerate(trading_days, 1):
            await self._check_cancelled()

            trade_date_str = trade_date.isoformat()
            month_key = f"{trade_date.year:04d}-{trade_date.month:02d}"

            # 逐关注指数采集 daily / dailybasic
            for ts_code in watched_codes:
                # daily：当日单点
                try:
                    n = await self._fetch_and_upsert_index_daily(
                        ts_code, trade_date, trade_date
                    )
                    daily_records += n
                except Exception as e:
                    err = f"daily {ts_code} {trade_date_str}: {e}"
                    errors.append(err)
                    logger.warning(f"[INDEX] 回填 {err}")

                # dailybasic：当日单点
                try:
                    n = await self._fetch_and_upsert_index_dailybasic(
                        ts_code, trade_date, trade_date
                    )
                    basic_records += n
                except Exception as e:
                    err = f"dailybasic {ts_code} {trade_date_str}: {e}"
                    errors.append(err)
                    logger.warning(f"[INDEX] 回填 {err}")

            # 权重：按月缓存，同月只拉一次（用当月 1 日至月末宽窗口）
            if month_key not in weight_months_done:
                month_start, month_end = self._month_range(trade_date)
                # 只对有 weight 数据的指数拉取（部分指数 weight 返回空列表，跳过）
                for ts_code in watched_codes:
                    try:
                        n = await self._fetch_and_upsert_index_weight(
                            ts_code, month_start, month_end
                        )
                        weight_records += n
                    except Exception as e:
                        err = f"weight {ts_code} {month_key}: {e}"
                        errors.append(err)
                        logger.warning(f"[INDEX] 回填 {err}")
                weight_months_done.add(month_key)

            await self.session.commit()

            await self._update_progress(
                i, total_days,
                f"历史回填进度 {i}/{total_days}（{trade_date_str}）"
            )

        if daily_records == 0:
            message = (
                f"历史回填覆盖 {total_days} 个交易日，但 index_daily 写入 0 条；"
                f"关注指数: {', '.join(watched_codes)}。"
                "请检查指数代码、数据源响应或接口权限"
            )
            logger.error("[INDEX] %s", message)
            await self._update_progress(total_days, total_days, message)
            raise RuntimeError(message)

        logger.info(
            f"[INDEX] 历史回填完成: 交易日 {total_days}, "
            f"daily {daily_records}, dailybasic {basic_records}, "
            f"weight {weight_records}, 错误 {len(errors)}"
        )
        await self._update_progress(
            total_days, total_days,
            f"历史回填完成: daily {daily_records}, dailybasic {basic_records}, "
            f"weight {weight_records}"
        )

        return {
            "trading_days": total_days,
            "daily_records": daily_records,
            "basic_records": basic_records,
            "weight_records": weight_records,
            "errors": errors[:50],  # 截断避免日志过长
        }

    # ------------------------------------------------------------------
    # sync_index_daily：当日增量采集
    # ------------------------------------------------------------------

    async def sync_index_daily(self, trade_date: str) -> dict:
        """采集指数当日行情/估值/权重增量。

        Args:
            trade_date: 交易日，'YYYY-MM-DD' 或 'YYYYMMDD'。

        流程：
        1. 查关注指数清单。
        2. 逐指数采集 daily + dailybasic，upsert 入库。
        3. 当月未入库权重时，用当月 1 日至月末宽窗口拉取权重。
        """
        if self.session is None:
            raise RuntimeError("IndexDataInitService.session 未设置")

        target_date = self._parse_trade_date(trade_date)

        # 非交易日无行情属于正常跳过，不能误判成数据源故障。
        is_trading_day, skip_reason = await TradingCalendar().is_trading_day(target_date)
        if not is_trading_day:
            message = f"{trade_date} 为{skip_reason or '非交易日'}，跳过指数当日采集"
            logger.info("[INDEX] %s", message)
            await self._update_progress(0, 0, message)
            return {
                "daily_records": 0,
                "basic_records": 0,
                "weight_records": 0,
                "errors": [],
                "skipped": True,
                "skip_reason": skip_reason or "非交易日",
            }

        watched_codes = await self._get_watched_codes()
        if not watched_codes:
            message = "关注指数清单为空，请先同步指数基础信息并设置关注指数"
            logger.error("[INDEX] sync_index_daily: %s", message)
            raise RuntimeError(message)

        total = len(watched_codes)
        logger.info(
            f"[INDEX] 当日增量采集 (trade_date={trade_date}), 关注指数 {total} 只"
        )
        await self._update_progress(
            0, total,
            f"当日增量采集 {trade_date}，共 {total} 只关注指数"
        )

        daily_records = 0
        basic_records = 0
        weight_records = 0
        errors: List[str] = []

        # 权重：检查当月是否已入库，未入库则用当月宽窗口拉取一次
        month_start, month_end = self._month_range(target_date)
        month_has_weight = await self._has_weight_for_month(target_date)
        weight_done = month_has_weight

        for i, ts_code in enumerate(watched_codes, 1):
            await self._check_cancelled()

            # daily
            try:
                n = await self._fetch_and_upsert_index_daily(
                    ts_code, target_date, target_date
                )
                daily_records += n
            except Exception as e:
                err = f"daily {ts_code}: {e}"
                errors.append(err)
                logger.warning(f"[INDEX] 当日增量 {err}")

            # dailybasic
            try:
                n = await self._fetch_and_upsert_index_dailybasic(
                    ts_code, target_date, target_date
                )
                basic_records += n
            except Exception as e:
                err = f"dailybasic {ts_code}: {e}"
                errors.append(err)
                logger.warning(f"[INDEX] 当日增量 {err}")

            # weight（同月只拉一次）
            if not weight_done:
                try:
                    n = await self._fetch_and_upsert_index_weight(
                        ts_code, month_start, month_end
                    )
                    weight_records += n
                except Exception as e:
                    err = f"weight {ts_code}: {e}"
                    errors.append(err)
                    logger.warning(f"[INDEX] 当日增量 {err}")

            if i % 2 == 0 or i == total:
                await self._update_progress(
                    i, total,
                    f"当日增量进度 {i}/{total}（{trade_date}）"
                )

        if daily_records == 0:
            await self.session.rollback()
            error_preview = "; ".join(errors[:3])
            message = (
                f"{trade_date} 为交易日，但 index_daily 写入 0 条；"
                f"关注指数: {', '.join(watched_codes)}。"
                "请检查数据发布时间、指数代码或数据源响应"
            )
            if error_preview:
                message = f"{message}；错误示例: {error_preview}"
            logger.error("[INDEX] %s", message)
            await self._update_progress(total, total, message)
            raise RuntimeError(message)

        await self.session.commit()

        logger.info(
            f"[INDEX] 当日增量采集完成 (trade_date={trade_date}): "
            f"daily {daily_records}, dailybasic {basic_records}, "
            f"weight {weight_records}, 错误 {len(errors)}"
        )
        await self._update_progress(
            total, total,
            f"当日增量完成: daily {daily_records}, dailybasic {basic_records}, "
            f"weight {weight_records}"
        )

        return {
            "daily_records": daily_records,
            "basic_records": basic_records,
            "weight_records": weight_records,
            "errors": errors[:50],
        }

    # ------------------------------------------------------------------
    # upsert 辅助方法
    # ------------------------------------------------------------------

    async def _fetch_and_upsert_index_daily(
        self, ts_code: str, start: date, end: date
    ) -> int:
        """拉取并 upsert index_daily 记录（冲突键 trade_date+ts_code）。

        Returns:
            成功 upsert 的条数。
        """
        tushare = self._get_data_source()
        records = tushare.get_index_daily(ts_code, start, end)
        if not records:
            return 0

        count = 0
        for record in records:
            trade_date = self._parse_date(record.get("trade_date"))
            if trade_date is None:
                continue

            stmt = pg_insert(IndexDaily).values(
                trade_date=trade_date,
                ts_code=record.get("ts_code") or ts_code,
                open=self._to_decimal(record.get("open")),
                high=self._to_decimal(record.get("high")),
                low=self._to_decimal(record.get("low")),
                close=self._to_decimal(record.get("close")),
                pre_close=self._to_decimal(record.get("pre_close")),
                change=self._to_decimal(record.get("change")),
                pct_chg=self._to_decimal(record.get("pct_chg")),
                vol=self._to_decimal(record.get("vol")),
                amount=self._to_decimal(record.get("amount")),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_index_daily_date_code",
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "pre_close": stmt.excluded.pre_close,
                    "change": stmt.excluded.change,
                    "pct_chg": stmt.excluded.pct_chg,
                    "vol": stmt.excluded.vol,
                    "amount": stmt.excluded.amount,
                },
            )
            await self.session.execute(stmt)
            count += 1

        return count

    async def _fetch_and_upsert_index_dailybasic(
        self, ts_code: str, start: date, end: date
    ) -> int:
        """拉取并 upsert index_dailybasic 记录（冲突键 trade_date+ts_code）。

        无估值指数返回空列表，跳过 upsert。

        Returns:
            成功 upsert 的条数。
        """
        tushare = self._get_data_source()
        records = tushare.get_index_dailybasic(ts_code, start, end)
        if not records:
            return 0

        count = 0
        for record in records:
            trade_date = self._parse_date(record.get("trade_date"))
            if trade_date is None:
                continue

            stmt = pg_insert(IndexDailyBasic).values(
                trade_date=trade_date,
                ts_code=record.get("ts_code") or ts_code,
                total_mv=self._to_decimal(record.get("total_mv")),
                float_mv=self._to_decimal(record.get("float_mv")),
                total_share=self._to_decimal(record.get("total_share")),
                float_share=self._to_decimal(record.get("float_share")),
                free_share=self._to_decimal(record.get("free_share")),
                turnover_rate=self._to_decimal(record.get("turnover_rate")),
                turnover_rate_f=self._to_decimal(record.get("turnover_rate_f")),
                pe=self._to_decimal(record.get("pe")),
                pe_ttm=self._to_decimal(record.get("pe_ttm")),
                pb=self._to_decimal(record.get("pb")),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_index_dailybasic_date_code",
                set_={
                    "total_mv": stmt.excluded.total_mv,
                    "float_mv": stmt.excluded.float_mv,
                    "total_share": stmt.excluded.total_share,
                    "float_share": stmt.excluded.float_share,
                    "free_share": stmt.excluded.free_share,
                    "turnover_rate": stmt.excluded.turnover_rate,
                    "turnover_rate_f": stmt.excluded.turnover_rate_f,
                    "pe": stmt.excluded.pe,
                    "pe_ttm": stmt.excluded.pe_ttm,
                    "pb": stmt.excluded.pb,
                },
            )
            await self.session.execute(stmt)
            count += 1

        return count

    async def _fetch_and_upsert_index_weight(
        self, index_code: str, start: date, end: date
    ) -> int:
        """拉取并 upsert index_weight 记录（冲突键 index_code+con_code+trade_date）。

        Returns:
            成功 upsert 的条数。
        """
        tushare = self._get_data_source()
        records = tushare.get_index_weight(index_code, start, end)
        if not records:
            return 0

        count = 0
        for record in records:
            trade_date = self._parse_date(record.get("trade_date"))
            if trade_date is None:
                continue

            stmt = pg_insert(IndexWeight).values(
                index_code=record.get("index_code") or index_code,
                con_code=record.get("con_code"),
                trade_date=trade_date,
                weight=self._to_decimal(record.get("weight")),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_index_weight_code_con_date",
                set_={
                    "weight": stmt.excluded.weight,
                },
            )
            await self.session.execute(stmt)
            count += 1

        return count

    # ------------------------------------------------------------------
    # 查询辅助方法
    # ------------------------------------------------------------------

    async def _get_watched_codes(self) -> List[str]:
        """查询 is_watched=true 的指数 ts_code 清单。"""
        stmt = select(IndexBasic.ts_code).where(IndexBasic.is_watched.is_(True))
        result = await self.session.execute(stmt)
        # scalars().all() 已经返回字符串标量，不能再取 row[0]，否则完整代码
        # "000300.SH" 会被截断为 "0"。
        raw_codes = result.scalars().all()
        codes: List[str] = []
        invalid_codes: List[str] = []
        seen: Set[str] = set()

        for value in raw_codes:
            code = str(value).strip() if value is not None else ""
            if not code:
                continue
            # Tushare 指数代码应包含代码段与市场后缀，例如 000300.SH。
            if "." not in code or code.startswith(".") or code.endswith("."):
                invalid_codes.append(code)
                continue
            if code not in seen:
                seen.add(code)
                codes.append(code)

        if invalid_codes:
            raise ValueError(
                "关注清单包含无效指数代码: " + ", ".join(invalid_codes)
            )

        logger.info("[INDEX] 已加载 %d 个关注指数: %s", len(codes), ", ".join(codes))
        return codes

    async def _has_weight_for_month(self, target_date: date) -> bool:
        """检查当月是否已有 index_weight 数据（任意指数任意成分股）。

        用于 sync_index_daily 决定是否需要拉取当月权重。
        """
        month_start, month_end = self._month_range(target_date)
        stmt = select(IndexWeight.id).where(
            IndexWeight.trade_date >= month_start,
            IndexWeight.trade_date <= month_end,
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ------------------------------------------------------------------
    # 日期/数值辅助方法（仿 EtfDataInitService）
    # ------------------------------------------------------------------

    @staticmethod
    def _month_range(d: date) -> tuple:
        """返回 d 所在月份的 (first_day, last_day) date 对象。"""
        first_day = date(d.year, d.month, 1)
        last_day_num = calendar.monthrange(d.year, d.month)[1]
        last_day = date(d.year, d.month, last_day_num)
        return first_day, last_day

    @staticmethod
    def _parse_date(value) -> Optional[date]:
        """解析日期字符串，兼容 YYYYMMDD 与 YYYY-MM-DD"""
        if value is None:
            return None
        try:
            s = str(value).strip()
            if not s or s == "None":
                return None
            for fmt in ("%Y%m%d", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    continue
            return None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_trade_date(value: str) -> date:
        """将 trade_date（YYYYMMDD 或 YYYY-MM-DD）转为 date 对象"""
        d = IndexDataInitService._parse_date(value)
        if d is None:
            raise ValueError(f"无效的 trade_date: {value}")
        return d

    @staticmethod
    def _to_decimal(value) -> Optional[Decimal]:
        """安全转 Decimal，失败返回 None"""
        if value is None:
            return None
        try:
            f = float(value)
            return Decimal(str(f))
        except (ValueError, TypeError):
            return None
