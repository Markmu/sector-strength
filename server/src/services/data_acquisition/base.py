"""
数据获取服务抽象接口

定义数据源的通用接口，支持多种数据源实现。
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from .models import (
    DailyQuote,
    LifecycleStock,
    MarketDailyQuote,
    SectorInfo,
    SectorMemberInfo,
    StockInfo,
    SuspensionRecord,
    TradingCalendarEntry,
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
            sector_type: 板块类型过滤 (industry/concept/region)，None 表示获取所有

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
    def get_trading_calendar(self) -> List[date]:
        """
        获取交易日历

        Returns:
            交易日日期列表

        Raises:
            DataFetchError: 数据获取失败
        """
        pass

    @abstractmethod
    def get_trading_calendar_range(
        self, start_date: date, end_date: date
    ) -> List[TradingCalendarEntry]:
        """
        获取闭区间全量开/休市记录（含休市日，不过滤 is_open）

        返回 ``[start_date, end_date]`` 闭区间内每个自然日一条 ``TradingCalendarEntry``，
        供本地 ``trading_calendar_days`` 表刷新与首页缺口轴使用。与 ``get_trading_calendar``
        （仅开市日）并存：本方法明确不传 is_open 过滤，保留休市日锚点（架构 ADR-6）。

        Args:
            start_date: 开始日期（闭区间，含）
            end_date: 结束日期（闭区间，含）

        Returns:
            闭区间内每个自然日一条的日历条目列表

        Raises:
            DataFetchError: 数据获取失败
            ValueError: 参数校验失败（start 晚于 end）
        """
        pass

    @abstractmethod
    def get_sector_members(self, ts_code: str) -> SectorMemberInfo:
        """
        获取板块成分股列表

        通过同花顺板块代码获取该板块下的所有成分股。

        Args:
            ts_code: 板块代码 (如 "850121.SI")

        Returns:
            SectorMemberInfo: 包含板块代码和成分股代码列表

        Raises:
            DataFetchError: 数据获取失败
        """
        pass

    @abstractmethod
    def get_sector_daily_data(
        self,
        sector_name: str,
        sector_type: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyQuote]:
        """
        获取板块日线行情数据

        按板块类型获取指定板块在日期范围内的日线数据。

        Args:
            sector_name: 板块名称
            sector_type: 板块类型（industry/concept/region）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            板块日线行情数据列表

        Raises:
            DataFetchError: 数据获取失败
        """
        pass

    @abstractmethod
    def get_market_daily_quotes(
        self, trade_date: date, expected_count: int
    ) -> List[MarketDailyQuote]:
        """
        获取单交易日全市场未复权行情（单日模式，参数化分页）

        按 ``trade_date`` 一次拉全沪深北全市场未复权日线（约 5500 行，单页
        3000 自动翻页并带硬停止守卫）。分页异常（页签名重复、满页无新增
        key、页数超限、跨页重复）抛 ``MarketDataIntegrityError``。

        Args:
            trade_date: 目标交易日
            expected_count: 预期股票数（由调用方从生命周期快照传入，用于
                计算硬页数上限 ``ceil(expected_count/3000)+1``）

        Returns:
            全市场未复权行情列表；首张空页时返回空列表，由调用方判为
            全市场空并失败

        Raises:
            MarketDataIntegrityError: 分页守卫或行级校验失败
            DataFetchError: 数据获取失败
        """
        pass

    @abstractmethod
    def get_close_quotes_in_window(
        self, ts_codes: List[str], window_start: date, window_end: date
    ) -> List[MarketDailyQuote]:
        """
        获取一批代码在时间窗口内的未复权行情（历史窗口模式，参数化分页）

        用于停牌补价的前收盘回溯（ADR-3）。批次内代码由调用方按 ≤100/批
        分块；本方法内部按接口上限再分块，每块独立分页并共享完整性守卫。
        每行校验 ``window_start <= trade_date <= window_end`` 且 ts_code 属于
        批次；窗口止于 T-1 由调用方保证。

        Args:
            ts_codes: 批次代码列表（ts_code 格式）
            window_start: 窗口开始日期（闭区间，含）
            window_end: 窗口结束日期（闭区间，含，应早于目标日 T）

        Returns:
            窗口内仅属批次代码的未复权行情列表；首张空页表示该窗口无命中，
            返回空列表，由调用方推进更早窗口

        Raises:
            MarketDataIntegrityError: 分页守卫或行级校验失败
            DataFetchError: 数据获取失败
        """
        pass

    @abstractmethod
    def get_suspensions(self, trade_date: date) -> List[SuspensionRecord]:
        """
        获取停牌查询原始行（suspend_d，原始数据保真）

        忠实返回 Provider 全量行，不做日期与类型过滤；每条记录携带行自带的
        日期（上游列名 suspend_date/trade_date 归一化为 ``suspend_date``）。
        上游忽略 suspend_date 查询过滤，调用方（plan-03）必须按
        ``record.suspend_date == trade_date`` 客户端过滤后才能作为当日停牌
        证据，``suspend_type='S'`` 与全天停牌判定同样由调用方做（ADR-3）。

        Args:
            trade_date: 目标交易日（作为 suspend_date 查询参数传入）

        Returns:
            停牌记录原始行列表（含各自行 suspend_date）；无记录返回空列表

        Raises:
            MarketDataIntegrityError: suspend_date 解析失败
            DataFetchError: 数据获取失败
        """
        pass

    @abstractmethod
    def get_lifecycle_stocks(self) -> List[LifecycleStock]:
        """
        获取 L/D/P/G 四状态生命周期股票全集

        对 ``list_status in ('L','D','P','G')`` 分别分页拉取 ``stock_basic``
        并合并返回；本方法不写库（upsert/set-diff 由调用方做，ADR-2）。

        Returns:
            四状态合并的生命周期股票列表；某状态 0 行时该状态为空集

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
