"""
个股 API 路由

提供个股相关的 REST API 端点。
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, or_

from src.api.deps import get_session
from src.api.schemas.stock import (
    StockListItem,
    StockDetail,
    StockListResponse,
    StockDetailResponse,
)
from src.api.schemas.response import PaginatedData
from src.api.exceptions import NotFoundError
from src.models.stock import Stock as StockModel
from src.models.sector_stock import SectorStock as SectorStockModel
from src.models.sector import Sector as SectorModel

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=StockListResponse)
async def get_stocks(
    sector_id: Optional[str] = Query(None, description="按板块代码筛选（如 BK0001）"),
    search: Optional[str] = Query(None, description="搜索股票代码或名称"),
    sort_by: str = Query("strength_score", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
) -> StockListResponse:
    """
    获取个股列表

    支持按板块筛选、搜索、排序、分页。
    """
    # 构建查询
    stmt = select(StockModel)

    # 按板块筛选（使用板块代码）
    if sector_id:
        stmt = stmt.join(SectorStockModel, StockModel.symbol == SectorStockModel.stock_code).where(
            SectorStockModel.sector_code == sector_id
        )

    # 搜索
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                StockModel.symbol.ilike(search_pattern),
                StockModel.name.ilike(search_pattern),
            )
        )

    # 排序
    sort_column = getattr(StockModel, sort_by, StockModel.strength_score)
    if sort_column is None:
        sort_column = StockModel.symbol

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

    # 转换为响应模型
    items = [
        StockListItem(
            id=str(s.id),
            symbol=s.symbol,
            name=s.name,
            current_price=s.current_price,
            market_cap=s.market_cap,
            strength_score=s.strength_score,
            trend_direction=s.trend_direction,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in stocks
    ]

    paginated_data = PaginatedData.create(items, total, page, page_size)

    return StockListResponse(success=True, data=paginated_data)


@router.get("/{stock_id}", response_model=StockDetailResponse)
async def get_stock_detail(
    stock_id: str,
    session: AsyncSession = Depends(get_session),
) -> StockDetailResponse:
    """
    获取个股详情

    包括个股基本信息、强度得分、所属板块列表等。
    """
    # 查询股票
    stmt = select(StockModel).where(StockModel.id == stock_id)
    result = await session.execute(stmt)
    stock = result.scalar_one_or_none()

    if not stock:
        raise NotFoundError(f"股票 {stock_id} 不存在")

    # 查询所属板块
    sector_stmt = (
        select(SectorModel)
        .join(SectorStockModel, SectorModel.code == SectorStockModel.sector_code)
        .where(SectorStockModel.stock_code == stock.symbol)
    )
    sector_result = await session.execute(sector_stmt)
    sectors = sector_result.scalars().all()

    sectors_data = [
        {
            "id": str(s.id),
            "code": s.code,
            "name": s.name,
            "type": s.type,
        }
        for s in sectors
    ]

    detail = StockDetail(
        id=str(stock.id),
        symbol=stock.symbol,
        name=stock.name,
        current_price=stock.current_price,
        market_cap=stock.market_cap,
        strength_score=stock.strength_score,
        trend_direction=stock.trend_direction,
        sectors=sectors_data,
        created_at=stock.created_at,
        updated_at=stock.updated_at,
    )

    return StockDetailResponse(success=True, data=detail)
