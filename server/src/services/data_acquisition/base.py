"""
数据获取服务抽象接口

定义数据源的通用接口，支持多种数据源实现。
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from .models import (
    DailyQuote,
    SectorInfo,
    StockInfo,
)


class BaseDataSource(ABC):
    """
    数据源抽象基类

    定义所有数据源必须实现的标准接口。

    所有子类必须实现抽象方法，提供数据获取能力。
    建议子类实现重试机制、数据验证和错误处理。
    """

    def __init__(self, source_name: str):
        """
        初始化数据源

        Args:
            source_name: 数据源名称（用于日志和错误追踪）
        """
        self.source_name = source_name

    @abstractmethod
    def get_stock_list(self) -> List[StockInfo]:
        """
        获取股票列表

        获取数据源支持的所有股票信息，包括股票代码、名称、
        市场类型、所属行业等基本信息。

        Returns:
            股票信息列表

        Raises:
            DataFetchError: 数据获取失败
        """
        pass

    @abstractmethod
    def get_sector_list(self, sector_type: Optional[str] = None) -> List[SectorInfo]:
        """
        获取板块列表

        获取行业板块或概念板块的信息。

        Args:
            sector_type: 板块类型过滤 (industry/concept)，None 表示获取所有

        Returns:
            板块信息列表，包含板块代码、名称、类型等

        Raises:
            DataFetchError: 数据获取失败
        """
        pass

    @abstractmethod
    def get_daily_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyQuote]:
        """
        获取日线行情数据

        获取指定股票在日期范围内的日线数据，包括开盘价、
        最高价、最低价、收盘价、成交量等信息。

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            日线行情数据列表

        Raises:
            DataFetchError: 数据获取失败
            ValueError: 参数校验失败（空代码或无效日期范围）
        """
        pass

    @abstractmethod
    def get_sector_daily_data(
        self,
        sector_code: str,
        sector_type: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyQuote]:
        """
        获取板块日线行情数据

        按板块类型获取指定板块在日期范围内的日线数据。

        Args:
            sector_code: 板块代码
            sector_type: 板块类型（industry/concept）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            板块日线行情数据列表

        Raises:
            DataFetchError: 数据获取失败
        """
        pass

    def health_check(self) -> bool:
        """
        检查数据源连接状态

        通过尝试获取少量数据来验证数据源连接是否正常。

        Returns:
            True 表示连接正常，False 表示连接异常
        """
        try:
            # 尝试获取少量数据验证连接
            stocks = self.get_stock_list()
            return len(stocks) > 0
        except Exception:
            return False
