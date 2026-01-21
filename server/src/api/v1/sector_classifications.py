"""
板块分类 API 路由

提供板块分类结果相关的 REST API 端点。
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.api.deps import get_session, get_current_user, require_admin
from src.models.user import User
from src.api.schemas.sector_classification import (
    SectorClassificationResponse,
    SectorClassificationListResponse
)
from src.models.sector_classification import SectorClassification
from src.services.classification_cache import classification_cache

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
    # 生成缓存键
    cache_key = f"classification:all:{skip}:{limit}"

    # 尝试从缓存获取（使用元组返回格式）
    hit, cached_data = classification_cache.get(cache_key)
    if hit:
        return cached_data

    # 缓存未命中，查询数据库
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

    response = SectorClassificationListResponse(data=data, total=total)

    # 存入缓存
    classification_cache.set(cache_key, response)

    return response


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
    # 生成缓存键
    cache_key = f"classification:{sector_id}"

    # 尝试从缓存获取（使用元组返回格式）
    hit, cached_data = classification_cache.get(cache_key)
    if hit:
        return cached_data

    # 缓存未命中，查询数据库
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

    # 转换为响应模型
    response = SectorClassificationResponse.model_validate(classification)

    # 存入缓存
    classification_cache.set(cache_key, response)

    return response


@router.post(
    "/cache/clear",
    status_code=status.HTTP_200_OK,
    summary="清除分类缓存",
    description="清除板块分类缓存，需要管理员权限"
)
async def clear_classification_cache(
    sector_id: Optional[int] = Query(None, description="板块ID（可选），如果不提供则清除所有缓存"),
    current_user: User = Depends(require_admin)
) -> dict:
    """
    清除分类缓存

    参数:
        sector_id: 板块ID（可选），如果不提供则清除所有缓存
        current_user: 当前认证用户（自动注入，需要管理员权限）

    返回:
        清除结果

    异常:
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
    """
    if sector_id is None:
        # 清除所有分类缓存
        count = classification_cache.clear_pattern("classification:")
        return {"message": f"已清除所有分类缓存，共 {count} 条"}
    else:
        # 清除单个板块缓存
        cache_key = f"classification:{sector_id}"
        count = classification_cache.clear(cache_key)
        # 同时清除相关的分页缓存
        classification_cache.clear_pattern("classification:all:")
        return {"message": f"已清除板块 {sector_id} 的缓存，共 {count + 1} 条（包含分页缓存）"}


@router.get(
    "/cache/stats",
    response_model=dict,
    summary="获取缓存统计",
    description="获取分类缓存统计信息，需要管理员权限"
)
async def get_cache_stats(
    current_user: User = Depends(require_admin)
) -> dict:
    """
    获取缓存统计信息

    参数:
        current_user: 当前认证用户（自动注入，需要管理员权限）

    返回:
        缓存统计信息

    异常:
        HTTPException 401: 未认证
        HTTPException 403: 权限不足
    """
    return classification_cache.get_stats()
