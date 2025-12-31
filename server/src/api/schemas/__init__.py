"""
API 数据模型模块

导出所有 Pydantic 模型。
"""

from .response import (
    ApiResponse,
    PaginatedData,
    ErrorDetail,
    ErrorResponse,
    EmptyResponse,
)
from .sector import (
    Sector,
    SectorBase,
    SectorDetail,
    SectorListItem,
    SectorListResponse,
    SectorDetailResponse,
    SectorStocksResponse,
    HeatmapSector,
    HeatmapData,
    HeatmapResponse,
)
from .stock import (
    Stock,
    StockBase,
    StockDetail,
    StockListItem,
    StockListResponse,
    StockDetailResponse,
)
from .strength import (
    # V1 兼容类型
    StrengthData,
    StrengthResponse,
    StrengthListResponse,
    PeriodStrength,
    RankingItem,
    RankingResponse,
    # V2 类型
    StrengthScoreBase,
    StockStrengthResponse,
    SectorStrengthResponse,
    StrengthHistoryData,
    StrengthHistoryResponse,
    StrengthRankingItem,
    StrengthRankingResponse,
    StrengthGradeDistribution,
    StrengthStatsResponse,
    BatchStrengthRequest,
    BatchCalculationItem,
    BatchStrengthResponse,
    StrengthStatsDetail,
)

__all__ = [
    # Response
    "ApiResponse",
    "PaginatedData",
    "ErrorDetail",
    "ErrorResponse",
    "EmptyResponse",
    # Sector
    "Sector",
    "SectorBase",
    "SectorDetail",
    "SectorListItem",
    "SectorListResponse",
    "SectorDetailResponse",
    "SectorStocksResponse",
    "HeatmapSector",
    "HeatmapData",
    "HeatmapResponse",
    # Stock
    "Stock",
    "StockBase",
    "StockDetail",
    "StockListItem",
    "StockListResponse",
    "StockDetailResponse",
    # Strength V1 (兼容)
    "StrengthData",
    "StrengthResponse",
    "StrengthListResponse",
    "PeriodStrength",
    "RankingItem",
    "RankingResponse",
    # Strength V2 (MA 系统)
    "StrengthScoreBase",
    "StockStrengthResponse",
    "SectorStrengthResponse",
    "StrengthHistoryData",
    "StrengthHistoryResponse",
    "StrengthRankingItem",
    "StrengthRankingResponse",
    "StrengthGradeDistribution",
    "StrengthStatsResponse",
    "BatchStrengthRequest",
    "BatchCalculationItem",
    "BatchStrengthResponse",
    "StrengthStatsDetail",
]
