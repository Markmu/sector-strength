"""
板块强度散点图数据聚合服务

提供板块散点图分析所需的数据聚合功能。
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import date, datetime
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.strength_score import StrengthScore
from src.api.schemas.strength import (
    SectorScatterResponse,
    SectorScatterDataset,
    SectorScatterData,
    DataCompleteness,
    SectorFullData,
    FiltersApplied,
    PaginationInfo,
)

logger = logging.getLogger(__name__)


# 维度字段映射
AXIS_FIELD_MAP = {
    'short': 'short_term_score',
    'medium': 'medium_term_score',
    'long': 'long_term_score',
    'composite': 'score',
}

# 强度等级到分数范围映射
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


class StrengthScatterService:
    """板块强度散点图数据聚合服务"""

    def __init__(self, session: AsyncSession):
        """
        初始化散点图服务

        Args:
            session: 数据库会话
        """
        self.session = session

    async def get_scatter_data(
        self,
        x_axis: str = 'short',
        y_axis: str = 'medium',
        sector_type: Optional[str] = None,
        min_grade: Optional[str] = None,
        max_grade: Optional[str] = None,
        offset: int = 0,
        limit: int = 200,
        calc_date: Optional[date] = None,
    ) -> SectorScatterResponse:
        """
        获取散点图数据

        Args:
            x_axis: X轴维度 (short/medium/long/composite)
            y_axis: Y轴维度 (short/medium/long/composite)
            sector_type: 板块类型筛选 (industry/concept)
            min_grade: 最低等级 (D/C/B/A/A+/S/S+)
            max_grade: 最高等级
            offset: 分页偏移
            limit: 每页数量
            calc_date: 计算日期，None 表示最新

        Returns:
            SectorScatterResponse
        """
        try:
            # 获取维度字段名
            x_field = AXIS_FIELD_MAP.get(x_axis, 'short_term_score')
            y_field = AXIS_FIELD_MAP.get(y_axis, 'medium_term_score')

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
                )
                .join(StrengthScore, and_(
                    StrengthScore.entity_type == 'sector',
                    StrengthScore.entity_id == Sector.id,
                    StrengthScore.period == 'all',
                ))
                .order_by(StrengthScore.date.desc())
            )

            # 筛选条件
            filters = []

            # 板块类型筛选
            if sector_type and sector_type in ('industry', 'concept'):
                filters.append(Sector.type == sector_type)

            # 强度等级筛选
            if min_grade or max_grade:
                score_filter = self._build_grade_filter(min_grade, max_grade)
                if score_filter is not None:
                    filters.append(score_filter)

            # 日期筛选
            if calc_date:
                filters.append(StrengthScore.date == calc_date)

            if filters:
                stmt = stmt.where(and_(*filters))

            # 先获取所有符合条件的数据（用于分页前计数）
            # 创建一个计数语句
            count_stmt = select(func.count()).select_from(stmt.subquery().alias('sub'))
            try:
                count_result = await self.session.execute(count_stmt)
                total_count = count_result.scalar() or 0
            except Exception:
                # 如果计数失败，使用 0
                total_count = 0

            # 应用分页
            stmt = stmt.offset(offset).limit(limit)

            # 执行查询
            result = await self.session.execute(stmt)
            rows = result.all()

            # 处理数据
            industry_data = []
            concept_data = []

            for row in rows:
                (
                    sector_id,
                    code,
                    name,
                    sector_type,
                    score,
                    short_score,
                    medium_score,
                    long_score,
                    strong_ratio,
                    grade,
                ) = row

                # 获取 X/Y 轴数值
                x_value = self._get_axis_value(row, x_field)
                y_value = self._get_axis_value(row, y_field)

                # 数据缺失处理
                size = self._calculate_size(strong_ratio)
                color_value = long_score if long_score is not None else 50.0

                # 数据完整度
                completeness = self._calculate_completeness(strong_ratio, long_score)

                # 构建数据点
                scatter_data = SectorScatterData(
                    symbol=code,
                    name=name,
                    sector_type=sector_type,
                    x=x_value,
                    y=y_value,
                    size=size,
                    color_value=color_value,
                    data_completeness=completeness,
                    full_data=SectorFullData(
                        score=score,
                        short_term_score=short_score,
                        medium_term_score=medium_score,
                        long_term_score=long_score,
                        strong_stock_ratio=strong_ratio,
                        strength_grade=grade,
                    ),
                )

                # 按类型分组
                if sector_type == 'industry':
                    industry_data.append(scatter_data)
                else:
                    concept_data.append(scatter_data)

            # 构建响应
            return SectorScatterResponse(
                scatter_data=SectorScatterDataset(
                    industry=industry_data,
                    concept=concept_data,
                ),
                total_count=total_count,
                returned_count=len(industry_data) + len(concept_data),
                filters_applied=FiltersApplied(
                    sector_type=sector_type,
                    grade_range=[min_grade, max_grade] if min_grade or max_grade else None,
                    axes=[x_axis, y_axis],
                    pagination=PaginationInfo(offset=offset, limit=limit),
                ),
                cache_status='miss',  # TODO: 添加缓存支持
            )

        except Exception as e:
            logger.error(f"获取散点图数据失败: {e}")
            raise

    def _get_axis_value(self, row: Tuple, field_name: str) -> float:
        """
        从查询结果中获取轴数值

        Args:
            row: 查询结果行
            field_name: 字段名

        Returns:
            轴数值，默认 0
        """
        # 字段索引映射（与 select() 中的字段顺序对应）
        field_index_map = {
            'score': 4,
            'short_term_score': 5,
            'medium_term_score': 6,
            'long_term_score': 7,
        }

        index = field_index_map.get(field_name)
        if index is not None:
            value = row[index]
            if value is not None:
                return float(value)

        return 0.0

    def _calculate_size(self, strong_ratio: Optional[float]) -> float:
        """
        计算气泡大小

        Args:
            strong_ratio: 强势股占比

        Returns:
            气泡大小 (10-60)
        """
        if strong_ratio is None:
            return 20.0  # 默认中等大小

        # 映射到 10-60 范围
        return max(strong_ratio * 50, 10.0)

    def _calculate_completeness(
        self,
        strong_ratio: Optional[float],
        long_score: Optional[float],
    ) -> DataCompleteness:
        """
        计算数据完整度

        Args:
            strong_ratio: 强势股占比
            long_score: 长期强度

        Returns:
            数据完整度
        """
        has_strong = strong_ratio is not None
        has_long = long_score is not None

        # 计算完整度百分比
        fields_count = 2
        complete_fields = sum([has_strong, has_long])
        percent = (complete_fields / fields_count) * 100 if fields_count > 0 else 0

        return DataCompleteness(
            has_strong_ratio=has_strong,
            has_long_term=has_long,
            completeness_percent=percent,
        )

    def _build_grade_filter(
        self,
        min_grade: Optional[str],
        max_grade: Optional[str],
    ) -> Optional[Any]:
        """
        构建强度等级筛选条件

        Args:
            min_grade: 最低等级
            max_grade: 最高等级

        Returns:
            SQLAlchemy 筛选表达式
        """
        filters = []

        # 最低等级筛选
        if min_grade:
            min_score = GRADE_RANGE_MAP.get(min_grade, (0, 100))[0]
            filters.append(StrengthScore.score >= min_score)

        # 最高等级筛选
        if max_grade:
            max_score = GRADE_RANGE_MAP.get(max_grade, (0, 100))[1]
            filters.append(StrengthScore.score <= max_score)

        if filters:
            return and_(*filters)

        return None
