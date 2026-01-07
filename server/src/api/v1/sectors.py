"""
板块 API 路由

提供板块相关的 REST API 端点。
"""

from typing import Optional, List
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, or_, and_

from src.api.deps import get_session, get_current_user
from src.models.user import User
from src.api.schemas.sector import (
    SectorListItem,
    SectorDetail,
    SectorListResponse,
    SectorDetailResponse,
    SectorStocksResponse,
)
from src.api.schemas.response import PaginatedData, ApiResponse
from src.api.exceptions import NotFoundError
from src.api.schemas.strength import (
    SectorStrengthResponse,
    StrengthHistoryResponse,
    StrengthHistoryData,
    SectorStrengthHistoryResponse,
    SectorStrengthHistoryPoint,
    SectorMAHistoryResponse,
    SectorMAHistoryPoint,
)
from src.models.sector import Sector as SectorModel
from src.models.sector_stock import SectorStock as SectorStockModel
from src.models.stock import Stock as StockModel
from src.models.strength_score import StrengthScore as StrengthScoreModel
from src.models.moving_average_data import MovingAverageData as MovingAverageDataModel
from src.services.strength_service_v2 import StrengthServiceV2
from src.services.strength_history_service import StrengthHistoryService

router = APIRouter(prefix="/sectors", tags=["sectors"])


@router.get("", response_model=SectorListResponse)
async def get_sectors(
    sector_type: Optional[str] = Query(None, description="板块类型: industry/concept"),
    min_strength_score: Optional[float] = Query(None, ge=0, le=100, description="最小强度分数"),
    max_strength_score: Optional[float] = Query(None, ge=0, le=100, description="最大强度分数"),
    sort_by: str = Query("strength_score", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SectorListResponse:
    """
    获取板块列表

    返回板块基本信息和强度得分，支持筛选、排序、分页。
    强度得分从 strength_scores 表中获取最新一天的数据。
    """
    # 使用 CTE 获取每个板块的最新强度分数
    latest_strength_cte = (
        select(
            StrengthScoreModel.entity_id,
            StrengthScoreModel.score,
            func.row_number().over(
                partition_by=StrengthScoreModel.entity_id,
                order_by=desc(StrengthScoreModel.date)
            ).label('rn')
        )
        .where(StrengthScoreModel.entity_type == 'sector')
        .subquery()
    )

    # 只保留每个板块的最新记录（rn = 1）
    latest_strength = (
        select(
            latest_strength_cte.c.entity_id,
            latest_strength_cte.c.score
        )
        .where(latest_strength_cte.c.rn == 1)
        .subquery()
    )

    # 主查询：关联板块和最新强度分数
    stmt = select(
        SectorModel,
        func.coalesce(latest_strength.c.score, 0).label('strength_score')
    ).outerjoin(
        latest_strength,
        SectorModel.id == latest_strength.c.entity_id
    )

    # 按类型筛选
    if sector_type:
        stmt = stmt.where(SectorModel.type == sector_type)

    # 按分数区间筛选（使用 JOIN 后的分数）
    if min_strength_score is not None:
        stmt = stmt.where(func.coalesce(latest_strength.c.score, 0) >= min_strength_score)
    if max_strength_score is not None:
        stmt = stmt.where(func.coalesce(latest_strength.c.score, 0) <= max_strength_score)

    # 排序（使用 JOIN 后的分数）
    if sort_by == "strength_score":
        score_column = func.coalesce(latest_strength.c.score, 0)
        if sort_order == "desc":
            stmt = stmt.order_by(desc(score_column))
        else:
            stmt = stmt.order_by(asc(score_column))
    else:
        sort_column = getattr(SectorModel, sort_by, SectorModel.id)
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
    rows = result.all()

    # 转换为响应模型
    items = []
    for row in rows:
        sector = row[0]
        strength_score = row[1]
        items.append(
            SectorListItem(
                id=str(sector.id),
                code=sector.code,
                name=sector.name,
                type=sector.type,
                description=sector.description,
                strength_score=float(strength_score) if strength_score is not None else 0,
                trend_direction=sector.trend_direction,
                created_at=sector.created_at,
                updated_at=sector.updated_at,
            )
        )

    paginated_data = PaginatedData.create(items, total, page, page_size)

    return SectorListResponse(success=True, data=paginated_data)


@router.get("/search", response_model=ApiResponse[List[dict]])
async def search_sectors(
    keyword: str = Query(..., min_length=1, description="搜索关键词（板块名称或代码）"),
    sector_type: Optional[str] = Query(None, description="板块类型: industry/concept"),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量限制"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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


# ============== V2 强度端点 (Story 10.4) ==============

@router.get("/{sector_id}/strength", response_model=SectorStrengthResponse)
async def get_sector_strength(
    sector_id: int,
    calc_date: Optional[date] = Query(None, description="计算日期，默认为最新"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SectorStrengthResponse:
    """
    获取板块强度数据 (V2)

    使用 MA 系统强度计算算法，返回板块的强度得分、均线排列、价格位置等信息。

    Args:
        sector_id: 板块ID
        calc_date: 计算日期，None 表示使用最新数据

    Returns:
        板块强度响应
    """
    # 查询板块是否存在
    stmt = select(SectorModel).where(SectorModel.id == sector_id)
    result = await session.execute(stmt)
    sector = result.scalar_one_or_none()

    if not sector:
        raise NotFoundError(f"板块 {sector_id} 不存在")

    # 查询强度数据
    strength_stmt = select(StrengthScoreModel).where(
        StrengthScoreModel.entity_type == "sector",
        StrengthScoreModel.entity_id == sector.id,
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
        calc_result = await service.calculate_sector_strength(sector.id, calc_date)

        if not calc_result.get("success"):
            raise NotFoundError(f"强度数据不可用: {calc_result.get('error')}")

        # 重新查询
        strength_result = await session.execute(strength_stmt)
        strength_data = strength_result.scalar_one_or_none()

    # 计算板块统计信息
    stock_count_stmt = select(func.count()).select_from(
        SectorStockModel
    ).where(SectorStockModel.sector_code == sector.code)
    stock_count_result = await session.execute(stock_count_stmt)
    stock_count = stock_count_result.scalar() or 0

    # 统计强势股数量（分数>60）
    strong_count_stmt = select(func.count()).select_from(
        StrengthScoreModel
    ).join(
        SectorStockModel, StrengthScoreModel.symbol == SectorStockModel.stock_code
    ).where(
        SectorStockModel.sector_code == sector.code,
        StrengthScoreModel.period == "all",
        StrengthScoreModel.date == strength_data.date,
        StrengthScoreModel.score > 60
    )
    strong_count_result = await session.execute(strong_count_stmt)
    strong_stock_count = strong_count_result.scalar() or 0

    strong_stock_ratio = round(strong_stock_count / stock_count * 100, 2) if stock_count > 0 else 0.0

    return SectorStrengthResponse(
        entity_type="sector",
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
        sector_name=sector.name,
        stock_count=stock_count,
        strong_stock_count=strong_stock_count,
        strong_stock_ratio=strong_stock_ratio,
    )


@router.get("/{sector_id}/strength/history", response_model=StrengthHistoryResponse)
async def get_sector_strength_history(
    sector_id: int,
    days: int = Query(30, ge=1, le=365, description="查询天数"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StrengthHistoryResponse:
    """
    获取板块强度历史数据

    Args:
        sector_id: 板块ID
        days: 查询天数（默认30天，最多365天）

    Returns:
        历史数据响应
    """
    # 查询板块是否存在
    stmt = select(SectorModel).where(SectorModel.id == sector_id)
    result = await session.execute(stmt)
    sector = result.scalar_one_or_none()

    if not sector:
        raise NotFoundError(f"板块 {sector_id} 不存在")

    # 使用历史数据服务
    history_service = StrengthHistoryService(session)
    history_data = await history_service.get_sector_history(sector.id, days)

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
        symbol=sector.code,
        name=sector.name,
        start_date=start_date,
        end_date=end_date,
        total_days=len(data_points),
        data_points=data_points,
    )


# ============== 板块分析图表端点 (Story 4-2) ==============


@router.get("/{sector_id}/strength-history", response_model=SectorStrengthHistoryResponse)
async def get_sector_strength_history_for_charts(
    sector_id: int,
    start_date: Optional[date] = Query(None, description="开始日期 (ISO 8601), 默认为2个月前"),
    end_date: Optional[date] = Query(None, description="结束日期 (ISO 8601), 默认为今天"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SectorStrengthHistoryResponse:
    """
    获取板块强度历史数据 (用于图表)

    返回指定时间范围内的板块强度得分和价格历史数据。

    Args:
        sector_id: 板块ID
        start_date: 开始日期 (默认为2个月前)
        end_date: 结束日期 (默认为今天)

    Returns:
        板块强度历史数据
    """
    # 查询板块是否存在
    stmt = select(SectorModel).where(SectorModel.id == sector_id)
    result = await session.execute(stmt)
    sector = result.scalar_one_or_none()

    if not sector:
        raise NotFoundError(f"板块 {sector_id} 不存在")

    # 设置默认日期范围
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=60)  # 默认2个月

    # 查询强度历史数据
    stmt = select(StrengthScoreModel).where(
        StrengthScoreModel.entity_type == "sector",
        StrengthScoreModel.entity_id == sector_id,
        StrengthScoreModel.period == "all",
        StrengthScoreModel.date >= start_date,
        StrengthScoreModel.date <= end_date,
    ).order_by(asc(StrengthScoreModel.date))

    result = await session.execute(stmt)
    history_data = result.scalars().all()

    # 构建响应
    data_points = [
        SectorStrengthHistoryPoint(
            date=item.date,
            score=float(item.score) if item.score is not None else None,
            short_term_score=float(item.short_term_score) if item.short_term_score is not None else None,
            medium_term_score=float(item.medium_term_score) if item.medium_term_score is not None else None,
            long_term_score=float(item.long_term_score) if item.long_term_score is not None else None,
            current_price=float(item.current_price) if item.current_price is not None else None,
        )
        for item in history_data
    ]

    return SectorStrengthHistoryResponse(
        sector_id=str(sector_id),
        sector_name=sector.name,
        data=data_points,
    )


@router.get("/{sector_id}/ma-history", response_model=SectorMAHistoryResponse)
async def get_sector_ma_history(
    sector_id: int,
    start_date: Optional[date] = Query(None, description="开始日期 (ISO 8601), 默认为2个月前"),
    end_date: Optional[date] = Query(None, description="结束日期 (ISO 8601), 默认为今天"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SectorMAHistoryResponse:
    """
    获取板块均线历史数据 (用于图表)

    返回指定时间范围内的板块均线数据(MA5/10/20/30/60/120/240)和当前价格。

    Args:
        sector_id: 板块ID
        start_date: 开始日期 (默认为2个月前)
        end_date: 结束日期 (默认为今天)

    Returns:
        板块均线历史数据
    """
    # 查询板块是否存在
    stmt = select(SectorModel).where(SectorModel.id == sector_id)
    result = await session.execute(stmt)
    sector = result.scalar_one_or_none()

    if not sector:
        raise NotFoundError(f"板块 {sector_id} 不存在")

    # 设置默认日期范围
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=60)  # 默认2个月

    # 从 strength_scores 表获取数据 (因为均线数据已经在该表中)
    stmt = select(StrengthScoreModel).where(
        StrengthScoreModel.entity_type == "sector",
        StrengthScoreModel.entity_id == sector_id,
        StrengthScoreModel.period == "all",
        StrengthScoreModel.date >= start_date,
        StrengthScoreModel.date <= end_date,
    ).order_by(asc(StrengthScoreModel.date))

    result = await session.execute(stmt)
    history_data = result.scalars().all()

    # 构建响应
    data_points = [
        SectorMAHistoryPoint(
            date=item.date,
            current_price=float(item.current_price) if item.current_price is not None else None,
            ma5=float(item.ma5) if item.ma5 is not None else None,
            ma10=float(item.ma10) if item.ma10 is not None else None,
            ma20=float(item.ma20) if item.ma20 is not None else None,
            ma30=float(item.ma30) if item.ma30 is not None else None,
            ma60=float(item.ma60) if item.ma60 is not None else None,
            ma90=float(item.ma90) if item.ma90 is not None else None,
            ma120=float(item.ma120) if item.ma120 is not None else None,
            ma240=float(item.ma240) if item.ma240 is not None else None,
        )
        for item in history_data
    ]

    return SectorMAHistoryResponse(
        sector_id=str(sector_id),
        sector_name=sector.name,
        data=data_points,
    )
