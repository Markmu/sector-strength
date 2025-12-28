"""
AkShare 数据源客户端

实现与 AkShare API 的交互，提供股票和板块数据获取功能。
"""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable, List, Optional, TypeVar

import pandas as pd
from pydantic import ValidationError

from .base import BaseDataSource
from .exceptions import DataFetchError, DataSourceTimeoutError, RetryExhaustedError
from .models import DailyQuote, SectorConstituent, SectorInfo, StockInfo

# 配置日志
logger = logging.getLogger(__name__)

T = TypeVar("T")


class AkShareDataSource(BaseDataSource):
    """
    AkShare 数据源实现

    提供重试机制、超时处理、数据验证、速率限制等功能。
    """

    # 默认配置
    DEFAULT_MAX_RETRIES = 3  # 最多重试3次，平衡可靠性和响应时间
    DEFAULT_RETRY_DELAY = 1.0  # 初始重试延迟1秒
    DEFAULT_BACKOFF_FACTOR = 2.0  # 指数退避因子
    DEFAULT_TIMEOUT = 30  # 请求超时30秒
    MIN_REQUEST_INTERVAL = 0.5  # 最小请求间隔500ms（速率限制：2 req/s）

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        timeout: float = DEFAULT_TIMEOUT,
        min_request_interval: float = MIN_REQUEST_INTERVAL,
    ):
        """
        初始化 AkShare 数据源

        Args:
            max_retries: 最大重试次数（默认3次）
            retry_delay: 初始重试延迟（秒）
            backoff_factor: 退避因子（指数退避）
            timeout: 请求超时时间（秒）
            min_request_interval: 最小请求间隔（秒），用于速率限制
        """
        super().__init__("AkShare")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.min_request_interval = min_request_interval

        # 延迟导入 akshare，避免未安装时启动失败
        self._ak = None
        # 速率限制：记录上次请求时间
        self._last_request_time: Optional[datetime] = None

    def _get_akshare(self) -> Any:
        """
        延迟加载 akshare 模块

        Returns:
            akshare 模块对象

        Raises:
            ImportError: akshare 未安装
        """
        if self._ak is None:
            try:
                import akshare as ak

                self._ak = ak
                logger.info("AkShare 模块加载成功")
            except ImportError as e:
                raise ImportError(
                    "akshare 模块未安装，请运行: pip install akshare"
                ) from e
        return self._ak

    def _enforce_rate_limit(self) -> None:
        """
        强制执行速率限制

        如果距离上次请求时间小于 min_request_interval，则等待。
        这有助于避免被 AkShare API 封禁。
        """
        if self._last_request_time is not None:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self.min_request_interval:
                sleep_time = self.min_request_interval - elapsed
                logger.debug(f"速率限制：等待 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)

    def _execute_with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """
        执行函数并在失败时重试（指数退避）

        Args:
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果

        Raises:
            RetryExhaustedError: 重试次数耗尽
            DataSourceTimeoutError: 请求超时
        """
        last_exception = None
        current_delay = self.retry_delay

        for attempt in range(1, self.max_retries + 1):
            try:
                # 应用速率限制
                self._enforce_rate_limit()

                # 执行函数
                result = func(*args, **kwargs)

                # 更新最后请求时间
                self._last_request_time = datetime.now()

                return result

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"第 {attempt}/{self.max_retries} 次尝试失败: {e}",
                    extra={
                        "source": self.source_name,
                        "attempt": attempt,
                        "max_retries": self.max_retries,
                        "error_type": type(e).__name__,
                    },
                )

                # 最后一次尝试失败，抛出异常
                if attempt >= self.max_retries:
                    break

                # 指数退避
                time.sleep(current_delay)
                current_delay *= self.backoff_factor

        # 所有重试都失败
        raise RetryExhaustedError(
            f"重试 {self.max_retries} 次后仍然失败",
            source=self.source_name,
            attempts=self.max_retries,
            original_error=last_exception,
        )

    def _safe_parse_date(self, date_value: Any) -> Optional[date]:
        """
        安全解析日期值

        支持多种日期格式：字符串、datetime、date、Excel 日期序列号等。

        Args:
            date_value: 日期值（可能是字符串、datetime、date 等）

        Returns:
            解析后的 date 对象，失败返回 None
        """
        if pd.isna(date_value):
            return None

        if isinstance(date_value, date):
            return date_value

        if isinstance(date_value, str):
            try:
                # 尝试多种日期格式
                for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
                    try:
                        return datetime.strptime(date_value, fmt).date()
                    except ValueError:
                        continue
            except Exception:
                pass

        if isinstance(date_value, (int, float)):
            try:
                # 处理 Excel 日期序列号
                return (datetime(1899, 12, 30) + pd.Timedelta(days=date_value)).date()
            except Exception:
                pass

        logger.warning(
            f"无法解析日期: {date_value} (类型: {type(date_value).__name__})",
            extra={"date_value": str(date_value), "type": type(date_value).__name__},
        )
        return None

    def get_stock_list(self) -> List[StockInfo]:
        """
        获取 A 股股票列表

        通过 AkShare 获取所有 A 股（包括上交所、深交所、北交所）的实时行情数据。

        Returns:
            股票信息列表，包含股票代码、名称、市场类型、所属行业等

        Raises:
            DataFetchError: 数据获取失败
            RetryExhaustedError: 重试次数耗尽
        """
        ak = self._get_akshare()

        def _fetch() -> pd.DataFrame:
            logger.info("正在获取 A 股股票列表...")
            df = ak.stock_zh_a_spot_em()
            logger.info(f"获取到 {len(df)} 只股票的实时行情数据")
            return df

        try:
            df = self._execute_with_retry(_fetch)

            # 数据转换和清洗
            stocks: List[StockInfo] = []
            errors = 0

            for _, row in df.iterrows():
                try:
                    # AkShare 返回的列名可能是中文，需要处理
                    symbol = str(row.get("代码", ""))
                    name = str(row.get("名称", ""))

                    if not symbol or not name:
                        continue

                    # 确定市场类型
                    market = None
                    if symbol.startswith("6"):
                        market = "SH"  # 上海证券交易所
                    elif symbol.startswith(("0", "3")):
                        market = "SZ"  # 深圳证券交易所
                    elif symbol.startswith("8") or symbol.startswith("4"):
                        market = "BJ"  # 北京证券交易所

                    # 获取行业信息
                    industry = None
                    if "行业" in row.index:
                        industry_val = row.get("行业")
                        if pd.notna(industry_val):
                            industry = str(industry_val)

                    stock_info = StockInfo(
                        symbol=symbol,
                        name=name,
                        market=market,
                        industry=industry,
                    )
                    stocks.append(stock_info)

                except (ValidationError, ValueError) as e:
                    errors += 1
                    logger.debug(
                        f"股票数据验证失败 {row.get('代码', '')}: {e}",
                        extra={"symbol": row.get("代码", ""), "error": str(e)},
                    )

            logger.info(
                f"成功转换 {len(stocks)} 只股票，忽略 {errors} 条异常数据",
                extra={"success_count": len(stocks), "error_count": errors},
            )
            return stocks

        except RetryExhaustedError:
            raise
        except Exception as e:
            raise DataFetchError(
                f"获取股票列表失败: {str(e)}",
                source=self.source_name,
                endpoint="stock_zh_a_spot_em",
                original_error=e,
            )

    def get_sector_list(self, sector_type: Optional[str] = None) -> List[SectorInfo]:
        """
        获取板块列表

        Args:
            sector_type: 板块类型过滤 (industry/concept)，None 表示获取所有

        Returns:
            板块信息列表

        Raises:
            DataFetchError: 数据获取失败
            RetryExhaustedError: 重试次数耗尽
        """
        ak = self._get_akshare()
        sectors: List[SectorInfo] = []

        def _fetch_industry() -> pd.DataFrame:
            logger.info("正在获取行业板块列表...")
            return ak.stock_board_industry_name_em()

        def _fetch_concept() -> pd.DataFrame:
            logger.info("正在获取概念板块列表...")
            return ak.stock_board_concept_name_em()

        try:
            # 根据类型决定获取哪些板块
            fetch_industry = sector_type is None or sector_type == "industry"
            fetch_concept = sector_type is None or sector_type == "concept"

            if fetch_industry:
                df_industry = self._execute_with_retry(_fetch_industry)
                for _, row in df_industry.iterrows():
                    try:
                        sectors.append(
                            SectorInfo(
                                code=str(row.get("板块代码", "")),
                                name=str(row.get("板块名称", "")),
                                type="industry",
                            )
                        )
                    except (ValidationError, ValueError) as e:
                        logger.debug(
                            f"行业板块数据验证失败: {e}",
                            extra={"sector": row.get("板块名称", ""), "error": str(e)},
                        )

            if fetch_concept:
                df_concept = self._execute_with_retry(_fetch_concept)
                for _, row in df_concept.iterrows():
                    try:
                        sectors.append(
                            SectorInfo(
                                code=str(row.get("板块代码", "")),
                                name=str(row.get("板块名称", "")),
                                type="concept",
                            )
                        )
                    except (ValidationError, ValueError) as e:
                        logger.debug(
                            f"概念板块数据验证失败: {e}",
                            extra={"sector": row.get("板块名称", ""), "error": str(e)},
                        )

            logger.info(f"获取到 {len(sectors)} 个板块", extra={"sector_count": len(sectors)})
            return sectors

        except RetryExhaustedError:
            raise
        except Exception as e:
            raise DataFetchError(
                f"获取板块列表失败: {str(e)}",
                source=self.source_name,
                endpoint="stock_board_*_name_em",
                original_error=e,
            )

    def get_daily_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyQuote]:
        """
        获取日线行情数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            日线行情数据列表

        Raises:
            DataFetchError: 数据获取失败
            RetryExhaustedError: 重试次数耗尽
            ValueError: 参数校验失败（空代码或无效日期范围）
        """
        if not symbol:
            raise ValueError("股票代码不能为空")

        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        ak = self._get_akshare()

        def _fetch() -> pd.DataFrame:
            logger.info(
                f"正在获取 {symbol} 的日线数据 ({start_date} 至 {end_date})...",
                extra={"symbol": symbol, "start_date": str(start_date), "end_date": str(end_date)},
            )
            return ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="qfq",  # 前复权
            )

        try:
            df = self._execute_with_retry(_fetch)

            if df.empty:
                logger.warning(
                    f"股票 {symbol} 在指定日期范围内无数据",
                    extra={"symbol": symbol, "start_date": str(start_date), "end_date": str(end_date)},
                )
                return []

            quotes: List[DailyQuote] = []
            errors = 0

            for _, row in df.iterrows():
                try:
                    # AkShare 返回的列名映射
                    trade_date = self._safe_parse_date(row.get("日期"))
                    if trade_date is None:
                        continue

                    # 清洗价格数据（处理 NaN 和异常值）
                    def safe_float(val: Any, default: float = 0.0) -> float:
                        """安全转换为浮点数，处理 NaN 和异常值"""
                        if pd.isna(val):
                            raise ValueError("价格数据为空")
                        return float(val)

                    quote = DailyQuote(
                        symbol=symbol,
                        trade_date=trade_date,
                        open=safe_float(row.get("开盘")),
                        high=safe_float(row.get("最高")),
                        low=safe_float(row.get("最低")),
                        close=safe_float(row.get("收盘")),
                        volume=safe_float(row.get("成交量")),
                        amount=safe_float(row.get("成交额"))
                        if "成交额" in row.index and pd.notna(row.get("成交额"))
                        else None,
                        turnover=safe_float(row.get("换手率"))
                        if "换手率" in row.index and pd.notna(row.get("换手率"))
                        else None,
                    )
                    quotes.append(quote)

                except (ValidationError, ValueError) as e:
                    errors += 1
                    logger.debug(
                        f"日线数据验证失败 {symbol} {row.get('日期')}: {e}",
                        extra={
                            "symbol": symbol,
                            "date": str(row.get("日期", "")),
                            "error": str(e),
                        },
                    )

            logger.info(
                f"成功转换 {len(quotes)} 条日线数据，忽略 {errors} 条异常数据",
                extra={"symbol": symbol, "success_count": len(quotes), "error_count": errors},
            )
            return quotes

        except RetryExhaustedError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise DataFetchError(
                f"获取 {symbol} 日线数据失败: {str(e)}",
                source=self.source_name,
                endpoint="stock_zh_a_hist",
                original_error=e,
            )

    def get_sector_daily_data(
        self,
        sector_code: str,
        start_date: date,
        end_date: date,
    ) -> List[DailyQuote]:
        """
        获取板块日线行情数据

        使用 AkShare 的 stock_board_industry_hist_em 接口直接获取板块历史数据。

        Args:
            sector_code: 板块代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            日线行情数据列表

        Raises:
            DataFetchError: 数据获取失败
            RetryExhaustedError: 重试次数耗尽
            ValueError: 参数校验失败（空代码或无效日期范围）
        """
        if not sector_code:
            raise ValueError("板块代码不能为空")

        if start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")

        ak = self._get_akshare()

        def _fetch() -> pd.DataFrame:
            logger.info(
                f"正在获取板块 {sector_code} 的历史数据 ({start_date} 至 {end_date})...",
                extra={"sector_code": sector_code, "start_date": str(start_date), "end_date": str(end_date)},
            )
            # 使用 AkShare 的板块历史数据接口
            return ak.stock_board_industry_hist_em(
                symbol=sector_code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )

        try:
            df = self._execute_with_retry(_fetch)

            if df.empty:
                logger.warning(
                    f"板块 {sector_code} 在指定日期范围内无数据",
                    extra={"sector_code": sector_code, "start_date": str(start_date), "end_date": str(end_date)},
                )
                return []

            quotes: List[DailyQuote] = []
            errors = 0

            for _, row in df.iterrows():
                try:
                    # 解析日期
                    trade_date = self._safe_parse_date(row.get("日期"))
                    if trade_date is None:
                        continue

                    # 清洗价格数据
                    def safe_float(val: Any, default: float = 0.0) -> float:
                        """安全转换为浮点数，处理 NaN 和异常值"""
                        if pd.isna(val):
                            raise ValueError("价格数据为空")
                        return float(val)

                    quote = DailyQuote(
                        symbol=sector_code,
                        trade_date=trade_date,
                        open=safe_float(row.get("开盘")),
                        high=safe_float(row.get("最高")),
                        low=safe_float(row.get("最低")),
                        close=safe_float(row.get("收盘")),
                        volume=safe_float(row.get("成交量")),
                        amount=safe_float(row.get("成交额"))
                        if "成交额" in row.index and pd.notna(row.get("成交额"))
                        else None,
                        turnover=safe_float(row.get("换手率"))
                        if "换手率" in row.index and pd.notna(row.get("换手率"))
                        else None,
                    )
                    quotes.append(quote)

                except (ValidationError, ValueError) as e:
                    errors += 1
                    logger.debug(
                        f"板块日线数据验证失败 {sector_code} {row.get('日期')}: {e}",
                        extra={
                            "sector_code": sector_code,
                            "date": str(row.get("日期", "")),
                            "error": str(e),
                        },
                    )

            logger.info(
                f"成功转换 {len(quotes)} 条板块日线数据，忽略 {errors} 条异常数据",
                extra={"sector_code": sector_code, "success_count": len(quotes), "error_count": errors},
            )
            return quotes

        except RetryExhaustedError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise DataFetchError(
                f"获取板块 {sector_code} 日线数据失败: {str(e)}",
                source=self.source_name,
                endpoint="stock_board_industry_hist_em",
                original_error=e,
            )

    def get_sector_stocks(self, sector_code: str) -> List[SectorConstituent]:
        """
        获取板块成分股

        Args:
            sector_code: 板块代码

        Returns:
            板块成分股列表

        Raises:
            DataFetchError: 数据获取失败
            RetryExhaustedError: 重试次数耗尽
            ValueError: 板块代码为空
        """
        if not sector_code:
            raise ValueError("板块代码不能为空")

        ak = self._get_akshare()

        def _fetch() -> pd.DataFrame:
            logger.info(
                f"正在获取板块 {sector_code} 的成分股...",
                extra={"sector_code": sector_code},
            )
            return ak.stock_board_concept_cons_em(symbol=sector_code)

        try:
            df = self._execute_with_retry(_fetch)

            if df.empty:
                logger.warning(
                    f"板块 {sector_code} 无成分股数据",
                    extra={"sector_code": sector_code},
                )
                return []

            constituents: List[SectorConstituent] = []
            errors = 0

            for _, row in df.iterrows():
                try:
                    symbol = str(row.get("代码", ""))
                    name = str(row.get("名称", ""))

                    if not symbol or not name:
                        continue

                    constituent = SectorConstituent(
                        sector_code=sector_code,
                        symbol=symbol,
                        name=name,
                    )
                    constituents.append(constituent)

                except (ValidationError, ValueError) as e:
                    errors += 1
                    logger.debug(
                        f"成分股数据验证失败: {e}",
                        extra={"sector_code": sector_code, "symbol": row.get("代码", ""), "error": str(e)},
                    )

            logger.info(
                f"成功转换 {len(constituents)} 只成分股，忽略 {errors} 条异常数据",
                extra={"sector_code": sector_code, "success_count": len(constituents), "error_count": errors},
            )
            return constituents

        except RetryExhaustedError:
            raise
        except ValueError:
            raise
        except Exception as e:
            raise DataFetchError(
                f"获取板块 {sector_code} 成分股失败: {str(e)}",
                source=self.source_name,
                endpoint="stock_board_concept_cons_em",
                original_error=e,
            )
