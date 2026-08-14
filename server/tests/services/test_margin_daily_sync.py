"""融资融券早间增量同步入口单元测试（margin_daily_sync）

覆盖 ``run_margin_daily_sync`` 的守卫与缺口计算分支：

- 休市守卫：今日休市 → ``skipped_closed``，不建任务；
- 无缺口（db_max 已到上一交易日 / db_max 超前）→ ``noop``；
- 单日/多日缺口 → 以正确起止建 ``sync_market_margin`` 互斥任务；
- 空表 / db_max 早于窗口 → 起点收敛到窗口下界（近 14 自然日边界）；
- 日历刷新失败透传（不建任务）；互斥拒绝返回 ``mutex_rejected``。

日历仓库、TaskManager、session 均以假实现注入，不触库不触 Provider。
"""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.margin_daily_sync import (
    MARGIN_DAILY_LOOKBACK_DAYS,
    run_margin_daily_sync,
)


def _date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def _weekday_calendar(start: date, end: date, closed: set = frozenset()):
    """工作日开市、周末休市的简化日历（closed 可额外指定休市日）。"""
    return {
        d: (d.weekday() < 5 and d not in closed)
        for d in _date_range(start, end)
    }


class _FakeCalendarRepo:
    """TradingCalendarRepository 假实现：按开休市映射回答只读查询。"""

    def __init__(self, open_map, refresh_error=None):
        self._open_map = open_map
        self._refresh_error = refresh_error
        self.refresh_calls = []

    async def refresh_range(self, start, end):
        self.refresh_calls.append((start, end))
        if self._refresh_error is not None:
            raise self._refresh_error
        return (0, 0)

    async def get_record(self, day):
        if day not in self._open_map:
            return None
        return SimpleNamespace(cal_date=day, is_open=self._open_map[day])

    async def get_trading_days(self, start, end):
        return sorted(
            d for d, o in self._open_map.items() if o and start <= d <= end
        )


class _FakeTaskManager:
    """TaskManager 假实现：记录互斥建任务调用，可配置返回 None（互斥拒绝）。"""

    def __init__(self, session):
        self.session = session
        self.create_calls = []
        self.next_task = SimpleNamespace(task_id="task_fake_margin_001")

    async def create_exclusive_task(
        self, task_type, params=None, created_by=None, timeout_seconds=14400
    ):
        self.create_calls.append(
            {"task_type": task_type, "params": params}
        )
        return self.next_task


def _make_session(db_max):
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = db_max
    session.execute = AsyncMock(return_value=result)
    return session


# 2026-08 真实星期：08-15/08-16 为周六/周日，08-17 为周一。
TODAY = date(2026, 8, 17)
WINDOW_START = TODAY - timedelta(days=MARGIN_DAILY_LOOKBACK_DAYS - 1)
PREV_OPEN = date(2026, 8, 14)  # 上一交易日（周五）


@pytest.fixture
def fake_task_manager():
    manager = _FakeTaskManager(session=MagicMock())
    with patch(
        "src.services.margin_daily_sync.TaskManager",
        return_value=manager,
    ):
        yield manager


async def _run(session, open_map, today=TODAY, refresh_error=None):
    cal = _FakeCalendarRepo(open_map, refresh_error=refresh_error)
    with patch(
        "src.services.margin_daily_sync.TradingCalendarRepository",
        return_value=cal,
    ):
        return await run_margin_daily_sync(session, today=today), cal


class TestRunMarginDailySync:
    async def test_today_closed_skips_without_task(self, fake_task_manager):
        """今日休市 → skipped_closed，不建任务（T+1 次一交易日才发布）。"""
        today = date(2026, 8, 15)  # 周六
        open_map = _weekday_calendar(
            today - timedelta(days=MARGIN_DAILY_LOOKBACK_DAYS - 1), today
        )
        session = _make_session(db_max=PREV_OPEN)

        result, _ = await _run(session, open_map, today=today)

        assert result["status"] == "skipped_closed"
        assert fake_task_manager.create_calls == []

    async def test_calendar_refresh_failure_propagates(self, fake_task_manager):
        """日历刷新失败原样透传（不建任务，调用方放弃本轮）。"""
        open_map = _weekday_calendar(WINDOW_START, TODAY)
        session = _make_session(db_max=PREV_OPEN)

        with pytest.raises(ValueError, match="响应不完整"):
            await _run(
                session,
                open_map,
                refresh_error=ValueError("响应不完整"),
            )
        assert fake_task_manager.create_calls == []

    async def test_no_gap_when_db_max_is_prev_open(self, fake_task_manager):
        """db_max 已到上一交易日 → noop，不建任务。"""
        open_map = _weekday_calendar(WINDOW_START, TODAY)
        session = _make_session(db_max=PREV_OPEN)

        result, _ = await _run(session, open_map)

        assert result["status"] == "noop"
        assert fake_task_manager.create_calls == []

    async def test_no_gap_when_db_max_in_future(self, fake_task_manager):
        """db_max 超前（脏数据晚于上一交易日）→ 缺口为空 noop。"""
        open_map = _weekday_calendar(WINDOW_START, TODAY)
        session = _make_session(db_max=TODAY)

        result, _ = await _run(session, open_map)

        assert result["status"] == "noop"
        assert fake_task_manager.create_calls == []

    async def test_single_day_gap_creates_task(self, fake_task_manager):
        """上一交易日缺失（如周五数据周一早晨补）→ 单日任务 start==end。"""
        open_map = _weekday_calendar(WINDOW_START, TODAY)
        session = _make_session(db_max=date(2026, 8, 13))  # 周四

        result, _ = await _run(session, open_map)

        assert result["status"] == "created"
        assert result["start_date"] == "2026-08-14"
        assert result["end_date"] == "2026-08-14"
        assert result["trading_days"] == 1
        assert fake_task_manager.create_calls == [
            {
                "task_type": "sync_market_margin",
                "params": {
                    "start_date": "2026-08-14",
                    "end_date": "2026-08-14",
                },
            }
        ]

    async def test_multi_day_gap_covers_missed_days(self, fake_task_manager):
        """连续多日缺口（job 停用数日后恢复）→ 范围任务一次补齐。"""
        open_map = _weekday_calendar(WINDOW_START, TODAY)
        session = _make_session(db_max=date(2026, 8, 11))  # 周二

        result, _ = await _run(session, open_map)

        assert result["status"] == "created"
        assert result["start_date"] == "2026-08-12"
        assert result["end_date"] == "2026-08-14"
        assert result["trading_days"] == 3  # 08-12/13/14

    async def test_empty_table_bounded_by_window(self, fake_task_manager):
        """空表 → 只同步窗口内开市日（更早历史走管理面板 bulk）。"""
        open_map = _weekday_calendar(WINDOW_START, TODAY)
        session = _make_session(db_max=None)

        result, _ = await _run(session, open_map)

        assert result["status"] == "created"
        assert result["start_date"] == WINDOW_START.isoformat()
        assert result["end_date"] == PREV_OPEN.isoformat()
        assert result["trading_days"] == len(
            [d for d in _date_range(WINDOW_START, PREV_OPEN) if d.weekday() < 5]
        )

    async def test_stale_db_max_bounded_by_window(self, fake_task_manager):
        """db_max 早于窗口（停用超两周）→ 起点收敛到窗口下界，不追全历史。"""
        open_map = _weekday_calendar(WINDOW_START, TODAY)
        session = _make_session(db_max=date(2026, 7, 31))

        result, _ = await _run(session, open_map)

        assert result["status"] == "created"
        assert result["start_date"] == WINDOW_START.isoformat()
        assert result["end_date"] == PREV_OPEN.isoformat()

    async def test_mutex_rejected_returns_status(self, fake_task_manager):
        """互斥拒绝（已有同类任务 pending/running）→ 返回状态不抛错。"""
        open_map = _weekday_calendar(WINDOW_START, TODAY)
        session = _make_session(db_max=date(2026, 8, 13))
        fake_task_manager.next_task = None

        result, _ = await _run(session, open_map)

        assert result["status"] == "mutex_rejected"

    async def test_refresh_range_covers_lookback_window(self, fake_task_manager):
        """日历刷新窗口 = today-13 ~ today（闭区间 14 自然日）。"""
        open_map = _weekday_calendar(WINDOW_START, TODAY)
        session = _make_session(db_max=PREV_OPEN)

        _, cal = await _run(session, open_map)

        assert cal.refresh_calls == [(WINDOW_START, TODAY)]
