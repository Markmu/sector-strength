"""MarketMetricsService 单元/集成测试（第 16 期 plan-03）

覆盖 plan-03 §5 验收标准：

- AC-01（单日正确性）：完整数据日落库一行，量/额/平均价可由原始行复算
  （手×100、千元×1000、Σclose/数）；任一非法/不平衡/越界/重复 → 不落库。
- AC-03（重复同步安全覆盖）：同日重复 sync_date → 一行、值覆盖。
- AC-09（非交易日守卫）：本地日历休市 → skipped 且零 Provider 调用；无记录 → 抛错。
- AC-13（全天停牌参与计算）：量额为 0、close=最近有效收盘；suspended 计入 final；
  停牌信息/前收盘缺失或无法判定 → 整日失败。
- 盘中临停（daily 有行）优先用 daily 行，不进补价集合。
- 补价窗口扫描遵守 100/批、≤250 窗、总预算常量；预算耗尽仍有未决 → 整日失败。
- G 固定排除；L/D/P 缺 list_date、D 缺 delist_date → 抛错。
- Decimal 全程：构造 float 精度陷阱用例断言无累计误差。

测试使用真实 PostgreSQL（conftest 拒绝 SQLite），DataSourceFactory 通过 patch 注入
确定性 fake 数据源；LifecycleSnapshot 直接构造以隔离 init 流程。
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from src.models.market_daily_metric import MarketDailyMetric
from src.services.data_acquisition.models import (
    LifecycleStock,
    MarketDailyQuote,
    SuspensionRecord,
    TradingCalendarEntry,
)
from src.services.market_metrics_service import (
    CLOSE_LOOKBACK_MAX_CODES_PER_BATCH,
    MAX_CLOSE_LOOKBACK_REQUESTS,
    LifecycleSnapshot,
    MarketMetricsService,
    MarketMetricsSyncError,
    build_lifecycle_snapshot,
)
from src.services import market_metrics_service as mms_module
from src.services.trading_calendar_repository import TradingCalendarRepository


T = date(2026, 3, 16)  # 目标交易日（周一）


# ---------------------------------------------------------------------------
# 测试替身：确定性 fake 数据源
# ---------------------------------------------------------------------------


class FakeMarketDataSource:
    """返回预设的行情/停牌/前收盘，可记录调用次数。"""

    def __init__(
        self,
        daily_quotes=None,
        suspensions=None,
        close_window_quotes=None,
        daily_exc=None,
    ):
        self._daily = list(daily_quotes or [])
        self._suspensions = list(suspensions or [])
        self._close_window = list(close_window_quotes or [])
        self._daily_exc = daily_exc
        self.get_market_daily_quotes_call_count = 0
        self.get_suspensions_call_count = 0
        self.get_close_quotes_in_window_calls = []
        self.get_close_quotes_in_window_arg_lists = []

    def get_market_daily_quotes(self, trade_date, expected_count):
        self.get_market_daily_quotes_call_count += 1
        if self._daily_exc is not None:
            raise self._daily_exc
        return list(self._daily)

    def get_suspensions(self, trade_date):
        self.get_suspensions_call_count += 1
        return list(self._suspensions)

    def get_close_quotes_in_window(self, ts_codes, window_start, window_end):
        self.get_close_quotes_in_window_calls.append((window_start, window_end))
        self.get_close_quotes_in_window_arg_lists.append(list(ts_codes))
        # 仅返回属于本次请求代码集合的行
        requested = set(ts_codes)
        return [q for q in self._close_window if q.ts_code in requested]


class _FakeCalendarSource:
    """仅服务日历刷新的 fake（返回闭区间全量自然日）。"""

    def __init__(self, entries):
        self._entries = list(entries)

    def get_trading_calendar_range(self, start_date, end_date):
        return list(self._entries)


def _patch_market_factory(fake):
    return patch(
        "src.services.market_metrics_service.DataSourceFactory.create",
        return_value=fake,
    )


async def _seed_calendar(db_session, start, end, closed_days=None):
    """用真实 refresh_range 写入本地日历（patch 日历的 DataSourceFactory）。"""
    closed_days = set(closed_days or [])
    entries = []
    d = start
    while d <= end:
        entries.append(TradingCalendarEntry(cal_date=d, is_open=d not in closed_days))
        d += timedelta(days=1)
    with patch(
        "src.services.trading_calendar_repository.DataSourceFactory.create",
        return_value=_FakeCalendarSource(entries),
    ):
        repo = TradingCalendarRepository(db_session)
        await repo.refresh_range(start, end)


def _quote(ts_code, close, vol, amount, trade_date=T, pre_close=None):
    return MarketDailyQuote(
        ts_code=ts_code,
        trade_date=trade_date,
        close=Decimal(str(close)),
        pre_close=Decimal(str(pre_close)) if pre_close is not None else None,
        vol=Decimal(str(vol)),
        amount=Decimal(str(amount)),
    )


def _snapshot(records, status_flags=None):
    flags = status_flags if status_flags is not None else {
        "L": True, "D": True, "P": True, "G": True
    }
    return LifecycleSnapshot(records=tuple(records), status_flags=flags)


# 三只正常交易 L 股（沪深北各一），均早于 T 上市
BASE_L_RECORDS = [
    LifecycleStock(
        ts_code="000001.SZ", exchange="SZSE", list_status="L",
        name="平安", list_date=date(2020, 1, 1), delist_date=None,
    ),
    LifecycleStock(
        ts_code="600000.SH", exchange="SSE", list_status="L",
        name="浦发", list_date=date(2019, 1, 1), delist_date=None,
    ),
    LifecycleStock(
        ts_code="830001.BJ", exchange="BSE", list_status="L",
        name="华邦", list_date=date(2020, 1, 1), delist_date=None,
    ),
]
BASE_DAILY = [
    _quote("000001.SZ", "10.5", "100", "50"),
    _quote("600000.SH", "20.0", "200", "100"),
    _quote("830001.BJ", "5.0", "300", "30"),
]


# ---------------------------------------------------------------------------
# AC-01：完整数据日正确性
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_date_complete_day_recomputable(db_session):
    """AC-01：完整日落库一行，量/额/平均价可由原始行复算。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)
    fake = FakeMarketDataSource(daily_quotes=BASE_DAILY)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        result = await service.sync_date(T, snapshot)

    assert result == "success"
    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.trade_date == T
    # 复算：vol×100 / amount×1000 / Σclose/final(4 位)
    assert row.volume_shares == Decimal((100 + 200 + 300) * 100)
    assert row.amount_yuan == Decimal((50 + 100 + 30) * 1000)
    assert row.average_price == (Decimal("35.5") / Decimal(3)).quantize(
        Decimal("0.0001")
    )
    assert row.expected_stock_count == 3
    assert row.daily_quote_count == 3
    assert row.suspended_stock_count == 0
    assert row.final_stock_count == 3


@pytest.mark.asyncio
async def test_sync_date_zero_provider_when_no_missing(db_session):
    """无缺失代码时不查停牌（get_suspensions 零调用）。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)
    fake = FakeMarketDataSource(daily_quotes=BASE_DAILY)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        await service.sync_date(T, snapshot)

    assert fake.get_suspensions_call_count == 0
    assert fake.get_market_daily_quotes_call_count == 1


# ---------------------------------------------------------------------------
# AC-01：不完整场景整日不落库
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_date_invalid_close_no_row(db_session):
    """AC-01：关键值非法（close=0）→ 整日不落库。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)
    bad = [_quote("000001.SZ", "0", "100", "50")] + BASE_DAILY[1:]
    fake = FakeMarketDataSource(daily_quotes=bad)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError):
            await service.sync_date(T, snapshot)

    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_sync_date_out_of_expected_no_row(db_session):
    """AC-01：越界代码（不在预期集合）→ 整日不落库。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)
    extra = BASE_DAILY + [_quote("999999.SZ", "1.0", "1", "1")]
    fake = FakeMarketDataSource(daily_quotes=extra)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError, match="越界"):
            await service.sync_date(T, snapshot)

    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_sync_date_duplicate_no_row(db_session):
    """AC-01：重复 ts_code → 整日不落库。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)
    dup = [BASE_DAILY[0], BASE_DAILY[0], BASE_DAILY[1], BASE_DAILY[2]]
    fake = FakeMarketDataSource(daily_quotes=dup)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError, match="重复"):
            await service.sync_date(T, snapshot)

    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_sync_date_empty_market_no_row(db_session):
    """AC-01：全市场行情为空 → 整日不落库。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)
    fake = FakeMarketDataSource(daily_quotes=[])

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError, match="为空"):
            await service.sync_date(T, snapshot)

    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_sync_date_imbalance_missing_code_no_row(db_session):
    """AC-01：缺失代码（既无 daily 也无停牌）→ 集合不平衡、整日不落库。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)
    # 只返回 2 只，缺 830001.BJ 且无停牌
    fake = FakeMarketDataSource(daily_quotes=BASE_DAILY[:2])

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError):
            await service.sync_date(T, snapshot)

    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


# ---------------------------------------------------------------------------
# AC-03：同日重复同步覆盖
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_date_repeat_overwrites_same_row(db_session):
    """AC-03：同日重复 sync_date → 恰一行，值覆盖（updated_at 非 NULL 且刷新）。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)

    with _patch_market_factory(FakeMarketDataSource(daily_quotes=BASE_DAILY)):
        service = MarketMetricsService(db_session)
        await service.sync_date(T, snapshot)

    db_session.expire_all()
    first = (
        (await db_session.execute(select(MarketDailyMetric))).scalars().first()
    )
    # S1 后补丁：首行插入即有 updated_at（server_default=now()），不再为 NULL
    assert first.created_at is not None
    assert first.updated_at is not None
    first_created_at = first.created_at
    first_updated_at = first.updated_at
    first_volume = first.volume_shares

    # 第二次：用不同数值覆盖
    new_daily = [
        _quote("000001.SZ", "11.0", "110", "55"),
        _quote("600000.SH", "22.0", "220", "110"),
        _quote("830001.BJ", "6.0", "330", "33"),
    ]
    with _patch_market_factory(FakeMarketDataSource(daily_quotes=new_daily)):
        service2 = MarketMetricsService(db_session)
        await service2.sync_date(T, snapshot)

    db_session.expire_all()
    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert len(rows) == 1  # 不新增重复行
    assert rows[0].volume_shares != first_volume  # 值覆盖
    assert rows[0].volume_shares == Decimal((110 + 220 + 330) * 100)
    # created_at 不变；updated_at 非 NULL 且 >= created_at（覆盖写显式 func.now()）
    assert rows[0].created_at == first_created_at
    assert rows[0].updated_at is not None
    assert rows[0].updated_at >= rows[0].created_at
    assert rows[0].updated_at >= first_updated_at


# ---------------------------------------------------------------------------
# AC-09：非交易日守卫
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_date_closed_day_returns_skipped_zero_provider(db_session):
    """AC-09：本地日历休市 → skipped 且零 Provider 调用。"""
    # T 标记为休市
    await _seed_calendar(db_session, T - timedelta(days=7), T, closed_days={T})
    snapshot = _snapshot(BASE_L_RECORDS)
    fake = FakeMarketDataSource(daily_quotes=BASE_DAILY)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        result = await service.sync_date(T, snapshot)

    assert result == "skipped"
    assert fake.get_market_daily_quotes_call_count == 0
    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_sync_date_no_calendar_record_raises(db_session):
    """AC-09：本地日历无覆盖记录 → 抛错（拒绝按自然日/工作日猜测）。"""
    # 仅刷新不含 T 的区间
    await _seed_calendar(
        db_session, T - timedelta(days=30), T - timedelta(days=10)
    )
    snapshot = _snapshot(BASE_L_RECORDS)
    fake = FakeMarketDataSource(daily_quotes=BASE_DAILY)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError, match="无覆盖记录"):
            await service.sync_date(T, snapshot)


# ---------------------------------------------------------------------------
# AC-13：全天停牌参与计算
# ---------------------------------------------------------------------------


def _suspended_stock():
    return LifecycleStock(
        ts_code="000002.SZ", exchange="SZSE", list_status="L",
        name="万科", list_date=date(2020, 1, 1), delist_date=None,
    )


@pytest.mark.asyncio
async def test_full_day_suspended_supplemented_with_last_close(db_session):
    """AC-13：全天停牌股量额为 0、close=最近有效收盘；suspended 计入 final。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    records = BASE_L_RECORDS + [_suspended_stock()]
    snapshot = _snapshot(records)
    # 000002.SZ 缺 daily
    daily = list(BASE_DAILY)
    # 跨多日的停牌记录（客户端必须按 suspend_date==T 过滤）+ 当日全天停牌
    suspensions = [
        SuspensionRecord(
            ts_code="000002.SZ", suspend_date=T - timedelta(days=2),
            suspend_type="S", suspend_timing=None,
        ),
        SuspensionRecord(
            ts_code="000002.SZ", suspend_date=T,
            suspend_type="S", suspend_timing=None,
        ),
    ]
    close_window = [
        MarketDailyQuote(
            ts_code="000002.SZ", trade_date=T - timedelta(days=1),
            close=Decimal("8.0"), pre_close=None, vol=Decimal("0"),
            amount=Decimal("0"),
        ),
    ]
    fake = FakeMarketDataSource(
        daily_quotes=daily, suspensions=suspensions, close_window_quotes=close_window
    )

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        result = await service.sync_date(T, snapshot)

    assert result == "success"
    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.expected_stock_count == 4
    assert row.daily_quote_count == 3
    assert row.suspended_stock_count == 1
    assert row.final_stock_count == 4
    # 量额不含停牌（0），平均价含停牌 close=8.0
    assert row.volume_shares == Decimal((100 + 200 + 300) * 100)
    assert row.amount_yuan == Decimal((50 + 100 + 30) * 1000)
    assert row.average_price == (Decimal("35.5") + Decimal("8.0")) / Decimal(4)
    # 客户端日期过滤生效：跨多日记录被忽略，仅当日 000002 进补价
    # （否则集合不平衡会失败；此处 success 即证明）


@pytest.mark.asyncio
async def test_suspension_undeterminable_timing_fails(db_session):
    """AC-13：suspend_timing 非空无法判定全天 → 整日失败。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    records = BASE_L_RECORDS + [_suspended_stock()]
    snapshot = _snapshot(records)
    daily = list(BASE_DAILY)  # 000002 缺 daily
    suspensions = [
        SuspensionRecord(
            ts_code="000002.SZ", suspend_date=T,
            suspend_type="S", suspend_timing="开盘",  # 盘中时段，无法判定全天
        ),
    ]
    fake = FakeMarketDataSource(daily_quotes=daily, suspensions=suspensions)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError):
            await service.sync_date(T, snapshot)

    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_missing_code_no_suspension_fails(db_session):
    """AC-13：缺失代码无停牌证据 → 整日失败。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    records = BASE_L_RECORDS + [_suspended_stock()]
    snapshot = _snapshot(records)
    daily = list(BASE_DAILY)  # 000002 缺 daily
    fake = FakeMarketDataSource(daily_quotes=daily, suspensions=[])

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError):
            await service.sync_date(T, snapshot)

    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_supplement_no_close_found_fails(db_session):
    """AC-13：全天停牌但前收盘扫描未命中 → 整日失败。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    records = BASE_L_RECORDS + [_suspended_stock()]
    snapshot = _snapshot(records)
    daily = list(BASE_DAILY)
    suspensions = [
        SuspensionRecord(
            ts_code="000002.SZ", suspend_date=T,
            suspend_type="S", suspend_timing=None,
        ),
    ]
    # 前收盘窗口返回空
    fake = FakeMarketDataSource(
        daily_quotes=daily, suspensions=suspensions, close_window_quotes=[]
    )

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError):
            await service.sync_date(T, snapshot)

    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_intraday_halt_uses_daily_not_supplement(db_session):
    """盘中临停（daily 有行）优先用 daily，不进补价集合。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    # 000001 同时有 daily 行和停牌记录（盘中临停）→ 应用 daily，不补价
    snapshot = _snapshot(BASE_L_RECORDS)
    suspensions = [
        SuspensionRecord(
            ts_code="000001.SZ", suspend_date=T,
            suspend_type="S", suspend_timing="开盘",
        ),
    ]
    fake = FakeMarketDataSource(daily_quotes=BASE_DAILY, suspensions=suspensions)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        result = await service.sync_date(T, snapshot)

    assert result == "success"
    # 没有缺失代码 → 不查停牌也不补价
    assert fake.get_close_quotes_in_window_calls == []
    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows[0].suspended_stock_count == 0


# ---------------------------------------------------------------------------
# 补价窗口扫描：100/批、预算常量、close_cache
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_cache_hit_avoids_provider_request(db_session):
    """补价命中 close_cache → 免 Provider 请求直接复用。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    records = BASE_L_RECORDS + [_suspended_stock()]
    snapshot = _snapshot(records)
    daily = list(BASE_DAILY)
    suspensions = [
        SuspensionRecord(
            ts_code="000002.SZ", suspend_date=T,
            suspend_type="S", suspend_timing=None,
        ),
    ]
    fake = FakeMarketDataSource(daily_quotes=daily, suspensions=suspensions)
    close_cache = {"000002.SZ": (T - timedelta(days=1), Decimal("9.0"))}

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        result = await service.sync_date(T, snapshot, close_cache=close_cache)

    assert result == "success"
    # 缓存命中：不发起补价请求
    assert fake.get_close_quotes_in_window_calls == []
    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    # 000002 close 取缓存 9.0
    assert rows[0].average_price == (Decimal("35.5") + Decimal("9.0")) / Decimal(4)


@pytest.mark.asyncio
async def test_supplement_budget_exhausted_fails(db_session, monkeypatch):
    """补价预算耗尽仍有未决代码 → 整日失败。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    records = BASE_L_RECORDS + [_suspended_stock()]
    snapshot = _snapshot(records)
    daily = list(BASE_DAILY)
    suspensions = [
        SuspensionRecord(
            ts_code="000002.SZ", suspend_date=T,
            suspend_type="S", suspend_timing=None,
        ),
    ]
    close_window = [
        MarketDailyQuote(
            ts_code="000002.SZ", trade_date=T - timedelta(days=1),
            close=Decimal("8.0"), pre_close=None, vol=Decimal("0"),
            amount=Decimal("0"),
        ),
    ]
    fake = FakeMarketDataSource(
        daily_quotes=daily, suspensions=suspensions, close_window_quotes=close_window
    )
    # 预算设为 0 → 不允许任何补价请求 → 未决 → 失败
    monkeypatch.setattr(mms_module, "MAX_CLOSE_LOOKBACK_REQUESTS", 0)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError):
            await service.sync_date(T, snapshot)

    assert fake.get_close_quotes_in_window_calls == []
    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_supplement_chunks_at_most_100_codes(db_session, monkeypatch):
    """补价分块 ≤100/批：构造 >100 只全天停牌股，断言每批 ≤100。"""
    await _seed_calendar(db_session, T - timedelta(days=120), T)
    # 3 只正常交易（有 daily）+ 105 只全天停牌 L 股（list_date 早于扫描下界）
    suspended_records = [
        LifecycleStock(
            ts_code=f"{300000 + i}.SZ", exchange="SZSE", list_status="L",
            name=f"s{i}", list_date=date(2010, 1, 1), delist_date=None,
        )
        for i in range(105)
    ]
    snapshot = _snapshot(BASE_L_RECORDS + suspended_records)
    # 仅 3 只正常交易返回 daily；105 只缺 daily → 全天停牌补价
    suspensions = [
        SuspensionRecord(
            ts_code=rec.ts_code, suspend_date=T,
            suspend_type="S", suspend_timing=None,
        )
        for rec in suspended_records
    ]
    close_window = [
        MarketDailyQuote(
            ts_code=rec.ts_code, trade_date=T - timedelta(days=1),
            close=Decimal("1.0"), pre_close=None, vol=Decimal("0"),
            amount=Decimal("0"),
        )
        for rec in suspended_records
    ]
    fake = FakeMarketDataSource(
        daily_quotes=BASE_DAILY, suspensions=suspensions,
        close_window_quotes=close_window,
    )
    # 预算放宽以容纳两批
    monkeypatch.setattr(mms_module, "MAX_CLOSE_LOOKBACK_REQUESTS", 10)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        result = await service.sync_date(T, snapshot)

    assert result == "success"
    # 每批代码数 ≤100
    assert fake.get_close_quotes_in_window_arg_lists, "应至少发起一批补价请求"
    for arg_list in fake.get_close_quotes_in_window_arg_lists:
        assert len(arg_list) <= CLOSE_LOOKBACK_MAX_CODES_PER_BATCH
    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    # 3 daily + 105 suspended = 108
    assert rows[0].final_stock_count == 108
    assert rows[0].suspended_stock_count == 105


# ---------------------------------------------------------------------------
# 快照校验：G 排除 / L/D/P 日期约束
# ---------------------------------------------------------------------------


def test_expected_codes_excludes_g_and_respects_dates():
    """G 固定排除；L/P 需 list_date<=T；D 另需 T<delist_date。"""
    records = [
        LifecycleStock(
            ts_code="000001.SZ", exchange="SZSE", list_status="L",
            name="a", list_date=date(2020, 1, 1), delist_date=None,
        ),
        LifecycleStock(
            ts_code="000002.SZ", exchange="SZSE", list_status="G",
            name="g", list_date=date(2020, 1, 1), delist_date=None,
        ),
        LifecycleStock(
            ts_code="000003.SZ", exchange="SZSE", list_status="P",
            name="p", list_date=date(2026, 3, 20), delist_date=None,
        ),
        LifecycleStock(
            ts_code="000004.SZ", exchange="SZSE", list_status="D",
            name="d", list_date=date(2020, 1, 1), delist_date=date(2026, 3, 20),
        ),
        LifecycleStock(
            ts_code="000005.SZ", exchange="SZSE", list_status="D",
            name="d2", list_date=date(2020, 1, 1), delist_date=date(2026, 3, 10),
        ),
    ]
    snap = _snapshot(records)
    codes = snap.expected_codes(T)
    assert "000001.SZ" in codes  # L, listed
    assert "000002.SZ" not in codes  # G excluded
    assert "000003.SZ" not in codes  # P not yet listed (list_date > T)
    assert "000004.SZ" in codes  # D listed and T < delist_date
    assert "000005.SZ" not in codes  # D already delisted (T >= delist_date)


@pytest.mark.asyncio
async def test_snapshot_l_missing_list_date_raises(db_session):
    """L 缺 list_date → 快照校验失败。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    bad = [
        LifecycleStock(
            ts_code="000001.SZ", exchange="SZSE", list_status="L",
            name="a", list_date=None, delist_date=None,
        )
    ]
    snapshot = _snapshot(bad)
    fake = FakeMarketDataSource(daily_quotes=[])

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError, match="快照记录校验失败"):
            await service.sync_date(T, snapshot)


@pytest.mark.asyncio
async def test_snapshot_d_missing_delist_date_raises(db_session):
    """D 缺 delist_date → 快照校验失败。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    bad = [
        LifecycleStock(
            ts_code="000001.SZ", exchange="SZSE", list_status="D",
            name="a", list_date=date(2020, 1, 1), delist_date=None,
        )
    ]
    snapshot = _snapshot(bad)
    fake = FakeMarketDataSource(daily_quotes=[])

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError, match="delist_date"):
            await service.sync_date(T, snapshot)


@pytest.mark.asyncio
async def test_snapshot_flags_incomplete_raises(db_session):
    """快照四类标记不全 → 失败（不用当前 L 集合降级）。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS, status_flags={"L": True, "D": False, "P": True, "G": True})
    fake = FakeMarketDataSource(daily_quotes=BASE_DAILY)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(MarketMetricsSyncError, match="四类标记不全"):
            await service.sync_date(T, snapshot)


# ---------------------------------------------------------------------------
# Decimal 精度：构造 float 精度陷阱用例
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decimal_precision_no_float_accumulation(db_session):
    """Decimal 全程：1.1+2.2+3.3 千元 → 6600 元精确，无 float 累积误差。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)
    daily = [
        _quote("000001.SZ", "1.0", "1", "1.1"),
        _quote("600000.SH", "1.0", "1", "2.2"),
        _quote("830001.BJ", "1.0", "1", "3.3"),
    ]
    fake = FakeMarketDataSource(daily_quotes=daily)

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        await service.sync_date(T, snapshot)

    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    # (1.1+2.2+3.3)*1000 = 6600 精确（float 会得 6600.000000000001）
    assert rows[0].amount_yuan == Decimal("6600")


# ---------------------------------------------------------------------------
# task_context 协议调用（plan-04 落地，此处用 mock 协议对象）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_context_lock_and_validate_invoked(db_session):
    """task_context 非 None 时 upsert 前调 lock_and_validate；同事务成功提交。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)
    fake = FakeMarketDataSource(daily_quotes=BASE_DAILY)

    class _FakeTaskContext:
        def __init__(self):
            self.locked = False

        async def lock_and_validate(self, session):
            self.locked = True
            assert session is db_session  # 同一事务

    ctx = _FakeTaskContext()
    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        result = await service.sync_date(T, snapshot, task_context=ctx)

    assert result == "success"
    assert ctx.locked is True
    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_task_context_validation_failure_rolls_back(db_session):
    """task_context 校验失败 → 业务写一起 rollback，不落库。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    snapshot = _snapshot(BASE_L_RECORDS)
    fake = FakeMarketDataSource(daily_quotes=BASE_DAILY)

    class _RejectingTaskContext:
        async def lock_and_validate(self, session):
            raise RuntimeError("task 已被取消/fencing 拒绝")

    with _patch_market_factory(fake):
        service = MarketMetricsService(db_session)
        with pytest.raises(RuntimeError, match="fencing"):
            await service.sync_date(
                T, snapshot, task_context=_RejectingTaskContext()
            )

    rows = (await db_session.execute(select(MarketDailyMetric))).scalars().all()
    assert rows == []


# ---------------------------------------------------------------------------
# build_lifecycle_snapshot：DB 读回 + init_stocks_lifecycle 集成
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_lifecycle_snapshot_reads_back_four_states(db_session):
    """build_lifecycle_snapshot 调 init_stocks_lifecycle 后从库读回四状态全集。"""
    # 既有 A 股 000099（将被清理，不在 union）
    from src.models.stock import Stock

    db_session.add(
        Stock(
            symbol="000099", name="tobedeleted", ts_code="000099.SZ",
            exchange="SZSE", list_status="L", current_price=None, market_cap=None,
        )
    )
    await db_session.commit()

    lifecycle_records = [
        LifecycleStock(
            ts_code="000001.SZ", exchange="SZSE", list_status="L",
            name="a", list_date=date(2020, 1, 1), delist_date=None,
        ),
        LifecycleStock(
            ts_code="000002.SZ", exchange="SZSE", list_status="D",
            name="d", list_date=date(2010, 1, 1), delist_date=date(2025, 1, 1),
        ),
        LifecycleStock(
            ts_code="600000.SH", exchange="SSE", list_status="P",
            name="p", list_date=date(2020, 1, 1), delist_date=None,
        ),
        LifecycleStock(
            ts_code="830001.BJ", exchange="BSE", list_status="G",
            name="g", list_date=None, delist_date=None,
        ),
    ]
    fake = MagicMock()
    fake.get_lifecycle_stocks.return_value = lifecycle_records

    with patch("src.services.data_init.DataSourceFactory.create", return_value=fake):
        snapshot = await build_lifecycle_snapshot(db_session)

    codes = {r.ts_code for r in snapshot.records}
    assert "000001.SZ" in codes  # L
    assert "000002.SZ" in codes  # D（旧 init_stocks 仅 L 清理会误删，此处保留）
    assert "600000.SH" in codes  # P
    assert "830001.BJ" in codes  # G
    # 000099 不在 union → 被清理
    remaining = (
        await db_session.execute(select(Stock.symbol))
    ).scalars().all()
    assert "000099" not in remaining
    assert snapshot.status_flags == {"L": True, "D": True, "P": True, "G": True}
