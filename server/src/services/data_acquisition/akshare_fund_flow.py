"""
akshare 板块资金流（同花顺即时）采集器

封装 akshare 的 stock_fund_flow_industry / stock_fund_flow_concept 接口，
提供行业 / 概念板块的即时资金流快照（流入、流出、净额、领涨股等）。

独立于 TushareDataSource：自带重试 + 限流逻辑（参考 tushare_client._execute_with_retry
范式），不依赖 DataSourceFactory（ADR-1）。
"""

import logging
import time
from datetime import datetime
from typing import Callable, List, Optional, TypeVar

from pydantic import BaseModel, ValidationError

from .exceptions import DataFetchError, RetryExhaustedError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SectorFundFlowInfo(BaseModel):
    """单个板块的即时资金流快照（不含 trade_date/sample_time，由调用方标记）"""

    sector_name: str
    sector_index: Optional[float] = None
    change_percent: Optional[float] = None  # 行业-涨跌幅(%)
    inflow: Optional[float] = None  # 流入资金(亿元)
    outflow: Optional[float] = None  # 流出资金(亿元)
    net_inflow: Optional[float] = None  # 净额(亿元)
    company_count: Optional[int] = None
    leading_stock: Optional[str] = None
    leading_stock_change: Optional[float] = None  # 领涨股-涨跌幅(%)
    current_price: Optional[float] = None  # 领涨股当前价


# 同花顺即时接口列名 → SectorFundFlowInfo 字段映射
# （行业/概念接口返回的列名完全一致，板块名列均叫"行业"）
_COLUMN_MAP = {
    "行业": "sector_name",
    "概念": "sector_name",
    "行业指数": "sector_index",
    "行业-涨跌幅": "change_percent",
    "流入资金": "inflow",
    "流出资金": "outflow",
    "净额": "net_inflow",
    "公司家数": "company_count",
    "领涨股": "leading_stock",
    "领涨股-涨跌幅": "leading_stock_change",
    "当前价": "current_price",
}

# 字符串类型字段（不做 float/int 转换）
_STRING_FIELDS = {"sector_name", "leading_stock"}

# sector_type → akshare 接口 + symbol 的路由
_SECTOR_API = {
    "industry": "stock_fund_flow_industry",
    "concept": "stock_fund_flow_concept",
}


class AkshareFundFlowFetcher:
    """
    akshare 板块资金流（同花顺即时）采集器

    独立 fetcher，不注册到 DataSourceFactory。
    重试 / 限流范式参考 src/services/data_acquisition/tushare_client.py:_execute_with_retry。
    """

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0
    DEFAULT_BACKOFF_FACTOR = 2.0
    # akshare 同花顺即时接口较轻，限流间隔 0.3s
    DEFAULT_API_INTERVAL = 0.3
    # 行业与概念两次调用之间的强制间隔，避免风控
    DEFAULT_BETWEEN_TYPE_INTERVAL = 1.0

    # 不可恢复错误关键词：命中即立即失败，不重试
    _NON_RETRYABLE_KEYWORDS = [
        "forbidden", "access denied",
        "invalid parameter", "参数错误",
        "unauthorized", "认证失败",
        "空数据", "no data", "empty",
    ]

    def __init__(self):
        self.source_name = "AkshareFundFlow"
        self._api_interval = self.DEFAULT_API_INTERVAL
        self._max_retries = self.DEFAULT_MAX_RETRIES
        self._retry_delay = self.DEFAULT_RETRY_DELAY
        self._backoff_factor = self.DEFAULT_BACKOFF_FACTOR
        self._last_request_time: Optional[datetime] = None

    def _enforce_rate_limit(self) -> None:
        """强制执行速率限制（距上次请求至少 _api_interval 秒）"""
        if self._last_request_time is not None:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self._api_interval:
                sleep_time = self._api_interval - elapsed
                logger.debug(f"[{self.source_name}] 速率限制：等待 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)

    def _execute_with_retry(self, func: Callable[..., T]) -> T:
        """执行函数并在失败时重试（指数退避），对不可恢复错误立即失败。

        范式参考 tushare_client._execute_with_retry。
        """
        last_exception = None
        current_delay = self._retry_delay

        for attempt in range(1, self._max_retries + 1):
            try:
                self._enforce_rate_limit()
                # 记录"请求开始"时刻，限流等待以"距上次开始多久"为基准
                self._last_request_time = datetime.now()
                result = func()
                return result
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()

                # 检查是否为不可恢复错误
                if any(kw in error_msg for kw in self._NON_RETRYABLE_KEYWORDS):
                    logger.error(
                        f"[{self.source_name}] 不可恢复错误，跳过重试: {e}"
                    )
                    raise DataFetchError(
                        f"不可恢复的API错误: {e}",
                        source=self.source_name,
                        original_error=e,
                    )

                logger.warning(
                    f"[{self.source_name}] 第 {attempt}/{self._max_retries} 次尝试失败: {e}"
                )
                if attempt >= self._max_retries:
                    break
                time.sleep(current_delay)
                current_delay *= self._backoff_factor

        raise RetryExhaustedError(
            f"重试 {self._max_retries} 次后仍然失败",
            source=self.source_name,
            attempts=self._max_retries,
            original_error=last_exception,
        )

    def fetch(self, sector_type: str) -> List[SectorFundFlowInfo]:
        """
        采集指定板块类型的即时资金流快照。

        Args:
            sector_type: "industry" 或 "concept"

        Returns:
            该类型下所有板块的资金流信息列表（成功部分；空数据返回 []）
        """
        normalized = (sector_type or "").strip().lower()
        if normalized not in _SECTOR_API:
            raise ValueError(
                f"无效的板块类型: {sector_type}，仅支持 industry / concept"
            )

        import akshare as ak
        import pandas as pd

        api_name = _SECTOR_API[normalized]
        api_func = getattr(ak, api_name)

        def _fetch():
            logger.info(
                f"[{self.source_name}] 正在获取{normalized}板块即时资金流..."
            )
            return api_func(symbol="即时")

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(
                f"[{self.source_name}] {normalized} 即时资金流返回空数据"
            )
            return []

        items: List[SectorFundFlowInfo] = []
        errors = 0
        for _, row in df.iterrows():
            try:
                data = {}
                for col, field in _COLUMN_MAP.items():
                    if col not in row.index:
                        continue
                    val = row[col]
                    if pd.isna(val):
                        data[field] = None
                    elif field in _STRING_FIELDS:
                        data[field] = str(val).strip()
                    elif field == "company_count":
                        data[field] = int(val)
                    else:
                        data[field] = float(val)
                # 板块名称必填且需清洗为字符串
                name = data.get("sector_name")
                if name is None:
                    continue
                data["sector_name"] = str(name).strip()
                if not data["sector_name"]:
                    continue
                items.append(SectorFundFlowInfo(**data))
            except (ValidationError, ValueError, TypeError):
                errors += 1

        logger.info(
            f"[{self.source_name}] {normalized} 成功转换 {len(items)} 个板块，"
            f"忽略 {errors} 条异常数据"
        )
        return items

    def fetch_all(self) -> dict[str, List[SectorFundFlowInfo]]:
        """
        采集行业 + 概念两类板块的即时资金流，两次调用之间强制 sleep。

        Returns:
            {"industry": [...], "concept": [...]}
        """
        industry = self.fetch("industry")
        # 行业与概念调用之间强制 sleep，避免风控
        time.sleep(self.DEFAULT_BETWEEN_TYPE_INTERVAL)
        concept = self.fetch("concept")
        return {"industry": industry, "concept": concept}
