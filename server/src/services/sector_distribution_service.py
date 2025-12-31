"""
板块类型分布服务

提供板块类型分布统计数据（行业板块/概念板块总数）。
"""

import logging
from datetime import date
from sqlalchemy import select, and_, func, case
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

            # 统计各类型板块数量
            stmt = (
                select(
                    StrengthScore.date,
                    func.sum(
                        case(
                            (Sector.type == 'industry', 1),
                            else_=0
                        )
                    ).label('industry_count'),
                    func.sum(
                        case(
                            (Sector.type == 'concept', 1),
                            else_=0
                        )
                    ).label('concept_count'),
                )
                .join(Sector, and_(
                    StrengthScore.entity_type == 'sector',
                    StrengthScore.entity_id == Sector.id,
                    StrengthScore.period == 'all',
                    StrengthScore.date == latest_date_stmt,
                ))
                .group_by(StrengthScore.date)
            )

            result = await self.session.execute(stmt)
            row = result.first()

            if not row:
                # 无数据时返回空结构
                return SectorDistributionResponse(
                    date=date.today(),
                    industry_count=0,
                    concept_count=0,
                    total_count=0,
                )

            data_date, industry_count, concept_count = row

            return SectorDistributionResponse(
                date=data_date,
                industry_count=int(industry_count or 0),
                concept_count=int(concept_count or 0),
                total_count=int((industry_count or 0) + (concept_count or 0)),
            )

        except Exception as e:
            logger.error(f"获取板块类型分布失败: {e}")
            raise
