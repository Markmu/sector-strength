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

        import pandas as pd

        for _, row in df.iterrows():
            try:
                ts_code = str(row["ts_code"])
                symbol = ts_code.split(".")[0]
                name = str(row["name"])
                # 直接使用 Tushare 返回的 exchange 字段
                exchange = str(row.get("exchange", "")) or None if pd.notna(row.get("exchange")) else None

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

        import pandas as pd

        for _, row in df.iterrows():
            try:
                ts_code = str(row["ts_code"])
                symbol = ts_code.split(".")[0]
                name = str(row["name"])

                fullname = str(row.get("fullname", "")) or None if pd.notna(row.get("fullname")) else None
                enname = str(row.get("enname", "")) or None if pd.notna(row.get("enname")) else None
                cnspell = str(row.get("cn_spell", "")) or None if pd.notna(row.get("cn_spell")) else None
                market = str(row.get("market", "")) or None if pd.notna(row.get("market")) else None
                curr_type = str(row.get("curr_type", "")) or None if pd.notna(row.get("curr_type")) else None
                list_status = str(row.get("list_status", "")) or None if pd.notna(row.get("list_status")) else None

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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
        import pandas as pd

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

    def get_fund_share(self, trade_date: str) -> List[dict]:
        """
        获取基金份额数据（按 trade_date 全量，客户端筛 fund_type=='ETF'）

        Args:
            trade_date: 交易日，格式 'YYYYMMDD'（如 '20260728'）

        Returns:
            原始字典列表，保留 Tushare 键名
            (ts_code/trade_date/fd_share/fund_type/market)
            fd_share 单位为万份。

        说明：实测按 trade_date 全量返回约 728 条（含 fund_type 列），
        筛 fund_type='ETF' 后单批即够，无需 offset 分页。
        """
        import pandas as pd

        pro = self._get_pro_api()

        def _fetch():
            logger.info(
                f"[Tushare] 正在获取基金份额 (trade_date={trade_date})..."
            )
            return pro.fund_share(trade_date=trade_date)

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(f"[Tushare] fund_share 返回空数据 (trade_date={trade_date})")
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

        # 客户端按 fund_type=='ETF' 筛选
        etf_records = [
            r for r in records if str(r.get("fund_type", "")).strip() == "ETF"
        ]
        logger.info(
            f"[Tushare] 获取到 {len(records)} 条基金份额，筛 fund_type=ETF 后 {len(etf_records)} 条"
        )
        return etf_records

    def get_fund_nav(self, ts_code: str) -> List[dict]:
        """
        获取基金净值历史（按 ts_code）

        fund_nav 接口按 ts_code 返回该基金的历史净值（不支持批量 trade_date），
        上层 sync_etf_daily 需对每只 ETF 逐只调用，配 TUSHARE_API_INTERVAL 限流。

        Args:
            ts_code: 基金代码，如 '510300.SH'

        Returns:
            原始字典列表，保留 Tushare 键名
            (ts_code/nav_date/unit_nav/accum_nav/accum_div/unit_accum_nav ...)
        """
        import pandas as pd

        pro = self._get_pro_api()

        def _fetch():
            logger.info(f"[Tushare] 正在获取基金净值 (ts_code={ts_code})...")
            return pro.fund_nav(ts_code=ts_code)

        df = self._execute_with_retry(_fetch)
        if df is None or (hasattr(df, "empty") and df.empty):
            logger.warning(f"[Tushare] fund_nav 返回空数据 (ts_code={ts_code})")
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

    async def get_top10_float_holders(
        self, ts_code: str, period: str
    ) -> List[dict]:
        """
        获取单只股票的前十大流通股东数据

        Args:
            ts_code: Tushare 股票代码，如 "600000.SH"
            period: 报告期，YYYYMMDD 格式，如 "20241231"

        Returns:
            dict 列表，每条包含: ts_code, ann_date, end_date, holder_name,
            hold_amount, hold_ratio, hold_float_ratio, hold_change, holder_type
        """
        import pandas as pd

        pro = self._get_pro_api()

        def _fetch():
            return pro.top10_floatholders(
                ts_code=ts_code,
                period=period,
            )

        df = self._execute_with_retry(_fetch)
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
        无需 trade_cal 映射。

        Args:
            month: 月份，YYYYMM 格式，如 "202606"

        Returns:
            dict 列表，每条包含: ts_code, trade_date, name, broker, reason
        """
        import pandas as pd

        pro = self._get_pro_api()

        def _fetch():
            logger.info(f"[Tushare] 正在获取券商金股数据 (month={month})...")
            return pro.broker_recommend(month=month)

        df = self._execute_with_retry(_fetch)
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
