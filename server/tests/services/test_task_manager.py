"""plan-04 TaskManager fencing 基础设施测试。

覆盖 plan-04 §5 验收标准（任务系统测试为质量门）：

- AC-11（互斥底座）：并发两次 create_exclusive_task 仅一个成功（真 PG advisory lock）
- AC-02 状态机：pending→running→终态；取消 pending 立即 cancelled；running 取消只写
  cancel_requested_at，仍占互斥直至 finalize
- 条件停止写入首因胜出（request_cancel / request_timeout）
- 三个 finalize_with_result 原子终态 + token fencing 拒绝旧 token
- recover_stale_market_metrics_tasks 三分支（cancel/timeout/restarted）+ 双标记 critical
  + unprocessedDates + 计数只来自已提交 dateResults + IS DISTINCT FROM 含 NULL
- 接管竞态行锁二选一
- 其他任务类型不受影响（新列 NULL，取消/超时/重试语义不变）
- count_task_logs 真实 count
"""

import asyncio
import json
import uuid
from datetime import date, datetime, timezone, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.async_task import AsyncTask, AsyncTaskParam, AsyncTaskLog
from src.models.trading_calendar_day import TradingCalendarDay
from src.services.task_manager import (
    TaskManager,
    RESERVED_TASK_TYPES,
    MARKET_METRICS_LOCK_KEY,
)
from src.services.task_fence import (
    OwnerGenerationGuard,
    TaskFenceContext,
    TaskFenceRegistry,
    FenceValidationError,
)

MM = "sync_market_metrics"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

async def _make_mm_task(
    session: AsyncSession,
    *,
    status: str = "running",
    token: str = "old-token-aaaa",
    cancel_at: datetime | None = None,
    timeout_at: datetime | None = None,
    result: dict | None = None,
    started: datetime | None = None,
    start_date: str = "2026-03-16",
    end_date: str = "2026-03-18",
    task_id: str | None = None,
) -> AsyncTask:
    """直接插入一条指定状态的 sync_market_metrics 任务（含 start/end 参数）。"""
    task = AsyncTask(
        task_id=task_id or f"task_{uuid.uuid4().hex[:12]}",
        task_type=MM,
        status=status,
        max_retries=0,
        timeout_seconds=14400,
        executor_acquisition_token=token,
        cancel_requested_at=cancel_at,
        timeout_requested_at=timeout_at,
        result=result,
        started_at=started or datetime.now(timezone.utc),
    )
    session.add(task)
    await session.flush()
    session.add(AsyncTaskParam(task_id=task.task_id, key="start_date", value=json.dumps(start_date)))
    session.add(AsyncTaskParam(task_id=task.task_id, key="end_date", value=json.dumps(end_date)))
    await session.commit()
    return task


async def _seed_calendar(session: AsyncSession, days: list[date], open_days: set[date]):
    for d in days:
        session.add(TradingCalendarDay(cal_date=d, is_open=(d in open_days)))
    await session.commit()


def _second_factory(session: AsyncSession):
    """基于测试会话的 engine 构造第二个会话工厂（同 schema，NullPool 独立连接）。"""
    return async_sessionmaker(
        bind=session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# ---------------------------------------------------------------------------
# create_exclusive_task：互斥创建
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_exclusive_task_basic_max_retries_zero(db_session):
    """create_exclusive_task 创建的任务固定 max_retries=0，类型正确。"""
    manager = TaskManager(db_session)
    task = await manager.create_exclusive_task(
        MM, {"start_date": "2026-03-16", "end_date": "2026-03-18"}
    )
    assert task is not None
    assert task.task_type == MM
    assert task.max_retries == 0
    assert task.status == "pending"
    # 新增 fencing 字段初始为 NULL
    assert task.executor_acquisition_token is None
    assert task.cancel_requested_at is None
    assert task.timeout_requested_at is None
    assert task.result is None


@pytest.mark.asyncio
async def test_create_exclusive_task_rejects_when_running_exists(db_session):
    """已有同类型 running（含停止中/待 recovery）→ 返回 None。"""
    await _make_mm_task(db_session, status="running", token="owner-1")
    manager = TaskManager(db_session)
    task = await manager.create_exclusive_task(MM, {"start_date": "2026-03-16", "end_date": "2026-03-18"})
    assert task is None


@pytest.mark.asyncio
async def test_create_exclusive_task_rejects_when_pending_exists(db_session):
    """已有同类型 pending → 返回 None。"""
    await _make_mm_task(db_session, status="pending", token=None)
    manager = TaskManager(db_session)
    task = await manager.create_exclusive_task(MM, {"start_date": "2026-03-16", "end_date": "2026-03-18"})
    assert task is None


@pytest.mark.asyncio
async def test_create_exclusive_task_releases_mutex_after_terminal(db_session):
    """终态任务不占用互斥——可再次创建新任务。"""
    await _make_mm_task(db_session, status="completed", token="old")
    manager = TaskManager(db_session)
    task = await manager.create_exclusive_task(MM, {"start_date": "2026-03-16", "end_date": "2026-03-18"})
    assert task is not None


@pytest.mark.asyncio
async def test_create_exclusive_task_concurrent_only_one_succeeds(db_session):
    """AC-11：并发两次 create_exclusive_task 仅一个成功（真 PG advisory lock 事务级）。"""
    factory = _second_factory(db_session)
    # 两条独立连接的会话，在同一个测试 schema 上并发创建。
    async def try_create():
        async with factory() as s:
            m = TaskManager(s)
            return await m.create_exclusive_task(
                MM, {"start_date": "2026-03-16", "end_date": "2026-03-18"}
            )

    t1, t2 = await asyncio.gather(try_create(), try_create())
    results = [r for r in (t1, t2) if r is not None]
    assert len(results) == 1, "并发创建应只有一个成功"
    # 确认库里只有一条 pending/running
    rows = await db_session.execute(
        select(AsyncTask).where(
            AsyncTask.task_type == MM,
            AsyncTask.status.in_(["pending", "running"]),
        )
    )
    assert len(rows.scalars().all()) == 1


# ---------------------------------------------------------------------------
# 条件停止写入（首因胜出）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_request_cancel_writes_first_cause(db_session):
    """running 且无停止字段 → request_cancel 写入并返回 True。"""
    task = await _make_mm_task(db_session, status="running", token="owner")
    manager = TaskManager(db_session)
    assert await manager.request_cancel(task.task_id) is True
    fresh = await manager.get_task(task.task_id)
    assert fresh.cancel_requested_at is not None
    # running 取消只写标记，状态仍 running（仍占互斥直至 finalize）
    assert fresh.status == "running"


@pytest.mark.asyncio
async def test_request_cancel_second_cause_loses(db_session):
    """已有 timeout 标记 → request_cancel 不再写入（首因胜出）。"""
    now = datetime.now(timezone.utc)
    task = await _make_mm_task(db_session, status="running", token="owner", timeout_at=now)
    manager = TaskManager(db_session)
    assert await manager.request_cancel(task.task_id) is False
    fresh = await manager.get_task(task.task_id)
    assert fresh.cancel_requested_at is None


@pytest.mark.asyncio
async def test_request_timeout_first_cause(db_session):
    task = await _make_mm_task(db_session, status="running", token="owner")
    manager = TaskManager(db_session)
    assert await manager.request_timeout(task.task_id) is True
    fresh = await manager.get_task(task.task_id)
    assert fresh.timeout_requested_at is not None
    assert fresh.cancel_requested_at is None


@pytest.mark.asyncio
async def test_cancel_pending_immediate_cancelled(db_session):
    """AC-02：pending 任务取消立即置 cancelled（走 cancel_task，不写标记）。"""
    await _make_mm_task(db_session, status="pending", token=None)
    # 取一条 pending
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.status == "pending"))
    task = rows.scalars().one()
    manager = TaskManager(db_session)
    assert await manager.cancel_task(task.task_id) is True
    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "cancelled"
    assert fresh.cancelled_at is not None


# ---------------------------------------------------------------------------
# 三个 finalize_with_result：原子终态 + token fencing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_finalize_cancel_with_result(db_session):
    task = await _make_mm_task(db_session, status="running", token="owner-1")
    manager = TaskManager(db_session)
    ok = await manager.finalize_cancel_with_result(
        task.task_id, "owner-1", {"successCount": 3, "failedCount": 0}
    )
    assert ok is True
    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "cancelled"
    assert fresh.result == {"successCount": 3, "failedCount": 0}
    assert fresh.completed_at is not None


@pytest.mark.asyncio
async def test_finalize_timeout_with_result(db_session):
    task = await _make_mm_task(db_session, status="running", token="owner-1")
    manager = TaskManager(db_session)
    ok = await manager.finalize_timeout_with_result(task.task_id, "owner-1", {"failedCount": 1})
    assert ok is True
    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "failed"
    assert fresh.error_message == "task_timeout"


@pytest.mark.asyncio
async def test_finalize_restarted_with_result_no_token_check(db_session):
    """recovery 路径：finalize_restarted 不校验 token（旧 token 任务）。"""
    task = await _make_mm_task(db_session, status="running", token="stale-old-token")
    manager = TaskManager(db_session)
    ok = await manager.finalize_restarted_with_result(task.task_id, {"failedCount": 0})
    assert ok is True
    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "failed"
    assert fresh.error_message == "executor_restarted"


@pytest.mark.asyncio
async def test_finalize_fencing_rejects_old_token(db_session):
    """旧 token 的 finalize 被拒绝（fencing），任务保持 running 留给 recovery。"""
    task = await _make_mm_task(db_session, status="running", token="current-owner")
    task_id = task.task_id  # 捕获：finalize rollback 会 expire ORM 对象
    manager = TaskManager(db_session)
    ok = await manager.finalize_cancel_with_result(task_id, "stale-old-token", {})
    assert ok is False
    fresh = await manager.get_task(task_id)
    assert fresh.status == "running"


@pytest.mark.asyncio
async def test_finalize_rejects_non_running(db_session):
    task = await _make_mm_task(db_session, status="completed", token="owner")
    manager = TaskManager(db_session)
    ok = await manager.finalize_cancel_with_result(task.task_id, "owner", {})
    assert ok is False


# ---------------------------------------------------------------------------
# recover_stale_market_metrics_tasks：三分支 + 双标记 + 计数
# ---------------------------------------------------------------------------

async def _seed_range_calendar(db_session):
    days = [date(2026, 3, 16), date(2026, 3, 17), date(2026, 3, 18), date(2026, 3, 19)]
    open_days = {date(2026, 3, 16), date(2026, 3, 17), date(2026, 3, 18)}
    await _seed_calendar(db_session, days, open_days)


@pytest.mark.asyncio
async def test_recover_cancel_branch(db_session):
    """仅 cancel 标记 → cancelled + partial result。"""
    await _seed_range_calendar(db_session)
    now = datetime.now(timezone.utc)
    await _make_mm_task(
        db_session, status="running", token="stale-token",
        cancel_at=now,
        result={"dateResults": [{"tradeDate": "2026-03-16", "status": "success"}]},
    )
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_market_metrics_tasks("new-owner-token")
    assert stats["recovered"] == 1
    assert stats["cancel"] == 1
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MM))
    t = rows.scalars().one()
    assert t.status == "cancelled"
    assert t.result is not None
    assert t.result["successCount"] == 1
    # 未处理日 = [03-17, 03-18]（03-16 已处理），不计入 failedCount
    assert set(t.result["unprocessedDates"]) == {"2026-03-17", "2026-03-18"}
    assert t.result["failedCount"] == 0


@pytest.mark.asyncio
async def test_recover_timeout_branch(db_session):
    await _seed_range_calendar(db_session)
    now = datetime.now(timezone.utc)
    await _make_mm_task(
        db_session, status="running", token="stale-token",
        timeout_at=now,
        result={"dateResults": [
            {"tradeDate": "2026-03-16", "status": "success"},
            {"tradeDate": "2026-03-17", "status": "failed"},
        ]},
    )
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_market_metrics_tasks("new-owner-token")
    assert stats["timeout"] == 1
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MM))
    t = rows.scalars().one()
    assert t.status == "failed"
    assert t.error_message == "task_timeout"
    assert t.result["failedCount"] == 1
    assert t.result["successCount"] == 1
    assert t.result["unprocessedDates"] == ["2026-03-18"]


@pytest.mark.asyncio
async def test_recover_restarted_branch_no_stop_fields(db_session):
    """两字段均空 → failed(executor_restarted)。"""
    await _seed_range_calendar(db_session)
    await _make_mm_task(
        db_session, status="running", token="stale-token",
        result={"dateResults": [{"tradeDate": "2026-03-16", "status": "success"}]},
    )
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_market_metrics_tasks("new-owner-token")
    assert stats["restarted"] == 1
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MM))
    t = rows.scalars().one()
    assert t.status == "failed"
    assert t.error_message == "executor_restarted"


@pytest.mark.asyncio
async def test_recover_includes_null_token(db_session):
    """IS DISTINCT FROM 含 NULL：token 为 NULL 的遗留 running 也会被回收。"""
    await _seed_range_calendar(db_session)
    await _make_mm_task(db_session, status="running", token=None)
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_market_metrics_tasks("new-owner-token")
    assert stats["recovered"] == 1
    assert stats["restarted"] == 1


@pytest.mark.asyncio
async def test_recover_skips_current_token_task(db_session):
    """token 等于 current_token 的 running 不被回收（属于当前 owner）。"""
    await _seed_range_calendar(db_session)
    await _make_mm_task(db_session, status="running", token="current-owner")
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_market_metrics_tasks("current-owner")
    assert stats["recovered"] == 0
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MM))
    t = rows.scalars().one()
    assert t.status == "running"


@pytest.mark.asyncio
async def test_recover_releases_mutex_allowing_new_task(db_session):
    """三分支终态后释放互斥——可创建新任务。"""
    await _seed_range_calendar(db_session)
    await _make_mm_task(db_session, status="running", token="stale-token")
    manager = TaskManager(db_session)
    await manager.recover_stale_market_metrics_tasks("new-owner-token")
    # 现在可以创建新任务
    new_task = await manager.create_exclusive_task(
        MM, {"start_date": "2026-03-16", "end_date": "2026-03-18"}
    )
    assert new_task is not None


@pytest.mark.asyncio
async def test_recover_double_mark_chooses_earlier_cancel(db_session, caplog):
    """双标记不变量破坏：critical 告警 + 较早时间首因（同刻 cancel 优先）。"""
    await _seed_range_calendar(db_session)
    base = datetime.now(timezone.utc)
    cancel_earlier = base
    timeout_later = base + timedelta(seconds=5)
    await _make_mm_task(
        db_session, status="running", token="stale-token",
        cancel_at=cancel_earlier, timeout_at=timeout_later,
    )
    manager = TaskManager(db_session)
    with caplog.at_level("CRITICAL"):
        stats = await manager.recover_stale_market_metrics_tasks("new-owner-token")
    assert stats["double_mark"] == 1
    assert any("INVARIANT BROKEN" in r.message for r in caplog.records)
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MM))
    t = rows.scalars().one()
    # 较早时间 cancel 胜出 → cancelled
    assert t.status == "cancelled"


@pytest.mark.asyncio
async def test_recover_double_mark_timeout_when_timeout_earlier(db_session):
    await _seed_range_calendar(db_session)
    base = datetime.now(timezone.utc)
    await _make_mm_task(
        db_session, status="running", token="stale-token",
        cancel_at=base + timedelta(seconds=5), timeout_at=base,
    )
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_market_metrics_tasks("new-owner-token")
    assert stats["double_mark"] == 1
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MM))
    t = rows.scalars().one()
    assert t.status == "failed"
    assert t.error_message == "task_timeout"


@pytest.mark.asyncio
async def test_recover_counts_only_from_committed_dateresults(db_session):
    """unprocessedDates 准确且未处理日不计入 failedCount。"""
    await _seed_range_calendar(db_session)
    await _make_mm_task(
        db_session, status="running", token="stale-token",
        result={"dateResults": [{"tradeDate": "2026-03-16", "status": "failed"}]},
    )
    manager = TaskManager(db_session)
    await manager.recover_stale_market_metrics_tasks("new-owner-token")
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MM))
    t = rows.scalars().one()
    # 1 个 failed（已处理），2 个未处理不计入 failedCount
    assert t.result["failedCount"] == 1
    assert set(t.result["unprocessedDates"]) == {"2026-03-17", "2026-03-18"}


@pytest.mark.asyncio
async def test_recover_multiple_stale_independent_transactions(db_session):
    """多条 stale running 逐行独立回收，各自落正确终态。"""
    await _seed_range_calendar(db_session)
    now = datetime.now(timezone.utc)
    await _make_mm_task(db_session, status="running", token="t1", cancel_at=now, task_id="t_cancel")
    await _make_mm_task(db_session, status="running", token="t2", timeout_at=now, task_id="t_timeout")
    await _make_mm_task(db_session, status="running", token="t3", task_id="t_restart")
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_market_metrics_tasks("new-owner")
    assert stats["cancel"] == 1
    assert stats["timeout"] == 1
    assert stats["restarted"] == 1
    assert stats["recovered"] == 3


# ---------------------------------------------------------------------------
# TaskFenceContext：fencing 拒绝
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fence_context_rejects_after_guard_invalidate(db_session):
    """lock loss 后旧 guard 失效：lock_and_validate 抛 FenceValidationError。"""
    task = await _make_mm_task(db_session, status="running", token="token-1")
    guard = OwnerGenerationGuard("token-1")
    guard.activate()
    ctx = TaskFenceContext(task.task_id, "token-1", guard)
    # guard 仍 active → 校验通过（task token 匹配）
    await ctx.lock_and_validate(db_session)
    # 失效后再次校验 → 拒绝
    guard.invalidate()
    with pytest.raises(FenceValidationError):
        await ctx.lock_and_validate(db_session)


@pytest.mark.asyncio
async def test_fence_context_rejects_token_mismatch(db_session):
    """旧 token 的事务写被 fencing 拒绝（token 已被新 owner 回收）。"""
    task = await _make_mm_task(db_session, status="running", token="current-owner")
    guard = OwnerGenerationGuard("stale-old-token")
    guard.activate()
    ctx = TaskFenceContext(task.task_id, "stale-old-token", guard)
    with pytest.raises(FenceValidationError):
        await ctx.lock_and_validate(db_session)


@pytest.mark.asyncio
async def test_fence_context_rejects_when_stop_pending(db_session):
    """已有停止请求首因胜出 → 拒绝新业务写事务。"""
    now = datetime.now(timezone.utc)
    task = await _make_mm_task(db_session, status="running", token="owner", cancel_at=now)
    guard = OwnerGenerationGuard("owner")
    guard.activate()
    ctx = TaskFenceContext(task.task_id, "owner", guard)
    with pytest.raises(FenceValidationError):
        await ctx.lock_and_validate(db_session)


# ---------------------------------------------------------------------------
# 接管竞态：recovery 与旧事务共用 Task 行锁，二选一
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_takeover_race_row_lock_one_of_two(db_session):
    """recovery 先提交 → 旧 token finalize 被拒绝（行锁串行化二选一）。"""
    await _seed_range_calendar(db_session)
    task = await _make_mm_task(db_session, status="running", token="stale-old-token")
    task_id = task.task_id  # 捕获：recovery finalize rollback 会 expire ORM 对象

    # recovery 先回收（restarted 分支，因为无停止字段）
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_market_metrics_tasks("new-owner-token")
    assert stats["restarted"] == 1

    # 旧 token 的 finalize 尝试（已不是 running）→ 被拒绝
    ok = await manager.finalize_cancel_with_result(task_id, "stale-old-token", {})
    assert ok is False
    fresh = await manager.get_task(task_id)
    assert fresh.status == "failed"
    assert fresh.error_message == "executor_restarted"


# ---------------------------------------------------------------------------
# 其他任务类型不受影响
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_other_task_type_new_columns_null_and_legacy_semantics(db_session):
    """非 sync_market_metrics 任务：新列 NULL，取消/超时/重试语义不变。"""
    manager = TaskManager(db_session)
    task = await manager.create_task(
        task_type="init_stocks", params={"foo": "bar"}, max_retries=3
    )
    assert task.executor_acquisition_token is None
    assert task.cancel_requested_at is None
    assert task.timeout_requested_at is None
    assert task.result is None

    # 正常状态机：pending -> running -> completed
    assert await manager.start_task(task.task_id) is True
    assert await manager.complete_task(task.task_id, success=True) is True
    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "completed"
    assert fresh.executor_acquisition_token is None  # 仍 NULL


@pytest.mark.asyncio
async def test_other_task_type_cancel_uses_legacy_path(db_session):
    """非本类型 running 取消仍走 cancel_task 立即 cancelled（不走 request_cancel 标记）。"""
    manager = TaskManager(db_session)
    task = await manager.create_task(task_type="init_stocks", params={})
    await manager.start_task(task.task_id)
    assert await manager.cancel_task(task.task_id) is True
    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "cancelled"
    # request_cancel 对非本类型 running 仍可写入标记列？不——request_cancel 不区分类型。
    # 关键：其他类型走 cancel_task（立即 cancelled），不依赖 request_cancel。


@pytest.mark.asyncio
async def test_other_task_type_retry_semantics_unchanged(db_session):
    """非本类型保留重试语义（max_retries>0）。"""
    manager = TaskManager(db_session)
    task = await manager.create_task(task_type="init_stocks", params={}, max_retries=2)
    await manager.start_task(task.task_id)
    assert await manager.increment_retry(task.task_id) is True
    assert await manager.reset_for_retry(task.task_id) is True
    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "pending"
    assert fresh.retry_count == 1


@pytest.mark.asyncio
async def test_recovery_ignores_other_task_types(db_session):
    """recovery 只回收 sync_market_metrics，不碰其他类型 running。"""
    await _seed_range_calendar(db_session)
    manager = TaskManager(db_session)
    # 一个普通 running 任务
    other = await manager.create_task(task_type="init_stocks", params={})
    await manager.start_task(other.task_id)
    # 一个本类型 stale running
    await _make_mm_task(db_session, status="running", token="stale")

    stats = await manager.recover_stale_market_metrics_tasks("new-owner")
    assert stats["recovered"] == 1
    # 普通任务仍是 running，未被 recovery 触碰
    other_fresh = await manager.get_task(other.task_id)
    assert other_fresh.status == "running"


# ---------------------------------------------------------------------------
# count_task_logs 真实 count
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_count_task_logs_true_total(db_session):
    manager = TaskManager(db_session)
    task = await manager.create_task(task_type="init_stocks", params={})
    for i in range(5):
        await manager.log_message(task.task_id, "INFO", f"msg {i}")
    await manager.log_message(task.task_id, "WARNING", "warn")
    # create_task 自带 1 条 INFO 创建日志 + 5 INFO + 1 WARNING = 7
    total = await manager.count_task_logs(task.task_id)
    assert total == 7
    info_only = await manager.count_task_logs(task.task_id, level="INFO")
    assert info_only == 6


# ---------------------------------------------------------------------------
# to_dict result 透传
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_to_dict_passes_result(db_session):
    task = await _make_mm_task(
        db_session, status="running", token="owner",
        result={"successCount": 2, "failedCount": 1, "dateResults": [], "unprocessedDates": []},
    )
    # 通过 manager.get_task（selectinload params）加载后调用 to_dict
    manager = TaskManager(db_session)
    loaded = await manager.get_task(task.task_id)
    d = loaded.to_dict()
    assert d["result"]["successCount"] == 2
    assert d["result"]["failedCount"] == 1


@pytest.mark.asyncio
async def test_to_dict_result_none_for_other_types(db_session):
    """非本类型 to_dict result 为 None。"""
    manager = TaskManager(db_session)
    task = await manager.create_task(task_type="init_stocks", params={})
    loaded = await manager.get_task(task.task_id)
    assert loaded.to_dict()["result"] is None


@pytest.mark.asyncio
async def test_reserved_task_types_constant():
    assert "sync_market_metrics" in RESERVED_TASK_TYPES


@pytest.mark.asyncio
async def test_registry_set_get_pop():
    TaskFenceRegistry.clear()
    guard = OwnerGenerationGuard("t")
    ctx = TaskFenceContext("task_x", "t", guard)
    TaskFenceRegistry.set("task_x", ctx)
    assert TaskFenceRegistry.get("task_x") is ctx
    assert TaskFenceRegistry.pop("task_x") is ctx
    assert TaskFenceRegistry.get("task_x") is None
    TaskFenceRegistry.clear()


# ---------------------------------------------------------------------------
# admin/tasks.py：RESERVED 封堵 + result 字段 + logs total
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_create_rejects_reserved_task_type():
    """通用 POST 创建 sync_market_metrics 被拒并提示专用端点（架构 §7.3）。"""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch
    from src.api.admin.tasks import CreateTaskRequest, create_task

    request = CreateTaskRequest(
        task_type="sync_market_metrics",
        params={"start_date": "2026-03-16", "end_date": "2026-03-18"},
    )
    response = await create_task(
        request=request,
        session=AsyncMock(),
        _admin=SimpleNamespace(id="admin-1"),
    )
    assert response.success is False
    assert "保留任务类型" in response.message
    assert "market-metrics" in response.message


@pytest.mark.asyncio
async def test_admin_task_response_has_result_field():
    """TaskResponse / TaskDetailResponse 含 nullable result 字段。"""
    from src.api.admin.tasks import TaskResponse, TaskDetailResponse

    fields = set(TaskResponse.model_fields.keys())
    assert "result" in fields
    detail_fields = set(TaskDetailResponse.model_fields.keys())
    assert "result" in detail_fields


@pytest.mark.asyncio
async def test_admin_logs_total_uses_true_count(db_session):
    """GET /{task_id}/logs 的 total 为数据库真实 count（而非当前页 len）。"""
    from src.api.admin.tasks import get_task_logs

    manager = TaskManager(db_session)
    task = await manager.create_task(task_type="init_stocks", params={})
    # create_task 自带 1 条 INFO；再追加多条日志超过单页
    for i in range(5):
        await manager.log_message(task.task_id, "INFO", f"extra {i}")

    from fastapi import Query
    # 以默认 page_size=100 调用，total 应为真实全量计数
    response = await get_task_logs(
        task_id=task.task_id,
        level=None,
        page=1,
        page_size=100,
        session=db_session,
        _admin=None,
    )
    assert response.success is True
    # 1 条创建 + 5 条追加 = 6
    assert response.data.total == 6
    assert len(response.data.logs) == 6


# ===========================================================================
# 第 17 期 plan-04 增量：sync_market_margin 互斥 / finalize / recovery / 封堵
# ===========================================================================

from src.services.task_manager import (  # noqa: E402
    MARGIN_LOCK_KEY,
    MARGIN_OWNER_LOCK_KEY,
    MARKET_METRICS_OWNER_LOCK_KEY,
)

MARGIN = "sync_market_margin"


async def _make_margin_task(
    session: AsyncSession,
    *,
    status: str = "running",
    token: str | None = "old-token-bbbb",
    cancel_at: datetime | None = None,
    timeout_at: datetime | None = None,
    result: dict | None = None,
    started: datetime | None = None,
    start_date: str = "2026-08-11",
    end_date: str = "2026-08-13",
    task_id: str | None = None,
) -> AsyncTask:
    """直接插入一条指定状态的 sync_market_margin 任务（含 start/end 参数）。"""
    task = AsyncTask(
        task_id=task_id or f"task_{uuid.uuid4().hex[:12]}",
        task_type=MARGIN,
        status=status,
        max_retries=0,
        timeout_seconds=14400,
        executor_acquisition_token=token,
        cancel_requested_at=cancel_at,
        timeout_requested_at=timeout_at,
        result=result,
        started_at=started or datetime.now(timezone.utc),
    )
    session.add(task)
    await session.flush()
    session.add(AsyncTaskParam(task_id=task.task_id, key="start_date", value=json.dumps(start_date)))
    session.add(AsyncTaskParam(task_id=task.task_id, key="end_date", value=json.dumps(end_date)))
    await session.commit()
    return task


async def _seed_margin_calendar(db_session):
    """seed 2026-08-10(一)~08-14(五)：08-10~08-13 开市、08-14(五) 开市、08-15/16 周末休市。"""
    days = [
        date(2026, 8, 10), date(2026, 8, 11), date(2026, 8, 12),
        date(2026, 8, 13), date(2026, 8, 14), date(2026, 8, 15), date(2026, 8, 16),
    ]
    open_days = {date(2026, 8, 10), date(2026, 8, 11), date(2026, 8, 12), date(2026, 8, 13)}
    await _seed_calendar(db_session, days, open_days)


def test_margin_lock_keys_do_not_collide_with_market_metrics():
    """margin 锁 key 与 16 期 9001001/9001002 不冲突（plan §3 暂停条件防线）。"""
    assert MARGIN_LOCK_KEY == 9001003
    assert MARGIN_OWNER_LOCK_KEY == 9001004
    assert MARGIN_LOCK_KEY not in (MARKET_METRICS_LOCK_KEY, MARKET_METRICS_OWNER_LOCK_KEY)
    assert MARGIN_OWNER_LOCK_KEY not in (MARKET_METRICS_LOCK_KEY, MARKET_METRICS_OWNER_LOCK_KEY)


@pytest.mark.asyncio
async def test_margin_create_exclusive_task_basic_max_retries_zero(db_session):
    """margin 互斥创建：固定 max_retries=0，fencing 字段初始 NULL。"""
    manager = TaskManager(db_session)
    task = await manager.create_exclusive_task(
        MARGIN, {"start_date": "2026-08-11", "end_date": "2026-08-13"}
    )
    assert task is not None
    assert task.task_type == MARGIN
    assert task.max_retries == 0
    assert task.status == "pending"
    assert task.executor_acquisition_token is None
    assert task.result is None


@pytest.mark.asyncio
async def test_margin_create_exclusive_task_rejects_when_running(db_session):
    """同类型 margin running 存在 → 返回 None（AC-3）。"""
    await _make_margin_task(db_session, status="running", token="owner-1")
    manager = TaskManager(db_session)
    assert await manager.create_exclusive_task(
        MARGIN, {"start_date": "2026-08-11", "end_date": "2026-08-13"}
    ) is None


@pytest.mark.asyncio
async def test_margin_create_exclusive_task_rejects_when_pending(db_session):
    """同类型 margin pending 存在 → 返回 None（AC-3）。"""
    await _make_margin_task(db_session, status="pending", token=None)
    manager = TaskManager(db_session)
    assert await manager.create_exclusive_task(
        MARGIN, {"start_date": "2026-08-11", "end_date": "2026-08-13"}
    ) is None


@pytest.mark.asyncio
async def test_margin_mutex_independent_of_market_metrics(db_session):
    """mm running 不阻塞 margin 创建（创建互斥按类型分 key；AC-3/边界场景）。"""
    await _make_mm_task(db_session, status="running", token="mm-owner")
    manager = TaskManager(db_session)
    task = await manager.create_exclusive_task(
        MARGIN, {"start_date": "2026-08-11", "end_date": "2026-08-13"}
    )
    assert task is not None
    assert task.task_type == MARGIN


@pytest.mark.asyncio
async def test_margin_create_exclusive_task_concurrent_only_one_succeeds(db_session):
    """AC-3：并发两次 margin create_exclusive_task 仅一个成功（真 PG advisory lock）。"""
    factory = _second_factory(db_session)

    async def try_create():
        async with factory() as s:
            m = TaskManager(s)
            return await m.create_exclusive_task(
                MARGIN, {"start_date": "2026-08-11", "end_date": "2026-08-13"}
            )

    t1, t2 = await asyncio.gather(try_create(), try_create())
    results = [r for r in (t1, t2) if r is not None]
    assert len(results) == 1, "margin 并发创建应只有一个成功"
    rows = await db_session.execute(
        select(AsyncTask).where(
            AsyncTask.task_type == MARGIN,
            AsyncTask.status.in_(["pending", "running"]),
        )
    )
    assert len(rows.scalars().all()) == 1


@pytest.mark.asyncio
async def test_margin_finalize_cancel_with_result(db_session):
    """margin 停止分支：finalize_cancel_with_result 对 sync_market_margin 落 cancelled。"""
    task = await _make_margin_task(db_session, status="running", token="margin-owner")
    manager = TaskManager(db_session)
    ok = await manager.finalize_cancel_with_result(
        task.task_id, "margin-owner", {"successCount": 1, "failedCount": 0}
    )
    assert ok is True
    fresh = await manager.get_task(task.task_id)
    assert fresh.status == "cancelled"
    assert fresh.result == {"successCount": 1, "failedCount": 0}


@pytest.mark.asyncio
async def test_margin_finalize_fencing_rejects_old_token(db_session):
    """旧 token 的 margin finalize 被拒绝（fencing），任务保持 running 留给 recovery。"""
    task = await _make_margin_task(db_session, status="running", token="current-owner")
    task_id = task.task_id
    manager = TaskManager(db_session)
    ok = await manager.finalize_cancel_with_result(task_id, "stale-old-token", {})
    assert ok is False
    fresh = await manager.get_task(task_id)
    assert fresh.status == "running"


@pytest.mark.asyncio
async def test_margin_recover_cancel_branch(db_session):
    """margin recovery：cancel 分支 → cancelled + partial result，unprocessedDates 重建。"""
    await _seed_margin_calendar(db_session)
    now = datetime.now(timezone.utc)
    await _make_margin_task(
        db_session, status="running", token="stale-margin",
        cancel_at=now,
        result={"dateResults": [{"tradeDate": "2026-08-11", "status": "success"}]},
    )
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_fenced_tasks(MARGIN, "new-margin-owner")
    assert stats["recovered"] == 1
    assert stats["cancel"] == 1
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MARGIN))
    t = rows.scalars().one()
    assert t.status == "cancelled"
    assert t.result["successCount"] == 1
    # 范围 [08-11, 08-13] 三个交易日，08-11 已处理 → 未处理 08-12/08-13
    assert set(t.result["unprocessedDates"]) == {"2026-08-12", "2026-08-13"}
    assert t.result["failedCount"] == 0  # 未处理日不计入 failedCount


@pytest.mark.asyncio
async def test_margin_recover_restarted_branch_includes_null_token(db_session):
    """margin recovery：无停止字段（含 NULL token）→ failed(executor_restarted)。"""
    await _seed_margin_calendar(db_session)
    await _make_margin_task(db_session, status="running", token=None)
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_fenced_tasks(MARGIN, "new-margin-owner")
    assert stats["recovered"] == 1
    assert stats["restarted"] == 1
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MARGIN))
    t = rows.scalars().one()
    assert t.status == "failed"
    assert t.error_message == "executor_restarted"


@pytest.mark.asyncio
async def test_margin_recovery_parameterized_does_not_touch_market_metrics(db_session):
    """recover_stale_fenced_tasks 按 task_type 参数化：回收 margin 不碰 mm stale。"""
    await _seed_margin_calendar(db_session)
    await _make_mm_task(db_session, status="running", token="mm-stale", task_id="t_mm_stale")
    await _make_margin_task(db_session, status="running", token="margin-stale", task_id="t_margin_stale")
    manager = TaskManager(db_session)
    stats = await manager.recover_stale_fenced_tasks(MARGIN, "new-margin-owner")
    assert stats["recovered"] == 1
    # mm stale 不被 margin recovery 触碰
    mm_fresh = await manager.get_task("t_mm_stale")
    assert mm_fresh.status == "running"
    margin_fresh = await manager.get_task("t_margin_stale")
    assert margin_fresh.status == "failed"


@pytest.mark.asyncio
async def test_margin_recovery_releases_mutex_allowing_new_task(db_session):
    """margin 三分支终态后释放互斥——可创建新任务。"""
    await _seed_margin_calendar(db_session)
    await _make_margin_task(db_session, status="running", token="stale-margin")
    manager = TaskManager(db_session)
    await manager.recover_stale_fenced_tasks(MARGIN, "new-margin-owner")
    new_task = await manager.create_exclusive_task(
        MARGIN, {"start_date": "2026-08-11", "end_date": "2026-08-13"}
    )
    assert new_task is not None


@pytest.mark.asyncio
async def test_reserved_task_types_contains_margin():
    assert "sync_market_margin" in RESERVED_TASK_TYPES
    assert "sync_market_metrics" in RESERVED_TASK_TYPES


@pytest.mark.asyncio
async def test_admin_create_rejects_margin_reserved_task_type():
    """AC-8：通用 POST 创建 sync_market_margin 被拒并提示专用端点。"""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from src.api.admin.tasks import CreateTaskRequest, create_task

    request = CreateTaskRequest(
        task_type="sync_market_margin",
        params={"start_date": "2026-08-11", "end_date": "2026-08-13"},
    )
    response = await create_task(
        request=request,
        session=AsyncMock(),
        _admin=SimpleNamespace(id="admin-1"),
    )
    assert response.success is False
    assert "保留任务类型" in response.message
    assert "POST /api/v1/admin/init/margin" in response.message
