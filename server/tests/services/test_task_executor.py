"""plan-04 TaskExecutor fencing 基础设施测试。

覆盖 plan-04 §5 验收标准（架构 §9 Phase B.5 列出的执行器分支）：

- 同一 TaskExecutor 断线重连生成新 acquisition token（断言 token 变化）
- lock loss 后旧 guard 失效：旧 token 协程不能再开新 fence 事务（FenceValidationError）
- acquisition 后 recovery 接线：回收旧/NULL token 的本类型 running
- 并发 gate 前消费停止请求（cancel/timeout 胜出 → cancel 对应协程）
- 专属 owner lock：真 PG pg_try_advisory_lock，单 owner + standby
- 其他任务类型不受影响（执行器路径零行为变化）
"""

import asyncio
import json
import uuid
from datetime import date, datetime, timezone, timedelta

import pytest
from sqlalchemy import bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from src.models.async_task import AsyncTask, AsyncTaskParam
from src.models.trading_calendar_day import TradingCalendarDay
from src.services.task_manager import (
    TaskManager,
    MARGIN_OWNER_LOCK_KEY,
    MARKET_METRICS_OWNER_LOCK_KEY,
)
from src.services.task_executor import TaskExecutor
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

def _factory_for(session: AsyncSession):
    """基于测试会话 engine 构造会话工厂（同 schema）。"""
    return async_sessionmaker(
        bind=session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def _make_mm_task(
    session: AsyncSession,
    *,
    status: str = "running",
    token: str = "stale-token-aaaa",
    cancel_at: datetime | None = None,
    timeout_at: datetime | None = None,
    result: dict | None = None,
    started: datetime | None = None,
    start_date: str = "2026-03-16",
    end_date: str = "2026-03-18",
    task_id: str | None = None,
) -> AsyncTask:
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


async def _seed_calendar(session: AsyncSession):
    days = [date(2026, 3, 16), date(2026, 3, 17), date(2026, 3, 18)]
    open_days = {date(2026, 3, 16), date(2026, 3, 17), date(2026, 3, 18)}
    for d in days:
        session.add(TradingCalendarDay(cal_date=d, is_open=(d in open_days)))
    await session.commit()


def _new_executor(session: AsyncSession) -> TaskExecutor:
    """构造一个注入测试会话工厂的 TaskExecutor（不启动后台线程）。"""
    exec_ = TaskExecutor()
    exec_._session_factory = _factory_for(session)
    exec_._mm_lock_engine = None  # 真实 PG 测试单独注入
    return exec_


@pytest.fixture(autouse=True)
async def _release_owner_advisory_lock(db_session):
    """安全网：每个测试后释放可能泄漏的 owner session advisory lock。

    专属 owner lock 用会话级 pg_try_advisory_lock 绑定长连接；若断言失败前未显式
    _lose，连接被 GC 时可能滞后释放，污染后续测试。此处按 objid 终止残留持有者，
    保证测试隔离（仅测试用，不影响生产代码）。第 17 期 plan-04 增量：同时清理
    margin owner lock key（9001004）。
    """
    yield
    try:
        async with db_session.bind.connect() as c:
            await c.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_locks "
                    "WHERE locktype='advisory' AND objid IN :keys"
                ).bindparams(bindparam("keys", expanding=True)),
                {"keys": [MARKET_METRICS_OWNER_LOCK_KEY, MARGIN_OWNER_LOCK_KEY]},
            )
            await c.commit()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# token 轮换：断线重连生成新 token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_acquisition_generates_new_token_each_time(db_session):
    """同一 TaskExecutor 两次 acquisition 生成不同 token（断线重连必须换 token）。"""
    await _seed_calendar(db_session)
    exec_ = _new_executor(db_session)

    await exec_._on_mm_owner_acquired()
    token1 = exec_._mm_owner_token
    guard1 = exec_._mm_guard
    assert token1 is not None
    assert guard1.active is True
    assert exec_._mm_lock_held is True

    # 锁丢失
    await exec_._lose_mm_owner_lock()
    assert exec_._mm_lock_held is False
    assert exec_._mm_owner_token is None
    assert guard1.active is False  # 旧 guard 失效

    # 重连 → 新 acquisition → 新 token
    await exec_._on_mm_owner_acquired()
    token2 = exec_._mm_owner_token
    assert token2 is not None
    assert token2 != token1


# ---------------------------------------------------------------------------
# lock loss：旧 guard 失效，旧 token 协程不能再开新 fence 事务
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lock_loss_invalidates_guard_and_blocks_fence(db_session):
    """lock loss 后旧 guard 失效：TaskFenceContext.lock_and_validate 抛 FenceValidationError。"""
    await _seed_calendar(db_session)
    exec_ = _new_executor(db_session)
    await exec_._on_mm_owner_acquired()
    token = exec_._mm_owner_token
    guard = exec_._mm_guard

    task = await _make_mm_task(db_session, status="running", token=token)
    ctx = TaskFenceContext(task.task_id, token, guard)
    # guard 仍 active → 校验通过
    await ctx.lock_and_validate(db_session)

    # 锁丢失
    await exec_._lose_mm_owner_lock()
    assert guard.active is False
    # 旧 guard 的 fence 事务被拒绝
    with pytest.raises(FenceValidationError):
        await ctx.lock_and_validate(db_session)


@pytest.mark.asyncio
async def test_guard_invalidate_cancels_registered_coroutines(db_session):
    """OwnerGenerationGuard.invalidate() cancel 注册到本 guard 的全部协程。"""
    guard = OwnerGenerationGuard("t1")

    async def long_running():
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            raise

    task1 = asyncio.create_task(long_running())
    task2 = asyncio.create_task(long_running())
    guard.register_coroutine(task1)
    guard.register_coroutine(task2)
    guard.activate()

    guard.invalidate()
    # 等待 cancel 传播
    results = await asyncio.gather(task1, task2, return_exceptions=True)
    assert all(isinstance(r, asyncio.CancelledError) for r in results)


# ---------------------------------------------------------------------------
# recovery 接线：acquisition 回收旧/NULL token 的本类型 running
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_acquisition_recovers_stale_running(db_session):
    """acquisition 后 recovery 回收旧 token 的本类型 running（restarted 分支）。"""
    await _seed_calendar(db_session)
    await _make_mm_task(db_session, status="running", token="ancient-token")
    exec_ = _new_executor(db_session)

    await exec_._on_mm_owner_acquired()
    new_token = exec_._mm_owner_token

    # 旧 token 任务被回收为 failed(executor_restarted)
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MM))
    t = rows.scalars().one()
    assert t.status == "failed"
    assert t.error_message == "executor_restarted"
    assert t.executor_acquisition_token == "ancient-token"  # 终态保留原 token
    # 新 owner 的 guard 激活
    assert exec_._mm_guard.active is True


@pytest.mark.asyncio
async def test_acquisition_recovers_null_token_running(db_session):
    """acquisition 回收 token 为 NULL 的遗留 running（IS DISTINCT FROM 含 NULL）。"""
    await _seed_calendar(db_session)
    await _make_mm_task(db_session, status="running", token=None)
    exec_ = _new_executor(db_session)
    await exec_._on_mm_owner_acquired()
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MM))
    t = rows.scalars().one()
    assert t.status == "failed"
    assert t.error_message == "executor_restarted"


# ---------------------------------------------------------------------------
# 并发 gate 前消费停止请求
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consume_stop_cancels_coroutine_on_cancel(db_session):
    """cancel 标记胜出 → cancel 对应协程。"""
    now = datetime.now(timezone.utc)
    task = await _make_mm_task(db_session, status="running", token="owner", cancel_at=now)
    exec_ = _new_executor(db_session)
    exec_._mm_lock_held = True
    exec_._mm_owner_token = "owner"

    cancelled = asyncio.Event()

    async def handler_sim():
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    coro_task = asyncio.create_task(handler_sim())
    exec_._mm_task_coroutines[task.task_id] = coro_task

    manager = TaskManager(db_session)
    await exec_._consume_mm_stop_requests(manager)

    # await 让 cancel 传播到协程（except 块 set event 后 re-raise）
    with pytest.raises(asyncio.CancelledError):
        await coro_task
    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_consume_stop_timeout_when_timeout_only(db_session):
    """仅 timeout 标记 → cancel 协程（cause=timeout）。"""
    now = datetime.now(timezone.utc)
    task = await _make_mm_task(db_session, status="running", token="owner", timeout_at=now)
    exec_ = _new_executor(db_session)
    exec_._mm_lock_held = True
    exec_._mm_owner_token = "owner"

    async def handler_sim():
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            raise

    coro_task = asyncio.create_task(handler_sim())
    exec_._mm_task_coroutines[task.task_id] = coro_task

    manager = TaskManager(db_session)
    await exec_._consume_mm_stop_requests(manager)
    with pytest.raises(asyncio.CancelledError):
        await coro_task


@pytest.mark.asyncio
async def test_consume_stop_ignores_other_owner_tasks(db_session):
    """停止消费只处理当前 owner 的任务（旧 token 任务留给 recovery）。"""
    now = datetime.now(timezone.utc)
    await _make_mm_task(
        db_session, status="running", token="other-owner", cancel_at=now, task_id="t_other"
    )
    exec_ = _new_executor(db_session)
    exec_._mm_lock_held = True
    exec_._mm_owner_token = "current-owner"
    manager = TaskManager(db_session)
    # 不应抛错；旧 token 任务不受影响（无映射协程）
    await exec_._consume_mm_stop_requests(manager)


@pytest.mark.asyncio
async def test_consume_stop_no_op_without_stop_fields(db_session):
    """无停止字段 → 不 cancel 任何协程。"""
    task = await _make_mm_task(db_session, status="running", token="owner")
    exec_ = _new_executor(db_session)
    exec_._mm_lock_held = True
    exec_._mm_owner_token = "owner"

    async def handler_sim():
        await asyncio.sleep(0.05)

    coro_task = asyncio.create_task(handler_sim())
    exec_._mm_task_coroutines[task.task_id] = coro_task

    manager = TaskManager(db_session)
    await exec_._consume_mm_stop_requests(manager)
    await coro_task  # 正常完成，未被 cancel
    assert coro_task.done()


# ---------------------------------------------------------------------------
# 专属 owner lock：真 PG pg_try_advisory_lock 单 owner + standby
# ---------------------------------------------------------------------------

async def _make_dedicated_engine(session: AsyncSession):
    schema = (await session.execute(text("SELECT current_schema()"))).scalar()
    url = session.bind.url.render_as_string(hide_password=False)
    return create_async_engine(
        url,
        poolclass=NullPool,
        connect_args={"server_settings": {"search_path": schema}},
    )


@pytest.mark.asyncio
async def test_owner_lock_single_owner_and_standby(db_session):
    """真 PG：两个独立连接竞争 pg_try_advisory_lock，仅一个成为 owner，另一个 standby。"""
    eng1 = await _make_dedicated_engine(db_session)
    eng2 = await _make_dedicated_engine(db_session)
    exec1 = TaskExecutor()
    exec1._session_factory = _factory_for(db_session)
    exec1._mm_lock_engine = eng1
    exec2 = TaskExecutor()
    exec2._session_factory = _factory_for(db_session)
    exec2._mm_lock_engine = eng2
    try:
        # exec1 先获取 owner lock
        await exec1._maintain_mm_owner_lock()
        assert exec1._mm_lock_held is True
        assert exec1._mm_owner_token is not None

        # exec2 处于 standby（try-advisory-lock 返回 False）
        await exec2._maintain_mm_owner_lock()
        assert exec2._mm_lock_held is False
        assert exec2._mm_owner_token is None

        # exec1 丢失锁
        await exec1._lose_mm_owner_lock()
        assert exec1._mm_lock_held is False

        # exec2 现在可以获取
        await exec2._maintain_mm_owner_lock()
        assert exec2._mm_lock_held is True
        assert exec2._mm_owner_token is not None
    finally:
        # 显式释放 owner lock 连接（dispose 不会关闭 checked-out 连接）
        await exec1._lose_mm_owner_lock()
        await exec2._lose_mm_owner_lock()
        await eng1.dispose()
        await eng2.dispose()


@pytest.mark.asyncio
async def test_owner_lock_ping_detects_connection_loss(db_session):
    """持锁后连接 ping 失败视为锁丢失（_mm_lock_held → False, guard 失效）。"""
    eng = await _make_dedicated_engine(db_session)
    exec_ = TaskExecutor()
    exec_._session_factory = _factory_for(db_session)
    exec_._mm_lock_engine = eng
    try:
        await exec_._maintain_mm_owner_lock()
        assert exec_._mm_lock_held is True
        guard = exec_._mm_guard

        # 模拟连接断开：直接关闭底层连接，再 ping 应失败
        conn = exec_._mm_lock_conn
        await conn.close()
        await exec_._maintain_mm_owner_lock()
        assert exec_._mm_lock_held is False
        assert guard.active is False
    finally:
        await exec_._lose_mm_owner_lock()
        await eng.dispose()


# ---------------------------------------------------------------------------
# 其他任务类型不受影响
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_executor_dispatch_writes_token_only_for_mm(db_session):
    """start_task 仅本类型写 token；其他类型 token 保持 NULL。"""
    manager = TaskManager(db_session)
    other = await manager.create_task(task_type="init_stocks", params={}, max_retries=3)
    # 非 mm 派发：acquisition_token=None
    assert await manager.start_task(other.task_id, acquisition_token=None) is True
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_id == other.task_id))
    t = rows.scalars().one()
    assert t.executor_acquisition_token is None
    assert t.status == "running"


@pytest.mark.asyncio
async def test_executor_timeout_uses_request_timeout_for_mm(db_session):
    """本类型超时走 request_timeout（条件更新写标记），不直接置 failed。"""
    # 模拟一个已超时的 mm running 任务（started_at 早于 timeout）
    old = datetime.now(timezone.utc) - timedelta(seconds=10000)
    task = await _make_mm_task(db_session, status="running", token="owner", started=old)
    # timeout_seconds 默认 14400，started 10000s 前 → 未超时。改短 timeout
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_id == task.task_id))
    t = rows.scalars().one()
    t.timeout_seconds = 1
    await db_session.commit()

    exec_ = _new_executor(db_session)
    exec_._mm_lock_held = True
    exec_._mm_owner_token = "owner"
    manager = TaskManager(db_session)
    # _get_executable_tasks 对本类型超时走 request_timeout
    await exec_._get_executable_tasks(manager, limit=10)
    fresh = await manager.get_task(task.task_id)
    assert fresh.timeout_requested_at is not None
    assert fresh.status == "running"  # 仍 running，未直接 failed


@pytest.mark.asyncio
async def test_executor_timeout_legacy_path_for_other_types(db_session):
    """其他类型超时仍走 _handle_task_timeout（retry 或 failed），不写 timeout_requested_at。"""
    manager = TaskManager(db_session)
    other = await manager.create_task(task_type="init_stocks", params={}, max_retries=0)
    await manager.start_task(other.task_id)
    # 设短超时
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_id == other.task_id))
    t = rows.scalars().one()
    t.timeout_seconds = 1
    await db_session.commit()
    await asyncio.sleep(1.5)

    exec_ = _new_executor(db_session)
    await exec_._get_executable_tasks(manager, limit=10)
    fresh = await manager.get_task(other.task_id)
    # max_retries=0 → 直接 failed（超时）
    assert fresh.status == "failed"
    assert fresh.timeout_requested_at is None  # 其他类型不写本类型标记列


# ---------------------------------------------------------------------------
# Registry 清理
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fence_registry_clear_after_task():
    TaskFenceRegistry.clear()
    guard = OwnerGenerationGuard("t")
    ctx = TaskFenceContext("tid", "t", guard)
    TaskFenceRegistry.set("tid", ctx)
    assert TaskFenceRegistry.get("tid") is ctx
    TaskFenceRegistry.pop("tid")
    assert TaskFenceRegistry.get("tid") is None
    TaskFenceRegistry.clear()


# ===========================================================================
# 第 17 期 plan-04 增量：sync_market_margin owner lock / 派发 / 停止 / 超时
# ===========================================================================

MARGIN = "sync_market_margin"


async def _make_margin_task(
    session: AsyncSession,
    *,
    status: str = "running",
    token: str | None = "stale-margin-aaa",
    cancel_at: datetime | None = None,
    timeout_at: datetime | None = None,
    result: dict | None = None,
    started: datetime | None = None,
    task_id: str | None = None,
) -> AsyncTask:
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
    await session.commit()
    return task


@pytest.mark.asyncio
async def test_margin_acquisition_generates_new_token_each_time(db_session):
    """margin：同一 TaskExecutor 两次 acquisition 生成不同 token（断线重连换 token）。"""
    await _seed_calendar(db_session)
    exec_ = _new_executor(db_session)

    await exec_._on_margin_owner_acquired()
    token1 = exec_._margin_owner_token
    guard1 = exec_._margin_guard
    assert token1 is not None
    assert guard1.active is True
    assert exec_._margin_lock_held is True

    await exec_._lose_margin_owner_lock()
    assert exec_._margin_lock_held is False
    assert exec_._margin_owner_token is None
    assert guard1.active is False

    await exec_._on_margin_owner_acquired()
    token2 = exec_._margin_owner_token
    assert token2 is not None
    assert token2 != token1


@pytest.mark.asyncio
async def test_margin_acquisition_recovers_stale_running(db_session):
    """margin：acquisition 后 recovery 回收旧/NULL token 的本类型 running。"""
    await _seed_calendar(db_session)
    await _make_margin_task(db_session, status="running", token="ancient-margin-token")
    exec_ = _new_executor(db_session)

    await exec_._on_margin_owner_acquired()

    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_type == MARGIN))
    t = rows.scalars().one()
    assert t.status == "failed"
    assert t.error_message == "executor_restarted"
    assert exec_._margin_guard.active is True


@pytest.mark.asyncio
async def test_margin_owner_lock_single_owner_and_standby(db_session):
    """真 PG：margin owner lock（9001004）两连接竞争仅一个 owner，另一个 standby。"""
    eng1 = await _make_dedicated_engine(db_session)
    eng2 = await _make_dedicated_engine(db_session)
    exec1 = TaskExecutor()
    exec1._session_factory = _factory_for(db_session)
    exec1._margin_lock_engine = eng1
    exec2 = TaskExecutor()
    exec2._session_factory = _factory_for(db_session)
    exec2._margin_lock_engine = eng2
    try:
        await exec1._maintain_margin_owner_lock()
        assert exec1._margin_lock_held is True
        assert exec1._margin_owner_token is not None

        await exec2._maintain_margin_owner_lock()
        assert exec2._margin_lock_held is False
        assert exec2._margin_owner_token is None

        await exec1._lose_margin_owner_lock()
        await exec2._maintain_margin_owner_lock()
        assert exec2._margin_lock_held is True
    finally:
        await exec1._lose_margin_owner_lock()
        await exec2._lose_margin_owner_lock()
        await eng1.dispose()
        await eng2.dispose()


@pytest.mark.asyncio
async def test_margin_and_mm_owner_locks_independent(db_session):
    """边界场景：两把 owner lock 独立 key，同一实例可同时持有（互不阻塞）。"""
    eng = await _make_dedicated_engine(db_session)
    exec_ = TaskExecutor()
    exec_._session_factory = _factory_for(db_session)
    exec_._mm_lock_engine = eng
    exec_._margin_lock_engine = eng
    try:
        await exec_._maintain_mm_owner_lock()
        assert exec_._mm_lock_held is True
        # mm 已持 9001002 不影响 margin 获取 9001004
        await exec_._maintain_margin_owner_lock()
        assert exec_._margin_lock_held is True
        assert exec_._mm_owner_token != exec_._margin_owner_token
    finally:
        await exec_._lose_mm_owner_lock()
        await exec_._lose_margin_owner_lock()
        await eng.dispose()


@pytest.mark.asyncio
async def test_margin_consume_stop_cancels_coroutine(db_session):
    """margin：cancel 标记胜出 → cancel 对应协程。"""
    now = datetime.now(timezone.utc)
    task = await _make_margin_task(db_session, status="running", token="margin-owner", cancel_at=now)
    exec_ = _new_executor(db_session)
    exec_._margin_lock_held = True
    exec_._margin_owner_token = "margin-owner"

    cancelled = asyncio.Event()

    async def handler_sim():
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    coro_task = asyncio.create_task(handler_sim())
    exec_._margin_task_coroutines[task.task_id] = coro_task

    manager = TaskManager(db_session)
    await exec_._consume_margin_stop_requests(manager)

    with pytest.raises(asyncio.CancelledError):
        await coro_task
    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_margin_pending_skipped_without_owner_lock(db_session):
    """未持 margin owner lock 的实例不拉取 sync_market_margin pending。"""
    await _make_margin_task(db_session, status="pending", token=None)
    exec_ = _new_executor(db_session)  # 未持任何 owner lock
    manager = TaskManager(db_session)
    tasks = await exec_._get_executable_tasks(manager, limit=10)
    assert all(t.task_type != MARGIN for t in tasks)

    # 持有 margin owner lock 后可拉取
    exec_._margin_lock_held = True
    exec_._margin_owner_token = "margin-owner"
    tasks = await exec_._get_executable_tasks(manager, limit=10)
    assert [t.task_type for t in tasks] == [MARGIN]


@pytest.mark.asyncio
async def test_executor_dispatch_writes_margin_token_and_fence_ctx(db_session):
    """持有 margin owner lock 后派发：start_task 写 _margin_owner_token 为
    acquisition_token，并注入对应 guard 的 TaskFenceContext。"""
    manager = TaskManager(db_session)
    task = await manager.create_task(task_type=MARGIN, params={})
    exec_ = _new_executor(db_session)
    exec_._margin_lock_held = True
    exec_._margin_owner_token = "margin-owner-token"
    exec_._margin_guard = OwnerGenerationGuard("margin-owner-token")
    exec_._margin_guard.activate()

    seen = {}

    async def fake_handler(task_id, params, mgr):
        t = await mgr.get_task(task_id)
        seen["token"] = t.executor_acquisition_token
        seen["fence"] = TaskFenceRegistry.get(task_id)

    from unittest.mock import patch as _patch
    with _patch(
        "src.services.task_executor.TaskRegistry.get_handler", return_value=fake_handler
    ):
        await exec_._execute_task(task.task_id)

    assert seen["token"] == "margin-owner-token"
    assert seen["fence"] is not None
    assert seen["fence"].acquisition_token == "margin-owner-token"
    assert seen["fence"].guard is exec_._margin_guard
    # 任务完成（fake handler 正常返回）。populate_existing 绕过 db_session
    # 身份映射中 create_task 留下的未过期对象，读到执行器会话写入的终态。
    rows = await db_session.execute(
        select(AsyncTask)
        .where(AsyncTask.task_id == task.task_id)
        .execution_options(populate_existing=True)
    )
    fresh = rows.scalars().one()
    assert fresh.status == "completed"


@pytest.mark.asyncio
async def test_margin_timeout_uses_request_timeout(db_session):
    """margin 超时同样走 request_timeout 条件更新（不直接置 failed）。"""
    old = datetime.now(timezone.utc) - timedelta(seconds=10000)
    task = await _make_margin_task(db_session, status="running", token="margin-owner", started=old)
    rows = await db_session.execute(select(AsyncTask).where(AsyncTask.task_id == task.task_id))
    t = rows.scalars().one()
    t.timeout_seconds = 1
    await db_session.commit()

    exec_ = _new_executor(db_session)
    exec_._margin_lock_held = True
    exec_._margin_owner_token = "margin-owner"
    manager = TaskManager(db_session)
    await exec_._get_executable_tasks(manager, limit=10)
    fresh = await manager.get_task(task.task_id)
    assert fresh.timeout_requested_at is not None
    assert fresh.status == "running"  # 仍 running，未直接 failed


@pytest.mark.asyncio
async def test_margin_handler_failure_lands_failed_without_retry(db_session):
    """margin handler 抛失败摘要 → 执行器直接落 failed（max_retries=0 不自动重试）。"""
    from src.services.margin_service import MarginSyncError

    manager = TaskManager(db_session)
    task = await manager.create_task(task_type=MARGIN, params={}, max_retries=0)
    exec_ = _new_executor(db_session)
    exec_._margin_lock_held = True
    exec_._margin_owner_token = "margin-owner"
    exec_._margin_guard = OwnerGenerationGuard("margin-owner")
    exec_._margin_guard.activate()

    async def failing_handler(task_id, params, mgr):
        raise MarginSyncError(
            "sync_market_margin 范围同步存在失败日: success=1 failed=1"
        )

    from unittest.mock import patch as _patch
    with _patch(
        "src.services.task_executor.TaskRegistry.get_handler",
        return_value=failing_handler,
    ):
        await exec_._execute_task(task.task_id)

    rows = await db_session.execute(
        select(AsyncTask)
        .where(AsyncTask.task_id == task.task_id)
        .execution_options(populate_existing=True)
    )
    fresh = rows.scalars().one()
    assert fresh.status == "failed"
    assert "失败日" in (fresh.error_message or "")
    assert fresh.retry_count == 0  # fenced 类型失败不自动重试
