"""
数据访问层 (Repository 模式)

提供统一的数据库操作接口。
"""

from .base import BaseRepository
from .sector_repository import SectorRepository
from .stock_repository import StockRepository
from .market_data_repository import MarketDataRepository, MovingAverageRepository

__all__ = [
    "BaseRepository",
    "SectorRepository",
    "StockRepository",
    "MarketDataRepository",
    "MovingAverageRepository",
]
