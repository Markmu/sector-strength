"""
热力图 API 路由

提供热力图数据相关的 REST API 端点。
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from src.api.deps import get_session
from src.api.schemas.sector import HeatmapData, HeatmapResponse, HeatmapSector
from src.models.sector import Sector as SectorModel

router = APIRouter(prefix="/heatmap", tags=["heatmap"])


def _get_color_for_strength(strength: float) -> str:
    """
    根据强度值获取颜色

    Args:
        strength: 强度值 (0-100)

    Returns:
        颜色 hex 值
    """
    if strength is None:
        return "#94a3b8"  # 灰色 - 无数据

    if strength >= 80:
        return "#22c55e"  # 绿色 - 非常强势
    elif strength >= 65:
        return "#4ade80"  # 浅绿 - 强势
    elif strength >= 50:
        return "#facc15"  # 黄色 - 偏强
    elif strength >= 35:
        return "#94a3b8"  # 灰色 - 中性
    elif strength >= 20:
        return "#fb923c"  # 橙色 - 偏弱
    elif strength >= 10:
        return "#f87171"  # 浅红 - 弱势
    else:
        return "#ef4444"  # 红色 - 非常弱势


@router.get("", response_model=HeatmapResponse)
async def get_heatmap_data(
    sector_type: Optional[str] = Query(None, description="板块类型筛选"),
    session: AsyncSession = Depends(get_session),
) -> HeatmapResponse:
    """
    获取热力图渲染数据

    返回板块强度值，用于前端热力图渲染。
    """
    # 构建查询
    stmt = select(SectorModel)

    if sector_type:
        stmt = stmt.where(SectorModel.type == sector_type)

    # 只返回有强度得分的板块
    stmt = stmt.where(SectorModel.strength_score.isnot(None))

    # 按强度排序
    stmt = stmt.order_by(SectorModel.strength_score.desc())

    # 执行查询
    result = await session.execute(stmt)
    sectors = result.scalars().all()

    # 转换为热力图数据
    heatmap_sectors = []
    for sector in sectors:
        heatmap_sectors.append(
            HeatmapSector(
                id=str(sector.id),
                name=sector.name,
                value=sector.strength_score or 0,
                color=_get_color_for_strength(sector.strength_score),
            )
        )

    data = HeatmapData(
        sectors=heatmap_sectors,
        timestamp=datetime.now(),
    )

    return HeatmapResponse(success=True, data=data)
