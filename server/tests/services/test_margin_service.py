"""MarginService 单元/集成测试（第 17 期 plan-03）

覆盖 plan-03 §5 验收标准：

- AC-1（聚合复算）：spec 数值三行（SSE/SZSE/BSE）→ 五字段求和落库单行，
  rzye=1.82E12、rqye=9.0E10、rzmre=1.2E11、rzrqye=1.91E12。
- AC-1（rzrqye 重算）：行内 tushare rzrqye 为脏数据 → 落库值为
  Σrzye+Σrqye 重算值（不读行 rzrqye 参与聚合）。
- AC-2（幂等 upsert）：同日两次 sync_date → 恰一行、值覆盖、updated_at
  刷新（on_conflict_do_update set_ 显式 func.now()）。
- 日历守卫：休市日 skipped 且 get_margin 零调用；本地日历无记录 → 抛
  MarginSyncError。
- 空数据：get_margin 返回空列表 → 抛 MarginSyncError，表无新行。
- 失败回滚：聚合阶段（非 Decimal）与 upsert 阶段（DB 异常 / fence 拒绝）
  抛错 → 表无新行、无半成品。
- Decimal 全程：float 精度陷阱用例断言无累计误差。
- 交易所护栏：缺 SSE/SZSE 记 WARNING 后继续；仅缺 BSE 不告警。
- task_context 协议：非 None 时先 lock_and_validate 再 upsert（调用顺序）；
  FenceValidationError → 当日整体回滚。

测试使用真实 PostgreSQL（conftest 拒绝 SQLite，每用例独立 schema），
DataSourceFactory 通过 patch 注入确定性 fake 数据源；本地日历用真实
``TradingCalendarRepository.refresh_range`` 种子（16 期测试惯例）。
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.models.market_margin_daily import MarketMarginDaily
from src.services.data_acquisition.models import TradingCalendarEntry
from src.services.margin_service import MarginService, MarginSyncError
from src.services.task_fence import FenceValidationError
from src.services.trading_calendar_repository import TradingCalendarRepository


T = date(2026, 3, 16)  # 目标交易日（周一）


# ---------------------------------------------------------------------------
# 测试替身：确定性 fake 数据源
# ---------------------------------------------------------------------------


class FakeMarginDataSource:
    """返回预设的 margin 原始行，记录 get_margin 调用次数。"""

    def __init__(self, rows=None, exc=None):
        self._rows = list(rows or [])
        self._exc = exc
        self.get_margin_call_count = 0

    def get_margin(self, trade_date):
        self.get_margin_call_count += 1
        if self._exc is not None:
            raise self._exc
        return [dict(r) for r in self._rows]


class _FakeCalendarSource:
    """仅服务日历刷新的 fake（返回闭区间全量自然日）。"""

    def __init__(self, entries):
        self._entries = list(entries)

    def get_trading_calendar_range(self, start_date, end_date):
        return list(self._entries)


def _patch_margin_factory(fake):
    return patch(
        "src.services.margin_service.DataSourceFactory.create",
        return_value=fake,
    )


async def _seed_calendar(db_session, start, end, closed_days=None):
    """用真实 refresh_range 写入本地日历（patch 日历的 DataSourceFactory）。"""
    closed_days = set(closed_days or [])
    entries = []
    d = start
    while d <= end:
        entries.append(
            TradingCalendarEntry(cal_date=d, is_open=d not in closed_days)
        )
        d += timedelta(days=1)
    with patch(
        "src.services.trading_calendar_repository.DataSourceFactory.create",
        return_value=_FakeCalendarSource(entries),
    ):
        repo = TradingCalendarRepository(db_session)
        await repo.refresh_range(start, end)


def _margin_row(
    exchange_id,
    rzye,
    rqye,
    rzmre,
    rzche="0",
    rqmcl="0",
    rzrqye=None,
    trade_date=T,
):
    """构造 plan-02 ``get_margin`` 保真行（七数值字段 Decimal）。"""
    row = {
        "trade_date": trade_date,
        "exchange_id": exchange_id,
        "rzye": Decimal(str(rzye)),
        "rqye": Decimal(str(rqye)),
        "rzmre": Decimal(str(rzmre)),
        "rzche": Decimal(str(rzche)),
        "rqmcl": Decimal(str(rqmcl)),
        "rqyl": Decimal("0"),  # 股口径余量，不入库（spec REQ-2）
    }
    row["rzrqye"] = (
        Decimal(str(rzrqye)) if rzrqye is not None
        else row["rzye"] + row["rqye"]
    )
    return row


# spec 数值三行（plan-03 §5 AC-1 用例数据）
SPEC_THREE_ROWS = [
    _margin_row("SSE", "1.0e12", "5.0e10", "7.0e10", rzche="3.0e10", rqmcl="2.0e9"),
    _margin_row("SZSE", "8.0e11", "3.0e10", "4.0e10", rzche="2.0e10", rqmcl="1.0e9"),
    _margin_row("BSE", "2.0e10", "1.0e10", "1.0e10", rzche="5.0e9", rqmcl="3.0e8"),
]

async def _all_rows(db_session):
    return (
        (await db_session.execute(select(MarketMarginDaily)))
        .scalars()
        .all()
    )


# ---------------------------------------------------------------------------
# AC-1：聚合复算（spec 数值三行）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_date_aggregates_all_exchange_rows(db_session):
    """AC-1：SSE+SZSE+BSE 三行 → 五字段求和 + rzrqye 重算落库单行。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    fake = FakeMarginDataSource(rows=SPEC_THREE_ROWS)

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        result = await service.sync_date(T)

    assert result == "success"
    rows = await _all_rows(db_session)
    assert len(rows) == 1
    row = rows[0]
    assert row.trade_date == T
    assert row.rzye == Decimal("1.82E12")
    assert row.rqye == Decimal("9.0E10")
    assert row.rzmre == Decimal("1.2E11")
    assert row.rzche == Decimal("5.5E10")
    assert row.rqmcl == Decimal("3.3E9")
    # rzrqye = Σrzye + Σrqye = 1.82E12 + 9.0E10
    assert row.rzrqye == Decimal("1.91E12")


@pytest.mark.asyncio
async def test_sync_date_rzrqye_recomputed_not_row_sum(db_session):
    """AC-1：行内 rzrqye 脏数据 → 落库为重算值（不读行 rzrqye 聚合）。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    dirty = [
        _margin_row(
            "SSE", "1.0e12", "5.0e10", "7.0e10", rzrqye="9.9e12"
        ),
        _margin_row(
            "SZSE", "8.0e11", "3.0e10", "4.0e10", rzrqye="8.8e12"
        ),
    ]
    fake = FakeMarginDataSource(rows=dirty)

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        result = await service.sync_date(T)

    assert result == "success"
    row = (await _all_rows(db_session))[0]
    # 重算值 1.8E12 + 8.0E10 = 1.88E12，而非行值之和 18.7E12 或任一行原值
    assert row.rzrqye == Decimal("1.88E12")
    assert row.rzrqye != Decimal("9.9E12") + Decimal("8.8E12")
    assert row.rzrqye not in {Decimal("9.9E12"), Decimal("8.8E12")}


@pytest.mark.asyncio
async def test_sync_date_single_row_still_sums(db_session):
    """边界：仅一行（接口行数以实际返回为准）→ 该行即全市场合计。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    fake = FakeMarginDataSource(
        rows=[_margin_row("SSE", "100.1", "50.2", "30.3")]
    )

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        result = await service.sync_date(T)

    assert result == "success"
    row = (await _all_rows(db_session))[0]
    assert row.rzye == Decimal("100.1")
    assert row.rqye == Decimal("50.2")
    assert row.rzmre == Decimal("30.3")
    assert row.rzrqye == Decimal("150.3")


# ---------------------------------------------------------------------------
# AC-2：幂等 upsert（同日覆盖 + updated_at 刷新）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_date_idempotent_overwrite_refreshes_updated_at(db_session):
    """AC-2：同日两次 sync → 恰一行、第二次值覆盖、updated_at 刷新。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)

    with _patch_margin_factory(FakeMarginDataSource(rows=SPEC_THREE_ROWS)):
        service = MarginService(db_session)
        first = await service.sync_date(T)
    assert first == "success"
    rows = await _all_rows(db_session)
    assert len(rows) == 1
    first_updated_at = rows[0].updated_at
    assert first_updated_at is not None

    # 第二次：数值变化（SZSE/BSE rzye 放大），断言覆盖而非新增
    second_rows = [
        _margin_row("SSE", "1.0e12", "5.0e10", "7.0e10"),
        _margin_row("SZSE", "9.0e11", "3.0e10", "4.0e10"),
        _margin_row("BSE", "3.0e11", "1.0e10", "1.0e10"),
    ]
    await asyncio.sleep(0.01)  # 保证事务时间戳可区分
    with _patch_margin_factory(FakeMarginDataSource(rows=second_rows)):
        service = MarginService(db_session)
        second = await service.sync_date(T)

    assert second == "success"
    db_session.expire_all()  # 覆盖写经核心 upsert，需失效身份映射缓存后重读
    rows = await _all_rows(db_session)
    assert len(rows) == 1  # 恰一行（覆盖非新增）
    row = rows[0]
    assert row.rzye == Decimal("2.2E12")
    assert row.rzrqye == Decimal("2.29E12")
    # updated_at 显式刷新（on_conflict_do_update set_ 中的 func.now()）
    assert row.updated_at > first_updated_at


# ---------------------------------------------------------------------------
# 日历守卫（休市 skipped 零调用 / 无记录抛错）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_date_closed_day_skipped_zero_provider_calls(db_session):
    """休市日 → skipped 且 get_margin 零调用，不落库。"""
    await _seed_calendar(
        db_session, T - timedelta(days=7), T, closed_days=[T]
    )
    fake = FakeMarginDataSource(rows=SPEC_THREE_ROWS)

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        result = await service.sync_date(T)

    assert result == "skipped"
    assert fake.get_margin_call_count == 0
    assert await _all_rows(db_session) == []


@pytest.mark.asyncio
async def test_sync_date_no_calendar_record_raises(db_session):
    """本地日历无该日记录 → 抛 MarginSyncError（拒绝猜测），不落库。"""
    # 日历只覆盖到 T-1，T 无记录
    await _seed_calendar(db_session, T - timedelta(days=7), T - timedelta(days=1))
    fake = FakeMarginDataSource(rows=SPEC_THREE_ROWS)

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        with pytest.raises(MarginSyncError, match="本地日历无覆盖记录"):
            await service.sync_date(T)

    assert fake.get_margin_call_count == 0
    assert await _all_rows(db_session) == []


# ---------------------------------------------------------------------------
# 空数据与失败回滚
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_date_empty_rows_raises(db_session):
    """get_margin 返回空列表 → 抛 MarginSyncError，表无新行。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    fake = FakeMarginDataSource(rows=[])

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        with pytest.raises(MarginSyncError, match="融资融券数据为空"):
            await service.sync_date(T)

    assert fake.get_margin_call_count == 1
    assert await _all_rows(db_session) == []


@pytest.mark.asyncio
async def test_sync_date_non_decimal_field_fails_before_upsert(db_session):
    """聚合阶段抛错（字段非 Decimal，Decimal 强约束被破坏）→ 不落库。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    bad_rows = [
        _margin_row("SSE", "1.0e12", "5.0e10", "7.0e10"),
        {**_margin_row("SZSE", "8.0e11", "3.0e10", "4.0e10"), "rzye": 8e11},
    ]
    fake = FakeMarginDataSource(rows=bad_rows)

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        with pytest.raises(MarginSyncError, match="非 Decimal"):
            await service.sync_date(T)

    assert await _all_rows(db_session) == []


@pytest.mark.asyncio
async def test_sync_date_upsert_db_error_rolls_back(db_session):
    """upsert 阶段 DB 异常 → rollback 后透传，表无新行、无半成品。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    fake = FakeMarginDataSource(rows=SPEC_THREE_ROWS)

    original_execute = db_session.execute

    async def _failing_execute(statement, *args, **kwargs):
        if getattr(statement, "table", None) is not None and (
            statement.table.name == "market_margin_daily"
        ):
            raise RuntimeError("simulated db failure on upsert")
        return await original_execute(statement, *args, **kwargs)

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        with patch.object(db_session, "execute", _failing_execute):
            with pytest.raises(RuntimeError, match="simulated db failure"):
                await service.sync_date(T)

    assert await _all_rows(db_session) == []


# ---------------------------------------------------------------------------
# Decimal 精度：float 精度陷阱用例
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decimal_precision_no_float_accumulation(db_session):
    """Decimal 全程：0.1+0.2+0.3 → 0.6 精确（float 会得 0.6000000000000001）。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    rows = [
        _margin_row("SSE", "0.1", "1.1", "0.01"),
        _margin_row("SZSE", "0.2", "2.2", "0.02"),
        _margin_row("BSE", "0.3", "3.3", "0.03"),
    ]
    fake = FakeMarginDataSource(rows=rows)

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        await service.sync_date(T)

    row = (await _all_rows(db_session))[0]
    assert row.rzye == Decimal("0.6")
    assert row.rqye == Decimal("6.6")
    assert row.rzmre == Decimal("0.06")
    assert row.rzrqye == Decimal("7.2")


# ---------------------------------------------------------------------------
# 交易所护栏：缺 SSE/SZSE 记 WARNING 后继续；仅缺 BSE 不告警
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_required_exchange_logs_warning_and_continues(
    db_session, caplog
):
    """缺 SSE → WARNING（含交易所集合）后继续，聚合照常落库。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    rows = [
        _margin_row("SZSE", "8.0e11", "3.0e10", "4.0e10"),
        _margin_row("BSE", "2.0e10", "1.0e10", "1.0e10"),
    ]
    fake = FakeMarginDataSource(rows=rows)

    with _patch_margin_factory(fake):
        with caplog.at_level("WARNING", logger="src.services.margin_service"):
            service = MarginService(db_session)
            result = await service.sync_date(T)

    assert result == "success"
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    assert "交易所行缺席" in warnings[0].getMessage()
    row = (await _all_rows(db_session))[0]
    assert row.rzye == Decimal("8.2E11")


@pytest.mark.asyncio
async def test_missing_bse_only_no_warning(db_session, caplog):
    """仅缺 BSE（SSE/SZSE 齐全）→ 不告警（BSE 缺席不触发护栏）。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    rows = [
        _margin_row("SSE", "1.0e12", "5.0e10", "7.0e10"),
        _margin_row("SZSE", "8.0e11", "3.0e10", "4.0e10"),
    ]
    fake = FakeMarginDataSource(rows=rows)

    with _patch_margin_factory(fake):
        with caplog.at_level("WARNING", logger="src.services.margin_service"):
            service = MarginService(db_session)
            result = await service.sync_date(T)

    assert result == "success"
    assert [r for r in caplog.records if r.levelname == "WARNING"] == []
    row = (await _all_rows(db_session))[0]
    assert row.rzye == Decimal("1.8E12")


# ---------------------------------------------------------------------------
# task_context 协议调用（16 期 task_fence 已落地，此处用 mock 协议对象）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_context_lock_and_validate_invoked_before_upsert(db_session):
    """task_context 非 None 时先 lock_and_validate 再 upsert（调用顺序）。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    fake = FakeMarginDataSource(rows=SPEC_THREE_ROWS)

    events: list = []
    original_execute = db_session.execute

    async def _recording_execute(statement, *args, **kwargs):
        if getattr(statement, "table", None) is not None and (
            statement.table.name == "market_margin_daily"
        ):
            events.append("upsert")
        return await original_execute(statement, *args, **kwargs)

    class _FakeTaskContext:
        async def lock_and_validate(self, session):
            assert session is db_session  # 同一事务
            events.append("lock_and_validate")

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        with patch.object(db_session, "execute", _recording_execute):
            result = await service.sync_date(T, task_context=_FakeTaskContext())

    assert result == "success"
    assert events == ["lock_and_validate", "upsert"]  # 先锁后写
    assert len(await _all_rows(db_session)) == 1


@pytest.mark.asyncio
async def test_task_context_fence_validation_failure_rolls_back(db_session):
    """lock_and_validate 抛 FenceValidationError → 当日整体回滚，不落库。"""
    await _seed_calendar(db_session, T - timedelta(days=7), T)
    fake = FakeMarginDataSource(rows=SPEC_THREE_ROWS)

    class _RejectingTaskContext:
        async def lock_and_validate(self, session):
            raise FenceValidationError(
                "fence rejected: guard inactive or token superseded"
            )

    with _patch_margin_factory(fake):
        service = MarginService(db_session)
        with pytest.raises(FenceValidationError, match="fence rejected"):
            await service.sync_date(T, task_context=_RejectingTaskContext())

    assert await _all_rows(db_session) == []
