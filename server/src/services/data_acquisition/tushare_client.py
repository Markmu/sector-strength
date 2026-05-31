"""
Tushare 数据源客户端

实现与 Tushare SDK 的交互，提供股票和板块数据获取功能。
"""

import logging
import os
import time
from datetime import date, datetime
from typing import Any, Callable, List, Optional, TypeVar

from pydantic import ValidationError

from .base import BaseDataSource
from .exceptions import DataFetchError, RetryExhaustedError
from .models import DailyQuote, SectorInfo, StockInfo

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TushareDataSource(BaseDataSource):
    """
    Tushare 数据源实现

    提供重试机制、频率控制、数据验证等功能。
    """

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 1.0
    DEFAULT_BACKOFF_FACTOR = 2.0
    DEFAULT_API_INTERVAL = 0.5

    def __init__(self):
        super().__init__("Tushare")
        self._token = os.getenv("TUSHARE_TOKEN", "").strip()
        self._api_url = os.getenv("TUSHARE_API_URL", "api.tushare.pro").strip()
        self._api_interval = float(
            os.getenv("TUSHARE_API_INTERVAL", str(self.DEFAULT_API_INTERVAL))
        )
        self._max_retries = self.DEFAULT_MAX_RETRIES
        self._retry_delay = self.DEFAULT_RETRY_DELAY
        self._backoff_factor = self.DEFAULT_BACKOFF_FACTOR
        self._pro_api = None
        self._last_request_time: Optional[datetime] = None

    def _get_pro_api(self) -> Any:
        """延迟初始化 Tushare pro_api"""
        if self._pro_api is None:
            if not self._token:
                raise DataFetchError(
                    "TUSHARE_TOKEN 未配置",
                    source=self.source_name,
                )
            try:
                import tushare as ts

                self._pro_api = ts.pro_api(self._token, api_url=self._api_url)
                logger.info(f"[Tushare] 初始化成功，服务地址: {self._api_url}")
            except ImportError as e:
                raise ImportError("tushare 未安装，请运行: pip install tushare") from e
            except Exception as e:
                raise DataFetchError(
                    f"Tushare 初始化失败: {e}",
                    source=self.source_name,
                    original_error=e,
                )
        return self._pro_api

    def _enforce_rate_limit(self) -> None:
        """强制执行速率限制"""
        if self._last_request_time is not None:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self._api_interval:
                sleep_time = self._api_interval - elapsed
                logger.debug(f"[Tushare] 速率限制：等待 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)

    def _execute_with_retry(self, func: Callable[..., T]) -> T:
        """执行函数并在失败时重试（指数退避）"""
        last_exception = None
        current_delay = self._retry_delay

        for attempt in range(1, self._max_retries + 1):
            try:
                self._enforce_rate_limit()
                result = func()
                self._last_request_time = datetime.now()
                return result
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"[Tushare] 第 {attempt}/{self._max_retries} 次尝试失败: {e}"
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

    @staticmethod
    def _symbol_to_ts_code(symbol: str) -> str:
        """将纯数字股票代码转换为 Tushare ts_code 格式"""
        if symbol.startswith("6"):
            return f"{symbol}.SH"
        elif symbol.startswith(("0", "3")):
            return f"{symbol}.SZ"
        elif symbol.startswith(("8", "4")):
            return f"{symbol}.BJ"
        return symbol

    def get_trading_calendar(self) -> List[date]:
        """获取上交所交易日历"""
        pro = self._get_pro_api()

        def _fetch():
            logger.info("[Tushare] 正在获取交易日历...")
            return pro.trade_cal(exchange="SSE", is_open="1")

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            raise DataFetchError(
                "交易日历返回空数据", source=self.source_name, endpoint="trade_cal"
            )

        dates: List[date] = []
        for val in df["cal_date"]:
            d = datetime.strptime(str(val), "%Y%m%d").date()
            dates.append(d)
        dates.sort()
        logger.info(f"[Tushare] 获取到 {len(dates)} 个交易日")
        return dates

    def get_stock_list(self) -> List[StockInfo]:
        """获取 A 股股票列表"""
        pro = self._get_pro_api()

        def _fetch():
            logger.info("[Tushare] 正在获取股票列表...")
            return pro.stock_basic(exchange="", list_status="L")

        df = self._execute_with_retry(_fetch)
        stocks: List[StockInfo] = []
        errors = 0

        import pandas as pd

        for _, row in df.iterrows():
            try:
                ts_code = str(row["ts_code"])
                symbol = ts_code.split(".")[0]
                name = str(row["name"])
                suffix = ts_code.split(".")[1] if "." in ts_code else ""
                market_map = {"SH": "SH", "SZ": "SZ", "BJ": "BJ"}
                market = market_map.get(suffix)
                industry = str(row.get("industry", "")) or None
                list_date = None
                if pd.notna(row.get("list_date")):
                    list_date = datetime.strptime(str(row["list_date"]), "%Y%m%d").date()
                stocks.append(
                    StockInfo(
                        symbol=symbol,
                        name=name,
                        market=market,
                        industry=industry,
                        list_date=list_date,
                    )
                )
            except (ValidationError, ValueError):
                errors += 1

        logger.info(
            f"[Tushare] 成功转换 {len(stocks)} 只股票，忽略 {errors} 条异常数据"
        )
        return stocks

    def get_sector_list(self, sector_type: Optional[str] = None) -> List[SectorInfo]:
        """获取板块列表"""
        pro = self._get_pro_api()
        normalized = sector_type.strip().lower() if sector_type else None
        if normalized and normalized not in ("industry", "concept"):
            raise ValueError(f"无效的板块类型过滤: {sector_type}")

        sectors: List[SectorInfo] = []

        if normalized is None or normalized == "industry":
            sectors.extend(self._fetch_sectors_by_type(pro, "行业", "industry"))
        if normalized is None or normalized == "concept":
            sectors.extend(self._fetch_sectors_by_type(pro, "概念", "concept"))

        logger.info(f"[Tushare] 获取到 {len(sectors)} 个板块")
        return sectors

    def _fetch_sectors_by_type(
        self, pro, is_type: str, type_label: str
    ) -> List[SectorInfo]:
        """按类型获取板块列表"""
        def _fetch():
            logger.info(f"[Tushare] 正在获取{is_type}板块列表...")
            return pro.ths_index(exchange="A", type=is_type)

        df = self._execute_with_retry(_fetch)
        result: List[SectorInfo] = []
        for _, row in df.iterrows():
            try:
                result.append(
                    SectorInfo(
                        code=str(row["ts_code"]),
                        name=str(row["name"]),
                        type=type_label,
                    )
                )
            except (ValidationError, ValueError):
                pass
        return result

    def get_daily_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> List[DailyQuote]:
        """获取个股前复权日线行情"""
        if not symbol:
            raise ValueError("股票代码不能为空")
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        import tushare as ts

        pro = self._get_pro_api()
        ts_code = self._symbol_to_ts_code(symbol)

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取 {symbol} 的日线数据 ({start_date} 至 {end_date})..."
            )
            return ts.pro_bar(
                ts_code=ts_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adj="qfq",
                api=pro,
            )

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            return []

        quotes: List[DailyQuote] = []
        errors = 0
        for _, row in df.iterrows():
            try:
                trade_date = datetime.strptime(str(row["trade_date"]), "%Y%m%d").date()
                turnover = None
                if "turnover_rate" in row.index and row.get("turnover_rate") is not None:
                    try:
                        turnover = float(row["turnover_rate"])
                    except (ValueError, TypeError):
                        pass
                quote = DailyQuote(
                    symbol=symbol,
                    trade_date=trade_date,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["vol"]),
                    amount=float(row["amount"]) * 1000,  # 千元 → 元
                    turnover=turnover,
                )
                quotes.append(quote)
            except (ValidationError, ValueError, TypeError):
                errors += 1

        quotes.sort(key=lambda q: q.trade_date)
        logger.info(
            f"[Tushare] 成功转换 {len(quotes)} 条日线数据，忽略 {errors} 条异常数据"
        )
        return quotes

    def get_sector_daily_data(
        self,
        sector_name: str,
        sector_type: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyQuote]:
        """获取板块日线行情"""
        if not sector_name:
            raise ValueError("板块名称不能为空")
        if not sector_type:
            raise ValueError("板块类型不能为空")
        normalized = sector_type.strip().lower()
        if normalized not in ("industry", "concept"):
            raise ValueError(f"无效的板块类型: {sector_type}")
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        pro = self._get_pro_api()

        # 通过板块名称查找 ts_code
        is_type = "行业" if normalized == "industry" else "概念"
        sectors = self._fetch_sectors_by_type(pro, is_type, normalized)
        ts_code = None
        for s in sectors:
            if s.name == sector_name:
                ts_code = s.code
                break
        if not ts_code:
            logger.warning(f"[Tushare] 未找到板块 '{sector_name}' 的 ts_code")
            return []

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取板块 {sector_name} 的日线数据 ({start_date} 至 {end_date})..."
            )
            return pro.ths_daily(
                ts_code=ts_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
            )

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            return []

        quotes: List[DailyQuote] = []
        errors = 0
        for _, row in df.iterrows():
            try:
                trade_date = datetime.strptime(str(row["trade_date"]), "%Y%m%d").date()
                quote = DailyQuote(
                    symbol=sector_name,
                    trade_date=trade_date,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["vol"]),
                )
                quotes.append(quote)
            except (ValidationError, ValueError, TypeError):
                errors += 1

        quotes.sort(key=lambda q: q.trade_date)
        logger.info(
            f"[Tushare] 成功转换 {len(quotes)} 条板块日线数据，忽略 {errors} 条异常数据"
        )
        return quotes

    def health_check(self) -> bool:
        """检查 Tushare 连接状态"""
        try:
            pro = self._get_pro_api()
            df = pro.trade_cal(exchange="SSE", limit=1)
            return df is not None and not df.empty
        except Exception as e:
            logger.warning(f"[Tushare] 健康检查失败: {e}")
            return False
