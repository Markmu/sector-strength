"""
数据获取服务模块

提供统一的数据源接口，支持 AkShare 等多个数据源。
"""

from .akshare_client import AkShareDataSource
from .base import BaseDataSource
from .exceptions import (
    DataFetchError,
    DataValidationError,
    DataSourceError,
    DataSourceTimeoutError,
    RetryExhaustedError,
)
from .models import (
    DailyQuote,
    DataFetchResult,
    SectorInfo,
    SectorList,
    DailyQuoteList,
    StockInfo,
    StockList,
)

__all__ = [
    # 数据源
    "BaseDataSource",
    "AkShareDataSource",
    # 异常
    "DataSourceError",
    "DataFetchError",
    "DataValidationError",
    "RetryExhaustedError",
    "DataSourceTimeoutError",
    # 模型
    "StockInfo",
    "StockList",
    "SectorInfo",
    "SectorList",
    "DailyQuote",
    "DailyQuoteList",
    "DataFetchResult",
]
