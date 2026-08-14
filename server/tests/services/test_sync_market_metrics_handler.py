"""sync_market_metrics handler 级单元测试（plan-05 review 建议项 2）。

补全 ``src.services.task_handlers.sync_market_metrics_task`` 的 handler 级分支覆盖，
原有测试只覆盖路由（tests/api/admin/test_init_market_metrics.py）、collector
（tests/test_data_updater.py）与执行器 fencing（tests/services/test_task_executor.py），
handler 本体的以下分支此前无单测：

- 正常多日路径：progress 按交易日口径更新、result 持久化结构
  ``{successCount,skippedCount,failedCount,dateResults,unprocessedDates}`` camelCase、
  ``failedCount == 0`` 不抛摘要。
- ``skippedCount > 0``：范围含非交易日（skippedCount = 自然日数 − 交易日数），
  非交易日不进计算（sync_date 仅对交易日调用）。
- 生命周期 preflight 每任务仅执行一次（``build_lifecycle_snapshot`` 调用次数 == 1）。
- 单日失败继续：``MarketMetricsSyncError`` / 其他异常 → 记为 failed、继续下一日；
  全部结束后持久化 result 且 ``failedCount > 0`` 抛一次摘要（成功日不回滚）。
- 停止分支：协程被 cancel（``CancelledError``）或 fence 拒绝（``FenceValidationError``）
  → ``finalize_*_with_result`` 保存 partial result + ``unprocessedDates``；未处理日
  不计入 ``failedCount``。

测试范式参照 ``tests/services/test_market_metrics_service.py``：部分真实 + 部分 mock。
真实部分：``TradingCalendarRepository`` / ``TaskManager``（真 PG，seed 本地日历 +
AsyncTask 行，校验 result 落库与终态）。mock 部分：``build_lifecycle_snapshot``、
``MarketMetricsService``（避免访问真实 Provider），以及 handler 内的
``_read_day_counts``（注入确定性计数，便于断言 dateResults 结构）。
"""

import asyncio
from contextlib import ExitStack, contextmanager
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.async_task import AsyncTask
from src.models.trading_calendar_day import TradingCalendarDay
from src.services.market_metrics_service import MarketMetricsSyncError
from src.services.task_fence import (
    FenceValidationError,
    OwnerGenerationGuard,
    TaskFenceContext,
    TaskFenceRegistry,
)
from src.services.task_handlers import sync_market_metrics_task
from src.services.task_manager import TaskManager


# ---------------------------------------------------------------------------
# 固定日历：2026-03-16 ~ 03-22（周一 ~ 周日）
# ---------------------------------------------------------------------------

MON, TUE, WED, THU, FRI, SAT, SUN = (
    date(2026, 3, 16), date(2026, 3, 17), date(2026, 3, 18),
    date(2026, 3, 19), date(2026, 3, 20), date(2026, 3, 21), date(2026, 3, 22),
)

EXPECTED_RESULT_KEYS = {
    "successCount", "skippedCount", "failedCount", "dateResults", "unprocessedDates",
}

# 成功日注入的确定性四类计数（_read_day_counts mock 用）。
_SUCCESS_COUNTS = {"expected": 3, "daily": 3, "suspended": 0, "final": 3}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_fence_registry():
    """每个测试前后清空进程级 TaskFenceRegistry，避免跨用例泄漏。"""
    TaskFenceRegistry.clear()
    yield
    TaskFenceRegistry.clear()


async def _seed_calendar(db_session, open_days, closed_days=()):
    """直接写入本地日历表（TradingCalendarDay）。"""
    for d in open_days:
        db_session.add(TradingCalendarDay(cal_date=d, is_open=True))
    for d in closed_days:
        db_session.add(TradingCalendarDay(cal_date=d, is_open=False))
    await db_session.commit()


async def _make_mm_task(
    db_session,
    *,
    task_id="task_handler_test",
    token="owner-token",
    cancel_at=None,
    timeout_at=None,
    status="running",
):
    """构造一条 sync_market_metrics 的 AsyncTask 行（真 PG）。"""
    task = AsyncTask(
        task_id=task_id,
        task_type="sync_market_metrics",
        status=status,
        max_retries=0,
        timeout_seconds=14400,
        executor_acquisition_token=token,
        cancel_requested_at=cancel_at,
        timeout_requested_at=timeout_at,
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    return task


def _wire_fence(task_id, token):
    """注册一个 active 的 TaskFenceContext（handler 第一步 TaskFenceRegistry.get 取用）。"""
    guard = OwnerGenerationGuard(token)
    guard.activate()
    ctx = TaskFenceContext(task_id, token, guard)
    TaskFenceRegistry.set(task_id, ctx)
    return ctx


def _service_mock(side_effects):
    """构造 mock MarketMetricsService 类：``MarketMetricsService(db)`` 返回可控实例。"""
    instance = MagicMock()
    instance.sync_date = AsyncMock(side_effect=list(side_effects))
    return MagicMock(return_value=instance), instance


def _spy(manager, method_name):
    """包装 manager 方法，记录调用参数同时保留真实行为。"""
    calls = []
    orig = getattr(manager, method_name)

    async def wrapper(*args, **kwargs):
        calls.append((args, kwargs))
        return await orig(*args, **kwargs)

    setattr(manager, method_name, wrapper)
    return calls


def _progress_sequence(progress_calls):
    """从 update_progress spy 调用记录提取 (progress, total) 序列。"""
    seq = []
    for args, kwargs in progress_calls:
        # update_progress(task_id, progress, total=None)
        progress = args[1] if len(args) > 1 else kwargs.get("progress")
        total = args[2] if len(args) > 2 else kwargs.get("total")
        seq.append((progress, total))
    return seq


@contextmanager
def _patched_internals(service_cls_mock, snapshot):
    """patch handler 在函数内 import 的 market_metrics_service 名称 + _read_day_counts。

    yield build_lifecycle_snapshot 的 AsyncMock，便于退出后断言调用次数。
    """
    build_mock = AsyncMock(return_value=snapshot)
    read_mock = AsyncMock(side_effect=lambda session, day: dict(_SUCCESS_COUNTS))
    with ExitStack() as stack:
        stack.enter_context(patch(
            "src.services.market_metrics_service.MarketMetricsService",
            service_cls_mock,
        ))
        stack.enter_context(patch(
            "src.services.market_metrics_service.build_lifecycle_snapshot",
            build_mock,
        ))
        stack.enter_context(patch(
            "src.services.task_handlers._read_day_counts",
            read_mock,
        ))
        yield build_mock


# ---------------------------------------------------------------------------
# 正常多日路径
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_normal_multi_day_success_progress_and_result_structure(db_session):
    """正常多日全部成功：progress 按交易日口径推进、result camelCase 持久化、不抛摘要。

    覆盖：
    - preflight（build_lifecycle_snapshot）每任务仅一次（调用次数 == 1）；
    - sync_date 仅对交易日调用（3 次）；
    - update_progress 序列 (0,3)→(1,3)→(2,3)→(3,3)（total = 交易日数）；
    - result 落库为 {successCount,skippedCount,failedCount,dateResults,unprocessedDates}
      camelCase，dateResults 三条 success、unprocessedDates 为空；
    - failedCount == 0 不抛异常。
    """
    await _seed_calendar(db_session, [MON, TUE, WED])
    task = await _make_mm_task(db_session)
    _wire_fence(task.task_id, task.executor_acquisition_token)

    snapshot = SimpleNamespace(records=("s1", "s2", "s3"))
    cls_mock, instance = _service_mock([None, None, None])  # 三日全成功

    manager = TaskManager(db_session)
    progress_calls = _spy(manager, "update_progress")

    with _patched_internals(cls_mock, snapshot) as build_mock:
        await sync_market_metrics_task(
            task.task_id,
            {"start_date": str(MON), "end_date": str(WED)},
            manager,
        )

    # preflight 仅一次
    assert build_mock.call_count == 1

    # sync_date 恰好 3 次，且传入的交易日升序
    called_days = [c.args[0] for c in instance.sync_date.call_args_list]
    assert called_days == [MON, TUE, WED]

    # progress 按交易日口径：total=3，0→3
    assert _progress_sequence(progress_calls) == [(0, 3), (1, 3), (2, 3), (3, 3)]

    # result 落库
    fresh = await manager.get_task(task.task_id)
    result = fresh.result
    assert set(result.keys()) == EXPECTED_RESULT_KEYS  # 无 snake_case 泄漏
    assert result["successCount"] == 3
    assert result["skippedCount"] == 0
    assert result["failedCount"] == 0
    assert result["unprocessedDates"] == []
    assert len(result["dateResults"]) == 3
    dr0 = result["dateResults"][0]
    assert dr0["tradeDate"] == str(MON)
    assert dr0["status"] == "success"
    assert dr0["expected"] == 3 and dr0["final"] == 3


# ---------------------------------------------------------------------------
# skippedCount > 0：范围含非交易日
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skipped_count_when_range_contains_non_trading_days(db_session):
    """范围含周末：skippedCount = 自然日数 − 交易日数，非交易日不进计算。

    范围 MON~SUN 共 7 个自然日；交易日 5（周一~周五），周末 2 天休市。
    """
    await _seed_calendar(
        db_session,
        open_days=[MON, TUE, WED, THU, FRI],
        closed_days=[SAT, SUN],
    )
    task = await _make_mm_task(db_session)
    _wire_fence(task.task_id, task.executor_acquisition_token)

    snapshot = SimpleNamespace(records=("s1",))
    cls_mock, instance = _service_mock([None, None, None, None, None])  # 5 个交易日

    manager = TaskManager(db_session)

    with _patched_internals(cls_mock, snapshot):
        await sync_market_metrics_task(
            task.task_id,
            {"start_date": str(MON), "end_date": str(SUN)},
            manager,
        )

    # 仅对 5 个交易日调用 sync_date（周末不进计算）
    called_days = [c.args[0] for c in instance.sync_date.call_args_list]
    assert called_days == [MON, TUE, WED, THU, FRI]

    fresh = await manager.get_task(task.task_id)
    result = fresh.result
    assert result["skippedCount"] == 2  # 7 自然日 − 5 交易日
    assert result["successCount"] == 5
    assert result["failedCount"] == 0


# ---------------------------------------------------------------------------
# 单日失败继续 + failedCount > 0 抛摘要
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_day_continues_then_raises_summary(db_session):
    """中间日 MarketMetricsSyncError：记为 failed、继续下一日；结束抛摘要。

    覆盖：
    - 失败日 dateResults 携带 status=failed + 异常四类计数 + reason；
    - 成功日不受影响（successCount=2）；
    - 全部结束持久化 result（unprocessedDates 空）；
    - failedCount > 0 抛一次 MarketMetricsSyncError 摘要。
    """
    await _seed_calendar(db_session, [MON, TUE, WED])
    task = await _make_mm_task(db_session)
    _wire_fence(task.task_id, task.executor_acquisition_token)

    snapshot = SimpleNamespace(records=("s1",))
    boom = MarketMetricsSyncError(
        "集合不平衡", expected=3, daily=2, suspended=0, final=2,
        problem_codes=["830001.BJ"],
    )
    cls_mock, instance = _service_mock([None, boom, None])  # day2 失败

    manager = TaskManager(db_session)

    with _patched_internals(cls_mock, snapshot):
        with pytest.raises(MarketMetricsSyncError, match="失败日"):
            await sync_market_metrics_task(
                task.task_id,
                {"start_date": str(MON), "end_date": str(WED)},
                manager,
            )

    # 三日均被调用（失败不中断）
    called_days = [c.args[0] for c in instance.sync_date.call_args_list]
    assert called_days == [MON, TUE, WED]

    fresh = await manager.get_task(task.task_id)
    result = fresh.result
    assert result["successCount"] == 2
    assert result["failedCount"] == 1
    assert result["unprocessedDates"] == []  # 范围已全部处理
    failed = next(d for d in result["dateResults"] if d["status"] == "failed")
    assert failed["tradeDate"] == str(TUE)
    assert failed["expected"] == 3 and failed["final"] == 2
    assert "集合不平衡" in failed["reason"]


@pytest.mark.asyncio
async def test_generic_exception_treated_as_failed_day(db_session):
    """非 MarketMetricsSyncError 的异常（网络/Provider）也记为单日失败并继续。

    reason 形如 ``<ExceptionType>: <msg>``，failedCount 计入，结束后抛摘要。
    """
    await _seed_calendar(db_session, [MON, TUE])
    task = await _make_mm_task(db_session)
    _wire_fence(task.task_id, task.executor_acquisition_token)

    snapshot = SimpleNamespace(records=("s1",))
    cls_mock, instance = _service_mock([RuntimeError("network boom"), None])

    manager = TaskManager(db_session)

    with _patched_internals(cls_mock, snapshot):
        with pytest.raises(MarketMetricsSyncError, match="失败日"):
            await sync_market_metrics_task(
                task.task_id,
                {"start_date": str(MON), "end_date": str(TUE)},
                manager,
            )

    called_days = [c.args[0] for c in instance.sync_date.call_args_list]
    assert called_days == [MON, TUE]

    fresh = await manager.get_task(task.task_id)
    result = fresh.result
    assert result["successCount"] == 1
    assert result["failedCount"] == 1
    failed = result["dateResults"][0]
    assert failed["tradeDate"] == str(MON)
    assert failed["status"] == "failed"
    assert failed["expected"] == 0 and failed["final"] == 0
    assert "RuntimeError: network boom" in failed["reason"]


# ---------------------------------------------------------------------------
# 停止分支：FenceValidationError → finalize_cancel 保存 partial result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stops_on_fence_validation_error_saves_partial_result(db_session):
    """第 2 交易日 sync_date 抛 FenceValidationError：保存 partial result 并落 cancelled。

    覆盖：
    - 未处理日 = trading_days[idx:]（含触发日及之后），不计入 failedCount；
    - _finalize_market_metrics_stop 按 cancel_requested_at 选首因 →
      finalize_cancel_with_result 写 cancelled + partial result（同事务）；
    - handler 正常返回（不 re-raise）。
    """
    await _seed_calendar(db_session, [MON, TUE, WED])
    task = await _make_mm_task(
        db_session, cancel_at=datetime.now(timezone.utc),
    )
    _wire_fence(task.task_id, task.executor_acquisition_token)

    snapshot = SimpleNamespace(records=("s1",))
    cls_mock, instance = _service_mock(
        [None, FenceValidationError("fence rejected: stop request pending")]
    )

    manager = TaskManager(db_session)

    with _patched_internals(cls_mock, snapshot):
        await sync_market_metrics_task(
            task.task_id,
            {"start_date": str(MON), "end_date": str(WED)},
            manager,
        )

    # 第 2 日触发即停，第 3 日不再处理
    called_days = [c.args[0] for c in instance.sync_date.call_args_list]
    assert called_days == [MON, TUE]

    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "cancelled"  # finalize_cancel_with_result 落终态
    result = fresh.result
    assert set(result.keys()) == EXPECTED_RESULT_KEYS
    assert result["successCount"] == 1
    assert result["failedCount"] == 0  # 未处理日不计入 failedCount
    # 未处理 = 触发日 + 之后（TUE, WED）
    assert result["unprocessedDates"] == [str(TUE), str(WED)]
    # 已成功日保留在 dateResults
    assert len(result["dateResults"]) == 1
    assert result["dateResults"][0]["tradeDate"] == str(MON)


@pytest.mark.asyncio
async def test_stops_on_fence_validation_error_timeout_branch(db_session):
    """停止首因为 timeout_requested_at → finalize_timeout_with_result 落 failed(task_timeout)。"""
    await _seed_calendar(db_session, [MON, TUE, WED])
    task = await _make_mm_task(
        db_session, timeout_at=datetime.now(timezone.utc),
    )
    _wire_fence(task.task_id, task.executor_acquisition_token)

    snapshot = SimpleNamespace(records=("s1",))
    cls_mock, _instance = _service_mock(
        [None, FenceValidationError("fence rejected: stop request pending")]
    )

    manager = TaskManager(db_session)

    with _patched_internals(cls_mock, snapshot):
        await sync_market_metrics_task(
            task.task_id,
            {"start_date": str(MON), "end_date": str(WED)},
            manager,
        )

    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "failed"
    assert fresh.error_message == "task_timeout"
    assert fresh.result["unprocessedDates"] == [str(TUE), str(WED)]


# ---------------------------------------------------------------------------
# 停止分支：CancelledError → finalize + re-raise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stops_on_cancelled_error_saves_partial_and_reraises(db_session):
    """第 2 交易日 sync_date 抛 asyncio.CancelledError：保存 partial result 后 re-raise。

    覆盖：
    - 未处理日进 unprocessedDates，不计入 failedCount；
    - _finalize_market_metrics_stop 仍被调用（落 cancelled + partial result）；
    - 原始 CancelledError 被 re-raise（交由执行器处理协程取消）。
    """
    await _seed_calendar(db_session, [MON, TUE, WED])
    task = await _make_mm_task(
        db_session, cancel_at=datetime.now(timezone.utc),
    )
    _wire_fence(task.task_id, task.executor_acquisition_token)

    snapshot = SimpleNamespace(records=("s1",))
    cls_mock, instance = _service_mock([None, asyncio.CancelledError()])

    manager = TaskManager(db_session)

    with _patched_internals(cls_mock, snapshot):
        with pytest.raises(asyncio.CancelledError):
            await sync_market_metrics_task(
                task.task_id,
                {"start_date": str(MON), "end_date": str(WED)},
                manager,
            )

    called_days = [c.args[0] for c in instance.sync_date.call_args_list]
    assert called_days == [MON, TUE]

    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "cancelled"
    result = fresh.result
    assert result["successCount"] == 1
    assert result["failedCount"] == 0
    assert result["unprocessedDates"] == [str(TUE), str(WED)]


# ---------------------------------------------------------------------------
# 缺少 fence context：取不到视为错误
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_fence_context_raises(db_session):
    """handler 缺少 TaskFenceContext（自动路径未注入）→ RuntimeError。"""
    await _seed_calendar(db_session, [MON, TUE])
    task = await _make_mm_task(db_session)
    # 故意不注册 fence context
    assert TaskFenceRegistry.get(task.task_id) is None

    manager = TaskManager(db_session)
    with pytest.raises(RuntimeError, match="TaskFenceContext"):
        await sync_market_metrics_task(
            task.task_id,
            {"start_date": str(MON), "end_date": str(TUE)},
            manager,
        )
