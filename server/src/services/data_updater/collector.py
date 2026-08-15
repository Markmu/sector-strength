"""
数据采集协调器

统一协调所有数据采集任务。
"""

import logging
import uuid
from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import AsyncSessionLocal
from src.models.update_log import DataUpdateLog
from src.models.sector import Sector
from src.models.stock import Stock
from src.models.daily_market_data import DailyMarketData
from src.models.stock_daily_market_data import StockDailyMarketData
from src.models.sector_fund_flow import SectorFundFlow
from src.services.data_acquisition import DataSourceFactory
from src.services.data_acquisition.akshare_fund_flow import AkshareFundFlowFetcher
from src.services.trading_calendar import TradingCalendar
from src.services.trading_calendar_repository import TradingCalendarRepository
from src.services.market_metrics_service import (
    MarketMetricsService,
    build_lifecycle_snapshot,
)
from src.services.cache.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

# A 股交易时区（同花顺即时资金流口径即北京交易日）。collector 用此时区确定
# trade_date/sample_time，避免容器 UTC 环境下凌晨采集把"上一交易日"数据标成当天。
BJ_TZ = ZoneInfo("Asia/Shanghai")

# A 股连续竞价时段（分钟数，含两端）：上午 09:30-11:30、下午 13:00-15:00
_MORNING_START = 9 * 60 + 30
_MORNING_END = 11 * 60 + 30
_AFTERNOON_START = 13 * 60
_AFTERNOON_END = 15 * 60


def _is_intraday_minutes(hour: int, minute: int) -> bool:
    """当前北京时间是否落在 A 股连续竞价时段内。"""
    hm = hour * 60 + minute
    return _MORNING_START <= hm <= _MORNING_END or _AFTERNOON_START <= hm <= _AFTERNOON_END


@asynccontextmanager
async def get_session():
    """Compatibility session context for tests that patch this symbol."""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


class DataCollector:

    def __init__(self):
        self._data_source = DataSourceFactory.create()
        # plan-05：lifecycle 快照与当日，由 run_daily_update 在守卫/preflight 后填充，
        # 供 _update_market_data（当日在市过滤）与 _update_market_metrics 复用。
        self._lifecycle_snapshot = None
        self._today = None

    async def run_daily_update(self) -> Dict[str, Any]:
        """
        执行每日数据更新

        Returns:
            更新结果统计
        """
        log_entry = DataUpdateLog(
            id=str(uuid.uuid4()),
            start_time=datetime.now(),
            status='running'
        )

        results = {
            'success': True,
            'message': '更新完成',
            'sectors_updated': 0,
            'stocks_updated': 0,
            'market_data_updated': 0,
            'market_metrics_updated': 0,
            # 强度/均线计算由任务体系（task_handlers calculate_*）执行，日更链
            # 不再调用旧的随机数脚手架；字段保留以兼容 DataUpdateLog schema
            'calculations_performed': 0,
            'cache_cleared': 0,
            'etf_daily_updated': 0,
            'index_daily_updated': 0,
            'errors': []
        }

        # plan-05：lifecycle 快照由 _update_stocks 构建，供 _update_market_data /
        # _update_market_metrics 复用（自动日更只构建一次，不读写 AsyncTask）。
        self._lifecycle_snapshot = None

        try:
            # 1. 交易日检查（plan-05：先 refresh_range(today,today) 再以本批记录守卫）。
            # 本次响应校验失败 → 日更失败，不用旧行冒充、不按工作日猜测；旧日历保留
            # 供首页只读降级（架构 §6.3 / AC-09）。
            today = datetime.now(BJ_TZ).date()
            async with get_session() as session:
                cal_repo = TradingCalendarRepository(session)
                # refresh_range 失败（Provider 异常或响应不完整）直接抛 → 日更失败。
                open_count, _closed_count = await cal_repo.refresh_range(today, today)
            if open_count == 0:
                # 本批记录表明今日休市 → skipped（AC-09，不调后续 Provider）。
                logger.info("[数据更新] 今日非交易日，跳过更新: %s", today)
                log_entry.status = 'skipped'
                log_entry.error_message = f"非交易日: {today}"
                log_entry.end_time = datetime.now()
                results['message'] = f'非交易日，跳过更新: {today}'
                await self._save_update_log(log_entry)
                return results
            self._today = today

            # 2. 采集板块数据
            results['sectors_updated'] = await self._update_sectors()

            # 3. 采集股票数据
            results['stocks_updated'] = await self._update_stocks()

            # 4. 采集行情数据（增量）
            results['market_data_updated'] = await self._update_market_data()

            # 5. 市场量价指标汇总（plan-05：在 _update_market_data 成功后调用）。
            # 自动日更不读写 AsyncTask、不传 fence（task_context=None）；失败写
            # results.errors 与 market_metrics_updated=0，不阻断指数/ETF 等后续步骤。
            try:
                results['market_metrics_updated'] = await self._update_market_metrics()
            except Exception as e:
                logger.error(f"[数据更新] 市场量价指标汇总失败: {e}")
                results['errors'].append(f"market_metrics: {e}")
                results['market_metrics_updated'] = 0

            # 6. 清除缓存
            results['cache_cleared'] = await self._clear_cache()

            # 7. 采集板块资金流即时快照（行业 + 概念）
            try:
                await self._update_sector_fund_flow()
            except Exception as e:
                # 资金流采集失败不影响主更新流程，仅记录
                logger.error(f"[数据更新] 板块资金流采集失败: {e}")
                results['errors'].append(f"sector_fund_flow: {e}")

            # 8. ETF 当日份额/净值快照（第 14 期）：先同步基础信息归类，再采集当日份额
            try:
                results['etf_daily_updated'] = await self._update_etf_daily()
            except Exception as e:
                # ETF 采集失败不影响主更新流程，仅记录
                logger.error(f"[数据更新] ETF 当日采集失败: {e}")
                results['errors'].append(f"etf_daily: {e}")

            # 9. 关键指数当日行情/估值/权重采集（第 15 期）：调用 IndexDataInitService.sync_index_daily
            try:
                results['index_daily_updated'] = await self._update_index_daily()
            except Exception as e:
                # 指数采集失败不影响主更新流程，仅记录
                logger.error(f"[数据更新] 指数当日采集失败: {e}")
                results['errors'].append(f"index_daily: {e}")

            # 更新日志状态为完成
            log_entry.status = 'completed'
            log_entry.end_time = datetime.now()
            log_entry.sectors_updated = results['sectors_updated']
            log_entry.stocks_updated = results['stocks_updated']
            log_entry.market_data_updated = results['market_data_updated']
            log_entry.calculations_performed = results['calculations_performed']

        except Exception as e:
            logger.error(f"[数据更新] 更新失败: {e}")
            results['errors'].append(str(e))
            results['success'] = False
            results['message'] = str(e)
            log_entry.status = 'failed'
            log_entry.error_message = str(e)
            log_entry.end_time = datetime.now()

        finally:
            await self._save_update_log(log_entry)

        return results

    async def _update_sectors(self) -> int:
        """更新板块数据到数据库"""
        logger.info("[数据更新] 开始更新板块数据")

        data_source = self._data_source
        sectors = data_source.get_sector_list()

        async with get_session() as session:
            result = await session.execute(select(Sector))
            existing_map = {s.code: s for s in result.scalars().all()}

            count = 0
            for sector_info in sectors:
                if sector_info.code in existing_map:
                    if existing_map[sector_info.code].name != sector_info.name:
                        existing_map[sector_info.code].name = sector_info.name
                        count += 1
                else:
                    session.add(Sector(
                        code=sector_info.code,
                        name=sector_info.name,
                        type=sector_info.type,
                    ))
                    count += 1

            await session.commit()

        logger.info(f"[数据更新] 板块数据更新完成: {count} 个板块")
        return count

    async def _update_stocks(self) -> int:
        """更新股票生命周期数据（plan-05 升级）。

        改调 ``DataInitService.init_stocks_lifecycle``（一次 L/D/P/G 联合 preflight +
        upsert/set-diff），并构建不可变 ``LifecycleSnapshot`` 存于 run 级变量
        ``self._lifecycle_snapshot``，供 ``_update_market_data``（当日在市过滤）与
        ``_update_market_metrics`` 复用（架构 §6.3.2）。
        """
        logger.info("[数据更新] 开始更新股票生命周期数据")
        async with get_session() as session:
            snapshot = await build_lifecycle_snapshot(session)
        self._lifecycle_snapshot = snapshot
        count = len(snapshot.records)
        logger.info("[数据更新] 股票生命周期更新完成: %d 只", count)
        return count

    async def _update_market_data(self) -> int:
        """更新行情数据到数据库"""
        logger.info("[数据更新] 开始更新行情数据")

        data_source = self._data_source
        # plan-05：与日更守卫同口径取北京时区当日（run_daily_update 已设 self._today）。
        today = getattr(self, "_today", None) or datetime.now(BJ_TZ).date()
        total_count = 0

        async with get_session() as session:
            # 构建板块映射 {code: (id, name, type)}
            sector_result = await session.execute(select(Sector))
            sector_map = {
                s.code: (s.id, s.name, s.type, s.code)
                for s in sector_result.scalars().all()
            }

            # 构建股票映射 {symbol: id}
            stock_result = await session.execute(select(Stock))
            stock_map = {s.symbol: s.id for s in stock_result.scalars().all()}

            # 写入板块行情（按 type 分流：同花顺按名称反查，申万按 code 取数）
            for code, (entity_id, name, stype, sector_code) in sector_map.items():
                try:
                    quotes = data_source.get_sector_daily_data(
                        sector_name=name,
                        sector_type=stype,
                        start_date=today,
                        end_date=today,
                        sector_code=sector_code,
                    )
                    if quotes:
                        for q in quotes:
                            stmt = pg_insert(DailyMarketData).values(
                                entity_type='sector',
                                entity_id=entity_id,
                                symbol=code,
                                date=q.trade_date,
                                open=q.open,
                                high=q.high,
                                low=q.low,
                                close=q.close,
                                volume=q.volume,
                                turnover=q.turnover,
                            )
                            stmt = stmt.on_conflict_do_nothing(
                                constraint='uq_daily_market_data_entity_date'
                            )
                            await session.execute(stmt)
                        total_count += len(quotes)
                except Exception as e:
                    logger.warning(f"[数据更新] 获取板块 {name} 行情失败: {e}")

            await session.commit()

            # 写入股票行情（写入股票独立表 stock_daily_market_data）
            # plan-05：仅遍历 snapshot 当日在市集合（不遍历历史退市全表，§6.3.2）。
            in_market_symbols = None
            if self._lifecycle_snapshot is not None:
                in_market_ts_codes = self._lifecycle_snapshot.expected_codes(today)
                in_market_symbols = {
                    tc.split(".", 1)[0] for tc in in_market_ts_codes
                }
            symbols = list(stock_map.items())
            if in_market_symbols is not None:
                symbols = [
                    (sym, sid) for sym, sid in symbols if sym in in_market_symbols
                ]
            failed_count = 0
            batch_size = 50
            stock_inserted_count = 0

            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                for symbol, entity_id in batch:
                    try:
                        quotes = data_source.get_daily_data(
                            symbol=symbol,
                            start_date=today,
                            end_date=today,
                        )
                        if quotes:
                            for q in quotes:
                                change_val = None
                                change_pct = None
                                if q.close and q.open:
                                    change_val = q.close - q.open
                                    if q.open != 0:
                                        change_pct = change_val / q.open * 100

                                stmt = pg_insert(StockDailyMarketData).values(
                                    stock_id=entity_id,
                                    symbol=symbol,
                                    date=q.trade_date,
                                    open=q.open,
                                    high=q.high,
                                    low=q.low,
                                    close=q.close,
                                    volume=q.volume,
                                    turnover=q.turnover,
                                    change=change_val,
                                    change_percent=change_pct,
                                )
                                stmt = stmt.on_conflict_do_nothing(
                                    constraint='uq_stock_daily_market_data_stock_date'
                                )
                                await session.execute(stmt)
                            total_count += len(quotes)
                            stock_inserted_count += len(quotes)
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"[数据更新] 获取 {symbol} 行情失败: {e}")

                await session.commit()

            # 可观测性日志（架构 §8.5）：确认股票行情写入新表，便于上线后核对 AC-01
            logger.info(
                "stock_market_data_inserted",
                extra={"table": "stock_daily_market_data", "count": stock_inserted_count},
            )

            if failed_count == len(symbols) and len(symbols) > 0:
                raise RuntimeError(f"所有 {len(symbols)} 只股票行情拉取失败")

        logger.info(f"[数据更新] 行情数据更新完成: {total_count} 条记录")
        return total_count

    async def _update_market_metrics(self) -> int:
        """市场量价指标当日汇总（plan-05，架构 §6.3.3-4）。

        在 ``_update_market_data`` 成功后调用，复用 ``_update_stocks`` 构建的
        ``LifecycleSnapshot``：``MarketMetricsService.sync_date(today, snapshot,
        task_context=None, ...)``。自动日更**不读写 AsyncTask、不传 fence**
        （``task_context=None`` → 直接原子 upsert，不经 ``lock_and_validate``）。

        休市已被 ``run_daily_update`` 步骤 1 守卫拦截，此处不再重复判定（AC-09）。
        失败时由调用方写 ``results.errors`` 与 ``market_metrics_updated=0``，不覆盖
        最近成功结果、不阻断指数/ETF 等后续步骤。

        Returns:
            1 表示当日指标已成功写入；抛异常表示失败（由调用方捕获）。
        """
        from src.db import database as db_module

        today = getattr(self, "_today", None) or datetime.now(BJ_TZ).date()
        if self._lifecycle_snapshot is None:
            raise RuntimeError(
                "市场量价指标汇总缺少生命周期快照（_update_stocks 未执行）"
            )

        logger.info("[数据更新] 开始汇总市场量价指标 (trade_date=%s)", today)
        async with db_module.AsyncSessionLocal() as session:
            service = MarketMetricsService(session)
            status = await service.sync_date(
                today, self._lifecycle_snapshot, task_context=None
            )
        if status != "success":
            # sync_date 返回 skipped（理论上已被守卫拦截）或异常；非 success 视为未写入。
            logger.warning(
                "[数据更新] 市场量价指标汇总未成功 trade_date=%s status=%s",
                today,
                status,
            )
            return 0
        logger.info("[数据更新] 市场量价指标汇总完成 (trade_date=%s)", today)
        return 1

    async def _update_sector_fund_flow(self) -> int:
        """采集同花顺即时板块资金流（行业 + 概念）并落库。

        盘中每分钟全量采样；同一采样分钟重复触发通过
        on_conflict_do_update 覆盖最新值（命中 uq_sector_fund_flow_sample）。

        守卫（北京时区，覆盖调度器与手动触发两条路径）：
        - 非盘中时段（9:30-11:30 / 13:00-15:00 之外）：akshare"即时"接口返回的是
          上一交易日收盘快照，写库会造成 trade_date/sample_time 错位污染曲线 → 跳过。
        - 非交易日（节假日）：同上，跳过；交易日历判断失败时保守跳过。

        Returns:
            写入/更新的记录条数（守卫命中时为 0）
        """
        # 用北京时区确定交易日与采样时刻，避免容器 UTC 下凌晨采集错位
        now = datetime.now(BJ_TZ)

        # 守卫1：盘中时段（非盘中直接返回，不调 akshare，避免无效请求/风控）
        if not _is_intraday_minutes(now.hour, now.minute):
            logger.info(
                "[数据更新] 板块资金流采样跳过：非盘中时段（北京 %02d:%02d）",
                now.hour,
                now.minute,
            )
            return 0

        trade_date = now.date()

        # 守卫2：交易日（节假日 akshare 即时返回上一交易日快照，写库会错位）
        calendar = TradingCalendar()
        try:
            is_trading, reason = await calendar.is_trading_day(trade_date)
        except Exception as e:
            # 判断失败保守跳过（与 job_manager 一致），宁可漏采不错采
            logger.warning("[数据更新] 板块资金流采样跳过：交易日判断失败 %s", e)
            return 0
        if not is_trading:
            logger.info(
                "[数据更新] 板块资金流采样跳过：非交易日（%s，%s）",
                trade_date,
                reason or "节假日",
            )
            return 0

        logger.info("[数据更新] 开始采集板块资金流即时快照（北京 %s）", now)

        fetcher = AkshareFundFlowFetcher()
        # 精度到分钟：秒/微秒置零，保证同分钟重采命中唯一约束而非新增。
        # sample_time 列为 naive DateTime（TIMESTAMP WITHOUT TIME ZONE），DB 实际存
        # 北京 wall-clock；aware datetime 写入会触发 asyncpg naive/aware 比较错误，
        # 故剥离 tzinfo 转为 naive（值仍是北京 wall-clock，口径与补点逻辑一致）。
        sample_time = now.replace(second=0, microsecond=0, tzinfo=None)

        total_count = 0
        async with get_session() as session:
            for sector_type in ("industry", "concept"):
                try:
                    items = fetcher.fetch(sector_type)
                except Exception as e:
                    # 单类板块失败不影响另一类：记录日志并跳过
                    logger.warning(
                        f"[数据更新] 采集 {sector_type} 资金流失败: {e}"
                    )
                    continue

                for item in items:
                    try:
                        stmt = pg_insert(SectorFundFlow).values(
                            trade_date=trade_date,
                            sample_time=sample_time,
                            sector_type=sector_type,
                            **item.model_dump(),
                        )
                        stmt = stmt.on_conflict_do_update(
                            constraint='uq_sector_fund_flow_sample',
                            set_={
                                'sector_index': stmt.excluded.sector_index,
                                'change_percent': stmt.excluded.change_percent,
                                'inflow': stmt.excluded.inflow,
                                'outflow': stmt.excluded.outflow,
                                'net_inflow': stmt.excluded.net_inflow,
                                'company_count': stmt.excluded.company_count,
                                'leading_stock': stmt.excluded.leading_stock,
                                'leading_stock_change': stmt.excluded.leading_stock_change,
                                'current_price': stmt.excluded.current_price,
                            },
                        )
                        await session.execute(stmt)
                        total_count += 1
                    except Exception as e:
                        logger.warning(
                            f"[数据更新] 写入板块资金流失败 "
                            f"({sector_type}/{item.sector_name}): {e}"
                        )

                await session.commit()

        logger.info(
            f"[数据更新] 板块资金流采集完成: {total_count} 条记录 "
            f"(trade_date={trade_date}, sample_time={sample_time})"
        )
        return total_count

    async def _update_etf_daily(self) -> int:
        """ETF 当日份额/净值快照采集（第 14 期，架构 §6.1 当日采集链路）。

        先同步 ETF 基础信息（归类），再采集当日份额/净值并计算
        share_change / net_inflow 落库。当日由 BJ_TZ 取。

        复用 EtfDataInitService 的采集能力，collector 仅负责编排与 session 注入
        （仿 _update_sector_fund_flow 的 session 使用范式）。

        Returns:
            当日处理的 ETF 份额记录条数
        """
        from src.services.data_init_etf import EtfDataInitService
        # 调用时从 db 模块取会话工厂，确保测试期 conftest 对
        # ``db_module.AsyncSessionLocal`` 的替换能生效（与 get_session() 不同，
        # 后者持有了模块加载时的 import 绑定，不会被运行时替换覆盖）。
        from src.db import database as db_module

        today = datetime.now(BJ_TZ).date()
        trade_date = today.strftime("%Y%m%d")

        logger.info(f"[数据更新] 开始采集 ETF 当日份额 (trade_date={trade_date})")

        async with db_module.AsyncSessionLocal() as session:
            svc = EtfDataInitService(session)
            try:
                # 先同步基础信息（归类），失败不阻断当日份额采集
                try:
                    await svc.sync_etf_basic()
                except Exception as e:
                    logger.warning(f"[数据更新] ETF 基础信息同步失败，继续当日份额采集: {e}")

                result = await svc.sync_etf_daily(trade_date)
            except Exception as e:
                logger.error(f"[数据更新] ETF 当日份额采集失败: {e}")
                raise

        processed = result.get("processed", 0)
        skipped = result.get("skipped", 0)
        logger.info(
            f"[数据更新] ETF 当日份额采集完成 (trade_date={trade_date}): "
            f"处理 {processed}, 跳过 {skipped}"
        )
        return processed

    async def _update_index_daily(self) -> int:
        """关键指数当日行情/估值/权重采集（第 15 期，架构 §6.1 当日采集链路）。

        复用 IndexDataInitService.sync_index_daily 的采集能力，collector 仅负责
        编排与 session 注入（仿 _update_etf_daily 的 session 使用范式）。

        Returns:
            当日处理的指数日线记录条数（daily_records）
        """
        from src.services.data_init_index import IndexDataInitService
        # 调用时从 db 模块取会话工厂，确保测试期 conftest 对
        # ``db_module.AsyncSessionLocal`` 的替换能生效（与 get_session() 不同，
        # 后者持有了模块加载时的 import 绑定，不会被运行时替换覆盖）。
        from src.db import database as db_module

        today = datetime.now(BJ_TZ).date()
        trade_date = today.strftime("%Y%m%d")

        logger.info(f"[数据更新] 开始采集指数当日行情 (trade_date={trade_date})")

        async with db_module.AsyncSessionLocal() as session:
            service = IndexDataInitService()
            service.set_session(session)
            try:
                result = await service.sync_index_daily(trade_date)
            except Exception as e:
                logger.error(f"[数据更新] 指数当日采集失败: {e}")
                raise

        daily_records = result.get("daily_records", 0)
        logger.info(
            f"[数据更新] 指数当日采集完成 (trade_date={trade_date}): "
            f"daily {daily_records}"
        )
        return daily_records

    async def _clear_cache(self):
        """清除缓存"""
        logger.info("[数据更新] 清除缓存")

        try:
            cache = get_cache_manager()
            if hasattr(cache, "clear_all"):
                total = await cache.clear_all()
            else:
                patterns = ["sectors:%", "stocks:%", "strength:%", "heatmap:%"]
                total = 0
                for pattern in patterns:
                    count = await cache.clear_pattern(pattern)
                    total += count

            logger.info(f"[数据更新] 清除了 {total} 条缓存")
            return total
        except Exception as e:
            logger.error(f"[数据更新] 清除缓存失败: {e}")
            return 0

    async def _save_update_log(self, log_entry: DataUpdateLog):
        """保存更新日志到数据库"""
        async with get_session() as session:
            if isinstance(log_entry, dict):
                log_entry = DataUpdateLog(
                    id=str(uuid.uuid4()),
                    start_time=log_entry.get("started_at", datetime.now()),
                    end_time=log_entry.get("completed_at"),
                    status="completed" if log_entry.get("success", True) else "failed",
                    sectors_updated=log_entry.get("sectors_updated", 0),
                    stocks_updated=log_entry.get("stocks_updated", 0),
                    market_data_updated=log_entry.get("market_data_updated", 0),
                    calculations_performed=log_entry.get("entities_calculated", 0),
                    error_message=log_entry.get("error"),
                )
            session.add(log_entry)
            await session.commit()

    async def get_latest_update_status(self) -> Optional[Dict[str, Any]]:
        """获取最新更新状态"""
        async with get_session() as session:
            stmt = select(DataUpdateLog).order_by(
                DataUpdateLog.start_time.desc()
            ).limit(1)
            if hasattr(session, "scalar"):
                latest_log = await session.scalar(stmt)
            else:
                result = await session.execute(stmt)
                latest_log = result.scalar_one_or_none()

            if not latest_log:
                return None

            start_time = getattr(latest_log, "start_time", None) or getattr(latest_log, "started_at", None)
            status = getattr(latest_log, "status", None)
            if not isinstance(status, str):
                status = "completed" if getattr(latest_log, "success", False) else "failed"

            return {
                'last_update': start_time.isoformat() if start_time else None,
                'status': status,
                'sectors_updated': getattr(latest_log, "sectors_updated", 0),
                'stocks_updated': getattr(latest_log, "stocks_updated", 0),
                'market_data_updated': getattr(latest_log, "market_data_updated", 0),
                'calculations_performed': getattr(latest_log, "calculations_performed", 0),
                'error': getattr(latest_log, "error_message", None),
                'success': status == 'completed',
            }

    async def get_update_history(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取更新历史"""
        async with get_session() as session:
            offset = (page - 1) * page_size
            stmt = (
                select(DataUpdateLog)
                .order_by(DataUpdateLog.start_time.desc())
                .offset(offset)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            logs = result.scalars().all()

            count_stmt = select(func.count(DataUpdateLog.id))
            total_result = await session.execute(count_stmt)
            total = total_result.scalar()

            return {
                'items': [
                    {
                        'id': log.id,
                        'start_time': log.start_time.isoformat(),
                        'end_time': log.end_time.isoformat() if log.end_time else None,
                        'status': log.status,
                        'sectors_updated': log.sectors_updated,
                        'stocks_updated': log.stocks_updated,
                        'market_data_updated': log.market_data_updated,
                        'calculations_performed': log.calculations_performed,
                        'error': log.error_message,
                    }
                    for log in logs
                ],
                'total': total or 0,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size if total else 0,
            }
