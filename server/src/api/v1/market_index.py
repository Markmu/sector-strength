"""
市场强度指数 API 路由

提供市场强度指数相关的 REST API 端点。
"""

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from src.api.deps import get_session, get_current_user
from src.models.user import User
from src.models.sector import Sector as SectorModel

router = APIRouter(prefix="/market-index", tags=["market-index"])


def _calculate_index_color(value: float) -> str:
    """
    根据指数值获取颜色

    Args:
        value: 指数值 (0-100)

    Returns:
        颜色 hex 值
    """
    if value >= 70:
        return "#10B981"  # 绿色 - 强
    elif value >= 40:
        return "#FBBF24"  # 黄色 - 中
    else:
        return "#EF4444"  # 红色 - 弱


@router.get("", response_model=dict)
async def get_market_index(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    获取市场强度指数

    计算：
    1. 加权平均市场指数 = Σ(板块强度 × 板块权重) / Σ(板块权重)
    2. 上涨/下跌板块统计
    3. 历史趋势数据（简化版本，返回当前指数）

    注意：
    - 简化版本，所有板块权重相同
    - 历史趋势需要额外的数据存储，当前返回模拟数据
    """
    # 获取所有有强度得分的板块
    stmt = select(SectorModel).where(SectorModel.strength_score.isnot(None))
    result = await session.execute(stmt)
    sectors = result.scalars().all()

    if not sectors:
        return {
            "success": True,
            "data": {
                "index": {
                    "value": 0.0,
                    "change": 0.0,
                    "timestamp": datetime.now().isoformat(),
                    "color": "#94a3b8",
                },
                "stats": {
                    "totalSectors": 0,
                    "upSectors": 0,
                    "downSectors": 0,
                    "neutralSectors": 0,
                },
                "trend": [],
            }
        }

    # 计算加权平均指数（简化版本，所有板块权重相同）
    total_score = sum(s.strength_score or 0 for s in sectors)
    avg_index = total_score / len(sectors)

    # 统计涨跌板块
    up_sectors = sum(1 for s in sectors if s.trend_direction == 1)
    down_sectors = sum(1 for s in sectors if s.trend_direction == -1)
    neutral_sectors = sum(1 for s in sectors if s.trend_direction == 0)

    # 计算变化（简化版本，基于强度得分的分布估算）
    # 如果上涨板块多，变化为正
    total = len(sectors)
    change = ((up_sectors - down_sectors) / total * 10) if total > 0 else 0

    # 生成模拟历史趋势数据（最近24小时，每小时一个点）
    trend = []
    base_value = avg_index - 5  # 起始值略低于当前值
    for i in range(24):
        trend_time = datetime.now() - timedelta(hours=23 - i)
        # 模拟随机波动
        import random
        trend_value = base_value + (i * 0.2) + random.uniform(-2, 2)
        trend_value = max(0, min(100, trend_value))  # 限制在 0-100 范围内
        trend.append({
            "timestamp": trend_time.isoformat(),
            "value": round(trend_value, 2),
        })

    return {
        "success": True,
        "data": {
            "index": {
                "value": round(avg_index, 2),
                "change": round(change, 2),
                "timestamp": datetime.now().isoformat(),
                "color": _calculate_index_color(avg_index),
            },
            "stats": {
                "totalSectors": total,
                "upSectors": up_sectors,
                "downSectors": down_sectors,
                "neutralSectors": neutral_sectors,
            },
            "trend": trend,
        }
    }
