"""
交易日历服务测试

测试 TradingCalendar 和 .get_trading_calendar()。
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
import pandas as pd

from src.services.trading_calendar import TradingCalendar
from src.services.data_acquisition.exceptions import DataFetchError, RetryExhaustedError


@pytest.fixture
def trading_calendar():
    """创建 TradingCalendar 实例"""
    return TradingCalendar()


@pytest.fixture
def sample_trading_dates():
    """样本交易日列表（2024-01-02 ~ 2024-01-05 为交易日，01-01 元旦非交易日）"""
    return [
        date(2023, 12, 29),
        date(2024, 1, 2),
        date(2024, 1, 3),
        date(2024, 1, 4),
        date(2024, 1, 5),
        date(2024, 1, 8),
    ]


class TestTradingCalendar:
    """交易日历服务测试"""

    @pytest.mark.asyncio
    async def test_is_trading_day_weekday(self, trading_calendar, sample_trading_dates):
        """测试交易日判断 - 普通工作日"""
        with patch.object(trading_calendar, '_get_trading_days', return_value=sample_trading_dates):
            is_trading, reason = await trading_calendar.is_trading_day(date(2024, 1, 2))
            assert is_trading is True
            assert reason is None

    @pytest.mark.asyncio
    async def test_is_trading_day_weekend(self, trading_calendar, sample_trading_dates):
        """测试交易日判断 - 周末"""
        with patch.object(trading_calendar, '_get_trading_days', return_value=sample_trading_dates):
            is_trading, reason = await trading_calendar.is_trading_day(date(2024, 1, 6))
            assert is_trading is False
            assert reason == "周末"

    @pytest.mark.asyncio
    async def test_is_trading_day_holiday(self, trading_calendar, sample_trading_dates):
        """测试交易日判断 - 法定节假日"""
        with patch.object(trading_calendar, '_get_trading_days', return_value=sample_trading_dates):
            is_trading, reason = await trading_calendar.is_trading_day(date(2024, 1, 1))
            assert is_trading is False
            assert reason == "节假日"

    @pytest.mark.asyncio
    async def test_is_trading_day_makeup_workday(self, trading_calendar):
        """测试交易日判断 - 调休工作日（周末补班）"""
        # 2024-04-07（周日）为五一调休工作日，应在交易日历中
        trading_days = [date(2024, 4, 1), date(2024, 4, 2), date(2024, 4, 3),
                        date(2024, 4, 7)]
        with patch.object(trading_calendar, '_get_trading_days', return_value=trading_days):
            is_trading, reason = await trading_calendar.is_trading_day(date(2024, 4, 7))
            assert is_trading is True
            assert reason is None

    @pytest.mark.asyncio
    async def test_is_trading_day_fallback_on_error(self, trading_calendar):
        """测试交易日判断 - 数据源不可用时降级为周末判断"""
        with patch.object(trading_calendar, '_get_trading_days', side_effect=DataFetchError("timeout", source="Tushare", endpoint="test")):
            # 降级：工作日视为交易日
            is_trading, reason = await trading_calendar.is_trading_day(date(2024, 1, 10))
            assert is_trading is True
            assert reason is None

            # 降级：周末仍为非交易日
            is_trading, reason = await trading_calendar.is_trading_day(date(2024, 1, 13))
            assert is_trading is False
            assert reason == "周末"

    @pytest.mark.asyncio
    async def test_is_trading_day_default_today(self, trading_calendar, sample_trading_dates):
        """测试交易日判断 - 默认使用今天"""
        with patch.object(trading_calendar, '_get_trading_days', return_value=sample_trading_dates):
            # 测试传入 None 使用默认日期
            is_trading, reason = await trading_calendar.is_trading_day()
            assert isinstance(is_trading, bool)

    @pytest.mark.asyncio
    async def test_get_trading_days_between(self, trading_calendar, sample_trading_dates):
        """测试获取指定范围内的交易日列表"""
        with patch.object(trading_calendar, '_get_trading_days', return_value=sample_trading_dates):
            result = await trading_calendar.get_trading_days_between(
                date(2024, 1, 2), date(2024, 1, 5)
            )
            assert result == [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)]

    @pytest.mark.asyncio
    async def test_get_trading_days_between_empty(self, trading_calendar, sample_trading_dates):
        """测试获取指定范围内无交易日"""
        with patch.object(trading_calendar, '_get_trading_days', return_value=sample_trading_dates):
            result = await trading_calendar.get_trading_days_between(
                date(2024, 2, 1), date(2024, 2, 10)
            )
            assert result == []

    @pytest.mark.asyncio
    async def test_cache_reuse_within_same_day(self, trading_calendar, sample_trading_dates):
        """测试同日内存缓存 - 多次调用不重复请求"""
        with patch('src.services.trading_calendar.DataSourceFactory') as mock_factory:
            mock_source = MagicMock()
            mock_source.get_trading_calendar.return_value = sample_trading_dates
            mock_factory.create.return_value = mock_source

            # 第一次调用：获取数据并缓存
            await trading_calendar.is_trading_day(date(2024, 1, 2))
            assert mock_source.get_trading_calendar.call_count == 1

            # 第二次调用：应使用缓存，不重新获取
            await trading_calendar.is_trading_day(date(2024, 1, 3))
            assert mock_source.get_trading_calendar.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_new_day(self, trading_calendar, sample_trading_dates):
        """测试缓存跨日失效"""
        trading_calendar._cache = sample_trading_dates
        trading_calendar._cache_date = date(2024, 1, 1)

        with patch.object(trading_calendar, '_get_trading_days', return_value=sample_trading_dates) as mock_get:
            await trading_calendar.is_trading_day(date(2024, 1, 2))
            # 缓存日期不匹配今天，应重新获取
            assert mock_get.call_count == 1
