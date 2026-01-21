"""
板块分类 API 路由

提供板块分类结果相关的 REST API 端点。
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.api.deps import get_session, get_current_user
from src.models.user import User
from src.api.schemas.sector_classification import (
    SectorClassificationResponse,
    SectorClassificationListResponse
)
from src.models.sector_classification import SectorClassification

router = APIRouter(prefix="/sector-classifications", tags=["sector-classifications"])


@router.get(
    "",
    response_model=SectorClassificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="获取所有板块分类结果",
    description="返回系统中所有板块的强弱分类数据，包括分类级别、状态、价格等信息"
)
async def get_sector_classifications(
    skip: int = Query(0, ge=0, description="跳过的记录数（分页）"),
    limit: int = Query(100, ge=1, le=100, description="返回的最大记录数（分页）"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> SectorClassificationListResponse:
    """
    获取所有板块分类结果

    参数:
        skip: 跳过的记录数（分页）
        limit: 返回的最大记录数（分页）
        current_user: 当前认证用户（自动注入）
        session: 数据库会话（自动注入）

    返回:
        包含分类数据列表和总数的响应

    异常:
        HTTPException 401: 未认证
    """
    # 计算总数
    count_stmt = select(func.count()).select_from(SectorClassification)
    count_result = await session.execute(count_stmt)
    total = count_result.scalar() or 0

    # 查询分类数据，按分类日期降序、板块ID排序
    stmt = select(SectorClassification).order_by(
        SectorClassification.classification_date.desc(),
        SectorClassification.sector_id
    ).offset(skip).limit(limit)

    result = await session.execute(stmt)
    classifications = result.scalars().all()

    # 转换为响应模型
    data = [
        SectorClassificationResponse.model_validate(classification)
        for classification in classifications
    ]

    return SectorClassificationListResponse(data=data, total=total)


@router.get(
    "/{sector_id}",
    response_model=SectorClassificationResponse,
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "板块不存在"}},
    summary="获取单个板块分类结果",
    description="根据板块ID返回该板块的强弱分类详情"
)
async def get_sector_classification(
    sector_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> SectorClassificationResponse:
    """
    获取单个板块分类结果

    参数:
        sector_id: 板块ID
        current_user: 当前认证用户（自动注入）
        session: 数据库会话（自动注入）

    返回:
        板块分类详情

    异常:
        HTTPException 401: 未认证
        HTTPException 404: 板块不存在
    """
    # 查询最新的分类数据（按分类日期降序，取第一条）
    stmt = select(SectorClassification).where(
        SectorClassification.sector_id == sector_id
    ).order_by(
        SectorClassification.classification_date.desc()
    ).limit(1)

    result = await session.execute(stmt)
    classification = result.scalar_one_or_none()

    if classification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"板块 {sector_id} 的分类数据不存在"
        )

    return SectorClassificationResponse.model_validate(classification)
