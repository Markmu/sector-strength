"""
板块散点图数据聚合服务测试
"""

import pytest
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.strength_scatter_service import StrengthScatterService
from src.models.sector import Sector
from src.models.strength_score import StrengthScore


@pytest.mark.asyncio
async def test_get_scatter_data_basic(db_session: AsyncSession, sample_sectors, sample_strength_scores):
    """测试基本散点图数据获取"""
    service = StrengthScatterService(db_session)

    result = await service.get_scatter_data(
        x_axis='short',
        y_axis='medium',
    )

    # 验证响应结构
    assert hasattr(result, 'scatter_data')
    assert hasattr(result, 'total_count')
    assert hasattr(result, 'returned_count')
    assert hasattr(result, 'filters_applied')
    assert hasattr(result, 'cache_status')

    # 验证数据集
    assert hasattr(result.scatter_data, 'industry')
    assert hasattr(result.scatter_data, 'concept')
    assert isinstance(result.scatter_data.industry, list)
    assert isinstance(result.scatter_data.concept, list)

    # 验证筛选器
    assert result.filters_applied.axes == ['short', 'medium']
    assert result.filters_applied.pagination is not None


@pytest.mark.asyncio
async def test_get_scatter_data_with_sector_type_filter(db_session: AsyncSession, sample_sectors, sample_strength_scores):
    """测试板块类型筛选"""
    service = StrengthScatterService(db_session)

    # 筛选行业板块
    result = await service.get_scatter_data(
        x_axis='short',
        y_axis='medium',
        sector_type='industry',
    )

    # 验证只返回行业板块
    assert all(point.sector_type == 'industry' for point in result.scatter_data.industry)
    assert len(result.scatter_data.concept) == 0  # 概念板块应为空
    assert result.filters_applied.sector_type == 'industry'


@pytest.mark.asyncio
async def test_get_scatter_data_with_grade_filter(db_session: AsyncSession, sample_sectors, sample_strength_scores):
    """测试强度等级筛选"""
    service = StrengthScatterService(db_session)

    # 筛选 A 级及以上
    result = await service.get_scatter_data(
        x_axis='short',
        y_axis='medium',
        min_grade='A',
        max_grade='S+',
    )

    # 验证筛选条件
    assert result.filters_applied.grade_range == ['A', 'S+']

    # 验证返回的数据符合等级范围
    all_points = result.scatter_data.industry + result.scatter_data.concept
    for point in all_points:
        if point.full_data.score is not None:
            assert point.full_data.score >= 70  # A 级最低 70 分


@pytest.mark.asyncio
async def test_get_scatter_data_pagination(db_session: AsyncSession, sample_sectors, sample_strength_scores):
    """测试分页功能"""
    service = StrengthScatterService(db_session)

    # 第一页
    result1 = await service.get_scatter_data(
        x_axis='short',
        y_axis='medium',
        offset=0,
        limit=2,
    )

    assert result1.returned_count <= 2
    assert result1.filters_applied.pagination.offset == 0
    assert result1.filters_applied.pagination.limit == 2

    # 第二页（如果有足够数据）
    if result1.total_count > 2:
        result2 = await service.get_scatter_data(
            x_axis='short',
            y_axis='medium',
            offset=2,
            limit=2,
        )

        assert result2.returned_count <= 2
        assert result2.filters_applied.pagination.offset == 2


@pytest.mark.asyncio
async def test_get_scatter_data_axis_mapping(db_session: AsyncSession, sample_sectors, sample_strength_scores):
    """测试不同轴维度的数据映射"""
    service = StrengthScatterService(db_session)

    # 测试短期强度
    result_short = await service.get_scatter_data(
        x_axis='short',
        y_axis='short',
    )

    # 验证数据点
    all_points_short = result_short.scatter_data.industry + result_short.scatter_data.concept
    if all_points_short:
        point = all_points_short[0]
        # X 和 Y 应该相等（都是短期强度）
        assert point.x == point.y

    # 测试长期强度
    result_long = await service.get_scatter_data(
        x_axis='long',
        y_axis='composite',
    )

    assert result_long.filters_applied.axes == ['long', 'composite']


@pytest.mark.asyncio
async def test_get_scatter_data_missing_values_handling(db_session: AsyncSession, sample_sectors_with_missing, sample_strength_scores_missing):
    """测试数据缺失处理"""
    service = StrengthScatterService(db_session)

    result = await service.get_scatter_data(
        x_axis='short',
        y_axis='medium',
    )

    # 验证数据完整度计算
    all_points = result.scatter_data.industry + result.scatter_data.concept
    for point in all_points:
        assert hasattr(point.data_completeness, 'has_strong_ratio')
        assert hasattr(point.data_completeness, 'has_long_term')
        assert hasattr(point.data_completeness, 'completeness_percent')
        assert 0 <= point.data_completeness.completeness_percent <= 100

        # 验证默认值
        assert point.size >= 10  # 最小气泡大小
        assert point.color_value >= 0  # 颜色值应在有效范围


@pytest.mark.asyncio
async def test_get_scatter_data_empty_result(db_session: AsyncSession):
    """测试空数据场景"""
    service = StrengthScatterService(db_session)

    result = await service.get_scatter_data(
        x_axis='short',
        y_axis='medium',
        calc_date=date(2020, 1, 1),  # 使用过去日期，应该没有数据
    )

    # 验证空数据响应
    assert result.total_count == 0
    assert result.returned_count == 0
    assert len(result.scatter_data.industry) == 0
    assert len(result.scatter_data.concept) == 0


@pytest.mark.asyncio
async def test_calculate_size(db_session: AsyncSession):
    """测试气泡大小计算"""
    service = StrengthScatterService(db_session)

    # 测试有数据的情况
    size_with_data = service._calculate_size(0.5)
    assert size_with_data == 25.0  # 0.5 * 50

    # 测试 null 值
    size_null = service._calculate_size(None)
    assert size_null == 20.0  # 默认值

    # 测试最小值
    size_min = service._calculate_size(0.1)
    assert size_min == 10.0  # 最小 10


@pytest.mark.asyncio
async def test_calculate_completeness(db_session: AsyncSession):
    """测试数据完整度计算"""
    service = StrengthScatterService(db_session)

    # 测试完整数据
    completeness_full = service._calculate_completeness(0.5, 80.0)
    assert completeness_full.has_strong_ratio is True
    assert completeness_full.has_long_term is True
    assert completeness_full.completeness_percent == 100.0

    # 测试部分缺失
    completeness_partial = service._calculate_completeness(0.5, None)
    assert completeness_partial.has_strong_ratio is True
    assert completeness_partial.has_long_term is False
    assert completeness_partial.completeness_percent == 50.0

    # 测试全部缺失
    completeness_empty = service._calculate_completeness(None, None)
    assert completeness_empty.has_strong_ratio is False
    assert completeness_empty.has_long_term is False
    assert completeness_empty.completeness_percent == 0.0


@pytest.mark.asyncio
async def test_build_grade_filter(db_session: AsyncSession):
    """测试强度等级筛选条件构建"""
    service = StrengthScatterService(db_session)

    # 测试只有最低等级
    filter_min = service._build_grade_filter('B', None)
    assert filter_min is not None

    # 测试只有最高等级
    filter_max = service._build_grade_filter(None, 'A')
    assert filter_max is not None

    # 测试范围筛选
    filter_range = service._build_grade_filter('B', 'S')
    assert filter_range is not None

    # 测试无筛选
    filter_none = service._build_grade_filter(None, None)
    assert filter_none is None
