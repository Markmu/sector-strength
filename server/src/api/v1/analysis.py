"""
分析 API 路由

提供数据分析和可视化相关的 REST API 端点。
"""

from typing import Optional
from datetime import date
from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, get_current_user
from src.models.user import User
from src.api.schemas.response import ApiResponse
from src.api.schemas.strength import SectorScatterResponse
from src.api.schemas.grade_table import SectorGradeTableResponse, SectorDistributionResponse
from src.services.strength_scatter_service import StrengthScatterService
from src.services.strength_grade_table_service import StrengthGradeTableService
from src.services.sector_distribution_service import SectorDistributionService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/sector-scatter", response_model=ApiResponse[SectorScatterResponse])
async def get_sector_scatter_data(
    x_axis: str = Query("short", description="X轴维度: short/medium/long/composite"),
    y_axis: str = Query("medium", description="Y轴维度: short/medium/long/composite"),
    sector_type: Optional[str] = Query(None, description="板块类型: industry/concept"),
    min_grade: Optional[str] = Query(None, description="最低等级: D/C/B/A/A+/S/S+"),
    max_grade: Optional[str] = Query(None, description="最高等级: D/C/B/A/A+/S/S+"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    limit: int = Query(200, ge=1, le=500, description="每页数量"),
    calc_date: Optional[date] = Query(None, description="计算日期，默认为最新"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[SectorScatterResponse]:
    """
    获取板块强度散点图数据

    返回用于散点图可视化的板块强度数据，支持多维度的强度分析。

    **维度说明:**
    - **short**: 短期强度 (short_term_score) - 反映近期走势
    - **medium**: 中期强度 (medium_term_score) - 反映中期趋势
    - **long**: 长期强度 (long_term_score) - 反映长期趋势
    - **composite**: 综合强度 (score) - 综合评分

    **散点图数据结构:**
    - **X轴**: 选定的 X 轴维度数值
    - **Y轴**: 选定的 Y 轴维度数值
    - **气泡大小**: 强势股占比 (strong_stock_ratio)
    - **气泡颜色**: 长期强度 (long_term_score)
    - **气泡形状**: 行业板块=圆形，概念板块=菱形

    Args:
        x_axis: X轴维度
        y_axis: Y轴维度
        sector_type: 板块类型筛选
        min_grade: 最低强度等级
        max_grade: 最高强度等级
        offset: 分页偏移（默认 0）
        limit: 每页数量（默认 200，最大 500）
        calc_date: 计算日期，None 表示最新数据
        session: 数据库会话

    Returns:
        板块散点图响应数据
    """
    service = StrengthScatterService(session)

    result = await service.get_scatter_data(
        x_axis=x_axis,
        y_axis=y_axis,
        sector_type=sector_type,
        min_grade=min_grade,
        max_grade=max_grade,
        offset=offset,
        limit=limit,
        calc_date=calc_date,
    )

    return ApiResponse(success=True, data=result)


@router.get("/sector-grade-table", response_model=ApiResponse[SectorGradeTableResponse])
async def get_sector_grade_table_data(
    sector_type: Optional[str] = Query(None, description="板块类型: industry/concept"),
    calc_date: Optional[date] = Query(None, description="计算日期，默认为最新"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[SectorGradeTableResponse]:
    """
    获取板块等级表格数据

    返回按强度等级分组的板块数据，以表格形式展示各等级的板块数量和详情。

    **数据结构:**
    - 按等级分组 (S+, S, A+, A, B+, B, C, D)
    - 每个等级显示行业板块和概念板块的数量
    - 可展开查看每个等级下的具体板块列表

    **板块数据包含:**
    - 基本信息: 代码、名称、类型
    - 强度得分: 综合、短期、中期、长期
    - 强度等级和排名
    - 强势股占比

    Args:
        sector_type: 板块类型筛选 (industry/concept)，None 表示全部
        calc_date: 计算日期，None 表示最新数据
        session: 数据库会话

    Returns:
        板块等级表格响应数据
    """
    service = StrengthGradeTableService(session)

    result = await service.get_grade_table_data(
        sector_type=sector_type,
        calc_date=calc_date,
    )

    return ApiResponse(success=True, data=result)


@router.get("/sector-distribution", response_model=ApiResponse[SectorDistributionResponse])
async def get_sector_distribution(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[SectorDistributionResponse]:
    """
    获取板块类型分布统计

    返回最新日期的板块类型分布数据，不受筛选条件影响。

    **数据说明:**
    - 返回所有板块的整体类型分布统计
    - 不受板块类型筛选影响
    - 始终返回最新日期的数据

    **返回数据:**
    - industry_count: 行业板块总数
    - concept_count: 概念板块总数
    - total_count: 板块总数
    - date: 数据日期

    Args:
        session: 数据库会话

    Returns:
        板块类型分布响应数据
    """
    service = SectorDistributionService(session)

    result = await service.get_sector_distribution()

    return ApiResponse(success=True, data=result)