"""
个股数据模型

定义个股相关的 Pydantic 模型。
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from .response import PaginatedData


class StockBase(BaseModel):
    """个股基础模型"""

    symbol: str = Field(..., description="股票代码", min_length=1)
    name: str = Field(..., description="股票名称", min_length=1)


class Stock(StockBase):
    """个股完整模型"""

    id: str = Field(..., description="股票 ID")
    current_price: Optional[float] = Field(None, description="当前价格", gt=0)
    market_cap: Optional[float] = Field(None, description="市值（元）", ge=0)
    strength_score: Optional[float] = Field(None, description="强度得分 (0-100)", ge=0, le=100)
    trend_direction: Optional[int] = Field(None, description="趋势方向: 1=上升, 0=横盘, -1=下降", ge=-1, le=1)
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "stock-001",
                "symbol": "000001",
                "name": "平安银行",
                "current_price": 10.5,
                "market_cap": 1000000000,
                "strength_score": 65.0,
                "trend_direction": 1,
            }
        }


class StockDetail(Stock):
    """个股详情（包含所属板块）"""

    sectors: List[dict] = Field(default_factory=list, description="所属板块列表")


class StockListItem(Stock):
    """股票列表项（简化版）"""

    pass


class StockListResponse(BaseModel):
    """股票列表响应"""

    success: bool = True
    data: PaginatedData[StockListItem]


class StockDetailResponse(BaseModel):
    """股票详情响应"""

    success: bool = True
    data: StockDetail
