"""LimitDataInitService 单元测试

回归重点：单日/范围同步失败时必须回滚会话，避免半途 delete 滞留
事务随后续 commit 误提交（评审报告 B2）。
"""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.data_init_limit import LimitDataInitService


def _make_record(**overrides):
    record = {"ts_code": "000001.SZ", "name": "平安银行"}
    record.update(overrides)
    return record


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def mock_tushare():
    tushare = MagicMock()
    tushare.get_limit_list_d = MagicMock(return_value=[_make_record()])
    tushare.get_limit_step = MagicMock(
        return_value=[_make_record(nums=3)]
    )
    tushare.get_limit_cpt_list = MagicMock(
        return_value=[_make_record(days=2, rank=1)]
    )
    return tushare


@pytest.fixture
def service(mock_session):
    return LimitDataInitService(session=mock_session)


class TestSyncLimitData:
    async def test_success_commits_three_tables(self, service, mock_session, mock_tushare):
        with patch(
            "src.services.data_init_limit.DataSourceFactory.create",
            return_value=mock_tushare,
        ):
            result = await service.sync_limit_data("2026-07-31")

        assert result["trade_date"] == "2026-07-31"
        assert result["limit_list_d"] == 1
        assert result["limit_step"] == 1
        assert result["limit_cpt_list"] == 1
        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_awaited()

    async def test_fetch_failure_rolls_back(
        self, service, mock_session, mock_tushare
    ):
        """表 1 delete 已执行后表 2 拉取失败：必须回滚再抛出。"""
        mock_tushare.get_limit_step = MagicMock(
            side_effect=RuntimeError("tushare down")
        )

        with patch(
            "src.services.data_init_limit.DataSourceFactory.create",
            return_value=mock_tushare,
        ):
            with pytest.raises(RuntimeError, match="tushare down"):
                await service.sync_limit_data("20260731")

        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_awaited()

    async def test_cancel_propagates_without_commit(
        self, service, mock_session, mock_tushare
    ):
        service.set_cancel_check(lambda: True)

        with patch(
            "src.services.data_init_limit.DataSourceFactory.create",
            return_value=mock_tushare,
        ):
            with pytest.raises(asyncio.CancelledError):
                await service.sync_limit_data("20260731")

        mock_session.commit.assert_not_awaited()


class TestSyncLimitDataRange:
    async def test_failed_day_rolls_back_and_continues(
        self, service, mock_session
    ):
        """失败日回滚后继续下一日；两日计数正确。"""
        trading_days = [date(2026, 7, 30), date(2026, 7, 31)]
        calendar = MagicMock()
        calendar.get_trading_days_between = AsyncMock(return_value=trading_days)

        sync_calls = []

        async def fake_sync(td_str):
            sync_calls.append(td_str)
            if td_str == "2026-07-30":
                raise RuntimeError("day 1 failed")
            return {"trade_date": td_str}

        with patch(
            "src.services.data_init_limit.TradingCalendar",
            return_value=calendar,
        ):
            with patch.object(service, "sync_limit_data", side_effect=fake_sync):
                result = await service.sync_limit_data_range(
                    "2026-07-30", "2026-07-31"
                )

        assert sync_calls == ["2026-07-30", "2026-07-31"]
        assert result["total_days"] == 2
        assert result["processed_days"] == 1
        assert result["failed_days"] == 1
        # 失败日必须回滚，避免残留事务进入次日提交
        mock_session.rollback.assert_awaited_once()

    async def test_no_trading_days(self, service, mock_session):
        calendar = MagicMock()
        calendar.get_trading_days_between = AsyncMock(return_value=[])

        with patch(
            "src.services.data_init_limit.TradingCalendar",
            return_value=calendar,
        ):
            result = await service.sync_limit_data_range(
                "2026-07-30", "2026-07-31"
            )

        assert result["total_days"] == 0
        assert result["failed_days"] == 0

    async def test_invalid_range_raises(self, service):
        with pytest.raises(ValueError, match="开始日期"):
            await service.sync_limit_data_range("2026-07-31", "2026-07-30")
