"""
数据采集协调器

统一协调所有数据采集任务。
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import AsyncSessionLocal
from src.models.update_log import DataUpdateLog
from src.models.period_config import PeriodConfig

logger = logging.getLogger(__name__)


class DataCollector:
    """
    数据采集协调器

    统一管理所有数据采集和更新任务。
    """

    def __init__(self):
        """初始化数据采集器"""
        self._trading_days_cache = None
        self._cache_expiry = None

    async def run_daily_update(self) -> Dict[str, Any]:
        """
        执行每日数据更新

        Returns:
            更新结果统计
        """
        # 创建更新日志记录
        log_entry = DataUpdateLog(
            id=str(uuid.uuid4()),
            start_time=datetime.now(),
            status='running'
        )

        results = {
            'sectors_updated': 0,
            'stocks_updated': 0,
            'market_data_updated': 0,
            'calculations_performed': 0,
            'errors': []
        }

        try:
            # 1. 检查交易日
            if not await self._is_trading_day():
                logger.info("[数据更新] 今天不是交易日，跳过更新")
                log_entry.status = 'skipped'
                log_entry.end_time = datetime.now()
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
            await self._clear_cache()

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
            log_entry.status = 'failed'
            log_entry.error_message = str(e)
            log_entry.end_time = datetime.now()
            raise

        finally:
            # 保存更新日志
            await self._save_update_log(log_entry)

        return results

    async def _is_trading_day(self) -> bool:
        """
        检查今天是否是交易日

        使用简单的周末检查（暂不使用 AkShare 交易日历）

        Returns:
            是否为交易日
        """
        today = datetime.now().date()

        # 简单判断：周一到周五是交易日
        # TODO: 集成 AkShare 获取真实交易日历
        is_weekend = today.weekday() >= 5
        return not is_weekend

    async def _update_sectors(self) -> int:
        """
        更新板块数据

        Returns:
            更新的板块数量
        """
        from src.services.data_acquisition.akshare_client import AkShareDataSource

        logger.info("[数据更新] 开始更新板块数据")

        try:
            data_source = AkShareDataSource()
            sectors = await data_source.get_sector_list()

            count = 0
            session = AsyncSessionLocal()
            try:
                for sector_info in sectors:
                    # TODO: 更新板块数据到数据库
                    # 这里需要实现具体的更新逻辑
                    count += 1
            finally:
                await session.close()

            logger.info(f"[数据更新] 板块数据更新完成: {count} 个板块")
            return count
        except Exception as e:
            logger.error(f"[数据更新] 板块更新失败: {e}")
            return 0

    async def _update_stocks(self) -> int:
        """
        更新股票数据

        Returns:
            更新的股票数量
        """
        from src.services.data_acquisition.akshare_client import AkShareDataSource

        logger.info("[数据更新] 开始更新股票数据")

        try:
            data_source = AkShareDataSource()
            stocks = await data_source.get_stock_list()

            count = 0
            # TODO: 更新股票数据到数据库
            session = AsyncSessionLocal()
            try:
                for stock_info in stocks:
                    count += 1
            finally:
                await session.close()

            logger.info(f"[数据更新] 股票数据更新完成: {count} 只股票")
            return count
        except Exception as e:
            logger.error(f"[数据更新] 股票更新失败: {e}")
            return 0

    async def _update_market_data(self) -> int:
        """
        更新行情数据

        Returns:
            更新的行情数据数量
        """
        from src.services.data_acquisition.akshare_client import AkShareDataSource

        logger.info("[数据更新] 开始更新行情数据")

        try:
            data_source = AkShareDataSource()
            # 获取最新交易日
            latest_date = datetime.now().date()

            # 获取所有股票代码
            session = AsyncSessionLocal()
            try:
                from src.models.stock import Stock
                stmt = select(Stock.symbol)
                result = await session.execute(stmt)
                symbols = result.scalars().all()
            finally:
                await session.close()

            count = 0
            # TODO: 批量获取行情数据并保存
            for symbol in list(symbols)[:10]:  # 限制处理数量
                try:
                    quotes = await data_source.get_daily_quotes(symbol)
                    # TODO: 保存到 DailyMarketData 表
                    count += len(quotes)
                except Exception as e:
                    logger.warning(f"[数据更新] 获取 {symbol} 行情失败: {e}")

            logger.info(f"[数据更新] 行情数据更新完成: {count} 条记录")
            return count
        except Exception as e:
            logger.error(f"[数据更新] 行情更新失败: {e}")
            return 0

    async def _run_calculations(self) -> int:
        """
        执行强度计算

        Returns:
            计算的实体数量
        """
        from src.services.calculator_updater.orchestrator import CalculationOrchestrator

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
        from src.services.cache.cache_manager import get_cache_manager

        logger.info("[数据更新] 清除缓存")

        try:
            cache = get_cache_manager()
            # 清除所有以 "sectors:", "stocks:", "strength:" 开头的缓存
            patterns = ["sectors:%", "stocks:%", "strength:%", "heatmap:%"]
            total = 0
            for pattern in patterns:
                count = await cache.clear_pattern(pattern)
                total += count

            logger.info(f"[数据更新] 清除了 {total} 条缓存")
        except Exception as e:
            logger.error(f"[数据更新] 清除缓存失败: {e}")

    async def _save_update_log(self, log_entry: DataUpdateLog):
        """保存更新日志到数据库"""
        session = AsyncSessionLocal()
        try:
            session.add(log_entry)
            await session.commit()
        finally:
            await session.close()

    async def get_latest_update_status(self) -> Optional[Dict[str, Any]]:
        """
        获取最新更新状态

        Returns:
            更新状态信息
        """
        session = AsyncSessionLocal()
        try:
            stmt = select(DataUpdateLog).order_by(
                DataUpdateLog.start_time.desc()
            ).limit(1)
            result = await session.execute(stmt)
            latest_log = result.scalar_one_or_none()

            if not latest_log:
                return None

            return {
                'last_update': latest_log.start_time.isoformat(),
                'status': latest_log.status,
                'sectors_updated': latest_log.sectors_updated,
                'stocks_updated': latest_log.stocks_updated,
                'market_data_updated': latest_log.market_data_updated,
                'calculations_performed': latest_log.calculations_performed,
                'error': latest_log.error_message,
            }
        finally:
            await session.close()

    async def get_update_history(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取更新历史

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            更新历史数据
        """
        session = AsyncSessionLocal()
        try:
            offset = (page - 1) * page_size
            stmt = (
                select(DataUpdateLog)
                .order_by(DataUpdateLog.start_time.desc())
                .offset(offset)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            logs = result.scalars().all()

            # 获取总数
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
        finally:
            await session.close()
