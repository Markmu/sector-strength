"""
Symbol-based Repository

提供基于代码(symbol/code)的数据访问操作。
"""

from datetime import date
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.daily_market_data import DailyMarketData
from src.models.sector_stock import SectorStock
from .base import BaseRepository


class SymbolMarketDataRepository(BaseRepository[DailyMarketData]):
    """基于代码的日线行情数据访问类"""

    def __init__(self, session: AsyncSession):
        """
        初始化 Repository

        Args:
            session: 异步数据库会话
        """
        super().__init__(DailyMarketData, session)

    async def get_by_symbol_and_date(
        self,
        symbol: str,
        date: date,
    ) -> Optional[DailyMarketData]:
        """
        通过代码获取指定日期的行情数据

        Args:
            symbol: 股票代码或板块代码
            date: 日期

        Returns:
            行情数据对象，不存在返回 None
        """
        stmt = select(DailyMarketData).where(
            and_(
                DailyMarketData.symbol == symbol,
                DailyMarketData.date == date,
            )
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history_by_symbol(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyMarketData]:
        """
        通过代码获取日期范围内的历史行情数据

        Args:
            symbol: 股票代码或板块代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            行情数据列表（按日期升序）
        """
        stmt = select(DailyMarketData).where(
            and_(
                DailyMarketData.symbol == symbol,
                DailyMarketData.date >= start_date,
                DailyMarketData.date <= end_date,
            )
        ).order_by(DailyMarketData.date.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_symbol(
        self,
        symbol: str,
    ) -> Optional[DailyMarketData]:
        """
        通过代码获取最新的行情数据

        Args:
            symbol: 股票代码或板块代码

        Returns:
            最新行情数据，不存在返回 None
        """
        stmt = (
            select(DailyMarketData)
            .where(DailyMarketData.symbol == symbol)
            .order_by(DailyMarketData.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_date_by_symbol(
        self,
        symbol: str,
    ) -> Optional[date]:
        """
        通过代码获取最新数据日期

        Args:
            symbol: 股票代码或板块代码

        Returns:
            最新日期，无数据返回 None
        """
        stmt = (
            select(DailyMarketData.date)
            .where(DailyMarketData.symbol == symbol)
            .order_by(DailyMarketData.date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class SectorStockRepository(BaseRepository[SectorStock]):
    """板块-股票关联仓库（基于代码）"""

    def __init__(self, session: AsyncSession):
        """
        初始化 Repository

        Args:
            session: 异步数据库会话
        """
        super().__init__(SectorStock, session)

    async def get_by_sector_code(
        self,
        sector_code: str,
    ) -> List[SectorStock]:
        """
        获取板块的所有股票关联

        Args:
            sector_code: 板块代码

        Returns:
            关联列表
        """
        stmt = select(SectorStock).where(
            SectorStock.sector_code == sector_code
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_stock_code(
        self,
        stock_code: str,
    ) -> List[SectorStock]:
        """
        获取股票的所有板块关联

        Args:
            stock_code: 股票代码

        Returns:
            关联列表
        """
        stmt = select(SectorStock).where(
            SectorStock.stock_code == stock_code
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_stock_codes_by_sector(
        self,
        sector_code: str,
    ) -> List[str]:
        """
        获取板块下的所有股票代码

        Args:
            sector_code: 板块代码

        Returns:
            股票代码列表
        """
        stmt = select(SectorStock.stock_code).where(
            SectorStock.sector_code == sector_code
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_sector_codes_by_stock(
        self,
        stock_code: str,
    ) -> List[str]:
        """
        获取股票所属的所有板块代码

        Args:
            stock_code: 股票代码

        Returns:
            板块代码列表
        """
        stmt = select(SectorStock.sector_code).where(
            SectorStock.stock_code == stock_code
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_relation(
        self,
        sector_code: str,
        stock_code: str,
    ) -> SectorStock:
        """
        添加板块-股票关联

        Args:
            sector_code: 板块代码
            stock_code: 股票代码

        Returns:
            关联对象
        """
        return await self.create(
            sector_code=sector_code,
            stock_code=stock_code,
        )

    async def remove_relation(
        self,
        sector_code: str,
        stock_code: str,
    ) -> bool:
        """
        删除板块-股票关联

        Args:
            sector_code: 板块代码
            stock_code: 股票代码

        Returns:
            是否删除成功
        """
        stmt = select(SectorStock).where(
            and_(
                SectorStock.sector_code == sector_code,
                SectorStock.stock_code == stock_code,
            )
        )
        result = await self.session.execute(stmt)
        relation = result.scalar_one_or_none()
        if relation:
            await self.session.delete(relation)
            return True
        return False

    async def bulk_add_relations(
        self,
        relations: list[tuple[str, str]],
    ) -> list[SectorStock]:
        """
        批量添加板块-股票关联

        Args:
            relations: (sector_code, stock_code) 元组列表

        Returns:
            关联对象列表
        """
        data_list = [
            {"sector_code": sc, "stock_code": st}
            for sc, st in relations
        ]
        return await self.bulk_create(data_list)
