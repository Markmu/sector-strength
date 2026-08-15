"""
Tushare 数据源客户端

实现与 Tushare SDK 的交互，提供股票和板块数据获取功能。
"""

import asyncio
import logging
import os
import time

import pandas as pd
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from math import ceil
from typing import Any, Callable, List, Optional, TypeVar

from pydantic import ValidationError

from .base import BaseDataSource
from .exceptions import DataFetchError, RetryExhaustedError
from .models import (
    DailyQuote,
    LifecycleStock,
    MarketDataIntegrityError,
    MarketDailyQuote,
    SectorInfo,
    SectorMemberInfo,
    StockInfo,
    SuspensionRecord,
    TradingCalendarEntry,
)
from .sector_types import (
    SECTOR_TYPES,
    SW_LEVELS,
    SW_SECTOR_TYPE,
    SW_SRC,
    THS_TYPE_LABEL,
    THS_TYPE_MAP,
    is_valid_sector_type,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")



def _opt_str(row, key: str):
    """行字段转字符串；NaN/None/空串统一返回 None。"""
    val = row.get(key)
    if val is None or not pd.notna(val):
        return None
    return str(val) or None


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

    # fund_basic / fund_portfolio 的 offset 分页安全上限（实测代理可能忽略
    # offset 重复回页，见 _fetch_lifecycle_by_status 同款守卫）。
    # fund_basic 15000/页：50 页 = 75 万行，远超全市场基金数；
    # fund_portfolio 5000/页：400 页 = 200 万行，覆盖单报告期全量持仓。
    FUND_BASIC_MAX_PAGES = 50
    FUND_PORTFOLIO_MAX_PAGES = 400

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
                # 记录"请求开始"时刻，限流等待以"距上次开始多久"为基准，
                # 这样请求耗时本身不再被算入节流间隔，节奏更稳定。
                self._last_request_time = datetime.now()
                result = func()
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

    def get_trading_calendar_range(
        self, start_date: date, end_date: date
    ) -> List[TradingCalendarEntry]:
        """获取闭区间全量开/休市记录（含休市日，不过滤 is_open）

        调用 ``pro.trade_cal(exchange='SSE', start_date, end_date, fields='cal_date,is_open')``，
        明确不传 ``is_open`` 过滤，保留休市日（架构 ADR-6：首页缺口轴与非交易日守卫
        需要休市日锚点）。整个调用包在 ``_execute_with_retry``（3 次指数退避）内。

        逐行映射为 ``TradingCalendarEntry``（``cal_date`` 字符串转 ``date``，
        ``is_open`` 转 ``bool``）。Provider 失败直接抛，由 Repository 决定不提交。

        与旧 ``get_trading_calendar()``（仅开市日、过滤休市）并存，本需求任何调用点
        不得使用旧方法。
        """
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取交易日历闭区间全量记录 "
                f"({start_date} 至 {end_date})..."
            )
            return pro.trade_cal(
                exchange="SSE",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                fields="cal_date,is_open",
            )

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            raise DataFetchError(
                "交易日历闭区间返回空数据",
                source=self.source_name,
                endpoint="trade_cal",
            )

        entries: List[TradingCalendarEntry] = []
        for _, row in df.iterrows():
            cal_date = datetime.strptime(str(row["cal_date"]), "%Y%m%d").date()
            # is_open 通常为 0/1 整数，兼容字符串/浮点
            is_open = bool(int(row["is_open"]))
            entries.append(TradingCalendarEntry(cal_date=cal_date, is_open=is_open))

        entries.sort(key=lambda e: e.cal_date)
        open_count = sum(1 for e in entries if e.is_open)
        logger.info(
            f"[Tushare] 获取到 {len(entries)} 条日历记录 "
            f"(开市 {open_count} / 休市 {len(entries) - open_count})"
        )
        return entries

    def get_stock_list(self) -> List[StockInfo]:
        """获取 A 股股票列表 — 提取 stock_basic 全部字段"""
        pro = self._get_pro_api()

        def _fetch():
            logger.info("[Tushare] 正在获取股票列表...")
            # 显式指定 fields，因为 Tushare 默认不返回 list_status/exchange/curr_type/delist_date/is_hs/fullname/enname 等字段
            fields = "ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type"
            return pro.stock_basic(exchange="", list_status="L", fields=fields)

        df = self._execute_with_retry(_fetch)
        stocks: List[StockInfo] = []
        errors = 0


        for _, row in df.iterrows():
            try:
                ts_code = str(row["ts_code"])
                symbol = ts_code.split(".")[0]
                name = str(row["name"])
                # 直接使用 Tushare 返回的 exchange 字段
                exchange = _opt_str(row, "exchange")

                # Tushare market 字段（主板/创业板/科创板/CDR）
                market = _opt_str(row, "market")
                industry = _opt_str(row, "industry")
                area = _opt_str(row, "area")
                fullname = _opt_str(row, "fullname")
                enname = _opt_str(row, "enname")
                cnspell = _opt_str(row, "cnspell")
                curr_type = _opt_str(row, "curr_type")
                list_status = _opt_str(row, "list_status")
                is_hs = _opt_str(row, "is_hs")
                act_name = _opt_str(row, "act_name")
                act_ent_type = _opt_str(row, "act_ent_type")

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

    def get_hk_stock_list(self) -> List[StockInfo]:
        """获取港股基础信息列表 — 提取 hk_basic 字段

        - hk_basic 不返回 exchange，统一设为 HKEX
        - 字段名 cn_spell（带下划线）映射到 cnspell
        - trade_unit/isin 为港股特有字段，stocks 表不存储，丢弃
        - industry/area/is_hs/act_name/act_ent_type 港股无对应，留空
        """
        pro = self._get_pro_api()

        def _fetch():
            logger.info("[Tushare] 正在获取港股列表...")
            fields = (
                "ts_code,name,fullname,enname,cn_spell,market,"
                "list_status,list_date,delist_date,curr_type"
            )
            return pro.hk_basic(exchange="", list_status="L", fields=fields)

        df = self._execute_with_retry(_fetch)
        stocks: List[StockInfo] = []
        errors = 0


        for _, row in df.iterrows():
            try:
                ts_code = str(row["ts_code"])
                symbol = ts_code.split(".")[0]
                name = str(row["name"])

                fullname = _opt_str(row, "fullname")
                enname = _opt_str(row, "enname")
                cnspell = _opt_str(row, "cn_spell")
                market = _opt_str(row, "market")
                curr_type = _opt_str(row, "curr_type")
                list_status = _opt_str(row, "list_status")

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
                        fullname=fullname,
                        enname=enname,
                        cnspell=cnspell,
                        market=market,
                        exchange="HKEX",  # hk_basic 不返回 exchange，统一标记港交所
                        curr_type=curr_type,
                        list_status=list_status,
                        list_date=list_date,
                        delist_date=delist_date,
                    )
                )
            except (ValidationError, ValueError):
                errors += 1

        logger.info(
            f"[Tushare] 成功转换 {len(stocks)} 只港股，忽略 {errors} 条异常数据"
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
        sector_code: Optional[str] = None,
    ) -> List[DailyQuote]:
        """获取板块日线行情

        按 ``sector_type`` 分流数据源：
        - 申万行业（``sw_industry``）：走 :meth:`get_sw_index_daily`，按 ``sector_code``
          取数（申万指数代码形如 801010.SI，避免与同花顺同名行业的 name 歧义）。
        - 同花顺（industry/concept/region）：维持原有按板块名称反查 ts_code +
          ``pro.ths_daily`` 的取数逻辑。

        Args:
            sector_name: 板块名称（同花顺按名称反查 ts_code；申万仅用于日志）
            sector_type: 板块类型，同花顺 industry/concept/region 或申万 sw_industry
            start_date: 开始日期
            end_date: 结束日期
            sector_code: 板块代码，申万分支必填（同花顺分支可选，用于日志）
        """
        if not sector_type:
            raise ValueError("板块类型不能为空")
        normalized = sector_type.strip().lower()
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        # 申万行业：按 sector_code 走申万指数日线接口
        if normalized == SW_SECTOR_TYPE:
            return self.get_sw_index_daily(
                ts_code=sector_code or "",
                start_date=start_date,
                end_date=end_date,
            )

        # 同花顺：维持原有校验与按名称反查 ts_code 的取数逻辑
        if not sector_name:
            raise ValueError("板块名称不能为空")
        if not is_valid_sector_type(normalized):
            raise ValueError(f"无效的板块类型: {sector_type}")

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

        pro = self._get_pro_api()
        all_records: List[dict] = []
        offset = 0
        batch_size = 15000
        page_no = 0
        seen_signatures = set()

        while True:
            page_no += 1
            if page_no > self.FUND_BASIC_MAX_PAGES:
                raise DataFetchError(
                    f"fund_basic(market={market}) 分页页数 {page_no} "
                    f"超过安全上限 {self.FUND_BASIC_MAX_PAGES}（疑似 offset 失效）",
                    source=self.source_name,
                    endpoint="fund_basic",
                )
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

            # 页签名重复（首行 ts_code + 行数在不同 offset 重现）说明代理
            # 忽略了 offset 在重复回页，继续循环只会无限追加重复数据
            page_first_key = (
                all_records[-1].get("ts_code") if all_records else None
            )
            signature = (page_first_key, len(df))
            if signature in seen_signatures:
                raise DataFetchError(
                    f"fund_basic(market={market}) 页签名重复: "
                    f"首行 ts_code={page_first_key}, 行数={len(df)} "
                    f"在 offset={current_offset} 再次出现 "
                    f"(第 {page_no} 页, 已收集 {len(all_records)} 行)",
                    source=self.source_name,
                    endpoint="fund_basic",
                )
            seen_signatures.add(signature)

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

        pro = self._get_pro_api()
        all_records: List[dict] = []
        offset = 0
        batch_size = 5000
        page_no = 0
        seen_signatures = set()

        while True:
            page_no += 1
            if page_no > self.FUND_PORTFOLIO_MAX_PAGES:
                raise DataFetchError(
                    f"fund_portfolio(period={period}) 分页页数 {page_no} "
                    f"超过安全上限 {self.FUND_PORTFOLIO_MAX_PAGES}"
                    f"（疑似 offset 失效）",
                    source=self.source_name,
                    endpoint="fund_portfolio",
                )
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

            # 页签名重复说明代理忽略 offset 在重复回页（同 fund_basic 守卫）
            page_first_key = (
                all_records[-1].get("ts_code") if all_records else None
            )
            signature = (page_first_key, len(df))
            if signature in seen_signatures:
                raise DataFetchError(
                    f"fund_portfolio(period={period}) 页签名重复: "
                    f"首行 ts_code={page_first_key}, 行数={len(df)} "
                    f"在 offset={current_offset} 再次出现 "
                    f"(第 {page_no} 页, 已收集 {len(all_records)} 行)",
                    source=self.source_name,
                    endpoint="fund_portfolio",
                )
            seen_signatures.add(signature)

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

    # ============== ETF 数据接口（第 14 期） ==============
    #
    # 复用 get_fund_list（offset 分页）+ _execute_with_retry + _enforce_rate_limit
    # + 返回原始 dict 的范式。返回字段保持 Tushare 原始键名，由上层服务消费。

    def get_fund_basic_etf(self) -> List[dict]:
        """
        获取 ETF 基础信息列表（pro.etf_basic，list_status='L' 仅上市）

        通过 Tushare 独立的 ``etf_basic`` 接口获取全市场已上市 ETF，天然不含
        LOF / 封闭式基金，且直接返回官方跟踪指数（index_code / index_name）。
        不再做 name 含 'ETF' 的客户端过滤。

        实测 list_status='L' 返回约 1600+ 只 ETF。

        Returns:
            原始字典列表，保留 Tushare 键名
            (ts_code/csname/extname/cname/index_code/index_name/setup_date/
             list_date/list_status/exchange/mgr_name/custod_name/mgt_fee/etf_type)
        """

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                "[Tushare] 正在获取 ETF 基础信息 (etf_basic, list_status=L)..."
            )
            return pro.etf_basic(list_status="L")

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning("[Tushare] etf_basic 返回空数据")
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

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条已上市 ETF (etf_basic list_status=L)"
        )
        return records

    def get_etf_share_size(self, trade_date: str) -> List[dict]:
        """
        获取 ETF 每日份额/规模/净值（pro.etf_share_size，按 trade_date 全量）

        Tushare 独立的 ``etf_share_size`` 接口，一次请求同时返回全市场 ETF 当日的
        总份额、总规模、单位净值、收盘价，取代旧 fund_share + 逐只 fund_nav 方案。

        实测 list_status='L' 交易日返回约 1600+ 条。

        Args:
            trade_date: 交易日，格式 'YYYYMMDD'（如 '20260728'）

        Returns:
            原始字典列表，保留 Tushare 键名
            (trade_date/ts_code/etf_name/total_share/total_size/nav/close/exchange)
            - total_share：总份额（万份，与 fund_share.fd_share 同口径）
            - total_size：总规模（万元，÷10000 转亿元展示）
            - nav：单位净值（元，部分日期缺失）
            - close：收盘价（元，部分日期缺失）
        """

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取 ETF 份额/规模 (etf_share_size, trade_date={trade_date})..."
            )
            return pro.etf_share_size(trade_date=trade_date)

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(
                f"[Tushare] etf_share_size 返回空数据 (trade_date={trade_date})"
            )
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

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条 ETF 份额/规模 (etf_share_size, trade_date={trade_date})"
        )
        return records

    def get_limit_list_d(self, trade_date: str) -> List[dict]:
        """
        获取每日涨跌停/炸板个股明细（pro.limit_list_d，按 trade_date 全量）

        Tushare ``limit_list_d`` 接口返回全市场当日涨跌停、炸板个股明细，
        数据从 2020 年开始（不含 ST 股票）。实测每个交易日返回约 200 条。

        Args:
            trade_date: 交易日，格式 'YYYYMMDD'（如 '20260731'）

        Returns:
            原始字典列表，保留 Tushare 键名
            (trade_date/ts_code/industry/name/close/pct_chg/amount/limit_amount/
             float_mv/total_mv/turnover_ratio/fd_amount/first_time/last_time/
             open_times/up_stat/limit_times/limit)
            - limit：U涨停 / D跌停 / Z炸板
            - limit_times：连板数（1=首板）
            - industry：申万行业（个股板块归属维度）
            - fd_amount：封单成交额（元，limit_amount 常为空）
        """

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取涨跌停明细 (limit_list_d, trade_date={trade_date})..."
            )
            return pro.limit_list_d(trade_date=trade_date)

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(
                f"[Tushare] limit_list_d 返回空数据 (trade_date={trade_date})"
            )
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

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条涨跌停明细 (limit_list_d, trade_date={trade_date})"
        )
        return records

    def get_limit_step(self, trade_date: str) -> List[dict]:
        """
        获取涨停连板天梯（pro.limit_step，按 trade_date 全量）

        Tushare ``limit_step`` 接口返回当日各连板高度晋级的股票，
        可分析连续涨停进阶个数。实测每个交易日返回约 10 条。

        Args:
            trade_date: 交易日，格式 'YYYYMMDD'（如 '20260731'）

        Returns:
            原始字典列表，保留 Tushare 键名
            (ts_code/name/trade_date/nums)
            - nums：连板数
        """

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取连板天梯 (limit_step, trade_date={trade_date})..."
            )
            return pro.limit_step(trade_date=trade_date)

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(
                f"[Tushare] limit_step 返回空数据 (trade_date={trade_date})"
            )
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

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条连板天梯 (limit_step, trade_date={trade_date})"
        )
        return records

    def get_limit_cpt_list(self, trade_date: str) -> List[dict]:
        """
        获取涨停最强概念板块（pro.limit_cpt_list，按 trade_date 全量）

        Tushare ``limit_cpt_list`` 接口返回当日涨停家数最多的概念板块排名，
        可分析强势板块轮动。实测每个交易日返回约 20 条。

        Args:
            trade_date: 交易日，格式 'YYYYMMDD'（如 '20260731'）

        Returns:
            原始字典列表，保留 Tushare 键名
            (ts_code/name/trade_date/days/up_stat/cons_nums/up_nums/pct_chg/rank)
            - up_nums：涨停家数
            - cons_nums：连板家数
            - rank：排名
        """

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取涨停最强板块 (limit_cpt_list, trade_date={trade_date})..."
            )
            return pro.limit_cpt_list(trade_date=trade_date)

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(
                f"[Tushare] limit_cpt_list 返回空数据 (trade_date={trade_date})"
            )
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

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条涨停最强板块 (limit_cpt_list, trade_date={trade_date})"
        )
        return records

    # ------------------------------------------------------------------
    # 申万行业分类（index_classify / index_member_all）
    # ------------------------------------------------------------------

    def get_sw_index_classify(self, level: str, src: str = SW_SRC) -> List[dict]:
        """
        获取申万行业分类列表（pro.index_classify，按 level 全量）

        Tushare ``index_classify`` 接口返回申万一/二/三级行业分类。
        实测 L1=31 条、L2=134 条、L3=346 条（SW2021 版）。

        Args:
            level: 行业层级，'L1' / 'L2' / 'L3'
            src: 分类标准，默认 'SW2021'（2021 版），可选 'SW2014'

        Returns:
            原始字典列表，保留 Tushare 键名
            (index_code/industry_name/level/industry_code/is_pub/parent_code/src)
            - index_code：申万指数代码（如 801010.SI）
            - parent_code：父级行业代码，一级为 '0'
            - is_pub：是否发布了指数（1/0）
        """

        if level not in SW_LEVELS:
            raise ValueError(f"无效的申万行业层级: {level}（可选 {SW_LEVELS}）")

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取申万{level}行业分类 (index_classify, src={src})..."
            )
            return pro.index_classify(level=level, src=src)

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(
                f"[Tushare] index_classify 返回空数据 (level={level}, src={src})"
            )
            return []

        records: List[dict] = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                record[col] = None if pd.isna(val) else val
            records.append(record)

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条申万{level}行业分类 (index_classify)"
        )
        return records

    def get_sw_index_member_all(self, src: str = SW_SRC) -> List[dict]:
        """
        获取申万行业成分股当前快照（pro.index_member_all，is_new='Y'）

        Tushare ``index_member_all`` 接口返回申万行业成分股，按三级分类展开。
        取当前快照（is_new='Y'），每只股票一行，含完整的 L1/L2/L3 归属。
        实测约 5889 条。

        Args:
            src: 分类标准（仅用于日志，接口本身按最新版返回）

        Returns:
            原始字典列表，保留 Tushare 键名
            (l1_code/l1_name/l2_code/l2_name/l3_code/l3_name/
             ts_code/name/in_date/out_date/is_new)
            - l*_code 与 index_classify.index_code 格式一致（如 801010.SI）
            - is_new='Y' 表示当前在册
        """

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                "[Tushare] 正在获取申万行业成分股当前快照 "
                "(index_member_all, is_new='Y')..."
            )
            return pro.index_member_all(is_new="Y")

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning("[Tushare] index_member_all 返回空数据")
            return []

        records: List[dict] = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                record[col] = None if pd.isna(val) else val
            records.append(record)

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条申万行业成分股 (index_member_all)"
        )
        return records

    def get_sw_index_daily(
        self,
        ts_code: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyQuote]:
        """获取申万行业指数日线行情（pro.sw_daily，按 ts_code 拉取）

        申万板块目录同步时已将申万指数代码（如 801010.SI）写入 ``sectors.code``，
        本方法直接按 code 取数，无需像同花顺那样按板块名称反查 ts_code，
        也避免了申万与同花顺存在同名行业（如"银行"）时的 name 歧义。

        Args:
            ts_code: 申万指数代码（如 801010.SI，需以 .SI 结尾）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            按交易日期升序排序的日线行情列表
        """
        if not ts_code:
            raise ValueError("申万指数代码不能为空")
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取申万指数 {ts_code} 的日线数据 "
                f"({start_date} 至 {end_date})..."
            )
            return pro.sw_daily(
                ts_code=ts_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
            )

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(f"[Tushare] 申万指数 {ts_code} 无日线数据")
            return []

        quotes: List[DailyQuote] = []
        errors = 0
        for _, row in df.iterrows():
            try:
                trade_date = datetime.strptime(str(row["trade_date"]), "%Y%m%d").date()
                quote = DailyQuote(
                    symbol=ts_code,
                    trade_date=trade_date,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["vol"]),
                    amount=float(row["amount"]) if "amount" in df.columns else None,
                )
                quotes.append(quote)
            except (ValidationError, ValueError, TypeError):
                errors += 1

        quotes.sort(key=lambda q: q.trade_date)
        logger.info(
            f"[Tushare] 成功转换 {len(quotes)} 条申万指数 {ts_code} 日线数据，"
            f"忽略 {errors} 条异常数据"
        )
        return quotes

    async def get_top10_float_holders(
        self, ts_code: str, period: str
    ) -> List[dict]:
        """
        获取单只股票的前十大流通股东数据

        网络请求与重试 sleep 是同步阻塞的，通过 to_thread 移出事件循环
        （调用方在事件循环内 await，裸同步实现会卡住整个 loop）。

        Args:
            ts_code: Tushare 股票代码，如 "600000.SH"
            period: 报告期，YYYYMMDD 格式，如 "20241231"

        Returns:
            dict 列表，每条包含: ts_code, ann_date, end_date, holder_name,
            hold_amount, hold_ratio, hold_float_ratio, hold_change, holder_type
        """

        pro = self._get_pro_api()

        def _fetch():
            return pro.top10_floatholders(
                ts_code=ts_code,
                period=period,
            )

        df = await asyncio.to_thread(self._execute_with_retry, _fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(
                f"[Tushare] top10_floatholders 返回空数据 "
                f"(ts_code={ts_code}, period={period})"
            )
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

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条十大流通股东数据 "
            f"(ts_code={ts_code}, period={period})"
        )
        return records

    async def get_broker_recommend(self, month: str) -> List[dict]:
        """
        获取某月份券商金股推荐数据

        接口原生支持 month 入参（Tushare doc 267），直接拉取该月数据，
        无需 trade_cal 映射。网络请求与重试 sleep 通过 to_thread 移出
        事件循环（同 get_top10_float_holders）。

        Args:
            month: 月份，YYYYMM 格式，如 "202606"

        Returns:
            dict 列表，每条包含: ts_code, trade_date, name, broker, reason
        """

        pro = self._get_pro_api()

        def _fetch():
            logger.info(f"[Tushare] 正在获取券商金股数据 (month={month})...")
            return pro.broker_recommend(month=month)

        df = await asyncio.to_thread(self._execute_with_retry, _fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(
                f"[Tushare] broker_recommend 返回空数据 (month={month})"
            )
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

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条券商金股数据 (month={month})"
        )
        return records

    # ------------------------------------------------------------------
    # 关键指数数据接口（第 15 期 index monitor）
    #
    # 复用 _get_pro_api + _execute_with_retry + _enforce_rate_limit + 返回原始 dict
    # 的范式。字段名保持 Tushare 原始键名，由上层服务（plan-02 IndexDataInitService）
    # 消费入库。
    # 存储层保持原始单位：成交额千元 / 成交量手，API 输出层（plan-03）再转亿元。
    # ------------------------------------------------------------------

    def get_index_basic(
        self, market: Optional[str] = None, ts_code: Optional[str] = None
    ) -> List[dict]:
        """获取指数基础信息（pro.index_basic，全量或按 market/ts_code 过滤）

        Tushare ``index_basic`` 接口返回全市场指数基础信息。实测全量返回约 1 万条，
        覆盖 SSE/SZSE/CSI/SW 各市场。

        注意：``name`` 参数在数据源代理（ts.gyzcloud.top）上不生效，不能靠 name
        过滤查代码，故本方法不暴露 name 入参。

        Args:
            market: 可选市场过滤（SSE/SZSE/CSI/SW），不传则全量
            ts_code: 可选指数代码过滤（如 '000300.SH'），不传则全量

        Returns:
            原始字典列表，保留 Tushare 键名
            (ts_code/name/market/publisher/category/base_date/base_point/list_date)
        """

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取指数基础信息 (index_basic, "
                f"market={market or '全部'}, ts_code={ts_code or '全部'})..."
            )
            params: dict = {}
            if market:
                params["market"] = market
            if ts_code:
                params["ts_code"] = ts_code
            return pro.index_basic(**params)

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning("[Tushare] index_basic 返回空数据")
            return []

        records: List[dict] = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                record[col] = None if pd.isna(val) else val
            records.append(record)

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条指数基础信息 (index_basic)"
        )
        return records

    def get_index_daily(
        self, ts_code: str, start_date: date, end_date: date
    ) -> List[dict]:
        """获取指数日线行情（pro.index_daily，按 ts_code + 日期区间）

        Tushare ``index_daily`` 接口返回指数日线行情（开盘/最高/最低/收盘/涨跌幅/
        成交量/成交额）。存储层保持原始单位：
        - ``vol``：成交量（手）
        - ``amount``：成交额（千元）

        Args:
            ts_code: 指数代码（如 '000300.SH' 沪深300）
            start_date: 开始日期（date 对象，内部转 YYYYMMDD）
            end_date: 结束日期（date 对象，内部转 YYYYMMDD）

        Returns:
            原始字典列表，保留 Tushare 键名
            (ts_code/trade_date/open/high/low/close/pre_close/change/pct_chg/vol/amount)
        """

        if not ts_code:
            raise ValueError("指数代码不能为空")
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取指数 {ts_code} 日线数据 "
                f"({start_date} 至 {end_date})..."
            )
            return pro.index_daily(
                ts_code=ts_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
            )

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(f"[Tushare] index_daily 返回空数据 (ts_code={ts_code})")
            return []

        records: List[dict] = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                record[col] = None if pd.isna(val) else val
            records.append(record)

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条指数日线 (index_daily, ts_code={ts_code})"
        )
        return records

    def get_index_dailybasic(
        self, ts_code: str, start_date: date, end_date: date
    ) -> List[dict]:
        """获取指数每日估值指标（pro.index_dailybasic，按 ts_code + 日期区间）

        Tushare ``index_dailybasic`` 接口返回指数的市值/股本/换手率/估值指标。
        估值覆盖有限：仅宽基指数（沪深300/上证50/中证500/上证180/深证成指/创业板指等）
        有数据，其余指数（如科创50 000688.SH）返回空列表，上层如实提示"暂无估值"。

        Args:
            ts_code: 指数代码（如 '000300.SH' 沪深300）
            start_date: 开始日期（date 对象，内部转 YYYYMMDD）
            end_date: 结束日期（date 对象，内部转 YYYYMMDD）

        Returns:
            原始字典列表，保留 Tushare 键名。无估值的指数返回空列表 []。
            (ts_code/trade_date/total_mv/float_mv/total_share/float_share/
             free_share/turnover_rate/turnover_rate_f/pe/pe_ttm/pb)
        """

        if not ts_code:
            raise ValueError("指数代码不能为空")
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取指数 {ts_code} 估值指标 "
                f"({start_date} 至 {end_date})..."
            )
            return pro.index_dailybasic(
                ts_code=ts_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
            )

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.info(
                f"[Tushare] index_dailybasic 返回空（指数 {ts_code} 可能无估值数据）"
            )
            return []

        records: List[dict] = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                record[col] = None if pd.isna(val) else val
            records.append(record)

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条指数估值指标 "
            f"(index_dailybasic, ts_code={ts_code})"
        )
        return records

    def get_index_weight(
        self, index_code: str, start_date: date, end_date: date
    ) -> List[dict]:
        """获取指数成分权重（pro.index_weight，按 index_code + 日期区间）

        Tushare ``index_weight`` 接口返回指数成分股及其权重。注意接口参数名是
        ``index_code``（不是 ts_code）。沪深300 实测返回约 300 条。

        成分股权重通常在指数调整日（如半年报）刷新，其余交易日数据沿用最近一次调整。

        Args:
            index_code: 指数代码（如 '000300.SH' 沪深300），作为接口入参
            start_date: 开始日期（date 对象，内部转 YYYYMMDD）
            end_date: 结束日期（date 对象，内部转 YYYYMMDD）

        Returns:
            原始字典列表，保留 Tushare 键名
            (index_code/con_code/trade_date/weight)
        """

        if not index_code:
            raise ValueError("指数代码不能为空")
        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取指数 {index_code} 成分权重 "
                f"({start_date} 至 {end_date})..."
            )
            return pro.index_weight(
                index_code=index_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
            )

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(
                f"[Tushare] index_weight 返回空数据 (index_code={index_code})"
            )
            return []

        records: List[dict] = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                record[col] = None if pd.isna(val) else val
            records.append(record)

        logger.info(
            f"[Tushare] 获取到 {len(records)} 条指数成分权重 "
            f"(index_weight, index_code={index_code})"
        )
        return records

    # ------------------------------------------------------------------
    # 全市场量价采集（第 16 期 plan-02）
    #
    # 参数化 daily 分页器（单日模式 + 历史窗口模式）、suspend_d 停牌查询、
    # L/D/P/G 生命周期分页拉取（ADR-1/2/3，架构 §6.1.3-6）。
    # 明确不复用逐股 qfq get_daily_data()；数值一律 Decimal(str(value))，
    # 单位保持 Tushare 原始口径（vol=手 / amount=千元），转换在 plan-03。
    # ------------------------------------------------------------------

    # daily 单页行数（ADR-1 / 架构 §6.1.3）
    MARKET_DAILY_PAGE_SIZE = 3000
    MARKET_DAILY_FIELDS = "ts_code,trade_date,close,pre_close,vol,amount"
    # 历史窗口模式 ts_code 内部分块上限（≤100/批，风险备注：接口参数超限时按此分块）
    WINDOW_TS_CODE_CHUNK_SIZE = 100
    # 生命周期四状态（ADR-2）
    LIFECYCLE_STATUSES = ("L", "D", "P", "G")
    LIFECYCLE_PAGE_SIZE = 3000
    # stock_basic 分页安全上限（防 offset 失效导致的死循环，远超任一状态实际行数）
    LIFECYCLE_MAX_PAGES = 50

    @staticmethod
    def _df_to_rows(df: Any) -> List[dict]:
        """DataFrame 页转原始行字典列表（NaN → None），空/None 返回空列表"""

        if df is None or (hasattr(df, "empty") and df.empty):
            return []
        rows: List[dict] = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                record[col] = None if pd.isna(val) else val
            rows.append(record)
        return rows

    def _parse_tushare_date(
        self,
        value: Any,
        *,
        ts_code: str = "",
        endpoint: str = "daily",
        field: str = "trade_date",
    ) -> date:
        """YYYYMMDD 字符串/数值转 date，失败抛含字段名的完整性错误"""
        try:
            return datetime.strptime(str(value), "%Y%m%d").date()
        except (ValueError, TypeError) as e:
            raise MarketDataIntegrityError(
                f"日期字段 {field} 无法解析: value={value!r} (ts_code={ts_code})",
                source=self.source_name,
                endpoint=endpoint,
                original_error=e,
            ) from e

    def _parse_optional_tushare_date(
        self,
        value: Any,
        *,
        ts_code: str = "",
        endpoint: str = "stock_basic",
        field: str = "list_date",
    ) -> Optional[date]:
        """可选 YYYYMMDD 转 date（None 直通，供 G 状态空日期等场景）"""
        if value is None:
            return None
        return self._parse_tushare_date(
            value, ts_code=ts_code, endpoint=endpoint, field=field
        )

    def _decimal_field(
        self,
        row: dict,
        field: str,
        *,
        ts_code: str,
        allow_none: bool = False,
    ) -> Optional[Decimal]:
        """行字段转 Decimal（架构 §6.1.4：Decimal(str(value))，禁止 binary float 路径）

        校验可解析与 is_finite()；数值范围（close>0 / vol>=0 / amount>=0）
        由调用方按字段语义追加。任一非法抛含 ts_code 与字段值的完整性错误。
        """
        value = row.get(field)
        if value is None:
            if allow_none:
                return None
            raise MarketDataIntegrityError(
                f"daily 行字段 {field} 为空 (ts_code={ts_code}, trade_date={row.get('trade_date')})",
                source=self.source_name,
                endpoint="daily",
            )
        try:
            dec = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as e:
            raise MarketDataIntegrityError(
                f"daily 行字段 {field} 无法转 Decimal: value={value!r} (ts_code={ts_code})",
                source=self.source_name,
                endpoint="daily",
                original_error=e,
            ) from e
        if not dec.is_finite():
            raise MarketDataIntegrityError(
                f"daily 行字段 {field} 非有限数: value={value!r} (ts_code={ts_code})",
                source=self.source_name,
                endpoint="daily",
            )
        return dec

    def _build_market_daily_quote(self, row: dict) -> MarketDailyQuote:
        """单行原始 dict → MarketDailyQuote（数值校验：close>0 / vol>=0 / amount>=0）"""
        raw_code = row.get("ts_code")
        if raw_code is None or not str(raw_code).strip():
            raise MarketDataIntegrityError(
                f"daily 行缺少 ts_code: {row!r}",
                source=self.source_name,
                endpoint="daily",
            )
        ts_code = str(raw_code)
        trade_date = self._parse_tushare_date(
            row.get("trade_date"), ts_code=ts_code
        )

        close = self._decimal_field(row, "close", ts_code=ts_code)
        assert close is not None  # allow_none=False 必返回值（类型收窄）
        if close <= 0:
            raise MarketDataIntegrityError(
                f"daily 行 close 非法: close={close} (ts_code={ts_code}, trade_date={trade_date})",
                source=self.source_name,
                endpoint="daily",
            )
        pre_close = self._decimal_field(
            row, "pre_close", ts_code=ts_code, allow_none=True
        )
        vol = self._decimal_field(row, "vol", ts_code=ts_code)
        assert vol is not None
        if vol < 0:
            raise MarketDataIntegrityError(
                f"daily 行 vol 非法: vol={vol} (ts_code={ts_code}, trade_date={trade_date})",
                source=self.source_name,
                endpoint="daily",
            )
        amount = self._decimal_field(row, "amount", ts_code=ts_code)
        assert amount is not None
        if amount < 0:
            raise MarketDataIntegrityError(
                f"daily 行 amount 非法: amount={amount} (ts_code={ts_code}, trade_date={trade_date})",
                source=self.source_name,
                endpoint="daily",
            )
        return MarketDailyQuote(
            ts_code=ts_code,
            trade_date=trade_date,
            close=close,
            pre_close=pre_close,
            vol=vol,
            amount=amount,
        )

    def _paginate_market_daily(
        self,
        page_params: dict,
        key_fn: Callable[[dict], Any],
        max_pages: int,
        mode_label: str,
    ) -> List[dict]:
        """共享参数化分页引擎（ADR-1 / 架构 §6.1.3 / §6.1.6）

        单日模式与历史窗口模式共用守卫、独享谓词（key_fn 与 page_params
        由两模式分别注入）。每页请求经 ``_execute_with_retry``（内含
        ``_enforce_rate_limit`` 0.3s 节流 + 3 次指数退避，非可重试关键字
        立即失败）。

        共同守卫（每页校验，违反抛 ``MarketDataIntegrityError``，错误信息
        含页数与计数，禁止 drop_duplicates 静默修复）：
        - 页签名重复：同一（首行 key + 行数）的内容形状在两个不同 offset
          上再次出现（如代理忽略 offset 重复回页）。offset 本身严格递增、
          不参与签名身份判定（否则该守卫不可达），但会记入错误信息。
        - 满页（rows == 3000）但本页新增 key 数为 0；
        - 跨页/页内出现重复行 key（单日模式 key=ts_code；历史模式
          key=(ts_code, trade_date) 以支持一股多日行）；
        - 请求页数超过 max_pages 硬上限（含尾部探测页）。

        终止语义：短页（<3000 行）正常终止；首张 0 行页直接返回已收集行
        （可能为空列表，语义由调用方解释：单日=全市场空、历史=窗口无命中）；
        至少一张合法满页后的 0 行页为正常终止（尾部探测页）。

        Args:
            page_params: 传给 ``pro.daily`` 的模式独享参数（单日=trade_date；
                历史=ts_code/start_date/end_date）
            key_fn: 行 key 提取器（重复检测粒度由模式决定）
            max_pages: 硬页数上限（含尾部探测页）
            mode_label: 日志/错误信息中的模式标签

        Returns:
            合并后的原始行字典列表（行级谓词与数值校验由调用方做）
        """
        pro = self._get_pro_api()
        page_size = self.MARKET_DAILY_PAGE_SIZE
        seen_signatures = set()
        seen_keys = set()
        merged: List[dict] = []
        offset = 0
        page_no = 0

        while True:
            page_no += 1
            if page_no > max_pages:
                raise MarketDataIntegrityError(
                    f"{mode_label}: daily 分页请求页数 {page_no} 超过硬上限 {max_pages} "
                    f"(已收集 {len(merged)} 行, 已见 key {len(seen_keys)} 个, offset={offset})",
                    source=self.source_name,
                    endpoint="daily",
                )
            current_offset = offset

            def _fetch(_offset=current_offset, _page=page_no):
                logger.info(
                    f"[Tushare] {mode_label} 拉取 daily 第 {_page} 页 "
                    f"(offset={_offset}, limit={page_size})..."
                )
                return pro.daily(
                    fields=self.MARKET_DAILY_FIELDS,
                    limit=page_size,
                    offset=_offset,
                    **page_params,
                )

            rows = self._df_to_rows(self._execute_with_retry(_fetch))
            row_count = len(rows)

            if row_count == 0:
                logger.info(
                    f"[Tushare] {mode_label} 第 {page_no} 页为空页，分页终止 "
                    f"(已收集 {len(merged)} 行)"
                )
                break

            first_key = key_fn(rows[0])
            signature = (first_key, row_count)
            if signature in seen_signatures:
                raise MarketDataIntegrityError(
                    f"{mode_label}: 页签名重复: 首行 key={first_key}, 行数={row_count} "
                    f"在 offset={current_offset} 再次出现 (第 {page_no} 页, "
                    f"已收集 {len(merged)} 行, 已见 key {len(seen_keys)} 个)",
                    source=self.source_name,
                    endpoint="daily",
                )
            seen_signatures.add(signature)

            page_keys = [key_fn(r) for r in rows]
            new_key_count = sum(1 for k in page_keys if k not in seen_keys)
            if row_count == page_size and new_key_count == 0:
                raise MarketDataIntegrityError(
                    f"{mode_label}: 满页({row_count} 行)但新增 key 数为 0 "
                    f"(第 {page_no} 页, offset={current_offset}, "
                    f"已见 key {len(seen_keys)} 个, 已收集 {len(merged)} 行)",
                    source=self.source_name,
                    endpoint="daily",
                )
            for key in page_keys:
                if key in seen_keys:
                    raise MarketDataIntegrityError(
                        f"{mode_label}: 出现重复行 key={key} (第 {page_no} 页, "
                        f"offset={current_offset}, 已见 key {len(seen_keys)} 个, "
                        f"已收集 {len(merged)} 行)",
                        source=self.source_name,
                        endpoint="daily",
                    )
                seen_keys.add(key)

            merged.extend(rows)
            if row_count < page_size:
                break
            offset += page_size

        logger.info(
            f"[Tushare] {mode_label} 分页完成: 共 {page_no} 页请求, "
            f"合并 {len(merged)} 行, 唯一 key {len(seen_keys)} 个"
        )
        return merged

    def get_market_daily_quotes(
        self, trade_date: date, expected_count: int
    ) -> List[MarketDailyQuote]:
        """单日模式：拉取单交易日全市场未复权行情（ADR-1 / 架构 §6.1.3）

        ``pro.daily(trade_date=YYYYMMDD, limit=3000, offset=...)`` 参数化分页；
        硬页数 = ``ceil(expected_count/3000)+1``（含尾部探测页，
        expected_count 由调用方从生命周期快照传入，expected_count=0 时硬页数=1
        仅探测一页）。每行校验 ``trade_date == T`` 与数值合法性。

        首张 0 行页由本方法返回空列表，由调用方（plan-03）判为全市场空并
        失败；至少一张合法满页后的 0 行页为正常终止。
        """
        if expected_count < 0:
            raise ValueError("expected_count 不能为负数")

        max_pages = ceil(expected_count / self.MARKET_DAILY_PAGE_SIZE) + 1
        rows = self._paginate_market_daily(
            page_params={"trade_date": trade_date.strftime("%Y%m%d")},
            key_fn=lambda r: str(r.get("ts_code")),
            max_pages=max_pages,
            mode_label=f"单日模式 trade_date={trade_date} expected_count={expected_count}",
        )

        quotes: List[MarketDailyQuote] = []
        for row in rows:
            ts_code = str(row.get("ts_code"))
            row_date = self._parse_tushare_date(row.get("trade_date"), ts_code=ts_code)
            if row_date != trade_date:
                raise MarketDataIntegrityError(
                    f"单日模式出现非目标日期行: 期望 trade_date={trade_date}, "
                    f"实际 {row_date} (ts_code={ts_code})",
                    source=self.source_name,
                    endpoint="daily",
                )
            quotes.append(self._build_market_daily_quote(row))

        quotes.sort(key=lambda q: (q.trade_date, q.ts_code))
        logger.info(
            f"[Tushare] 单日模式 {trade_date} 获取 {len(quotes)} 行全市场未复权行情"
        )
        return quotes

    def get_close_quotes_in_window(
        self, ts_codes: List[str], window_start: date, window_end: date
    ) -> List[MarketDailyQuote]:
        """历史窗口模式：拉取一批代码在时间窗口内的未复权行情（ADR-3 / 架构 §6.1.6）

        批次内代码由调用方按 ≤100/批分块；本方法再按 ``WINDOW_TS_CODE_CHUNK_SIZE``
        内部分块，每块独立分页（ts_code 逗号拼接 + start_date/end_date）。
        每块硬页数 = ``ceil(块内代码数 × 窗口自然日数 / 3000)+1``（含尾部
        探测页）。每行校验 ``window_start <= trade_date <= window_end`` 且
        ts_code ∈ 批次（窗口止于 T-1 由调用方保证）。

        首张空页 ≠ 失败：表示该窗口无命中，返回空列表，由调用方推进更早窗口。
        """
        if window_start > window_end:
            raise ValueError("开始日期不能晚于结束日期")

        codes: List[str] = []
        for code in ts_codes:
            normalized = str(code).strip()
            if normalized:
                codes.append(normalized)
        if not codes:
            return []

        code_set = set(codes)
        window_days = (window_end - window_start).days + 1
        quotes: List[MarketDailyQuote] = []

        total_chunks = ceil(len(codes) / self.WINDOW_TS_CODE_CHUNK_SIZE)
        for chunk_index in range(total_chunks):
            chunk = codes[
                chunk_index
                * self.WINDOW_TS_CODE_CHUNK_SIZE : (chunk_index + 1)
                * self.WINDOW_TS_CODE_CHUNK_SIZE
            ]
            max_candidates = len(chunk) * window_days
            max_pages = ceil(max_candidates / self.MARKET_DAILY_PAGE_SIZE) + 1
            rows = self._paginate_market_daily(
                page_params={
                    "ts_code": ",".join(chunk),
                    "start_date": window_start.strftime("%Y%m%d"),
                    "end_date": window_end.strftime("%Y%m%d"),
                },
                key_fn=lambda r: (str(r.get("ts_code")), str(r.get("trade_date"))),
                max_pages=max_pages,
                mode_label=(
                    f"历史窗口模式 [{window_start}~{window_end}] "
                    f"块 {chunk_index + 1}/{total_chunks} ({len(chunk)} 只)"
                ),
            )
            for row in rows:
                ts_code = str(row.get("ts_code"))
                row_date = self._parse_tushare_date(
                    row.get("trade_date"), ts_code=ts_code
                )
                if not (window_start <= row_date <= window_end):
                    raise MarketDataIntegrityError(
                        f"历史窗口模式出现窗口外日期行: trade_date={row_date} "
                        f"不在 [{window_start}, {window_end}] (ts_code={ts_code})",
                        source=self.source_name,
                        endpoint="daily",
                    )
                if ts_code not in code_set:
                    raise MarketDataIntegrityError(
                        f"历史窗口模式出现批次外代码: ts_code={ts_code} "
                        f"(窗口 [{window_start}, {window_end}], 批次 {len(codes)} 只)",
                        source=self.source_name,
                        endpoint="daily",
                    )
                quotes.append(self._build_market_daily_quote(row))

        quotes.sort(key=lambda q: (q.trade_date, q.ts_code))
        logger.info(
            f"[Tushare] 历史窗口模式 [{window_start}~{window_end}] 批次 "
            f"{len(codes)} 只获取 {len(quotes)} 行未复权行情"
        )
        return quotes

    # margin 汇总接口七个数值字段（元/股原始口径；spec D1/D2：rqyl 不入库、
    # rzrqye 仅供排查参考，本层保真透传，聚合口径在 plan-03）
    MARGIN_DECIMAL_FIELDS = (
        "rzye",
        "rzmre",
        "rzche",
        "rqye",
        "rqmcl",
        "rqyl",
        "rzrqye",
    )

    def get_margin(self, trade_date: date) -> List[dict]:
        """获取单日融资融券交易汇总原始行（margin，spec D1，无分页）

        ``pro.margin(trade_date=YYYYMMDD)``——**不传 fields**（取 Provider
        原生 schema；16 期 suspend_d 实测教训：显式请求字段可能得到全空列）。
        单日返回全部交易所行（实测 SSE/SZSE/BSE 三行，2026-08-14 裁定全量
        入聚合；本层不强制行数），一次调用取全、**不做 offset/limit 分页**。
        整个调用包在 ``_execute_with_retry``（3 次指数退避）内。

        每行经 ``_build_margin_row`` 校验（exchange_id 非空、行日期一致、
        七数值字段 Decimal 强约束且非负）。空结果（None/空 DataFrame）返回
        空列表，由调用方（plan-03）判为当日失败。
        """
        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取融资融券交易汇总 "
                f"(margin, trade_date={trade_date})..."
            )
            return pro.margin(trade_date=trade_date.strftime("%Y%m%d"))

        rows = self._df_to_rows(self._execute_with_retry(_fetch))
        result = [self._build_margin_row(row, trade_date) for row in rows]
        logger.info(
            "[Tushare] margin %s 获取 %d 行（交易所: %s）",
            trade_date,
            len(result),
            [r["exchange_id"] for r in result],
        )
        return result

    def _build_margin_row(self, row: dict, trade_date: date) -> dict:
        """单行 margin 原始 dict → 保真行 dict（七字段 Decimal + 非负 + 日期一致）

        键名与 tushare 原生 schema 一致（蛇形）：trade_date/exchange_id/
        rzye/rzmre/rzche/rqye/rqmcl/rqyl/rzrqye。数值范围复验（七字段均
        ``>= 0``，余额/买入额/偿还额/卖出量/余量不可能为负）在本方法追加
        （``_decimal_field`` 只保证可解析与有限）。rqyl/rzrqye 不做删改：
        rqyl 不入库（spec REQ-2）、rzrqye 仅供排查参考（spec 冻结 D2：
        服务层禁止直接 sum 每行 rzrqye），两字段在本层保真透传。
        """
        raw_exchange = row.get("exchange_id")
        if raw_exchange is None or not str(raw_exchange).strip():
            raise MarketDataIntegrityError(
                f"margin 行缺少 exchange_id: {row!r}",
                source=self.source_name,
                endpoint="margin",
            )
        exchange_id = str(raw_exchange).strip()

        row_date = self._parse_tushare_date(
            row.get("trade_date"), ts_code=exchange_id, endpoint="margin"
        )
        if row_date != trade_date:
            raise MarketDataIntegrityError(
                f"margin 出现非目标日期行: 期望 trade_date={trade_date}, "
                f"实际 {row_date} (exchange_id={exchange_id})",
                source=self.source_name,
                endpoint="margin",
            )

        built: dict = {"trade_date": row_date, "exchange_id": exchange_id}
        for field in self.MARGIN_DECIMAL_FIELDS:
            value = self._decimal_field(row, field, ts_code=exchange_id)
            assert value is not None  # allow_none=False 必返回值（类型收窄）
            if value < 0:
                raise MarketDataIntegrityError(
                    f"margin 行字段 {field} 非法: {field}={value} < 0 "
                    f"(exchange_id={exchange_id}, trade_date={row_date})",
                    source=self.source_name,
                    endpoint="margin",
                )
            built[field] = value
        return built

    def _suspend_row_date(self, row: dict, ts_code: str) -> date:
        """停牌行日期归一化：兼容 suspend_date（官方 schema）/ trade_date（代理实测）列名"""
        for key in ("suspend_date", "trade_date"):
            value = row.get(key)
            if value is not None:
                return self._parse_tushare_date(
                    value, ts_code=ts_code, endpoint="suspend_d", field=key
                )
        raise MarketDataIntegrityError(
            f"停牌行缺少日期字段（suspend_date/trade_date 均为空）(ts_code={ts_code})",
            source=self.source_name,
            endpoint="suspend_d",
        )

    def get_suspensions(self, trade_date: date) -> List[SuspensionRecord]:
        """获取停牌查询原始行（suspend_d，ADR-3，原始数据保真）

        ``pro.suspend_d(suspend_date=YYYYMMDD)``——**不传 fields**，取 Provider
        原生 schema。

        **上游行为（实测）**：
        1. 代理忽略 ``suspend_date`` 查询过滤（任意日期返回同一批约 5000 行
           全量、跨约 300 个日期）；offset 分页正常；
        2. 代理把停牌日期列命名为 ``trade_date``（官方 schema 为
           ``suspend_date``）；显式请求 ``suspend_date`` 字段只会得到全空列，
           故不传 fields 并对两列名做兼容归一化。

        因此本方法忠实返回 Provider 全量行、**不做任何日期过滤**，行日期
        归一化为 ``SuspensionRecord.suspend_date``；调用方（plan-03）必须按
        ``record.suspend_date == trade_date`` 客户端过滤后才能作为当日停牌
        证据。``suspend_type`` 同样不过滤（'S' 与全天停牌判定由 plan-03 做）。
        日期解析失败抛完整性错误；空结果返回空列表。
        """
        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取停牌记录 (suspend_d, suspend_date={trade_date})..."
            )
            return pro.suspend_d(suspend_date=trade_date.strftime("%Y%m%d"))

        rows = self._df_to_rows(self._execute_with_retry(_fetch))
        records: List[SuspensionRecord] = []
        for row in rows:
            ts_code = str(row["ts_code"])
            records.append(
                SuspensionRecord(
                    ts_code=ts_code,
                    suspend_date=self._suspend_row_date(row, ts_code),
                    suspend_type=str(row["suspend_type"]),
                    suspend_timing=(
                        str(row["suspend_timing"])
                        if row.get("suspend_timing") is not None
                        else None
                    ),
                )
            )
        logger.info(
            f"[Tushare] 获取到 {len(records)} 条停牌记录 (suspend_d, "
            f"查询 suspend_date={trade_date}；原始全量行，未做日期过滤)"
        )
        return records

    def get_lifecycle_stocks(self) -> List[LifecycleStock]:
        """获取 L/D/P/G 四状态生命周期股票全集（ADR-2，不写库）

        对 ``list_status in ('L','D','P','G')`` 分别调用
        ``pro.stock_basic(exchange='', list_status=..., offset/limit 分页)`` 并
        合并返回；某状态 0 行时该状态为空集，合并继续。upsert/set-diff 与
        L/D/P 强制 list_date、D 强制 delist_date 等集合校验在 plan-03。
        """
        stocks: List[LifecycleStock] = []
        for status in self.LIFECYCLE_STATUSES:
            stocks.extend(self._fetch_lifecycle_by_status(status))
        logger.info(
            f"[Tushare] 生命周期四状态合并完成，共 {len(stocks)} 只 "
            f"(L/D/P/G={self.LIFECYCLE_STATUSES})"
        )
        return stocks

    def _fetch_lifecycle_by_status(self, list_status: str) -> List[LifecycleStock]:
        """按单个 list_status 分页拉取 stock_basic（offset/limit while 循环）"""
        pro = self._get_pro_api()
        fields = (
            "ts_code,symbol,name,area,industry,market,exchange,"
            "list_status,list_date,delist_date"
        )
        collected: List[LifecycleStock] = []
        offset = 0
        page_no = 0

        while True:
            page_no += 1
            if page_no > self.LIFECYCLE_MAX_PAGES:
                raise DataFetchError(
                    f"stock_basic(list_status={list_status}) 分页页数 {page_no} "
                    f"超过安全上限 {self.LIFECYCLE_MAX_PAGES}（疑似 offset 失效）",
                    source=self.source_name,
                    endpoint="stock_basic",
                )
            current_offset = offset

            def _fetch(_offset=current_offset):
                logger.info(
                    f"[Tushare] 正在获取生命周期股票 "
                    f"(list_status={list_status}, offset={_offset})..."
                )
                return pro.stock_basic(
                    exchange="",
                    list_status=list_status,
                    fields=fields,
                    offset=_offset,
                    limit=self.LIFECYCLE_PAGE_SIZE,
                )

            rows = self._df_to_rows(self._execute_with_retry(_fetch))
            if not rows:
                break

            for row in rows:
                ts_code = str(row["ts_code"])
                collected.append(
                    LifecycleStock(
                        ts_code=ts_code,
                        exchange=str(row.get("exchange") or ""),
                        list_status=(
                            str(row.get("list_status") or "").strip() or list_status
                        ),
                        name=(
                            str(row["name"])
                            if row.get("name") is not None
                            else None
                        ),
                        list_date=self._parse_optional_tushare_date(
                            row.get("list_date"), ts_code=ts_code, field="list_date"
                        ),
                        delist_date=self._parse_optional_tushare_date(
                            row.get("delist_date"), ts_code=ts_code, field="delist_date"
                        ),
                    )
                )

            if len(rows) < self.LIFECYCLE_PAGE_SIZE:
                break
            offset += self.LIFECYCLE_PAGE_SIZE

        return collected
