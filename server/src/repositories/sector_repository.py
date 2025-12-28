"""
板块 Repository

提供板块相关的数据访问操作。
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.sector import Sector
from .base import BaseRepository


class SectorRepository(BaseRepository[Sector]):
    """板块数据访问类"""

    def __init__(self, session: AsyncSession):
        """
        初始化板块 Repository

        Args:
            session: 异步数据库会话
        """
        super().__init__(Sector, session)

    async def get_by_code(self, code: str) -> Optional[Sector]:
        """
        根据代码获取板块

        Args:
            code: 板块代码

        Returns:
            板块对象，不存在返回 None
        """
        return await self.get_by(code=code)

    async def get_by_type(
        self,
        sector_type: str,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Sector]:
        """
        根据类型获取板块列表

        Args:
            sector_type: 板块类型 (industry/concept)
            offset: 偏移量
            limit: 返回数量限制

        Returns:
            板块列表
        """
        return await self.list(type=sector_type, offset=offset, limit=limit)

    async def get_with_stocks(self, sector_id: int) -> Optional[Sector]:
        """
        获取板块及其成分股

        Args:
            sector_id: 板块 ID

        Returns:
            板块对象（包含成分股），不存在返回 None
        """
        stmt = (
            select(Sector)
            .where(Sector.id == sector_id)
            .options(selectinload(Sector.stocks))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_top_by_strength(
        self,
        sector_type: Optional[str] = None,
        *,
        limit: int = 10,
    ) -> List[Sector]:
        """
        获取强度得分最高的板块

        Args:
            sector_type: 板块类型过滤，None 表示所有类型
            limit: 返回数量限制

        Returns:
            板块列表（按强度得分降序）
        """
        stmt = select(Sector)
        if sector_type:
            stmt = stmt.where(Sector.type == sector_type)
        stmt = stmt.order_by(Sector.strength_score.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_strength_score(
        self,
        sector_id: int,
        strength_score: float,
    ) -> Optional[Sector]:
        """
        更新板块强度得分

        Args:
            sector_id: 板块 ID
            strength_score: 强度得分

        Returns:
            更新后的板块对象
        """
        return await self.update(sector_id, {"strength_score": strength_score})

    async def update_trend_direction(
        self,
        sector_id: int,
        trend_direction: int,
    ) -> Optional[Sector]:
        """
        更新板块趋势方向

        Args:
            sector_id: 板块 ID
            trend_direction: 趋势方向 (1: 上升, -1: 下降, 0: 横盘)

        Returns:
            更新后的板块对象
        """
        return await self.update(sector_id, {"trend_direction": trend_direction})
