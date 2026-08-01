"""ETF 数据采集服务（第 14 期）

负责从 Tushare 拉取 ETF 基础信息与日份额/净值并写入数据库。
仿 ``FundDataInitService``（progress/cancel 回调 + pg upsert）范式。

- ``sync_etf_basic()``：拉 ETF 清单（pro.etf_basic list_status='L'）→ upsert etf_basic。
  跟踪指数用官方 index_code / index_name 直接入库，不再做文本归类。
- ``sync_etf_daily(trade_date)``：拉当日份额 → 逐只拉净值 → 查前日份额 →
  计算 share_change / net_inflow → upsert etf_daily。

净流入额公式（ADR-3）：``net_inflow = share_change(万份) × unit_nav / 10000``（亿元）。
采集时即计算并存储，查询直接读现成字段。
"""

import logging
import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.etf import EtfBasic, EtfDaily
from src.services.data_acquisition import DataSourceFactory
from src.services.trading_calendar import TradingCalendar

logger = logging.getLogger(__name__)


class EtfDataInitService:
    """ETF 数据采集服务

    提供 ETF 基础信息同步（sync_etf_basic）与日份额/净值采集（sync_etf_daily）。
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
    # sync_etf_basic：ETF 基础信息（etf_basic 接口，官方指数直取）
    # ------------------------------------------------------------------

    async def sync_etf_basic(self) -> dict:
        """同步 ETF 基础信息（跟踪指数用官方 index_code / index_name 直接入库）。

        流程（仿 FundDataInitService.sync_fund_basic）：
        1. 调 get_fund_basic_etf() 拉 ETF 清单（pro.etf_basic list_status='L'）
        2. 字段映射（csname→name / cname→full_name / index_code / index_name 等）
        3. upsert etf_basic（冲突键 ts_code，on_conflict_do_update 覆盖字段）

        Returns:
            {"added": int, "updated": int, "failed": int, "skipped": int}
            （added/upsert 处理数；upsert 无法精确区分 insert/update，
             added=成功 upsert 条数，updated 固定 0）
        """
        if self.session is None:
            raise RuntimeError("EtfDataInitService.session 未设置")

        tushare = DataSourceFactory.create()
        added = 0
        failed = 0
        skipped = 0

        await self._update_progress(0, 1, "正在从 Tushare 拉取 ETF 基础信息...")

        try:
            records = tushare.get_fund_basic_etf()
        except Exception as e:
            logger.error(f"拉取 ETF 基础信息失败: {e}")
            raise

        total = len(records)
        logger.info(f"拉取到 {total} 条 ETF 基础信息")
        await self._update_progress(0, total, f"共 {total} 条 ETF 待入库")

        for i, record in enumerate(records, 1):
            try:
                ts_code = record.get("ts_code")

                if not ts_code:
                    failed += 1
                    continue

                list_date = self._parse_date(record.get("list_date"))
                setup_date = self._parse_date(record.get("setup_date"))

                stmt = pg_insert(EtfBasic).values(
                    ts_code=ts_code,
                    name=record.get("csname"),
                    full_name=record.get("cname"),
                    index_code=record.get("index_code"),
                    index_name=record.get("index_name"),
                    list_date=list_date,
                    setup_date=setup_date,
                    list_status=record.get("list_status"),
                    exchange=record.get("exchange"),
                    mgr_name=record.get("mgr_name"),
                    etf_type=record.get("etf_type"),
                )
                update_cols = {
                    "name": stmt.excluded.name,
                    "full_name": stmt.excluded.full_name,
                    "index_code": stmt.excluded.index_code,
                    "index_name": stmt.excluded.index_name,
                    "list_date": stmt.excluded.list_date,
                    "setup_date": stmt.excluded.setup_date,
                    "list_status": stmt.excluded.list_status,
                    "exchange": stmt.excluded.exchange,
                    "mgr_name": stmt.excluded.mgr_name,
                    "etf_type": stmt.excluded.etf_type,
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=["ts_code"],
                    set_=update_cols,
                )
                await self.session.execute(stmt)
                added += 1

            except Exception as e:
                failed += 1
                logger.warning(f"写入 ETF 基础信息 {record.get('ts_code')} 失败: {e}")
                continue

            if i % 200 == 0 or i == total:
                await self._update_progress(i, total, f"已处理 {i}/{total} 条 ETF 基础信息")

        await self.session.commit()

        logger.info(
            f"[ETF] 基础信息同步完成: 总计 {total}, 入库 {added}, 失败 {failed}"
        )
        await self._update_progress(
            total, total,
            f"ETF 基础信息同步完成: 入库 {added}, 失败 {failed}"
        )

        return {
            "added": added,
            "updated": 0,
            "failed": failed,
            "skipped": skipped,
        }

    # ------------------------------------------------------------------
    # sync_etf_daily：当日份额/规模/净值采集（etf_share_size 单接口）
    # ------------------------------------------------------------------

    async def sync_etf_daily(self, trade_date: str) -> dict:
        """采集 ETF 当日份额/规模/净值并计算 share_change / net_inflow / change_percent 落库。

        Args:
            trade_date: 交易日，格式 'YYYYMMDD'（如 '20260729'）。

        流程：
        1. 调 get_etf_share_size(trade_date) 拉当日全市场 ETF 份额/规模/净值/收盘价
           （约 1600 条，单接口拿齐，取代旧 fund_share + 逐只 fund_nav 方案）。
        2. 查前一日份额与收盘价：etf_daily 中 trade_date < 给定日的最大 trade_date 记录。
        3. 计算：
           - share_change = 当日 total_share − 前日 total_share（前日不存在则 null）
           - net_inflow = share_change × nav / 10000（亿元），nav 缺失则 null
           - change_percent = (当日close − 前日close) / 前日close × 100，close 缺失则 null
        4. 批量 upsert etf_daily（on_conflict_do_update 覆盖）。
        5. 返回 {processed, added, updated, skipped}。
        """
        if self.session is None:
            raise RuntimeError("EtfDataInitService.session 未设置")

        tushare = DataSourceFactory.create()
        target_date = self._parse_trade_date(trade_date)
        # etf_share_size 接口要求 YYYYMMDD 无横杠格式
        target_date_str_yyyymmdd = trade_date.replace("-", "")

        processed = 0
        added = 0
        updated = 0
        skipped = 0

        await self._update_progress(0, 1, f"正在拉取 ETF 份额/规模 (trade_date={trade_date})...")

        # 1. 拉当日 ETF 份额/规模/净值/收盘价（etf_share_size 单接口）
        try:
            records = tushare.get_etf_share_size(target_date_str_yyyymmdd)
        except Exception as e:
            logger.error(f"拉取 ETF 份额/规模失败 (trade_date={trade_date}): {e}")
            raise

        total = len(records)
        logger.info(f"拉取到 {total} 条 ETF 份额/规模 (trade_date={trade_date})")
        await self._update_progress(0, total, f"共 {total} 条 ETF 待处理")

        nav_miss_count = 0
        close_miss_count = 0
        for i, record in enumerate(records, 1):
            try:
                ts_code = record.get("ts_code")
                if not ts_code:
                    skipped += 1
                    continue

                total_share = self._to_decimal(record.get("total_share"))
                if total_share is None:
                    skipped += 1
                    continue

                total_size = self._to_decimal(record.get("total_size"))
                nav = self._to_decimal(record.get("nav"))
                close = self._to_decimal(record.get("close"))

                # total_size 缺失时用 total_share(万份) × nav(元) 估算规模(万元)兜底。
                # 实测 etf_share_size 在非主更新日可能不返回 total_size（全 NULL），
                # 用份额×净值近似保证规模列总有值（与 total_size 口径一致：万元）。
                if total_size is None and nav is not None:
                    total_size = (total_share * nav).quantize(Decimal("0.0001"))

                if nav is None:
                    nav_miss_count += 1
                if close is None:
                    close_miss_count += 1

                # 2. 查前一日份额与收盘价
                prev_share, prev_close = await self._get_prev_share_and_close(
                    ts_code, target_date
                )

                # 3. 计算 share_change / net_inflow / change_percent
                if prev_share is not None:
                    share_change = total_share - prev_share
                    if nav is not None:
                        # net_inflow = share_change(万份) × nav / 10000（亿元）
                        net_inflow = (share_change * nav / Decimal("10000"))
                        net_inflow = net_inflow.quantize(Decimal("0.0001"))
                    else:
                        net_inflow = None
                else:
                    # 首日（无前日数据）share_change / net_inflow 为 null
                    share_change = None
                    net_inflow = None

                # change_percent = (当日close − 前日close) / 前日close × 100
                if close is not None and prev_close is not None and prev_close != 0:
                    change_percent = (
                        (close - prev_close) / prev_close * Decimal("100")
                    )
                    change_percent = change_percent.quantize(Decimal("0.0001"))
                else:
                    change_percent = None

                # 4. upsert etf_daily（on_conflict_do_update 覆盖）
                stmt = pg_insert(EtfDaily).values(
                    trade_date=target_date,
                    ts_code=ts_code,
                    total_share=total_share,
                    total_size=total_size,
                    nav=nav,
                    close=close,
                    share_change=share_change,
                    net_inflow=net_inflow,
                    change_percent=change_percent,
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_etf_daily_date_code",
                    set_={
                        "total_share": stmt.excluded.total_share,
                        "total_size": stmt.excluded.total_size,
                        "nav": stmt.excluded.nav,
                        "close": stmt.excluded.close,
                        "share_change": stmt.excluded.share_change,
                        "net_inflow": stmt.excluded.net_inflow,
                        "change_percent": stmt.excluded.change_percent,
                    },
                )
                await self.session.execute(stmt)
                processed += 1
                added += 1  # upsert 无法精确区分 insert/update，统计为 added

            except Exception as e:
                skipped += 1
                logger.warning(f"处理 ETF 份额记录失败 ({record.get('ts_code')}): {e}")
                continue

            if i % 200 == 0 or i == total:
                await self._update_progress(
                    i, total,
                    f"已处理 {i}/{total} 条 ETF (净值缺失 {nav_miss_count}, 收盘价缺失 {close_miss_count})"
                )

        await self.session.commit()

        logger.info(
            f"[ETF] 当日份额/规模采集完成 (trade_date={trade_date}): "
            f"处理 {processed}, 跳过 {skipped}, 净值缺失 {nav_miss_count}, 收盘价缺失 {close_miss_count}"
        )
        await self._update_progress(
            total, total,
            f"ETF 当日采集完成: 处理 {processed}, 跳过 {skipped}, 净值缺失 {nav_miss_count}"
        )

        return {
            "processed": processed,
            "added": added,
            "updated": updated,
            "skipped": skipped,
        }

    # ------------------------------------------------------------------
    # backfill_etf_history：按日期范围回填历史（复用 sync_etf_daily 同口径）
    # ------------------------------------------------------------------

    async def backfill_etf_history(self, start_date: str, end_date: str) -> dict:
        """按日期范围回填历史 ETF 数据（ADR-5：复用 sync_etf_daily 同口径）。

        仿 ``init_historical_data_by_date_range``（data_init.py:851）范式：
        日期校验 + 10 年上限 + progress/cancel。

        流程：
        1. 日期校验：start <= end，范围上限 10 年（3650 天）。
        2. 先调 ``self.sync_etf_basic()`` 确保 ETF 基础信息最新（避免回填时缺 etf_basic）。
        3. 用 TradingCalendar 筛选范围内交易日，**按日期升序**逐日循环。
        4. 对每个交易日调用与当日采集**完全相同**的 ``self.sync_etf_daily(trade_date)``
           （含前日份额查询、share_change、net_inflow 计算）。

           **关键：按日期升序保证 share_change 的前日依赖就地满足**——上一日已写入，
           当日 sync_etf_daily 查前日份额（``trade_date < 给定日的最大 trade_date``）
           能命中上一日记录。
        5. 每日处理完调 progress_callback（progress/total），支持 cancel_check。
        6. 某日采集失败计入 failed_days，继续下一日（不中断整体）。

        Args:
            start_date: 起始日期，'YYYY-MM-DD' 或 'YYYYMMDD'。
            end_date: 结束日期，'YYYY-MM-DD' 或 'YYYYMMDD'。

        Returns:
            {"total_days": int, "processed_days": int, "failed_days": int}
        """
        if self.session is None:
            raise RuntimeError("EtfDataInitService.session 未设置")

        # 1. 日期校验（仿 init_historical_data_by_date_range）
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)
        if start is None or end is None:
            raise ValueError(f"无效的日期范围: start_date={start_date}, end_date={end_date}")
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")

        # 范围上限 10 年（3650 天）
        if (end - start).days > 3650:
            raise ValueError("日期范围不能超过 10 年")

        await self._update_progress(0, 1, "正在同步 ETF 基础信息...")
        # 2. 先同步基础信息，确保回填时 etf_basic 已就绪（ETF 清单 + 指数归类）
        try:
            await self.sync_etf_basic()
        except Exception as e:
            logger.error(f"[ETF] 回填前置 sync_etf_basic 失败，继续尝试逐日回填: {e}")

        # 3. 用交易日历筛选范围内交易日（按日期升序）
        calendar = TradingCalendar()
        trading_days: List[date] = await calendar.get_trading_days_between(start, end)

        total_days = len(trading_days)
        processed_days = 0
        failed_days = 0

        logger.info(
            f"[ETF] 开始历史回填: {start} ~ {end}, 交易日 {total_days} 天"
        )
        await self._update_progress(
            0, max(total_days, 1),
            f"历史回填范围 {start} ~ {end}，共 {total_days} 个交易日"
        )

        if total_days == 0:
            logger.info(f"[ETF] 回填范围 {start} ~ {end} 内无交易日，跳过")
            return {
                "total_days": total_days,
                "processed_days": processed_days,
                "failed_days": failed_days,
            }

        # 4. 按日期升序逐日调 sync_etf_daily（同口径，前日依赖就地满足）
        for i, trade_date in enumerate(trading_days, 1):
            await self._check_cancelled()
            # sync_etf_daily 内部 _parse_trade_date 兼容 YYYYMMDD / YYYY-MM-DD
            trade_date_str = trade_date.isoformat()
            try:
                await self.sync_etf_daily(trade_date_str)
                processed_days += 1
            except asyncio.CancelledError:
                # 取消：已处理日保留，向上抛出
                logger.warning(f"[ETF] 历史回填在 {trade_date_str} 被取消")
                raise
            except Exception as e:
                failed_days += 1
                logger.warning(
                    f"[ETF] 历史回填 {trade_date_str} 失败，跳过该日: {e}"
                )

            await self._update_progress(
                i, total_days,
                f"历史回填进度 {i}/{total_days}（{trade_date_str}）"
            )

        logger.info(
            f"[ETF] 历史回填完成: 总计 {total_days}, 成功 {processed_days}, "
            f"失败 {failed_days}"
        )
        await self._update_progress(
            total_days, total_days,
            f"历史回填完成: 成功 {processed_days}, 失败 {failed_days}"
        )

        return {
            "total_days": total_days,
            "processed_days": processed_days,
            "failed_days": failed_days,
        }

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    async def _get_prev_share_and_close(
        self, ts_code: str, target_date: date
    ) -> tuple[Optional[Decimal], Optional[Decimal]]:
        """查询某 ts_code 在 target_date 之前最近一日的份额与收盘价。

        子查询语义：SELECT total_share, close FROM etf_daily
                   WHERE ts_code=? AND trade_date<? ORDER BY trade_date DESC LIMIT 1

        Returns:
            (前一日份额, 前一日收盘价)，首日无前日数据返回 (None, None)
        """
        stmt = (
            select(EtfDaily.total_share, EtfDaily.close)
            .where(
                EtfDaily.ts_code == ts_code,
                EtfDaily.trade_date < target_date,
            )
            .order_by(EtfDaily.trade_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.first()
        if row is None:
            return None, None
        return row[0], row[1]

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
        d = EtfDataInitService._parse_date(value)
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
