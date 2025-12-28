"""
股票 Repository

提供股票相关的数据访问操作。
"""

from typing import List, Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.stock import Stock
from .base import BaseRepository


class StockRepository(BaseRepository[Stock]):
    """股票数据访问类"""

    def __init__(self, session: AsyncSession):
        """
        初始化股票 Repository

        Args:
            session: 异步数据库会话
        """
        super().__init__(Stock, session)

    async def get_by_symbol(self, symbol: str) -> Optional[Stock]:
        """
        根据代码获取股票

        Args:
            symbol: 股票代码

        Returns:
            股票对象，不存在返回 None
        """
        return await self.get_by(symbol=symbol)

    async def search_by_name(
        self,
        name_keyword: str,
        *,
        limit: int = 20,
    ) -> List[Stock]:
        """
        根据名称关键词搜索股票

        Args:
            name_keyword: 名称关键词
            limit: 返回数量限制

        Returns:
            股票列表
        """
        stmt = (
            select(Stock)
            .where(Stock.name.ilike(f"%{name_keyword}%"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_symbols(
        self,
        symbols: List[str],
    ) -> List[Stock]:
        """
        根据代码列表批量获取股票

        Args:
            symbols: 股票代码列表

        Returns:
            股票列表
        """
        stmt = select(Stock).where(Stock.symbol.in_(symbols))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_sectors(self, stock_id: int) -> Optional[Stock]:
        """
        获取股票及其所属板块

        Args:
            stock_id: 股票 ID

        Returns:
            股票对象（包含板块），不存在返回 None
        """
        stmt = (
            select(Stock)
            .where(Stock.id == stock_id)
            .options(selectinload(Stock.sectors).selectinload("sector"))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_top_by_market_cap(
        self,
        *,
        limit: int = 50,
    ) -> List[Stock]:
        """
        获取市值最高的股票

        Args:
            limit: 返回数量限制

        Returns:
            股票列表（按市值降序）
        """
        stmt = (
            select(Stock)
            .where(Stock.market_cap.isnot(None))
            .order_by(Stock.market_cap.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_price(
        self,
        stock_id: int,
        current_price: float,
    ) -> Optional[Stock]:
        """
        更新股票当前价格

        Args:
            stock_id: 股票 ID
            current_price: 当前价格

        Returns:
            更新后的股票对象
        """
        return await self.update(stock_id, {"current_price": current_price})

    async def update_market_cap(
        self,
        stock_id: int,
        market_cap: float,
    ) -> Optional[Stock]:
        """
        更新股票市值

        Args:
            stock_id: 股票 ID
            market_cap: 市值

        Returns:
            更新后的股票对象
        """
        return await self.update(stock_id, {"market_cap": market_cap})

    async def update_strength_score(
        self,
        stock_id: int,
        strength_score: float,
    ) -> Optional[Stock]:
        """
        更新股票强度得分

        Args:
            stock_id: 股票 ID
            strength_score: 强度得分 (0-100)

        Returns:
            更新后的股票对象
        """
        return await self.update(stock_id, {"strength_score": strength_score})

    async def update_trend_direction(
        self,
        stock_id: int,
        trend_direction: int,
    ) -> Optional[Stock]:
        """
        更新股票趋势方向

        Args:
            stock_id: 股票 ID
            trend_direction: 趋势方向 (1=上升, 0=横盘, -1=下降)

        Returns:
            更新后的股票对象
        """
        return await self.update(stock_id, {"trend_direction": trend_direction})

    async def get_all_active(self) -> List[Stock]:
        """
        获取所有活跃股票（有价格数据的股票）

        Returns:
            活跃股票列表
        """
        stmt = (
            select(Stock)
            .where(Stock.current_price.isnot(None))
            .order_by(Stock.market_cap.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
