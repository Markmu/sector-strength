"""
强度数据 Pydantic Schema (V2)

定义强度相关的 Pydantic 模型，使用 MA 系统强度计算结果。
"""

from __future__ import annotations

from datetime import date
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


# ========== V1 兼容类型 (用于旧 API，待迁移) ==========
# 这些类型保留用于向后兼容，待 strength.py (v1 API) 重构后移除

class StrengthData(BaseModel):
    """V1 强度数据 (兼容)"""
    entity_id: str
    entity_type: str
    strength_score: float
    trend_direction: float
    current_price: Optional[float] = None
    period_strengths: Dict[str, 'PeriodStrength'] = Field(default_factory=dict)
    calculated_at: date


class PeriodStrength(BaseModel):
    """V1 周期强度 (兼容)"""
    period: str
    ma_value: Optional[float] = None
    price_ratio: Optional[float] = None
    weight: float


class StrengthResponse(BaseModel):
    """V1 响应 (兼容)"""
    success: bool
    data: Optional[StrengthData] = None


class StrengthListResponse(BaseModel):
    """V1 列表响应 (兼容)"""
    success: bool
    data: List[StrengthData] = Field(default_factory=list)


class RankingItem(BaseModel):
    """V1 排名项 (兼容)"""
    rank: int
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    symbol: Optional[str] = None
    # Legacy response compatibility fields
    id: Optional[str] = None
    code: Optional[str] = None
    name: Optional[str] = None
    strength_score: Optional[float] = None
    trend_direction: Optional[float] = None
    current_price: Optional[float] = None


class RankingResponse(BaseModel):
    """V1 排名响应 (兼容)"""
    success: bool
    data: List[RankingItem] = Field(default_factory=list)
    total: int = 0
    top_n: Optional[int] = None


# ========== V2 类型 (MA 系统强度) ==========


class StrengthScoreBase(BaseModel):
    """强度得分基础 Schema"""
    entity_type: str
    entity_id: int
    symbol: str
    date: date
    period: str = 'all'

    # 核心得分
    score: Optional[float] = None
    price_position_score: Optional[float] = None
    ma_alignment_score: Optional[float] = None
    ma_alignment_state: Optional[str] = None

    # 短中长期强度
    short_term_score: Optional[float] = None
    medium_term_score: Optional[float] = None
    long_term_score: Optional[float] = None

    # 均线数据
    current_price: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma30: Optional[float] = None
    ma60: Optional[float] = None
    ma90: Optional[float] = None
    ma120: Optional[float] = None
    ma240: Optional[float] = None

    # 价格相对均线位置
    price_above_ma5: Optional[bool] = None
    price_above_ma10: Optional[bool] = None
    price_above_ma20: Optional[bool] = None
    price_above_ma30: Optional[bool] = None
    price_above_ma60: Optional[bool] = None
    price_above_ma90: Optional[bool] = None
    price_above_ma120: Optional[bool] = None
    price_above_ma240: Optional[bool] = None

    # 排名和等级
    rank: Optional[int] = None
    percentile: Optional[float] = None
    change_rate_1d: Optional[float] = None
    change_rate_5d: Optional[float] = None
    strength_grade: Optional[str] = None

    class Config:
        from_attributes = True


class StockStrengthResponse(StrengthScoreBase):
    """股票强度响应"""
    stock_name: Optional[str] = None


class SectorStrengthResponse(StrengthScoreBase):
    """板块强度响应"""
    sector_name: Optional[str] = None
    stock_count: Optional[int] = None
    strong_stock_count: Optional[int] = None
    strong_stock_ratio: Optional[float] = None


class StrengthHistoryData(BaseModel):
    """历史数据点"""
    date: date
    score: Optional[float] = None
    rank: Optional[int] = None
    percentile: Optional[float] = None
    strength_grade: Optional[str] = None
    price_position_score: Optional[float] = None
    ma_alignment_score: Optional[float] = None
    ma_alignment_state: Optional[str] = None
    short_term_score: Optional[float] = None
    medium_term_score: Optional[float] = None
    long_term_score: Optional[float] = None
    current_price: Optional[float] = None


class StrengthHistoryResponse(BaseModel):
    """历史数据响应"""
    symbol: str
    name: Optional[str] = None
    start_date: date
    end_date: date
    total_days: int
    data_points: List[StrengthHistoryData]


class StrengthRankingItem(BaseModel):
    """排名项"""
    rank: int
    entity_id: int
    symbol: str
    name: Optional[str] = None
    score: Optional[float] = None
    percentile: Optional[float] = None
    strength_grade: Optional[str] = None
    change_rate_1d: Optional[float] = None


class StrengthRankingResponse(BaseModel):
    """排名响应"""
    date: date
    entity_type: str
    total_count: int
    returned_count: int
    offset: int = 0
    limit: int = 50
    rankings: List[StrengthRankingItem]


class StrengthGradeDistribution(BaseModel):
    """等级分布"""
    grade: str
    count: int
    percentage: float


class StrengthStatsResponse(BaseModel):
    """统计信息响应"""
    date: date
    entity_type: str
    total_count: int
    grade_distribution: List[StrengthGradeDistribution]
    avg_score: Optional[float] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    strong_ratio: Optional[float] = None
    weak_ratio: Optional[float] = None


class BatchStrengthRequest(BaseModel):
    """批量计算请求"""
    entity_ids: List[int]
    calc_date: Optional[date] = None
    period: str = 'all'


class BatchCalculationItem(BaseModel):
    """批量计算项"""
    entity_id: int
    symbol: str
    name: Optional[str] = None
    success: bool
    score: Optional[float] = None
    error: Optional[str] = None


class BatchStrengthResponse(BaseModel):
    """批量计算响应"""
    calc_date: date
    period: str
    total_count: int
    success_count: int
    failure_count: int
    results: List[BatchCalculationItem]


class StrengthStatsDetail(BaseModel):
    """详细统计数据"""
    entity_id: int
    entity_type: str
    days: int
    data_count: int
    latest_score: Optional[float] = None
    max_score: Optional[float] = None
    min_score: Optional[float] = None
    avg_score: Optional[float] = None
    up_days: int = 0
    down_days: int = 0
    flat_days: int = 0
    grade_distribution: Dict[str, int] = Field(default_factory=dict)
    start_date: date
    end_date: date


# ========== 散点图分析类型 ==========


class DataCompleteness(BaseModel):
    """数据完整度"""
    has_strong_ratio: bool = Field(default=False, description="是否有强势股占比数据")
    has_long_term: bool = Field(default=False, description="是否有长期强度数据")
    completeness_percent: float = Field(default=0.0, ge=0, le=100, description="完整度百分比")


class SectorFullData(BaseModel):
    """完整板块数据（用于 tooltip 显示）"""
    score: Optional[float] = None
    short_term_score: Optional[float] = None
    medium_term_score: Optional[float] = None
    long_term_score: Optional[float] = None
    strong_stock_ratio: Optional[float] = None
    strength_grade: Optional[str] = None


class SectorScatterData(BaseModel):
    """板块散点图数据点"""
    symbol: str = Field(..., description="板块代码")
    name: str = Field(..., description="板块名称")
    sector_type: str = Field(..., description="板块类型: industry 或 concept")
    x: float = Field(..., description="X轴数值")
    y: float = Field(..., description="Y轴数值")
    size: float = Field(default=20.0, description="气泡大小 (strong_stock_ratio，默认20)")
    color_value: float = Field(default=50.0, description="颜色值 (long_term_score，默认50)")
    data_completeness: DataCompleteness = Field(default_factory=DataCompleteness, description="数据完整度")
    full_data: SectorFullData = Field(default_factory=SectorFullData, description="完整数据")

    class Config:
        from_attributes = True


class PaginationInfo(BaseModel):
    """分页信息"""
    offset: int = Field(default=0, ge=0, description="分页偏移")
    limit: int = Field(default=200, ge=1, le=500, description="每页数量")


class FiltersApplied(BaseModel):
    """应用的筛选条件"""
    sector_type: Optional[str] = Field(None, description="板块类型筛选")
    grade_range: Optional[List[str]] = Field(None, description="强度等级范围")
    axes: List[str] = Field(default_factory=list, description="坐标轴 [x_axis, y_axis]")
    pagination: Optional[PaginationInfo] = Field(None, description="分页信息")


class SectorScatterDataset(BaseModel):
    """板块散点图数据集（按类型分组）"""
    industry: List[SectorScatterData] = Field(default_factory=list, description="行业板块数据")
    concept: List[SectorScatterData] = Field(default_factory=list, description="概念板块数据")


class SectorScatterResponse(BaseModel):
    """板块散点图响应"""
    scatter_data: SectorScatterDataset = Field(..., description="散点图数据集")
    total_count: int = Field(..., ge=0, description="总板块数（分页前）")
    returned_count: int = Field(..., ge=0, description="返回的板块数")
    filters_applied: FiltersApplied = Field(..., description="应用的筛选条件")
    cache_status: str = Field(default="miss", description="缓存状态: hit 或 miss")


# ========== 板块分析图表类型 ==========


class SectorStrengthHistoryPoint(BaseModel):
    """板块强度历史数据点"""
    date: date
    score: Optional[float] = None
    short_term_score: Optional[float] = None
    medium_term_score: Optional[float] = None
    long_term_score: Optional[float] = None
    current_price: Optional[float] = None


class SectorStrengthHistoryResponse(BaseModel):
    """板块强度历史响应"""
    sector_id: str
    sector_name: str
    data: List[SectorStrengthHistoryPoint]


class SectorMAHistoryPoint(BaseModel):
    """板块均线历史数据点"""
    date: date
    current_price: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma30: Optional[float] = None
    ma60: Optional[float] = None
    ma90: Optional[float] = None
    ma120: Optional[float] = None
    ma240: Optional[float] = None


class SectorMAHistoryResponse(BaseModel):
    """板块均线历史响应"""
    sector_id: str
    sector_name: str
    data: List[SectorMAHistoryPoint]
