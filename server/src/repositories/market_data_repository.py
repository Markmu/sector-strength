"""
市场数据 Repository

提供行情数据和均线数据相关的数据访问操作。
"""

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.daily_market_data import DailyMarketData
from src.models.moving_average_data import MovingAverageData
from .base import BaseRepository


class MarketDataRepository(BaseRepository[DailyMarketData]):
    """日线行情数据访问类"""

    def __init__(self, session: AsyncSession):
        """
        初始化市场数据 Repository

        Args:
            session: 异步数据库会话
        """
        super().__init__(DailyMarketData, session)

    async def get_by_entity_and_date(
        self,
        entity_type: str,
        entity_id: int,
        date: date,
    ) -> Optional[DailyMarketData]:
        """
        获取指定实体和日期的行情数据

        Args:
            entity_type: 实体类型 (stock/sector)
            entity_id: 实体 ID
            date: 日期

        Returns:
            行情数据对象，不存在返回 None
        """
        return await self.get_by(
            entity_type=entity_type,
            entity_id=entity_id,
            date=date,
        )

    async def get_history(
        self,
        entity_type: str,
        entity_id: int,
        start_date: date,
        end_date: date,
    ) -> List[DailyMarketData]:
        """
        获取日期范围内的历史行情数据

        Args:
            entity_type: 实体类型 (stock/sector)
            entity_id: 实体 ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            行情数据列表（按日期升序）
        """
        stmt = select(DailyMarketData).where(
            and_(
                DailyMarketData.entity_type == entity_type,
                DailyMarketData.entity_id == entity_id,
                DailyMarketData.date >= start_date,
                DailyMarketData.date <= end_date,
            )
        ).order_by(DailyMarketData.date.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest(
        self,
        entity_type: str,
        entity_id: int,
    ) -> Optional[DailyMarketData]:
        """
        获取最新的行情数据

        Args:
            entity_type: 实体类型 (stock/sector)
            entity_id: 实体 ID

        Returns:
            最新行情数据，不存在返回 None
        """
        stmt = (
            select(DailyMarketData)
            .where(
                and_(
                    DailyMarketData.entity_type == entity_type,
                    DailyMarketData.entity_id == entity_id,
                )
            )
            .order_by(DailyMarketData.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def bulk_insert(
        self,
        data_list: List[Dict[str, Any]],
    ) -> List[DailyMarketData]:
        """
        批量插入行情数据

        Args:
            data_list: 行情数据字典列表

        Returns:
            插入的数据对象列表
        """
        return await self.bulk_create(data_list)

    async def get_latest_date(
        self,
        entity_type: str,
        entity_id: int,
    ) -> Optional[date]:
        """
        获取最新数据日期

        Args:
            entity_type: 实体类型 (stock/sector)
            entity_id: 实体 ID

        Returns:
            最新日期，无数据返回 None
        """
        stmt = (
            select(DailyMarketData.date)
            .where(
                and_(
                    DailyMarketData.entity_type == entity_type,
                    DailyMarketData.entity_id == entity_id,
                )
            )
            .order_by(DailyMarketData.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class MovingAverageRepository(BaseRepository[MovingAverageData]):
    """均线数据访问类"""

    def __init__(self, session: AsyncSession):
        """
        初始化均线数据 Repository

        Args:
            session: 异步数据库会话
        """
        super().__init__(MovingAverageData, session)

    async def get_by_entity_and_period(
        self,
        entity_type: str,
        entity_id: int,
        period: str,
        *,
        limit: int = 100,
    ) -> List[MovingAverageData]:
        """
        获取指定实体的均线数据

        Args:
            entity_type: 实体类型 (stock/sector)
            entity_id: 实体 ID
            period: 均线周期 (5d/10d/20d/30d/60d)
            limit: 返回数量限制

        Returns:
            均线数据列表（按日期降序）
        """
        stmt = (
            select(MovingAverageData)
            .where(
                and_(
                    MovingAverageData.entity_type == entity_type,
                    MovingAverageData.entity_id == entity_id,
                    MovingAverageData.period == period,
                )
            )
            .order_by(MovingAverageData.date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_ma(
        self,
        entity_type: str,
        entity_id: int,
        period: str,
    ) -> Optional[MovingAverageData]:
        """
        获取最新均线数据

        Args:
            entity_type: 实体类型 (stock/sector)
            entity_id: 实体 ID
            period: 均线周期

        Returns:
            最新均线数据，不存在返回 None
        """
        stmt = (
            select(MovingAverageData)
            .where(
                and_(
                    MovingAverageData.entity_type == entity_type,
                    MovingAverageData.entity_id == entity_id,
                    MovingAverageData.period == period,
                )
            )
            .order_by(MovingAverageData.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_periods_latest(
        self,
        entity_type: str,
        entity_id: int,
        periods: List[str],
    ) -> Dict[str, Optional[MovingAverageData]]:
        """
        获取所有周期的最新均线数据

        Args:
            entity_type: 实体类型 (stock/sector)
            entity_id: 实体 ID
            periods: 均线周期列表

        Returns:
            周期到均线数据的映射
        """
        result_map: Dict[str, Optional[MovingAverageData]] = {}
        for period in periods:
            result_map[period] = await self.get_latest_ma(
                entity_type, entity_id, period
            )
        return result_map

    async def bulk_insert(
        self,
        data_list: List[Dict[str, Any]],
    ) -> List[MovingAverageData]:
        """
        批量插入均线数据

        Args:
            data_list: 均线数据字典列表

        Returns:
            插入的数据对象列表
        """
        return await self.bulk_create(data_list)
