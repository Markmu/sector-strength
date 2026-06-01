"""
板块等级表格 Schema
"""

from datetime import date
from typing import Dict, Optional
from pydantic import BaseModel, Field


class SectorTableItem(BaseModel):
    """表格中的板块项"""
    id: int
    code: str
    name: str
    sector_type: str
    score: Optional[float] = None
    short_term_score: Optional[float] = None
    medium_term_score: Optional[float] = None
    long_term_score: Optional[float] = None
    strength_grade: Optional[str] = None
    strong_stock_ratio: Optional[float] = None
    rank: Optional[int] = None

    model_config = {"from_attributes": True}


class GradeSectorStats(BaseModel):
    """某个等级的板块统计"""
    grade: str
    type_counts: Dict[str, int] = Field(default_factory=dict, description="各类型板块数量")
    total_count: int = 0
    sectors: list[SectorTableItem] = Field(default_factory=list)


class SectorGradeTableResponse(BaseModel):
    """板块等级表格响应"""
    date: date
    stats: list[GradeSectorStats]
    type_totals: Dict[str, int] = Field(default_factory=dict, description="各类型板块总数")
    total_sectors: int = 0
    cache_status: str = "miss"


class SectorDistributionResponse(BaseModel):
    """板块类型分布响应"""
    date: date
    type_counts: Dict[str, int] = Field(default_factory=dict, description="各类型板块数量")
    total_count: int = 0
