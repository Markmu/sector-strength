import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from src.services.data_acquisition.akshare_client import AkShareDataSource
from src.services.data_acquisition.exceptions import DataFetchError, RetryExhaustedError

logger = logging.getLogger(__name__)


class TradingCalendar:
    def __init__(self):
        self._cache: Optional[List[date]] = None
        self._cache_date: Optional[date] = None

    def _is_cache_valid(self) -> bool:
        today = datetime.now().date()
        return self._cache is not None and self._cache_date == today

    async def _get_trading_days(self) -> List[date]:
        if self._is_cache_valid():
            return self._cache

        source = AkShareDataSource()
        trading_days = source.get_trading_calendar()

        self._cache = trading_days
        self._cache_date = datetime.now().date()
        return trading_days

    async def is_trading_day(self, check_date: Optional[date] = None) -> Tuple[bool, Optional[str]]:
        """判断是否为交易日，返回 (是否交易日, 跳过原因)"""
        target = check_date or datetime.now().date()

        try:
            trading_days = await self._get_trading_days()
            if target in trading_days:
                return (True, None)

            if target.weekday() >= 5:
                return (False, "周末")
            return (False, "节假日")

        except (DataFetchError, RetryExhaustedError) as e:
            logger.warning(f"交易日历获取失败，降级为周末判断: {e}")
            if target.weekday() >= 5:
                return (False, "周末")
            return (True, None)

    async def get_trading_days_between(self, start: date, end: date) -> List[date]:
        """获取两个日期之间的交易日列表"""
        trading_days = await self._get_trading_days()
        return [d for d in trading_days if start <= d <= end]
