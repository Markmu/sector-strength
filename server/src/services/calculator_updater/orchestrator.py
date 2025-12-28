"""
计算流程协调器

协调所有强度计算任务的执行。
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import AsyncSessionLocal
from src.models.stock import Stock
from src.models.sector import Sector
from src.models.period_config import PeriodConfig
from src.services.calculation.strength_calculator import StrengthCalculator
from src.services.calculation.moving_average_calculator import MovingAverageCalculator
from src.services.calculation.trend_analyzer import TrendAnalyzer
from src.config.calculation import DEFAULT_PERIOD_CONFIGS

logger = logging.getLogger(__name__)


class CalculationOrchestrator:
    """
    计算流程协调器

    协调均线计算和强度得分的批量计算。
    """

    def __init__(self):
        """初始化计算协调器"""
        self.ma_calculator = MovingAverageCalculator()
        self.strength_calculator = StrengthCalculator()
        self.trend_analyzer = TrendAnalyzer()

    async def run_all_calculations(self) -> int:
        """
        运行所有计算任务

        Returns:
            计算的实体数量
        """
        count = 0

        try:
            # 1. 获取周期配置
            period_configs = await self._get_period_configs()

            # 2. 计算股票强度
            stock_count = await self._calculate_all_stocks(period_configs)
            count += stock_count

            # 3. 计算板块强度
            sector_count = await self._calculate_all_sectors(period_configs)
            count += sector_count

            logger.info(f"[计算协调] 完成所有计算: {count} 个实体")

        except Exception as e:
            logger.error(f"[计算协调] 计算失败: {e}")
            raise

        return count

    async def _get_period_configs(self) -> list:
        """获取周期配置"""
        session = AsyncSessionLocal()
        try:
            stmt = select(PeriodConfig).where(PeriodConfig.is_active == True)
            result = await session.execute(stmt)
            configs = result.scalars().all()

            return [
                {
                    'period': c.period,
                    'days': c.days,
                    'weight': c.weight,
                }
                for c in configs
            ]
        finally:
            await session.close()

    async def _calculate_all_stocks(self, period_configs: list) -> int:
        """
        计算所有股票的强度

        Args:
            period_configs: 周期配置列表

        Returns:
            计算的股票数量
        """
        logger.info("[计算协调] 开始计算股票强度")

        session = AsyncSessionLocal()
        try:
            stmt = select(Stock)
            result = await session.execute(stmt)
            stocks = result.scalars().all()
        finally:
            await session.close()

        count = 0
        for stock in stocks[:100]:  # 限制处理数量
            try:
                # 获取历史价格数据
                prices = await self._get_stock_prices(stock.symbol)
                if prices is None or len(prices) < 60:
                    continue

                # 计算强度
                result = self.strength_calculator.calculate_entity_strength(
                    prices=prices,
                    current_price=stock.current_price or prices.iloc[-1],
                    period_configs=period_configs,
                )

                if result.get('strength_score'):
                    # TODO: 更新数据库
                    count += 1

            except Exception as e:
                logger.warning(f"[计算协调] 股票 {stock.symbol} 计算失败: {e}")

        return count

    async def _calculate_all_sectors(self, period_configs: list) -> int:
        """
        计算所有板块的强度

        Args:
            period_configs: 周期配置列表

        Returns:
            计算的板块数量
        """
        logger.info("[计算协调] 开始计算板块强度")

        session = AsyncSessionLocal()
        try:
            stmt = select(Sector)
            result = await session.execute(stmt)
            sectors = result.scalars().all()
        finally:
            await session.close()

        count = 0
        for sector in sectors[:20]:  # 限制处理数量
            try:
                # 获取成分股强度
                sector_strength = await self._calculate_sector_from_stocks(sector.id, session)

                if sector_strength:
                    # TODO: 更新数据库
                    count += 1

            except Exception as e:
                logger.warning(f"[计算协调] 板块 {sector.name} 计算失败: {e}")

        return count

    async def _get_stock_prices(self, symbol: str) -> Optional[list]:
        """
        获取股票历史价格

        Args:
            symbol: 股票代码

        Returns:
            价格列表
        """
        session = AsyncSessionLocal()
        try:
            # TODO: 从 DailyMarketData 表获取历史价格
            # 这里返回模拟数据
            import pandas as pd
            import numpy as np

            dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
            base_price = 100.0
            prices = pd.Series([
                base_price + i * 0.1 + np.random.randn() * 2
                for i in range(100)
            ], index=dates)

            return prices
        finally:
            await session.close()

    async def _calculate_sector_from_stocks(
        self,
        sector_id: str,
        session: AsyncSession
    ) -> Optional[float]:
        """
        从成分股计算板块强度

        Args:
            sector_id: 板块 ID
            session: 数据库会话

        Returns:
            板块强度得分
        """
        # TODO: 查询成分股强度并计算加权平均
        # 这里返回模拟值
        return 50.0

    async def calculate_single_stock(self, stock_id: str) -> Optional[Dict]:
        """
        计算单个股票的强度

        Args:
            stock_id: 股票 ID

        Returns:
            计算结果
        """
        session = AsyncSessionLocal()
        try:
            stmt = select(Stock).where(Stock.id == stock_id)
            result = await session.execute(stmt)
            stock = result.scalar_one_or_none()
        finally:
            await session.close()

        if not stock:
            logger.warning(f"[计算协调] 股票 {stock_id} 不存在")
            return None

        try:
            # 获取历史价格
            prices = await self._get_stock_prices(stock.symbol)
            if prices is None or len(prices) < 60:
                return {
                    'error': '历史数据不足'
                }

            # 获取周期配置
            period_configs = await self._get_period_configs()

            # 计算强度
            result = self.strength_calculator.calculate_entity_strength(
                prices=prices,
                current_price=stock.current_price or prices.iloc[-1],
                period_configs=period_configs,
            )

            return result

        except Exception as e:
            logger.error(f"[计算协调] 股票 {stock_id} 计算失败: {e}")
            return {
                'error': str(e)
            }

    async def calculate_single_sector(self, sector_id: str) -> Optional[Dict]:
        """
        计算单个板块的强度

        Args:
            sector_id: 板块 ID

        Returns:
            计算结果
        """
        session = AsyncSessionLocal()
        try:
            stmt = select(Sector).where(Sector.id == sector_id)
            result = await session.execute(stmt)
            sector = result.scalar_one_or_none()
        finally:
            await session.close()

        if not sector:
            logger.warning(f"[计算协调] 板块 {sector_id} 不存在")
            return None

        try:
            # 从成分股计算板块强度
            strength = await self._calculate_sector_from_stocks(sector_id, session)

            # 判定趋势
            trend = self.trend_analyzer.determine_trend(
                current_price=100,  # TODO: 获取板块当前价格
                ma_values={}  # TODO: 获取板块均线
            )

            return {
                'strength_score': strength,
                'trend_direction': int(trend),
            }

        except Exception as e:
            logger.error(f"[计算协调] 板块 {sector_id} 计算失败: {e}")
            return {
                'error': str(e)
            }
