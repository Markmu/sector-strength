"""
排名 API 路由

提供排名相关的 REST API 端点。
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc, func

from src.api.deps import get_session
from src.api.schemas.strength import RankingItem, RankingResponse
from src.models.stock import Stock as StockModel
from src.models.sector import Sector as SectorModel
from src.models.sector_stock import SectorStock as SectorStockModel

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/sectors", response_model=RankingResponse)
async def get_sector_rankings(
    top_n: int = Query(20, ge=1, le=100, description="返回数量"),
    order: str = Query("desc", description="desc=强势, asc=弱势"),
    sector_type: Optional[str] = Query(None, description="板块类型筛选"),
    session: AsyncSession = Depends(get_session),
) -> RankingResponse:
    """
    获取板块排名

    返回按强度得分排序的 TOP N 板块。
    """
    # 构建查询
    stmt = select(SectorModel)

    if sector_type:
        stmt = stmt.where(SectorModel.type == sector_type)

    # 只返回有强度得分的板块
    stmt = stmt.where(SectorModel.strength_score.isnot(None))

    # 排序
    if order == "desc":
        stmt = stmt.order_by(desc(SectorModel.strength_score))
    else:
        stmt = stmt.order_by(asc(SectorModel.strength_score))

    # 限制数量
    stmt = stmt.limit(top_n)

    # 执行查询
    result = await session.execute(stmt)
    sectors = result.scalars().all()

    # 转换为排名项
    items = []
    for rank, sector in enumerate(sectors, start=1):
        items.append(
            RankingItem(
                id=str(sector.id),
                name=sector.name,
                code=sector.code,
                strength_score=sector.strength_score,
                trend_direction=sector.trend_direction,
                rank=rank,
            )
        )

    # 计算总数
    count_stmt = select(func.count()).select_from(SectorModel).where(
        SectorModel.strength_score.isnot(None)
    )
    if sector_type:
        count_stmt = count_stmt.where(SectorModel.type == sector_type)

    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    return RankingResponse(success=True, data=items, total=total, top_n=len(items))


@router.get("/stocks", response_model=RankingResponse)
async def get_stock_rankings(
    top_n: int = Query(50, ge=1, le=200, description="返回数量"),
    order: str = Query("desc", description="desc=强势, asc=弱势"),
    sector_id: Optional[str] = Query(None, description="按板块代码筛选（如 BK0001）"),
    session: AsyncSession = Depends(get_session),
) -> RankingResponse:
    """
    获取个股排名

    返回按强度得分排序的 TOP N 个股。
    """
    # 构建查询
    stmt = select(StockModel)

    # 按板块筛选（使用板块代码）
    if sector_id:
        stmt = stmt.join(SectorStockModel, StockModel.symbol == SectorStockModel.stock_code).where(
            SectorStockModel.sector_code == sector_id
        )

    # 只返回有强度得分的股票
    stmt = stmt.where(StockModel.strength_score.isnot(None))

    # 排序
    if order == "desc":
        stmt = stmt.order_by(desc(StockModel.strength_score))
    else:
        stmt = stmt.order_by(asc(StockModel.strength_score))

    # 限制数量
    stmt = stmt.limit(top_n)

    # 执行查询
    result = await session.execute(stmt)
    stocks = result.scalars().all()

    # 转换为排名项
    items = []
    for rank, stock in enumerate(stocks, start=1):
        items.append(
            RankingItem(
                id=str(stock.id),
                name=stock.name,
                code=stock.symbol,
                strength_score=stock.strength_score,
                trend_direction=stock.trend_direction,
                rank=rank,
            )
        )

    # 计算总数
    count_stmt = select(func.count()).select_from(StockModel).where(
        StockModel.strength_score.isnot(None)
    )

    if sector_id:
        count_stmt = count_stmt.join(
            SectorStockModel, StockModel.symbol == SectorStockModel.stock_code
        ).where(SectorStockModel.sector_code == sector_id)

    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    return RankingResponse(success=True, data=items, total=total, top_n=len(items))
