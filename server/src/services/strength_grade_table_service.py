"""
板块等级表格数据服务

提供按等级分组的板块数据查询功能。
"""

import logging
from typing import List, Dict, Optional
from datetime import date
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.strength_score import StrengthScore
from src.api.schemas.grade_table import (
    SectorGradeTableResponse,
    GradeSectorStats,
    SectorTableItem,
)

logger = logging.getLogger(__name__)

# 等级顺序（从高到低）
GRADE_ORDER = ['S+', 'S', 'A+', 'A', 'B+', 'B', 'C', 'D']

# 等级到分数范围映射
GRADE_RANGE_MAP = {
    'S+': (90, 100),
    'S': (80, 89),
    'A+': (70, 79),
    'A': (60, 69),
    'B+': (50, 59),
    'B': (40, 49),
    'C': (30, 39),
    'D': (0, 29),
}


class StrengthGradeTableService:
    """板块等级表格数据服务"""

    def __init__(self, session: AsyncSession):
        """
        初始化服务

        Args:
            session: 数据库会话
        """
        self.session = session

    async def get_grade_table_data(
        self,
        sector_type: Optional[str] = None,
        calc_date: Optional[date] = None,
    ) -> SectorGradeTableResponse:
        """
        获取板块等级表格数据

        Args:
            sector_type: 板块类型筛选 (industry/concept)
            calc_date: 计算日期，None 表示最新

        Returns:
            SectorGradeTableResponse
        """
        try:
            # 构建查询
            stmt = (
                select(
                    Sector.id,
                    Sector.code,
                    Sector.name,
                    Sector.type,
                    StrengthScore.score,
                    StrengthScore.short_term_score,
                    StrengthScore.medium_term_score,
                    StrengthScore.long_term_score,
                    StrengthScore.strong_stock_ratio,
                    StrengthScore.strength_grade,
                    StrengthScore.rank,
                    StrengthScore.date,
                )
                .join(StrengthScore, and_(
                    StrengthScore.entity_type == 'sector',
                    StrengthScore.entity_id == Sector.id,
                    StrengthScore.period == 'all',
                ))
            )

            # 筛选条件
            filters = []

            # 板块类型筛选
            if sector_type and sector_type in ('industry', 'concept'):
                filters.append(Sector.type == sector_type)

            # 日期筛选：如果指定日期则使用该日期，否则只查询最新日期
            if calc_date:
                filters.append(StrengthScore.date == calc_date)
            else:
                # 子查询获取最新日期
                latest_date_stmt = (
                    select(StrengthScore.date)
                    .where(StrengthScore.period == 'all')
                    .order_by(StrengthScore.date.desc())
                    .limit(1)
                    .scalar_subquery()
                )
                stmt = stmt.where(StrengthScore.date == latest_date_stmt)

            if filters:
                stmt = stmt.where(and_(*filters))

            # 执行查询
            result = await self.session.execute(stmt)
            rows = result.all()

            if not rows:
                # 无数据时返回空结构
                return SectorGradeTableResponse(
                    date=calc_date or date.today(),
                    stats=[],
                    total_industry=0,
                    total_concept=0,
                    total_sectors=0,
                    cache_status='miss',
                )

            # 获取日期（已过滤，只有单一日期）
            data_date = rows[0][-1]  # date 是最后一列

            # 按等级分组数据
            grade_dict: Dict[str, Dict[str, List]] = {}
            for grade in GRADE_ORDER:
                grade_dict[grade] = {'industry': [], 'concept': []}

            total_industry = 0
            total_concept = 0

            for row in rows:
                (
                    sector_id,
                    code,
                    name,
                    sectype,
                    score,
                    short_score,
                    medium_score,
                    long_score,
                    strong_ratio,
                    grade,
                    rank,
                    _date,
                ) = row

                # 确定等级（如果没有等级，根据分数计算）
                if not grade and score is not None:
                    grade = self._score_to_grade(score)

                if not grade:
                    grade = 'D'  # 默认最低等级

                # 只处理有效等级
                if grade not in grade_dict:
                    continue

                # 构建板块项
                sector_item = SectorTableItem(
                    id=sector_id,
                    code=code,
                    name=name,
                    sector_type=sectype,
                    score=score,
                    short_term_score=short_score,
                    medium_term_score=medium_score,
                    long_term_score=long_score,
                    strong_stock_ratio=strong_ratio,
                    strength_grade=grade,
                    rank=rank,
                )

                # 按类型和等级分组
                if sectype == 'industry':
                    grade_dict[grade]['industry'].append(sector_item)
                    total_industry += 1
                elif sectype == 'concept':
                    grade_dict[grade]['concept'].append(sector_item)
                    total_concept += 1

            # 构建响应
            grade_stats = []
            for grade in GRADE_ORDER:
                industry_list = grade_dict[grade]['industry']
                concept_list = grade_dict[grade]['concept']

                # 合并并排序（按分数降序）
                all_sectors = sorted(
                    industry_list + concept_list,
                    key=lambda x: (x.score or 0),
                    reverse=True,
                )

                grade_stats.append(GradeSectorStats(
                    grade=grade,
                    industry_count=len(industry_list),
                    concept_count=len(concept_list),
                    total_count=len(all_sectors),
                    sectors=all_sectors,
                ))

            return SectorGradeTableResponse(
                date=data_date,
                stats=grade_stats,
                total_industry=total_industry,
                total_concept=total_concept,
                total_sectors=total_industry + total_concept,
                cache_status='miss',  # TODO: 添加缓存支持
            )

        except Exception as e:
            logger.error(f"获取等级表格数据失败: {e}")
            raise

    def _score_to_grade(self, score: float) -> str:
        """
        根据分数转换为等级

        Args:
            score: 分数

        Returns:
            等级
        """
        for grade, (min_score, max_score) in GRADE_RANGE_MAP.items():
            if min_score <= score <= max_score:
                return grade
        return 'D'
