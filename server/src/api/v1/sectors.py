"""
板块 API 路由

提供板块相关的 REST API 端点。
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, or_

from src.api.deps import get_session
from src.api.schemas.sector import (
    SectorListItem,
    SectorDetail,
    SectorListResponse,
    SectorDetailResponse,
    SectorStocksResponse,
)
from src.api.schemas.response import PaginatedData, ApiResponse
from src.api.exceptions import NotFoundError
from src.models.sector import Sector as SectorModel
from src.models.sector_stock import SectorStock as SectorStockModel
from src.models.stock import Stock as StockModel

router = APIRouter(prefix="/sectors", tags=["sectors"])


@router.get("", response_model=SectorListResponse)
async def get_sectors(
    sector_type: Optional[str] = Query(None, description="板块类型: industry/concept"),
    sort_by: str = Query("strength_score", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
) -> SectorListResponse:
    """
    获取板块列表

    返回板块基本信息和强度得分，支持筛选、排序、分页。
    """
    # 构建查询
    stmt = select(SectorModel)

    # 筛选
    if sector_type:
        stmt = stmt.where(SectorModel.type == sector_type)

    # 排序
    sort_column = getattr(SectorModel, sort_by, SectorModel.strength_score)
    if sort_order == "desc":
        stmt = stmt.order_by(desc(sort_column))
    else:
        stmt = stmt.order_by(asc(sort_column))

    # 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    # 执行查询
    result = await session.execute(stmt)
    sectors = result.scalars().all()

    # 转换为响应模型
    items = [
        SectorListItem(
            id=str(s.id),
            code=s.code,
            name=s.name,
            type=s.type,
            description=s.description,
            strength_score=s.strength_score,
            trend_direction=s.trend_direction,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sectors
    ]

    paginated_data = PaginatedData.create(items, total, page, page_size)

    return SectorListResponse(success=True, data=paginated_data)


@router.get("/search", response_model=ApiResponse[List[dict]])
async def search_sectors(
    keyword: str = Query(..., min_length=1, description="搜索关键词（板块名称或代码）"),
    sector_type: Optional[str] = Query(None, description="板块类型: industry/concept"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量限制"),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[List[dict]]:
    """
    搜索板块

    根据板块名称或代码关键词搜索板块，支持模糊匹配。
    用于前端下拉选择框的搜索功能。
    """
    # 构建搜索查询
    stmt = select(SectorModel).where(
        or_(
            SectorModel.name.ilike(f"%{keyword}%"),
            SectorModel.code.ilike(f"%{keyword}%")
        )
    )

    # 按类型筛选
    if sector_type:
        stmt = stmt.where(SectorModel.type == sector_type)

    # 按名称排序
    stmt = stmt.order_by(asc(SectorModel.name))

    # 限制结果数量
    stmt = stmt.limit(limit)

    # 执行查询
    result = await session.execute(stmt)
    sectors = result.scalars().all()

    # 转换为响应格式
    items = [
        {
            "id": s.id,
            "code": s.code,
            "name": s.name,
            "type": s.type,
            "label": f"{s.name} ({s.code})",
            "value": s.id
        }
        for s in sectors
    ]

    return ApiResponse(success=True, data=items)


@router.get("/{sector_id}", response_model=SectorDetailResponse)
async def get_sector_detail(
    sector_id: int,
    session: AsyncSession = Depends(get_session),
) -> SectorDetailResponse:
    """
    获取板块详情

    包括板块基本信息、强度得分、成分股数量等。
    """
    # 查询板块
    stmt = select(SectorModel).where(SectorModel.id == sector_id)
    result = await session.execute(stmt)
    sector = result.scalar_one_or_none()

    if not sector:
        raise NotFoundError(f"板块 {sector_id} 不存在")

    # 统计成分股数量
    count_stmt = select(func.count()).select_from(
        SectorStockModel
    ).where(SectorStockModel.sector_code == sector.code)
    count_result = await session.execute(count_stmt)
    stock_count = count_result.scalar() or 0

    detail = SectorDetail(
        id=str(sector.id),
        code=sector.code,
        name=sector.name,
        type=sector.type,
        description=sector.description,
        strength_score=sector.strength_score,
        trend_direction=sector.trend_direction,
        stock_count=stock_count,
        created_at=sector.created_at,
        updated_at=sector.updated_at,
    )

    return SectorDetailResponse(success=True, data=detail)


@router.get("/{sector_id}/stocks", response_model=SectorStocksResponse)
async def get_sector_stocks(
    sector_id: int,
    sort_by: str = Query("strength_score", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
) -> SectorStocksResponse:
    """
    获取板块成分股

    返回指定板块的成分股列表，支持按强度排序。
    """
    # 验证板块存在并获取板块代码
    sector_stmt = select(SectorModel).where(SectorModel.id == sector_id)
    sector_result = await session.execute(sector_stmt)
    sector = sector_result.scalar_one_or_none()

    if not sector:
        raise NotFoundError(f"板块 {sector_id} 不存在")

    # 查询成分股（使用板块代码关联）
    stmt = (
        select(StockModel)
        .join(SectorStockModel, StockModel.symbol == SectorStockModel.stock_code)
        .where(SectorStockModel.sector_code == sector.code)
    )

    # 排序
    sort_column = getattr(StockModel, sort_by, StockModel.strength_score)
    if sort_order == "desc":
        stmt = stmt.order_by(desc(sort_column))
    else:
        stmt = stmt.order_by(asc(sort_column))

    # 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    # 执行查询
    result = await session.execute(stmt)
    stocks = result.scalars().all()

    # 转换为响应格式
    items = [
        {
            "id": str(s.id),
            "symbol": s.symbol,
            "name": s.name,
            "current_price": s.current_price,
            "market_cap": s.market_cap,
            "strength_score": s.strength_score,
            "trend_direction": s.trend_direction,
        }
        for s in stocks
    ]

    paginated_data = PaginatedData.create(items, total, page, page_size)

    return SectorStocksResponse(success=True, data=paginated_data)
