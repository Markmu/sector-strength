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
from .models import DailyQuote, SectorInfo, SectorMemberInfo, StockInfo
from .sector_types import (
    SECTOR_TYPES,
    THS_TYPE_LABEL,
    THS_TYPE_MAP,
    is_valid_sector_type,
)

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
    # 速率限制：每分钟 200 次 → 间隔 = 60 / 200 = 0.3 秒
    DEFAULT_API_INTERVAL = 0.3

    def __init__(self):
        super().__init__("Tushare")
        self._token = os.getenv("TUSHARE_TOKEN", "").strip()
        self._api_url = os.getenv(
            "TUSHARE_API_URL", "https://ts.gyzcloud.top/api"
        ).strip()
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
                from tushare.pro.client import DataApi

                self._pro_api = DataApi(token=self._token, timeout=60)
                # DataApi 的 __http_url 是类属性，通过 _DataApi__http_url 修改
                self._pro_api._DataApi__http_url = self._api_url
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

    # 不可恢复错误关键词：遇到这些错误时立即失败，不重试
    _NON_RETRYABLE_KEYWORDS = [
        "权限不足", "没有足够积分", "forbidden",
        "参数错误", "invalid parameter",
        "token不对", "认证失败", "unauthorized",
        "没有权限",
    ]

    def _execute_with_retry(self, func: Callable[..., T]) -> T:
        """执行函数并在失败时重试（指数退避），对不可恢复错误立即失败"""
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
                error_msg = str(e).lower()

                # 检查是否为不可恢复错误
                if any(kw in error_msg for kw in self._NON_RETRYABLE_KEYWORDS):
                    logger.error(f"[Tushare] 不可恢复错误，跳过重试: {e}")
                    raise DataFetchError(
                        f"不可恢复的API错误: {e}",
                        source=self.source_name,
                        original_error=e,
                    )

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
        """获取 A 股股票列表 — 提取 stock_basic 全部字段"""
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

                # 交易所映射：ts_code 后缀 → Tushare exchange 字段
                exchange_map = {"SH": "SSE", "SZ": "SZSE", "BJ": "BSE"}
                exchange = exchange_map.get(suffix)

                # Tushare market 字段（主板/创业板/科创板/CDR）
                market = str(row.get("market", "")) or None if pd.notna(row.get("market")) else None
                industry = str(row.get("industry", "")) or None if pd.notna(row.get("industry")) else None
                area = str(row.get("area", "")) or None if pd.notna(row.get("area")) else None
                fullname = str(row.get("fullname", "")) or None if pd.notna(row.get("fullname")) else None
                enname = str(row.get("enname", "")) or None if pd.notna(row.get("enname")) else None
                cnspell = str(row.get("cnspell", "")) or None if pd.notna(row.get("cnspell")) else None
                curr_type = str(row.get("curr_type", "")) or None if pd.notna(row.get("curr_type")) else None
                list_status = str(row.get("list_status", "")) or None if pd.notna(row.get("list_status")) else None
                is_hs = str(row.get("is_hs", "")) or None if pd.notna(row.get("is_hs")) else None
                act_name = str(row.get("act_name", "")) or None if pd.notna(row.get("act_name")) else None
                act_ent_type = str(row.get("act_ent_type", "")) or None if pd.notna(row.get("act_ent_type")) else None

                list_date = None
                if pd.notna(row.get("list_date")):
                    list_date = datetime.strptime(str(row["list_date"]), "%Y%m%d").date()

                delist_date = None
                if pd.notna(row.get("delist_date")):
                    delist_date = datetime.strptime(str(row["delist_date"]), "%Y%m%d").date()

                stocks.append(
                    StockInfo(
                        symbol=symbol,
                        name=name,
                        ts_code=ts_code,
                        area=area,
                        industry=industry,
                        fullname=fullname,
                        enname=enname,
                        cnspell=cnspell,
                        market=market,
                        exchange=exchange,
                        curr_type=curr_type,
                        list_status=list_status,
                        list_date=list_date,
                        delist_date=delist_date,
                        is_hs=is_hs,
                        act_name=act_name,
                        act_ent_type=act_ent_type,
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
        if normalized and not is_valid_sector_type(normalized):
            raise ValueError(f"无效的板块类型过滤: {sector_type}")

        sectors: List[SectorInfo] = []
        types_to_fetch = [normalized] if normalized else list(SECTOR_TYPES)

        for t in types_to_fetch:
            is_code = THS_TYPE_MAP[t]
            sectors.extend(self._fetch_sectors_by_type(pro, is_code, t))

        logger.info(f"[Tushare] 获取到 {len(sectors)} 个板块")
        return sectors

    def _fetch_sectors_by_type(
        self, pro, is_type: str, type_label: str
    ) -> List[SectorInfo]:
        """按类型获取板块列表"""
        label = THS_TYPE_LABEL.get(is_type, is_type)

        def _fetch():
            logger.info(f"[Tushare] 正在获取{label}板块列表...")
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

    def get_sector_members(self, ts_code: str) -> SectorMemberInfo:
        """
        获取板块成分股列表

        通过同花顺板块代码调用 ths_member 接口获取成分股，
        返回的 stock_codes 为短码格式（与 stocks.symbol 对齐）。

        Args:
            ts_code: 板块代码 (如 "850121.SI")

        Returns:
            SectorMemberInfo: 板块代码 + 成分股代码列表
        """
        if not ts_code:
            raise ValueError("板块代码不能为空")

        pro = self._get_pro_api()

        def _fetch():
            logger.info(f"[Tushare] 正在获取板块 {ts_code} 的成分股...")
            return pro.ths_member(ts_code=ts_code)

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(f"[Tushare] 板块 {ts_code} 无成分股数据")
            return SectorMemberInfo(sector_code=ts_code, stock_codes=[])

        stock_codes: List[str] = []
        for _, row in df.iterrows():
            try:
                con_code = str(row["con_code"])
                # con_code 格式为 "000001.SZ"，提取短码部分以对齐 stocks.symbol
                symbol = con_code.split(".")[0] if "." in con_code else con_code
                if symbol:
                    stock_codes.append(symbol)
            except (KeyError, ValueError):
                pass

        logger.info(f"[Tushare] 板块 {ts_code} 获取到 {len(stock_codes)} 只成分股")
        return SectorMemberInfo(sector_code=ts_code, stock_codes=stock_codes)

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
        if not is_valid_sector_type(normalized):
            raise ValueError(f"无效的板块类型: {sector_type}")
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        pro = self._get_pro_api()

        # 通过板块名称查找 ts_code
        is_type = THS_TYPE_MAP.get(normalized, "I")
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

    # ============== 基金数据接口 ==============

    def get_fund_list(self, market: str) -> List[dict]:
        """
        获取基金列表（基本信息）

        通过 offset 分页循环获取全部数据（单次最大 15000 条）。

        Args:
            market: 市场类型，'E' 场内 / 'O' 场外

        Returns:
            原始字典列表，字段名保持 Tushare 原始键名
        """
        import pandas as pd

        pro = self._get_pro_api()
        all_records: List[dict] = []
        offset = 0
        batch_size = 15000

        while True:
            current_offset = offset

            def _fetch(_offset=current_offset):
                logger.info(
                    f"[Tushare] 正在获取基金列表 (market={market}, offset={_offset})..."
                )
                return pro.fund_basic(
                    market=market,
                    offset=_offset,
                    limit=batch_size,
                )

            df = self._execute_with_retry(_fetch)
            if df is None or (hasattr(df, "empty") and df.empty):
                break

            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    val = row[col]
                    if pd.isna(val):
                        record[col] = None
                    else:
                        record[col] = val
                all_records.append(record)

            if len(df) < batch_size:
                break

            offset += batch_size

        logger.info(
            f"[Tushare] 获取到 {len(all_records)} 条基金基本信息 (market={market})"
        )
        return all_records

    def get_fund_portfolio(self, period: str) -> List[dict]:
        """
        获取基金持仓明细

        通过 offset 分页循环获取全部数据（每次 5000 条）。

        Args:
            period: 报告期，格式 'YYYYMMDD'（如 '20241231'）

        Returns:
            原始字典列表，字段名保持 Tushare 原始键名
        """
        import pandas as pd

        pro = self._get_pro_api()
        all_records: List[dict] = []
        offset = 0
        batch_size = 5000

        while True:
            current_offset = offset

            def _fetch(_offset=current_offset):
                logger.info(
                    f"[Tushare] 正在获取基金持仓 (period={period}, offset={_offset})..."
                )
                return pro.fund_portfolio(
                    period=period,
                    offset=_offset,
                    limit=batch_size,
                )

            df = self._execute_with_retry(_fetch)
            if df is None or (hasattr(df, "empty") and df.empty):
                break

            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    val = row[col]
                    if pd.isna(val):
                        record[col] = None
                    else:
                        record[col] = val
                all_records.append(record)

            if len(df) < batch_size:
                break

            offset += batch_size

        logger.info(
            f"[Tushare] 获取到 {len(all_records)} 条基金持仓明细 (period={period})"
        )
        return all_records

    def get_fund_portfolio_by_code(
        self, ts_code: str, period: str
    ) -> List[dict]:
        """
        按单个基金代码获取持仓明细

        当代理不支持按 period 全量查询时，逐个基金拉取。

        Args:
            ts_code: 基金代码，如 '000001.OF'
            period: 报告期，格式 'YYYYMMDD'（如 '20241231'）

        Returns:
            原始字典列表，字段名保持 Tushare 原始键名
        """
        import pandas as pd

        pro = self._get_pro_api()

        def _fetch():
            return pro.fund_portfolio(
                ts_code=ts_code,
                period=period,
            )

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            return []

        records: List[dict] = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                if pd.isna(val):
                    record[col] = None
                else:
                    record[col] = val
            records.append(record)

        return records
