"""
板块分类响应模型

定义板块分类 API 的 Pydantic 响应模型。
"""

from pydantic import BaseModel, Field, field_serializer, ConfigDict, field_validator
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


# ============== 请求模型 ==============

class InitializeClassificationRequest(BaseModel):
    """初始化分类数据请求"""
    start_date: Optional[str] = Field(None, description="起始日期 (YYYY-MM-DD)，None 表示从最早日期开始")
    overwrite: bool = Field(False, description="是否覆盖已有数据")

    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v: Optional[str]) -> Optional[str]:
        """验证起始日期格式"""
        if v is None:
            return v
        try:
            # 尝试解析日期
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('start_date 必须为 YYYY-MM-DD 格式')


class UpdateDailyClassificationRequest(BaseModel):
    """每日更新分类数据请求"""
    target_date: Optional[str] = Field(None, description="目标日期 (YYYY-MM-DD)，None 表示今天")
    overwrite: bool = Field(False, description="是否覆盖已有数据")

    @field_validator('target_date')
    @classmethod
    def validate_target_date(cls, v: Optional[str]) -> Optional[str]:
        """验证目标日期格式"""
        if v is None:
            return v
        try:
            # 尝试解析日期
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('target_date 必须为 YYYY-MM-DD 格式')


# ============== 状态响应模型 ==============

class ClassificationStatusResponse(BaseModel):
    """分类状态响应"""
    latest_date: Optional[str] = Field(None, description="最新分类日期")
    total_sectors: int = Field(0, description="板块总数")
    by_level: dict = Field(default_factory=dict, description="按级别统计")
    by_state: dict = Field(default_factory=dict, description="按状态统计")
