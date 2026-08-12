"""关键指数数据同步服务回归测试。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.data_init_index import IndexDataInitService


def _scalar_result(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


@pytest.mark.asyncio
async def test_get_watched_codes_keeps_complete_ts_codes():
    """scalars() 返回的是字符串标量，不能再次用 row[0] 截断。"""
    session = AsyncMock()
    session.execute.return_value = _scalar_result(
        ["000016.SH", "399300.SZ", "932000.CSI"]
    )
    service = IndexDataInitService(session)

    codes = await service._get_watched_codes()

    assert codes == ["000016.SH", "399300.SZ", "932000.CSI"]


@pytest.mark.asyncio
async def test_get_watched_codes_rejects_invalid_codes():
    session = AsyncMock()
    session.execute.return_value = _scalar_result(["000016.SH", "0"])
    service = IndexDataInitService(session)

    with pytest.raises(ValueError, match="无效指数代码: 0"):
        await service._get_watched_codes()


def test_data_source_is_reused_within_one_service():
    session = AsyncMock()
    data_source = MagicMock()
    service = IndexDataInitService(session)

    with patch(
        "src.services.data_init_index.DataSourceFactory.create",
        return_value=data_source,
    ) as create:
        assert service._get_data_source() is data_source
        assert service._get_data_source() is data_source

    create.assert_called_once_with()


@pytest.mark.asyncio
async def test_backfill_fails_when_all_daily_results_are_empty():
    """有交易日但行情全为空时必须失败，不能产生 completed 假成功。"""
    session = AsyncMock()
    service = IndexDataInitService(session)
    service._get_watched_codes = AsyncMock(return_value=["000016.SH"])
    service._fetch_and_upsert_index_daily = AsyncMock(return_value=0)
    service._fetch_and_upsert_index_dailybasic = AsyncMock(return_value=0)
    service._fetch_and_upsert_index_weight = AsyncMock(return_value=0)

    with patch(
        "src.services.data_init_index.TradingCalendar.get_trading_days_between",
        new=AsyncMock(return_value=[date(2026, 8, 11)]),
    ):
        with pytest.raises(RuntimeError, match="index_daily 写入 0 条"):
            await service.backfill_index_history("2026-08-11", "2026-08-11")


@pytest.mark.asyncio
async def test_backfill_passes_complete_codes_to_fetchers():
    session = AsyncMock()
    service = IndexDataInitService(session)
    service._get_watched_codes = AsyncMock(
        return_value=["000016.SH", "399300.SZ"]
    )
    service._fetch_and_upsert_index_daily = AsyncMock(return_value=1)
    service._fetch_and_upsert_index_dailybasic = AsyncMock(return_value=0)
    service._fetch_and_upsert_index_weight = AsyncMock(return_value=0)
    trade_date = date(2026, 8, 11)

    with patch(
        "src.services.data_init_index.TradingCalendar.get_trading_days_between",
        new=AsyncMock(return_value=[trade_date]),
    ):
        result = await service.backfill_index_history(
            "2026-08-11", "2026-08-11"
        )

    assert result["daily_records"] == 2
    assert [call.args[0] for call in service._fetch_and_upsert_index_daily.call_args_list] == [
        "000016.SH",
        "399300.SZ",
    ]


@pytest.mark.asyncio
async def test_daily_sync_skips_non_trading_day():
    session = AsyncMock()
    service = IndexDataInitService(session)

    with patch(
        "src.services.data_init_index.TradingCalendar.is_trading_day",
        new=AsyncMock(return_value=(False, "周末")),
    ):
        result = await service.sync_index_daily("2026-08-09")

    assert result["skipped"] is True
    assert result["skip_reason"] == "周末"
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_daily_sync_rolls_back_when_trading_day_has_no_daily_data():
    session = AsyncMock()
    service = IndexDataInitService(session)
    service._get_watched_codes = AsyncMock(return_value=["000016.SH"])
    service._has_weight_for_month = AsyncMock(return_value=False)
    service._fetch_and_upsert_index_daily = AsyncMock(return_value=0)
    service._fetch_and_upsert_index_dailybasic = AsyncMock(return_value=0)
    service._fetch_and_upsert_index_weight = AsyncMock(return_value=0)

    with patch(
        "src.services.data_init_index.TradingCalendar.is_trading_day",
        new=AsyncMock(return_value=(True, None)),
    ):
        with pytest.raises(RuntimeError, match="index_daily 写入 0 条"):
            await service.sync_index_daily("2026-08-11")

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
