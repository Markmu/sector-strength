"""
板块分类响应模型

定义板块分类 API 的 Pydantic 响应模型。
"""

from pydantic import BaseModel, Field, field_serializer, ConfigDict
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional


class SectorClassificationBase(BaseModel):
    """板块分类基础模型"""

    sector_id: int = Field(..., description="板块ID")
    symbol: str = Field(..., description="板块编码", max_length=20)
    classification_date: date = Field(..., description="分类日期")
    classification_level: int = Field(..., ge=1, le=9, description="分类级别(1-9)")
    state: str = Field(..., description="状态: '反弹' 或 '调整'")
    current_price: Optional[Decimal] = Field(None, description="当前价格")
    change_percent: Optional[Decimal] = Field(None, description="涨跌幅(%)")
    price_5_days_ago: Optional[Decimal] = Field(None, description="5天前价格")

    # 均线数据
    ma_5: Optional[Decimal] = Field(None, description="5日均线")
    ma_10: Optional[Decimal] = Field(None, description="10日均线")
    ma_20: Optional[Decimal] = Field(None, description="20日均线")
    ma_30: Optional[Decimal] = Field(None, description="30日均线")
    ma_60: Optional[Decimal] = Field(None, description="60日均线")
    ma_90: Optional[Decimal] = Field(None, description="90日均线")
    ma_120: Optional[Decimal] = Field(None, description="120日均线")
    ma_240: Optional[Decimal] = Field(None, description="240日均线")


class SectorClassificationResponse(SectorClassificationBase):
    """板块分类完整响应模型"""

    id: int = Field(..., description="分类记录ID")
    created_at: datetime = Field(..., description="创建时间")

    model_config = ConfigDict(
        from_attributes=True
    )

    # Pydantic V2 序列化方式
    @field_serializer('current_price', 'change_percent', 'price_5_days_ago',
                      'ma_5', 'ma_10', 'ma_20', 'ma_30', 'ma_60', 'ma_90', 'ma_120', 'ma_240')
    def serialize_decimal(self, value: Optional[Decimal]) -> Optional[float]:
        """序列化 Decimal 为 float"""
        return float(value) if value is not None else None

    @field_serializer('created_at')
    def serialize_datetime(self, value: datetime) -> str:
        """序列化 datetime 为 ISO 格式字符串"""
        return value.isoformat()


class SectorClassificationListResponse(BaseModel):
    """板块分类列表响应模型"""

    data: List[SectorClassificationResponse] = Field(..., description="分类数据列表")
    total: int = Field(..., description="总记录数")
