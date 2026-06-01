"""
板块类型分布服务

提供板块类型分布统计数据（按板块类型分组计数）。
"""

import logging
from collections import defaultdict
from datetime import date
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.strength_score import StrengthScore
from src.api.schemas.grade_table import SectorDistributionResponse

logger = logging.getLogger(__name__)


class SectorDistributionService:
    """板块类型分布服务"""

    def __init__(self, session: AsyncSession):
        """
        初始化服务

        Args:
            session: 数据库会话
        """
        self.session = session

    async def get_sector_distribution(self) -> SectorDistributionResponse:
        """
        获取板块类型分布统计

        返回最新日期的板块类型分布数据，不受筛选条件影响。

        Returns:
            SectorDistributionResponse
        """
        try:
            # 子查询获取最新日期
            latest_date_stmt = (
                select(StrengthScore.date)
                .where(StrengthScore.period == 'all')
                .order_by(StrengthScore.date.desc())
                .limit(1)
                .scalar_subquery()
            )

            # 按 Sector.type 分组统计
            stmt = (
                select(
                    StrengthScore.date,
                    Sector.type,
                    func.count().label('cnt'),
                )
                .join(Sector, and_(
                    StrengthScore.entity_type == 'sector',
                    StrengthScore.entity_id == Sector.id,
                    StrengthScore.period == 'all',
                    StrengthScore.date == latest_date_stmt,
                ))
                .group_by(StrengthScore.date, Sector.type)
            )

            result = await self.session.execute(stmt)
            rows = result.all()

            if not rows:
                # 无数据时返回空结构
                return SectorDistributionResponse(
                    date=date.today(),
                    type_counts={},
                    total_count=0,
                )

            data_date = rows[0][0]
            type_counts: dict[str, int] = {}
            total = 0
            for row in rows:
                _, sector_type, cnt = row
                type_counts[sector_type] = int(cnt)
                total += int(cnt)

            return SectorDistributionResponse(
                date=data_date,
                type_counts=type_counts,
                total_count=total,
            )

        except Exception as e:
            logger.error(f"获取板块类型分布失败: {e}")
            raise
