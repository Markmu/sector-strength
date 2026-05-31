"""
数据获取服务模块

提供统一的数据源接口，基于 Tushare 数据源。
"""

import os
import logging

from .base import BaseDataSource
from .tushare_client import TushareDataSource
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

logger = logging.getLogger(__name__)


class DataSourceFactory:
    """数据源工厂，根据环境变量创建对应的数据源实例"""

    VALID_TYPES = ("tushare",)

    @staticmethod
    def create() -> BaseDataSource:
        """
        根据 DATA_SOURCE_TYPE 环境变量创建数据源实例

        Returns:
            BaseDataSource 子类实例

        Raises:
            ValueError: 环境变量值无效
        """
        source_type = os.getenv("DATA_SOURCE_TYPE", "tushare").strip().lower()

        if source_type not in DataSourceFactory.VALID_TYPES:
            raise ValueError(
                f"无效的数据源类型: '{source_type}'，可选值: {', '.join(DataSourceFactory.VALID_TYPES)}"
            )

        instance = TushareDataSource()
        logger.info(f"数据源切换为: {instance.source_name}")
        return instance


__all__ = [
    # 数据源
    "BaseDataSource",
    "TushareDataSource",
    "DataSourceFactory",
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
