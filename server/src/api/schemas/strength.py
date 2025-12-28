"""
强度数据模型

定义强度相关的 Pydantic 模型。
"""

from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class PeriodStrength(BaseModel):
    """单周期强度数据"""

    period: str = Field(..., description="周期: 5d/10d/20d/30d/60d")
    ma_value: Optional[float] = Field(None, description="均线值")
    price_ratio: Optional[float] = Field(None, description="价格比率 (%)")
    weight: float = Field(..., description="权重", ge=0, le=1)


class StrengthData(BaseModel):
    """强度数据"""

    entity_id: str = Field(..., description="实体 ID")
    entity_type: str = Field(..., description="实体类型: stock/sector")
    strength_score: Optional[float] = Field(None, description="综合强度得分 (0-100)", ge=0, le=100)
    trend_direction: Optional[int] = Field(None, description="趋势方向: 1=上升, 0=横盘, -1=下降", ge=-1, le=1)
    current_price: Optional[float] = Field(None, description="当前价格")
    period_strengths: Dict[str, PeriodStrength] = Field(
        default_factory=dict,
        description="各周期强度数据"
    )
    calculated_at: Optional[datetime] = Field(None, description="计算时间")

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "stock-001",
                "entity_type": "stock",
                "strength_score": 75.5,
                "trend_direction": 1,
                "current_price": 105.0,
                "period_strengths": {
                    "5d": {"period": "5d", "ma_value": 100.0, "price_ratio": 5.0, "weight": 0.15},
                    "10d": {"period": "10d", "ma_value": 98.0, "price_ratio": 7.14, "weight": 0.20},
                },
                "calculated_at": "2024-01-15T15:00:00Z",
            }
        }


class StrengthQueryParams(BaseModel):
    """强度查询参数"""

    entity_type: Optional[str] = Field(None, description="实体类型: stock/sector")
    entity_id: Optional[str] = Field(None, description="实体 ID")
    period: Optional[str] = Field(None, description="周期筛选")
    date: Optional[str] = Field(None, description="日期筛选 (YYYY-MM-DD)")


class StrengthListResponse(BaseModel):
    """强度列表响应"""

    success: bool = True
    data: List[StrengthData]


class StrengthResponse(BaseModel):
    """强度详情响应"""

    success: bool = True
    data: StrengthData


# 排名数据模型
class RankingItem(BaseModel):
    """排名项"""

    id: str = Field(..., description="ID")
    name: str = Field(..., description="名称")
    code: str = Field(..., description="代码")
    strength_score: Optional[float] = Field(None, description="强度得分")
    trend_direction: Optional[int] = Field(None, description="趋势方向")
    rank: int = Field(..., description="排名", ge=1)


class RankingResponse(BaseModel):
    """排名响应"""

    success: bool = True
    data: List[RankingItem]
    total: int = Field(..., description="总数", ge=0)
    top_n: int = Field(..., description="返回数量", ge=1)
