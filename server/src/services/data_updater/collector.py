"""
数据采集协调器

统一协调所有数据采集任务。
"""

import logging
import uuid
from datetime import datetime, date
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
from src.services.data_acquisition import DataSourceFactory
from src.services.trading_calendar import TradingCalendar
from src.services.cache.cache_manager import get_cache_manager

try:
    from src.services.calculator_updater.orchestrator import CalculationOrchestrator
except Exception:  # pragma: no cover - compatibility fallback
    class CalculationOrchestrator:  # type: ignore
        async def run_all_calculations(self):
            return 0

logger = logging.getLogger(__name__)


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
        self._trading_calendar = TradingCalendar()
        self._data_source = DataSourceFactory.create()

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
            'calculations_performed': 0,
            'cache_cleared': 0,
            'errors': []
        }

        try:
            # 1. 检查交易日
            is_trading, reason = await self._trading_calendar.is_trading_day()
            if not is_trading:
                logger.info(f"[数据更新] 今天不是交易日，跳过更新: {reason}")
                log_entry.status = 'skipped'
                log_entry.error_message = reason
                log_entry.end_time = datetime.now()
                results['message'] = f'非交易日，跳过更新: {reason}'
                await self._save_update_log(log_entry)
                return results

            # 2. 采集板块数据
            results['sectors_updated'] = await self._update_sectors()

            # 3. 采集股票数据
            results['stocks_updated'] = await self._update_stocks()

            # 4. 采集行情数据（增量）
            results['market_data_updated'] = await self._update_market_data()

            # 5. 执行计算
            results['calculations_performed'] = await self._run_calculations()

            # 6. 清除缓存
            results['cache_cleared'] = await self._clear_cache()

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

    async def _is_trading_day(self, check_date: Optional[date] = None) -> tuple[bool, Optional[str]]:
        """检查是否为交易日"""
        return await self._trading_calendar.is_trading_day(check_date)

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
        """更新股票数据到数据库"""
        logger.info("[数据更新] 开始更新股票数据")

        data_source = self._data_source
        stocks = data_source.get_stock_list()

        # 需要增量同步的基础字段列表
        _basic_fields = [
            "name", "ts_code", "area", "industry", "fullname", "enname",
            "cnspell", "market", "exchange", "curr_type", "list_status",
            "list_date", "delist_date", "is_hs", "act_name", "act_ent_type",
        ]

        async with get_session() as session:
            result = await session.execute(select(Stock))
            existing_map = {s.symbol: s for s in result.scalars().all()}

            count = 0
            for stock_info in stocks:
                if stock_info.symbol in existing_map:
                    existing = existing_map[stock_info.symbol]
                    changed = False
                    for field in _basic_fields:
                        new_val = getattr(stock_info, field, None)
                        old_val = getattr(existing, field, None)
                        if new_val != old_val:
                            setattr(existing, field, new_val)
                            changed = True
                    if changed:
                        count += 1
                else:
                    session.add(Stock(
                        symbol=stock_info.symbol,
                        name=stock_info.name,
                        ts_code=stock_info.ts_code,
                        area=stock_info.area,
                        industry=stock_info.industry,
                        fullname=stock_info.fullname,
                        enname=stock_info.enname,
                        cnspell=stock_info.cnspell,
                        market=stock_info.market,
                        exchange=stock_info.exchange,
                        curr_type=stock_info.curr_type,
                        list_status=stock_info.list_status,
                        list_date=stock_info.list_date,
                        delist_date=stock_info.delist_date,
                        is_hs=stock_info.is_hs,
                        act_name=stock_info.act_name,
                        act_ent_type=stock_info.act_ent_type,
                    ))
                    count += 1

            await session.commit()

        logger.info(f"[数据更新] 股票数据更新完成: {count} 只股票")
        return count

    async def _update_market_data(self) -> int:
        """更新行情数据到数据库"""
        logger.info("[数据更新] 开始更新行情数据")

        data_source = self._data_source
        today = datetime.now().date()
        total_count = 0

        async with get_session() as session:
            # 构建板块映射 {code: (id, name, type)}
            sector_result = await session.execute(select(Sector))
            sector_map = {s.code: (s.id, s.name, s.type) for s in sector_result.scalars().all()}

            # 构建股票映射 {symbol: id}
            stock_result = await session.execute(select(Stock))
            stock_map = {s.symbol: s.id for s in stock_result.scalars().all()}

            # 写入板块行情
            for code, (entity_id, name, stype) in sector_map.items():
                try:
                    quotes = data_source.get_sector_daily_data(
                        sector_name=name,
                        sector_type=stype,
                        start_date=today,
                        end_date=today,
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
            symbols = list(stock_map.items())
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

    async def _run_calculations(self) -> int:
        """执行强度计算"""
        logger.info("[数据更新] 开始执行强度计算")

        try:
            orchestrator = CalculationOrchestrator()
            count = await orchestrator.run_all_calculations()
            logger.info(f"[数据更新] 强度计算完成: {count} 个实体")
            return count
        except Exception as e:
            logger.error(f"[数据更新] 强度计算失败: {e}")
            return 0

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
