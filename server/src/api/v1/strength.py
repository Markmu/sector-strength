"""
强度 API 路由

提供强度数据相关的 REST API 端点。
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc
from datetime import date

from src.api.deps import get_session, get_current_user
from src.models.user import User
from src.api.schemas.strength import (
    StrengthData,
    StrengthResponse,
    StrengthListResponse,
    PeriodStrength,
)
from src.api.exceptions import NotFoundError
from src.models.stock import Stock as StockModel
from src.models.sector import Sector as SectorModel
from src.models.moving_average_data import MovingAverageData as MovingAverageDataModel
from src.models.period_config import PeriodConfig as PeriodConfigModel

router = APIRouter(prefix="/strength", tags=["strength"])


async def _build_strength_data(
    entity_id: str,
    entity_type: str,
    entity_model,
    session: AsyncSession,
) -> Optional[StrengthData]:
    """
    构建强度数据

    Args:
        entity_id: 实体 ID
        entity_type: 实体类型
        entity_model: 实体模型类
        session: 数据库会话

    Returns:
        StrengthData: 强度数据
    """
    # 兼容旧接口：路径参数可能是字符串，模型主键为整型时先做安全转换。
    lookup_id = entity_id
    is_int_pk = False
    try:
        is_int_pk = entity_model.id.type.python_type is int
    except Exception:
        is_int_pk = False
    if is_int_pk:
        if not str(entity_id).isdigit():
            return None
        lookup_id = int(entity_id)

    # 查询实体
    stmt = select(entity_model).where(entity_model.id == lookup_id)
    result = await session.execute(stmt)
    entity = result.scalar_one_or_none()

    if not entity:
        return None

    # 查询周期配置
    config_stmt = select(PeriodConfigModel).where(PeriodConfigModel.is_active == True)
    config_result = await session.execute(config_stmt)
    period_configs = config_result.scalars().all()

    # 查询各周期均线数据
    period_strengths = {}
    for config in period_configs:
        ma_stmt = select(MovingAverageDataModel).where(
            MovingAverageDataModel.entity_id == lookup_id,
            MovingAverageDataModel.entity_type == entity_type,
            MovingAverageDataModel.period == config.period,
        ).order_by(desc(MovingAverageDataModel.date)).limit(1)

        ma_result = await session.execute(ma_stmt)
        ma_data = ma_result.scalar_one_or_none()

        period_strengths[config.period] = PeriodStrength(
            period=config.period,
            ma_value=ma_data.ma_value if ma_data else None,
            price_ratio=ma_data.price_ratio if ma_data else None,
            weight=config.weight,
        )

    # 获取当前价格
    current_price = None
    if entity_type == "stock":
        current_price = entity.current_price
    elif entity_type == "sector":
        # 板块是抽象概念，没有单一价格。
        # 如需板块价格，可以计算成分股的加权平均价格（按市值加权）。
        # 当前设计：板块强度基于成分股强度聚合，不直接使用板块价格。
        current_price = None

    return StrengthData(
        entity_id=str(entity.id),
        entity_type=entity_type,
        strength_score=entity.strength_score,
        trend_direction=entity.trend_direction,
        current_price=current_price,
        period_strengths=period_strengths,
        calculated_at=date.today(),
    )


@router.get("/{entity_type}/{entity_id}", response_model=StrengthResponse)
async def get_strength_detail(
    entity_type: str,
    entity_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StrengthResponse:
    """
    获取单个实体的强度数据

    Args:
        entity_type: 实体类型 (stock/sector)
        entity_id: 实体 ID
    """
    if entity_type not in ["stock", "sector"]:
        raise NotFoundError(f"无效的实体类型: {entity_type}")

    entity_model = StockModel if entity_type == "stock" else SectorModel

    strength_data = await _build_strength_data(
        entity_id, entity_type, entity_model, session
    )

    if not strength_data:
        raise NotFoundError(f"{entity_type} {entity_id} 不存在")

    return StrengthResponse(success=True, data=strength_data)


@router.get("", response_model=StrengthListResponse)
async def get_strength_list(
    entity_type: Optional[str] = Query(None, description="实体类型: stock/sector"),
    entity_ids: Optional[str] = Query(None, description="多个实体 ID，逗号分隔"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StrengthListResponse:
    """
    获取强度数据列表

    支持批量查询多个实体的强度数据。
    """
    if entity_type and entity_type not in ["stock", "sector"]:
        raise NotFoundError(f"无效的实体类型: {entity_type}")

    entity_model = StockModel if entity_type == "stock" else SectorModel

    # 解析 ID 列表
    ids: List[int] = []
    if entity_ids:
        for raw in [id.strip() for id in entity_ids.split(",") if id.strip()]:
            if raw.isdigit():
                ids.append(int(raw))

    # 构建查询
    if entity_type:
        stmt = select(entity_model)
        if entity_ids and not ids:
            # 提供了无效 ID 列表时返回空集合（避免类型错误）
            return StrengthListResponse(success=True, data=[])
        if ids:
            stmt = stmt.where(entity_model.id.in_(ids))
        stmt = stmt.order_by(desc(entity_model.strength_score)).limit(limit)
    else:
        # 默认返回板块数据
        stmt = select(SectorModel).order_by(desc(SectorModel.strength_score)).limit(limit)

    result = await session.execute(stmt)
    entities = result.scalars().all()

    # 构建强度数据列表
    strength_list = []
    for entity in entities:
        ent_type = entity_type if entity_type else "sector"
        ent_model = entity_model if entity_type else SectorModel

        data = await _build_strength_data(
            str(entity.id), ent_type, ent_model, session
        )
        if data:
            strength_list.append(data)

    return StrengthListResponse(success=True, data=strength_list)
