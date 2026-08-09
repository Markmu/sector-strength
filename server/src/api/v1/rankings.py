"""
排名 API 路由

提供排名相关的 REST API 端点。
"""

from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc, func, and_
from pydantic import BaseModel

from src.api.deps import get_session, get_current_user
from src.models.user import User
from src.api.schemas.strength import (
    RankingItem, RankingResponse,  # V1 schema (向后兼容)
    StrengthRankingItem,
    StrengthRankingResponse,
    StrengthStatsResponse,
    StrengthGradeDistribution,
    BatchStrengthRequest,
    BatchStrengthResponse,
    BatchCalculationItem,
)
from src.models.stock import Stock as StockModel
from src.services.data_acquisition.models import A_STOCK_EXCHANGES
from src.models.sector import Sector as SectorModel
from src.models.sector_stock import SectorStock as SectorStockModel
from src.models.strength_score import StrengthScore as StrengthScoreModel
from src.models.stock_strength_scores import StockStrengthScore as StockStrengthScoreModel
from src.services.strength_service_v2 import StrengthServiceV2
from src.services.ranking_service import RankingService

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("/sectors", response_model=RankingResponse)
async def get_sector_rankings(
    top_n: int = Query(20, ge=1, le=100, description="返回数量"),
    order: str = Query("desc", description="desc=强势, asc=弱势"),
    sector_type: Optional[str] = Query(
        None, description="板块类型筛选: industry/concept/region/sw_industry"
    ),
    level: Optional[str] = Query(
        None, description="申万行业层级筛选: L1/L2/L3（仅 sector_type=sw_industry 时生效）"
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> RankingResponse:
    """
    获取板块排名

    返回按强度得分排序的 TOP N 板块。
    """
    # 构建查询
    stmt = select(SectorModel)

    if sector_type:
        stmt = stmt.where(SectorModel.type == sector_type)
    if level:
        stmt = stmt.where(SectorModel.level == level)

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
    current_user: User = Depends(get_current_user),
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

    # 只返回有强度得分的股票（且仅 A 股，排除港股）
    stmt = stmt.where(
        StockModel.strength_score.isnot(None),
        StockModel.exchange.in_(A_STOCK_EXCHANGES),
    )

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
        StockModel.strength_score.isnot(None),
        StockModel.exchange.in_(A_STOCK_EXCHANGES),
    )

    if sector_id:
        count_stmt = count_stmt.join(
            SectorStockModel, StockModel.symbol == SectorStockModel.stock_code
        ).where(SectorStockModel.sector_code == sector_id)

    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    return RankingResponse(success=True, data=items, total=total, top_n=len(items))


# ============== V2 强度排名端点 (Story 10.4) ==============

@router.get("/v2/stocks", response_model=StrengthRankingResponse)
async def get_stock_rankings_v2(
    calc_date: Optional[date] = Query(None, description="计算日期，默认为最新"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StrengthRankingResponse:
    """获取个股强度排名 (V2)"""
    # 切换到股票独立表 StockStrengthScore（无 entity_type、无 period，stock_id 替代 entity_id）
    stmt = select(StockStrengthScoreModel, StockModel).join(
        StockModel, StockStrengthScoreModel.stock_id == StockModel.id
    )

    if calc_date:
        stmt = stmt.where(StockStrengthScoreModel.date == calc_date)
    else:
        from sqlalchemy import desc as sql_desc
        latest_stmt = select(StockStrengthScoreModel.date).order_by(
            sql_desc(StockStrengthScoreModel.date)
        ).limit(1)
        latest_result = await session.execute(latest_stmt)
        latest_date = latest_result.scalar_one_or_none()
        if latest_date:
            stmt = stmt.where(StockStrengthScoreModel.date == latest_date)

    stmt = stmt.order_by(desc(StockStrengthScoreModel.score))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    rows = result.all()

    rankings = []
    for strength, stock in rows:
        rankings.append(
            StrengthRankingItem(
                rank=strength.rank or (offset + len(rankings) + 1),
                entity_id=strength.stock_id,
                symbol=strength.symbol,
                name=stock.name,
                score=strength.score,
                percentile=getattr(strength, "percentile", None),
                strength_grade=strength.strength_grade,
                change_rate_1d=strength.change_rate_1d,
            )
        )

    query_date = calc_date
    if not query_date and rows:
        query_date = rows[0][0].date

    return StrengthRankingResponse(
        date=query_date or date.today(),
        entity_type="stock",
        total_count=total,
        returned_count=len(rankings),
        offset=offset,
        limit=limit,
        rankings=rankings,
    )


@router.get("/v2/sectors", response_model=StrengthRankingResponse)
async def get_sector_rankings_v2(
    calc_date: Optional[date] = Query(None, description="计算日期，默认为最新"),
    offset: int = Query(0, ge=0, description="偏移量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    sector_type: Optional[str] = Query(
        None, description="板块类型筛选: industry/concept/region/sw_industry"
    ),
    level: Optional[str] = Query(
        None, description="申万行业层级筛选: L1/L2/L3（仅 sector_type=sw_industry 时生效）"
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StrengthRankingResponse:
    """获取板块强度排名 (V2)

    支持按板块来源筛选：同花顺（industry/concept/region）与申万行业
    （sw_industry，可进一步按 L1/L2/L3 层级筛选）。两者各自排名，避免不同
    分类体系混排。不传 sector_type 时返回全部板块的混合排名。
    """
    stmt = select(StrengthScoreModel, SectorModel).join(
        SectorModel, StrengthScoreModel.entity_id == SectorModel.id
    ).where(
        StrengthScoreModel.entity_type == "sector",
        StrengthScoreModel.period == "all"
    )

    # 按板块来源/层级筛选（申万与同花顺各自排名，避免混排）
    if sector_type:
        stmt = stmt.where(SectorModel.type == sector_type)
    if level:
        stmt = stmt.where(SectorModel.level == level)

    if calc_date:
        stmt = stmt.where(StrengthScoreModel.date == calc_date)
    else:
        from sqlalchemy import desc as sql_desc
        latest_stmt = select(StrengthScoreModel.date).where(
            StrengthScoreModel.period == "all"
        ).order_by(sql_desc(StrengthScoreModel.date)).limit(1)
        latest_result = await session.execute(latest_stmt)
        latest_date = latest_result.scalar_one_or_none()
        if latest_date:
            stmt = stmt.where(StrengthScoreModel.date == latest_date)

    stmt = stmt.order_by(desc(StrengthScoreModel.score))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    rows = result.all()

    rankings = []
    for strength, sector in rows:
        rankings.append(
            StrengthRankingItem(
                rank=strength.rank or (offset + len(rankings) + 1),
                entity_id=strength.entity_id,
                symbol=strength.symbol,
                name=sector.name,
                score=strength.score,
                percentile=getattr(strength, "percentile", None),
                strength_grade=strength.strength_grade,
                change_rate_1d=strength.change_rate_1d,
            )
        )

    query_date = calc_date
    if not query_date and rows:
        query_date = rows[0][0].date

    return StrengthRankingResponse(
        date=query_date or date.today(),
        entity_type="sector",
        total_count=total,
        returned_count=len(rankings),
        offset=offset,
        limit=limit,
        rankings=rankings,
    )


@router.get("/v2/stats", response_model=StrengthStatsResponse)
async def get_strength_stats(
    entity_type: str = Query(..., description="实体类型: stock/sector"),
    calc_date: Optional[date] = Query(None, description="计算日期，默认为最新"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StrengthStatsResponse:
    """获取强度统计信息 (V2)"""
    if entity_type not in ["stock", "sector"]:
        from src.api.exceptions import NotFoundError
        raise NotFoundError(f"无效的实体类型: {entity_type}")

    # ADR-4 内部分发：entity_type='stock' 查股票独立表，'sector' 查旧表
    is_stock = entity_type == "stock"
    Model = StockStrengthScoreModel if is_stock else StrengthScoreModel

    base_conds = []
    if not is_stock:
        base_conds.append(Model.entity_type == entity_type)
        base_conds.append(Model.period == "all")

    stmt = select(Model)
    if base_conds:
        stmt = stmt.where(*base_conds)

    if calc_date:
        stmt = stmt.where(Model.date == calc_date)
    else:
        from sqlalchemy import desc as sql_desc
        latest_stmt = select(Model.date)
        if not is_stock:
            latest_stmt = latest_stmt.where(Model.period == "all")
        latest_stmt = latest_stmt.order_by(sql_desc(Model.date)).limit(1)
        latest_result = await session.execute(latest_stmt)
        latest_date = latest_result.scalar_one_or_none()
        if latest_date:
            stmt = stmt.where(Model.date == latest_date)

    result = await session.execute(stmt)
    scores = result.scalars().all()

    if not scores:
        query_date = calc_date or date.today()
        return StrengthStatsResponse(
            date=query_date,
            entity_type=entity_type,
            total_count=0,
            grade_distribution=[],
            avg_score=None,
            min_score=None,
            max_score=None,
            strong_ratio=0.0,
            weak_ratio=0.0,
        )

    query_date = scores[0].date
    total_count = len(scores)
    valid_scores = [s.score for s in scores if s.score is not None]

    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else None
    min_score = min(valid_scores) if valid_scores else None
    max_score = max(valid_scores) if valid_scores else None

    strong_count = len([s for s in scores if s.score and s.score > 60])
    weak_count = len([s for s in scores if s.score and s.score < 40])
    strong_ratio = round(strong_count / total_count * 100, 2) if total_count > 0 else 0.0
    weak_ratio = round(weak_count / total_count * 100, 2) if total_count > 0 else 0.0

    grade_counts = {}
    for s in scores:
        grade = s.strength_grade or "N/A"
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

    grade_distribution = [
        StrengthGradeDistribution(
            grade=grade,
            count=count,
            percentage=round(count / total_count * 100, 2) if total_count > 0 else 0.0
        )
        for grade, count in sorted(grade_counts.items())
    ]

    return StrengthStatsResponse(
        date=query_date,
        entity_type=entity_type,
        total_count=total_count,
        grade_distribution=grade_distribution,
        avg_score=avg_score,
        min_score=min_score,
        max_score=max_score,
        strong_ratio=strong_ratio,
        weak_ratio=weak_ratio,
    )


@router.post("/v2/batch-calculate", response_model=BatchStrengthResponse)
async def batch_calculate_strength(
    request: BatchStrengthRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> BatchStrengthResponse:
    """批量计算强度 (V2)"""
    service = StrengthServiceV2(session)
    result = await service.batch_calculate(
        entity_type="stock",
        entity_ids=request.entity_ids,
        calc_date=request.calc_date
    )

    items = []
    for r in result.get("results", []):
        entity_id = r.get("stock_id") or r.get("sector_id")
        if entity_id:
            stmt = select(StockModel).where(StockModel.id == entity_id)
            entity_result = await session.execute(stmt)
            entity = entity_result.scalar_one_or_none()

            items.append(
                BatchCalculationItem(
                    entity_id=entity_id,
                    symbol=entity.symbol if entity else "",
                    name=entity.name if entity else None,
                    success=r.get("success", False),
                    score=r.get("result", {}).get("composite_score") if r.get("success") else None,
                    error=r.get("error"),
                )
            )

    return BatchStrengthResponse(
        calc_date=request.calc_date or date.today(),
        period=request.period,
        total_count=result.get("total", len(request.entity_ids)),
        success_count=result.get("success_count", 0),
        failure_count=result.get("error_count", 0),
        results=items,
    )
