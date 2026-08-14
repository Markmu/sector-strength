"""TradingCalendarRepository 单元/集成测试（第 16 期 plan-01）

覆盖 plan-01 §5 验收标准：

- AC-09（数据基础）：refresh_range 后本地表对闭区间每个自然日恰有一行，
  get_record(休市日).is_open=False。
- 部分响应（缺日）、重复行、越界行三种场景均抛 ValueError 且不提交任何行，
  旧批次数据原样保留（架构 §8.2-5）。
- 同一日期重复 refresh_range 为 upsert 覆盖，不产生重复行，
  refresh_batch_id/refreshed_at 更新为新批次。
- Provider 抛错时 refresh_range 透传失败，不吞异常。
- 闭区间仅 1 天（start==end）正常处理。
- 只读查询：get_record / get_trading_days / get_recent_open_days / has_any_open_day。
- 性能（架构 §8.1）：get_recent_open_days(250) 返回行数 ≤ 250。

测试使用真实 PostgreSQL（conftest 拒绝 SQLite），DataSourceFactory 通过 patch 注入
确定性 fake 数据源，避免依赖外部 Tushare。
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import delete, select

from src.models.trading_calendar_day import TradingCalendarDay
from src.services.data_acquisition.exceptions import DataFetchError
from src.services.data_acquisition.models import TradingCalendarEntry
from src.services.trading_calendar_repository import TradingCalendarRepository


# ---------------------------------------------------------------------------
# 测试替身：确定性 fake 数据源
# ---------------------------------------------------------------------------


class _FakeDataSource:
    """返回预设的 TradingCalendarEntry 列表，可配置抛错。"""

    def __init__(self, entries=None, exc=None):
        self._entries = list(entries) if entries else []
        self._exc = exc

    def get_trading_calendar_range(self, start_date, end_date):
        if self._exc is not None:
            raise self._exc
        return list(self._entries)


def _make_closed_range(start: date, end: date, closed_days=None):
    """构造闭区间全量自然日条目，closed_days 中的日期标记 is_open=False。"""
    closed_days = set(closed_days or [])
    out = []
    d = start
    while d <= end:
        out.append(TradingCalendarEntry(cal_date=d, is_open=d not in closed_days))
        d += timedelta(days=1)
    return out


def _patch_factory(fake):
    """patch 仓库模块的 DataSourceFactory.create 返回 fake。"""
    return patch(
        "src.services.trading_calendar_repository.DataSourceFactory.create",
        return_value=fake,
    )


# ---------------------------------------------------------------------------
# refresh_range：合法刷新
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_range_valid_writes_all_natural_days(db_session):
    """AC-09：合法响应写入闭区间每个自然日一行，返回 (open, closed)。"""
    start, end = date(2026, 1, 1), date(2026, 1, 10)
    # 元旦休市 + 周末休市
    closed = {date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 4), date(2026, 1, 10)}
    entries = _make_closed_range(start, end, closed)
    fake = _FakeDataSource(entries=entries)

    repo = TradingCalendarRepository(db_session)
    with _patch_factory(fake):
        open_count, closed_count = await repo.refresh_range(start, end)

    expected_total = (end - start).days + 1
    assert open_count + closed_count == expected_total
    assert open_count == expected_total - len(closed)
    assert closed_count == len(closed)

    rows = (await db_session.execute(
        select(TradingCalendarDay)
    )).scalars().all()
    assert len(rows) == expected_total
    # 休市日记为 False（AC-09）
    holiday = await repo.get_record(date(2026, 1, 1))
    assert holiday is not None
    assert holiday.is_open is False
    open_day = await repo.get_record(date(2026, 1, 5))
    assert open_day.is_open is True


@pytest.mark.asyncio
async def test_refresh_range_single_day_start_equals_end(db_session):
    """边界场景：闭区间仅 1 天（start==end，日更路径依赖）。"""
    day = date(2026, 3, 16)
    entries = [TradingCalendarEntry(cal_date=day, is_open=True)]
    fake = _FakeDataSource(entries=entries)

    repo = TradingCalendarRepository(db_session)
    with _patch_factory(fake):
        open_count, closed_count = await repo.refresh_range(day, day)

    assert open_count == 1
    assert closed_count == 0
    rec = await repo.get_record(day)
    assert rec is not None and rec.is_open is True


@pytest.mark.asyncio
async def test_refresh_range_sets_batch_id_and_refreshed_at(db_session):
    """合法刷新写入的行共享同一 refresh_batch_id 与 refreshed_at。"""
    start, end = date(2026, 2, 2), date(2026, 2, 5)
    entries = _make_closed_range(start, end)
    fake = _FakeDataSource(entries=entries)

    repo = TradingCalendarRepository(db_session)
    with _patch_factory(fake):
        await repo.refresh_range(start, end)

    from sqlalchemy import select

    rows = (await db_session.execute(select(TradingCalendarDay))).scalars().all()
    batch_ids = {r.refresh_batch_id for r in rows}
    refreshed = {r.refreshed_at for r in rows}
    assert len(batch_ids) == 1, "同批次应共享 refresh_batch_id"
    assert len(refreshed) == 1, "同批次应共享 refreshed_at"
    assert rows[0].refresh_batch_id is not None


# ---------------------------------------------------------------------------
# refresh_range：校验拒绝（缺日 / 重复 / 越界）且不提交
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_range_rejects_missing_days_no_commit(db_session):
    """部分响应（缺日）抛 ValueError，不提交任何行。"""
    start, end = date(2026, 1, 1), date(2026, 1, 5)
    entries = _make_closed_range(start, end)
    # 删掉中间一天
    del entries[2]
    fake = _FakeDataSource(entries=entries)

    repo = TradingCalendarRepository(db_session)
    with _patch_factory(fake):
        with pytest.raises(ValueError, match="缺失日期样本"):
            await repo.refresh_range(start, end)

    rows = (await db_session.execute(
        select(TradingCalendarDay)
    )).scalars().all()
    assert rows == [], "校验失败不应提交任何行"


@pytest.mark.asyncio
async def test_refresh_range_rejects_duplicates_no_commit(db_session):
    """重复 cal_date 抛 ValueError，不提交任何行。"""
    start, end = date(2026, 1, 1), date(2026, 1, 3)
    entries = _make_closed_range(start, end)
    # 追加一个重复日期
    entries.append(TradingCalendarEntry(cal_date=date(2026, 1, 2), is_open=True))
    fake = _FakeDataSource(entries=entries)

    repo = TradingCalendarRepository(db_session)
    with _patch_factory(fake):
        with pytest.raises(ValueError, match="重复"):
            await repo.refresh_range(start, end)

    rows = (await db_session.execute(
        select(TradingCalendarDay)
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_refresh_range_rejects_out_of_range_no_commit(db_session):
    """越界行（区间外日期）抛 ValueError，不提交任何行。"""
    start, end = date(2026, 1, 1), date(2026, 1, 3)
    entries = _make_closed_range(start, end)
    # 用区间外的一天替换最后一天
    entries[-1] = TradingCalendarEntry(cal_date=date(2026, 1, 10), is_open=True)
    fake = _FakeDataSource(entries=entries)

    repo = TradingCalendarRepository(db_session)
    with _patch_factory(fake):
        with pytest.raises(ValueError, match="越界"):
            await repo.refresh_range(start, end)

    rows = (await db_session.execute(
        select(TradingCalendarDay)
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_refresh_range_failure_preserves_old_batch(db_session):
    """校验失败时旧批次数据原样保留（架构 §8.2-5：旧行仅供读侧继续使用）。"""
    start, end = date(2026, 1, 1), date(2026, 1, 5)
    # 先成功写入一批
    entries = _make_closed_range(start, end)
    with _patch_factory(_FakeDataSource(entries=entries)):
        repo = TradingCalendarRepository(db_session)
        await repo.refresh_range(start, end)

    old_rec = await repo.get_record(date(2026, 1, 3))
    old_batch = old_rec.refresh_batch_id
    assert old_batch is not None

    # 再用缺失响应刷新（应失败，不改旧行）
    bad_entries = _make_closed_range(start, end)
    del bad_entries[1]
    with _patch_factory(_FakeDataSource(entries=bad_entries)):
        with pytest.raises(ValueError):
            await repo.refresh_range(start, end)

    # 旧批次原样保留
    rec = await repo.get_record(date(2026, 1, 3))
    assert rec is not None
    assert rec.refresh_batch_id == old_batch


# ---------------------------------------------------------------------------
# refresh_range：upsert 覆盖旧批
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_range_upsert_overwrites_same_date(db_session):
    """同一日期重复刷新为 upsert 覆盖，不产生重复行，批次字段更新。"""
    start, end = date(2026, 4, 1), date(2026, 4, 3)
    entries = _make_closed_range(start, end, closed_days={date(2026, 4, 1)})
    with _patch_factory(_FakeDataSource(entries=entries)):
        repo = TradingCalendarRepository(db_session)
        await repo.refresh_range(start, end)

    first_rec = await repo.get_record(date(2026, 4, 1))
    first_batch = first_rec.refresh_batch_id
    assert first_rec.is_open is False  # 首次休市

    # 第二次刷新：把 4/1 改为开市
    entries2 = _make_closed_range(start, end)  # 全开市
    with _patch_factory(_FakeDataSource(entries=entries2)):
        repo2 = TradingCalendarRepository(db_session)
        await repo2.refresh_range(start, end)

    # bulk upsert（core insert）不刷新 ORM identity map；test_session 用
    # expire_on_commit=False，故需手动 expire 以读取 DB 最新值（生产环境
    # expire_on_commit=True 默认在 commit 后自动 expire，无此问题）。
    db_session.expire_all()

    # 不产生重复行
    rows = (await db_session.execute(
        select(TradingCalendarDay)
    )).scalars().all()
    assert len(rows) == 3, "upsert 不应产生重复行"

    # 覆盖：is_open 与 batch_id 更新为新批次
    rec = await repo.get_record(date(2026, 4, 1))
    assert rec.is_open is True
    assert rec.refresh_batch_id != first_batch


# ---------------------------------------------------------------------------
# refresh_range：Provider 抛错透传
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_range_propagates_provider_error(db_session):
    """Provider 抛错时 refresh_range 透传失败，不吞异常，不提交。"""
    start, end = date(2026, 1, 1), date(2026, 1, 3)
    fake = _FakeDataSource(exc=DataFetchError("provider down", source="Tushare"))

    repo = TradingCalendarRepository(db_session)
    with _patch_factory(fake):
        with pytest.raises(DataFetchError, match="provider down"):
            await repo.refresh_range(start, end)

    rows = (await db_session.execute(
        select(TradingCalendarDay)
    )).scalars().all()
    assert rows == [], "Provider 失败不应提交任何行"


# ---------------------------------------------------------------------------
# 只读查询
# ---------------------------------------------------------------------------


async def _seed(db_session, start, end, closed_days=None):
    entries = _make_closed_range(start, end, closed_days=closed_days)
    with _patch_factory(_FakeDataSource(entries=entries)):
        repo = TradingCalendarRepository(db_session)
        await repo.refresh_range(start, end)
    return repo


@pytest.mark.asyncio
async def test_get_record_returns_none_when_absent(db_session):
    repo = await _seed(db_session, date(2026, 1, 1), date(2026, 1, 3))
    assert await repo.get_record(date(2026, 2, 1)) is None
    assert (await repo.get_record(date(2026, 1, 2))) is not None


@pytest.mark.asyncio
async def test_get_trading_days_filters_and_sorts(db_session):
    # 1/1 休市, 1/2 开, 1/3 周末休, 1/4 周末休, 1/5 开
    repo = await _seed(
        db_session,
        date(2026, 1, 1),
        date(2026, 1, 5),
        closed_days={date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 4)},
    )
    days = await repo.get_trading_days(date(2026, 1, 1), date(2026, 1, 5))
    assert days == [date(2026, 1, 2), date(2026, 1, 5)]
    # 升序
    assert days == sorted(days)


@pytest.mark.asyncio
async def test_get_recent_open_days_desc_then_reverse(db_session):
    # 构造 5 个开市日（连续工作日）
    repo = await _seed(db_session, date(2026, 3, 2), date(2026, 3, 6))
    # 取最近 3 个开市日 → 升序 [3/4, 3/5, 3/6]
    days = await repo.get_recent_open_days(3)
    assert days == [date(2026, 3, 4), date(2026, 3, 5), date(2026, 3, 6)]
    assert days == sorted(days)


@pytest.mark.asyncio
async def test_get_recent_open_days_capped_at_n(db_session):
    """性能验收（架构 §8.1）：返回行数 ≤ n（断言 ≤250 用大区间）。"""
    # 构造约一年工作日
    repo = await _seed(db_session, date(2025, 1, 1), date(2025, 12, 31))
    days = await repo.get_recent_open_days(250)
    assert len(days) <= 250
    assert days == sorted(days)


@pytest.mark.asyncio
async def test_has_any_open_day(db_session):
    repo = await _seed(db_session, date(2026, 1, 1), date(2026, 1, 2))
    assert await repo.has_any_open_day() is True

    # 空表场景
    from sqlalchemy import delete

    await db_session.execute(delete(TradingCalendarDay))
    await db_session.commit()
    repo2 = TradingCalendarRepository(db_session)
    assert await repo2.has_any_open_day() is False
