"""
个股 API 路由

提供个股相关的 REST API 端点。
"""

from typing import Optional, List
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, or_

from src.api.deps import get_session, get_current_user
from src.models.user import User
from src.api.schemas.stock import (
    StockListItem,
    StockDetail,
    StockListResponse,
    StockDetailResponse,
)
from src.api.schemas.response import PaginatedData
from src.api.exceptions import NotFoundError
from src.api.schemas.strength import (
    StockStrengthResponse,
    StrengthHistoryResponse,
    StrengthHistoryData,
)
from src.models.stock import Stock as StockModel
from src.models.sector_stock import SectorStock as SectorStockModel
from src.models.sector import Sector as SectorModel
from src.models.strength_score import StrengthScore as StrengthScoreModel
from src.services.strength_service_v2 import StrengthServiceV2
from src.services.strength_history_service import StrengthHistoryService

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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
) -> StockDetailResponse:
    """
    获取个股详情

    包括个股基本信息、强度得分、所属板块列表等。
    """
    if not stock_id.isdigit():
        raise NotFoundError(f"股票 {stock_id} 不存在")
    stock_id_int = int(stock_id)

    # 查询股票
    stmt = select(StockModel).where(StockModel.id == stock_id_int)
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


# ============== V2 强度端点 (Story 10.4) ==============

@router.get("/{stock_id}/strength", response_model=StockStrengthResponse)
async def get_stock_strength(
    stock_id: str,
    calc_date: Optional[date] = Query(None, description="计算日期，默认为最新"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StockStrengthResponse:
    """
    获取个股强度数据 (V2)

    使用 MA 系统强度计算算法，返回个股的强度得分、均线排列、价格位置等信息。

    Args:
        stock_id: 股票ID
        calc_date: 计算日期，None 表示使用最新数据

    Returns:
        个股强度响应
    """
    if not stock_id.isdigit():
        raise NotFoundError(f"股票 {stock_id} 不存在")
    stock_id_int = int(stock_id)

    # 查询股票是否存在
    stmt = select(StockModel).where(StockModel.id == stock_id_int)
    result = await session.execute(stmt)
    stock = result.scalar_one_or_none()

    if not stock:
        raise NotFoundError(f"股票 {stock_id} 不存在")

    # 查询强度数据
    strength_stmt = select(StrengthScoreModel).where(
        StrengthScoreModel.entity_type == "stock",
        StrengthScoreModel.entity_id == stock.id,
        StrengthScoreModel.period == "all"
    )

    if calc_date:
        strength_stmt = strength_stmt.where(StrengthScoreModel.date == calc_date)
    else:
        # 获取最新日期的数据
        from sqlalchemy import desc as sql_desc
        strength_stmt = strength_stmt.order_by(sql_desc(StrengthScoreModel.date)).limit(1)

    strength_result = await session.execute(strength_stmt)
    strength_data = strength_result.scalar_one_or_none()

    if not strength_data:
        # 如果没有强度数据，尝试计算
        service = StrengthServiceV2(session)
        calc_result = await service.calculate_stock_strength(stock.id, calc_date)

        if not calc_result.get("success"):
            raise NotFoundError(f"强度数据不可用: {calc_result.get('error')}")

        # 重新查询
        strength_result = await session.execute(strength_stmt)
        strength_data = strength_result.scalar_one_or_none()

    return StockStrengthResponse(
        entity_type="stock",
        entity_id=strength_data.entity_id,
        symbol=strength_data.symbol,
        date=strength_data.date,
        period=strength_data.period,
        score=strength_data.score,
        price_position_score=strength_data.price_position_score,
        ma_alignment_score=strength_data.ma_alignment_score,
        ma_alignment_state=strength_data.ma_alignment_state,
        short_term_score=strength_data.short_term_score,
        medium_term_score=strength_data.medium_term_score,
        long_term_score=strength_data.long_term_score,
        current_price=strength_data.current_price,
        ma5=strength_data.ma5,
        ma10=strength_data.ma10,
        ma20=strength_data.ma20,
        ma30=strength_data.ma30,
        ma60=strength_data.ma60,
        ma90=strength_data.ma90,
        ma120=strength_data.ma120,
        ma240=strength_data.ma240,
        price_above_ma5=strength_data.price_above_ma5,
        price_above_ma10=strength_data.price_above_ma10,
        price_above_ma20=strength_data.price_above_ma20,
        price_above_ma30=strength_data.price_above_ma30,
        price_above_ma60=strength_data.price_above_ma60,
        price_above_ma90=strength_data.price_above_ma90,
        price_above_ma120=strength_data.price_above_ma120,
        price_above_ma240=strength_data.price_above_ma240,
        rank=strength_data.rank,
        percentile=strength_data.percentile,
        change_rate_1d=strength_data.change_rate_1d,
        change_rate_5d=strength_data.change_rate_5d,
        strength_grade=strength_data.strength_grade,
        stock_name=stock.name,
    )


@router.get("/symbol/{symbol}/strength", response_model=StockStrengthResponse)
async def get_stock_strength_by_symbol(
    symbol: str,
    calc_date: Optional[date] = Query(None, description="计算日期，默认为最新"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StockStrengthResponse:
    """
    通过股票代码获取强度数据 (V2)

    Args:
        symbol: 股票代码
        calc_date: 计算日期，None 表示使用最新数据

    Returns:
        个股强度响应
    """
    # 通过 symbol 查询股票
    stmt = select(StockModel).where(StockModel.symbol == symbol)
    result = await session.execute(stmt)
    stock = result.scalar_one_or_none()

    if not stock:
        raise NotFoundError(f"股票代码 {symbol} 不存在")

    # 复用上面的逻辑（传入当前用户）
    return await get_stock_strength(stock.id, calc_date, session, current_user)


@router.get("/{stock_id}/strength/history", response_model=StrengthHistoryResponse)
async def get_stock_strength_history(
    stock_id: str,
    days: int = Query(30, ge=1, le=365, description="查询天数"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StrengthHistoryResponse:
    """
    获取个股强度历史数据

    Args:
        stock_id: 股票ID
        days: 查询天数（默认30天，最多365天）

    Returns:
        历史数据响应
    """
    if not stock_id.isdigit():
        raise NotFoundError(f"股票 {stock_id} 不存在")
    stock_id_int = int(stock_id)

    # 查询股票是否存在
    stmt = select(StockModel).where(StockModel.id == stock_id_int)
    result = await session.execute(stmt)
    stock = result.scalar_one_or_none()

    if not stock:
        raise NotFoundError(f"股票 {stock_id} 不存在")

    # 使用历史数据服务
    history_service = StrengthHistoryService(session)
    history_data = await history_service.get_stock_history(stock.id, days)

    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)

    # 构建响应
    data_points = [
        StrengthHistoryData(
            date=item.date,
            score=item.score,
            rank=item.rank,
            percentile=item.percentile,
            strength_grade=item.strength_grade,
            price_position_score=item.price_position_score,
            ma_alignment_score=item.ma_alignment_score,
            ma_alignment_state=item.ma_alignment_state,
            short_term_score=item.short_term_score,
            medium_term_score=item.medium_term_score,
            long_term_score=item.long_term_score,
            current_price=item.current_price,
        )
        for item in history_data
    ]

    return StrengthHistoryResponse(
        symbol=stock.symbol,
        name=stock.name,
        start_date=start_date,
        end_date=end_date,
        total_days=len(data_points),
        data_points=data_points,
    )
