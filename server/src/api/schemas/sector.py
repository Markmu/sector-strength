"""
板块数据模型

定义板块相关的 Pydantic 模型。
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from .response import PaginatedData


class SectorBase(BaseModel):
    """板块基础模型"""

    code: str = Field(..., description="板块代码", min_length=1)
    name: str = Field(..., description="板块名称", min_length=1)
    type: str = Field(..., description="板块类型: industry/concept")
    description: Optional[str] = Field(None, description="板块描述")


class Sector(SectorBase):
    """板块完整模型"""

    id: str = Field(..., description="板块 ID")
    strength_score: Optional[float] = Field(None, description="强度得分 (0-100)", ge=0, le=100)
    trend_direction: Optional[int] = Field(None, description="趋势方向: 1=上升, 0=横盘, -1=下降", ge=-1, le=1)
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "sector-001",
                "code": "BK0001",
                "name": "人工智能",
                "type": "concept",
                "description": "人工智能相关概念板块",
                "strength_score": 78.5,
                "trend_direction": 1,
            }
        }


class SectorDetail(Sector):
    """板块详情（包含成分股数量）"""

    stock_count: int = Field(..., description="成分股数量", ge=0)


class SectorListItem(Sector):
    """板块列表项（简化版）"""

    pass


class SectorListResponse(BaseModel):
    """板块列表响应"""

    success: bool = True
    data: PaginatedData[SectorListItem]


class SectorDetailResponse(BaseModel):
    """板块详情响应"""

    success: bool = True
    data: SectorDetail


class SectorStocksResponse(BaseModel):
    """板块成分股响应"""

    success: bool = True
    data: PaginatedData  # Stock 类型将在 stock.py 中定义


# 热力图数据模型
class HeatmapSector(BaseModel):
    """热力图板块数据"""

    id: str = Field(..., description="板块 ID")
    name: str = Field(..., description="板块名称")
    value: float = Field(..., description="强度值", ge=0, le=100)
    color: str = Field(..., description="显示颜色 (hex)")


class HeatmapData(BaseModel):
    """热力图数据"""

    sectors: List[HeatmapSector] = Field(default_factory=list)
    timestamp: Optional[datetime] = Field(None, description="数据时间戳")


class HeatmapResponse(BaseModel):
    """热力图响应"""

    success: bool = True
    data: HeatmapData
