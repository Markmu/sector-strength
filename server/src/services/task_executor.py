"""异步任务执行器

负责轮询任务表并执行待处理的任务。
在后台线程中运行，支持并发控制、超时处理和重试机制。

plan-04 扩展：为 ``sync_market_metrics`` 增加专属 session advisory owner lock +
acquisition token fencing + orphan recovery。每次成功取得 owner lock 生成全新 UUID
token 与 OwnerGenerationGuard；未持锁不拉取本类型 pending；并发 gate 前消费本类型
cancel/timeout 胜出者并 cancel 对应协程；本类型失败不自动重试（max_retries=0）；
超时改走 request_timeout 条件更新。其他约 28 类任务保持原路径、零行为变化。

第 17 期 plan-04 扩展：并列为 ``sync_market_margin`` 提供同款专属 owner lock 状态族
（独立 key 9001004）与派发/停止/超时分派（按类型集合判断）；``sync_market_metrics``
路径行为逐项不变。
"""

import asyncio
import threading
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from src.db.database import AsyncSessionLocal, get_task_executor_engine, close_task_executor_engine
from src.services.task_manager import (
    TaskManager,
    MARKET_METRICS_OWNER_LOCK_KEY,
    MARGIN_OWNER_LOCK_KEY,
    _MARKET_METRICS_TYPE,
)
from src.services.task_fence import (
    FENCED_TASK_TYPES,
    OwnerGenerationGuard,
    TaskFenceContext,
    TaskFenceRegistry,
)
from src.models.async_task import AsyncTask

logger = logging.getLogger(__name__)

# 与 task_fence.FENCED_TASK_TYPES 对齐的模块级常量（共享分支按类型集合判断）。
_FENCED_TYPES = FENCED_TASK_TYPES
_MARGIN_TYPE = "sync_market_margin"


class TaskRegistry:
    """任务注册表，管理任务类型到处理函数的映射"""

    _handlers: Dict[str, Callable] = {}

    @classmethod
    def register(cls, task_type: str):
        """
        装饰器：注册任务处理函数

        使用方法:
            @TaskRegistry.register("init_sectors")
            async def handle_init_sectors(task_id, params):
                ...
        """
        def decorator(func: Callable):
            cls._handlers[task_type] = func
            return func
        return decorator

    @classmethod
    def get_handler(cls, task_type: str) -> Optional[Callable]:
        """获取任务处理函数"""
        return cls._handlers.get(task_type)

    @classmethod
    def list_registered_tasks(cls) -> list:
        """列出所有已注册的任务类型"""
        return list(cls._handlers.keys())


class TaskExecutor:
    """
    任务执行器

    在后台线程中运行，定期轮询数据库中的待处理任务并执行。
    支持并发控制、超时处理和重试机制。
    使用独立的数据库引擎以避免与主 event loop 的冲突。
    """

    def __init__(
        self,
        poll_interval: float = 1.0,
        max_concurrent_tasks: int = 2,
    ):
        """
        初始化任务执行器

        Args:
            poll_interval: 轮询间隔（秒）
            max_concurrent_tasks: 最大并发任务数
        """
        self.poll_interval = poll_interval
        self.max_concurrent_tasks = max_concurrent_tasks
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # 跟踪正在运行的任务，防止竞态条件
        self._running_tasks: set[asyncio.Task] = set()
        # 任务执行器专用的数据库会话工厂
        self._session_factory = None
        # plan-04：sync_market_metrics 专属 owner lock 状态
        # 持有 owner lock 的独立长连接（会话级 pg_try_advisory_lock 绑定该连接）
        self._mm_lock_conn = None
        # owner lock 连接所用引擎（默认复用执行器引擎；测试可注入）
        self._mm_lock_engine = None
        self._mm_lock_held = False
        self._mm_owner_token: Optional[str] = None
        self._mm_guard: Optional[OwnerGenerationGuard] = None
        # 本类型 task_id -> asyncio.Task 映射（停止消费时 cancel 对应协程）
        self._mm_task_coroutines: Dict[str, asyncio.Task] = {}
        self._mm_standby_logged = False
        # 第 17 期 plan-04：sync_market_margin 专属 owner lock 状态族（与 _mm_* 同款，
        # 独立 key 9001004，与 market_metrics 互不阻塞）
        self._margin_lock_conn = None
        self._margin_lock_engine = None
        self._margin_lock_held = False
        self._margin_owner_token: Optional[str] = None
        self._margin_guard: Optional[OwnerGenerationGuard] = None
        # 本类型 task_id -> asyncio.Task 映射（停止消费时 cancel 对应协程）
        self._margin_task_coroutines: Dict[str, asyncio.Task] = {}
        self._margin_standby_logged = False

    def _lock_held_for(self, task_type: str) -> bool:
        """按任务类型判断是否持有对应的专属 owner lock。"""
        if task_type == _MARKET_METRICS_TYPE:
            return self._mm_lock_held
        if task_type == _MARGIN_TYPE:
            return self._margin_lock_held
        return True  # 非 fenced 类型不受 owner lock 约束

    def _owner_token_for(self, task_type: str) -> Optional[str]:
        """按任务类型取对应的 owner acquisition token（未持锁返回 None）。"""
        if task_type == _MARKET_METRICS_TYPE:
            return self._mm_owner_token if self._mm_lock_held else None
        if task_type == _MARGIN_TYPE:
            return self._margin_owner_token if self._margin_lock_held else None
        return None

    def start(self):
        """启动任务执行器（在后台线程中运行）"""
        if self._running:
            logger.warning("TaskExecutor is already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("TaskExecutor started")

    def stop(self, timeout: float = 30.0):
        """
        停止任务执行器

        Args:
            timeout: 等待超时时间（秒）
        """
        if not self._running:
            return

        logger.info("Stopping TaskExecutor...")
        self._running = False

        if self._thread:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning(f"TaskExecutor did not stop within {timeout}s")

        logger.info("TaskExecutor stopped")

    def _run_loop(self):
        """后台线程的主循环"""
        # 创建新的事件循环
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # 在这个线程的 event loop 中创建独立的数据库引擎
        _engine, self._session_factory = get_task_executor_engine()
        # plan-04：owner lock 复用执行器引擎（独立长连接）
        self._mm_lock_engine = _engine
        self._margin_lock_engine = _engine
        logger.info("TaskExecutor database engine initialized in background thread")

        try:
            self._loop.run_until_complete(self._wait_for_database_ready())
            self._loop.run_until_complete(self._poll_and_execute())
        except Exception as e:
            logger.exception("TaskExecutor loop error")
        finally:
            # 先收敛正在执行的任务，再关闭数据库引擎，避免连接被动断开
            self._loop.run_until_complete(self._shutdown_running_tasks())
            # plan-04：释放 owner lock 连接（若有）
            self._loop.run_until_complete(self._close_mm_lock_connection())
            self._loop.run_until_complete(self._close_margin_lock_connection())
            # 清理数据库引擎
            self._loop.run_until_complete(close_task_executor_engine())
            self._loop.close()
            logger.info("TaskExecutor database engine closed")

    async def _poll_and_execute(self):
        """轮询并执行任务"""
        while self._running:
            try:
                # 清理已完成的任务
                self._running_tasks = {task for task in self._running_tasks if not task.done()}

                # 使用任务执行器专用的会话工厂
                if self._session_factory is None:
                    logger.error("Session factory not initialized")
                    await asyncio.sleep(self.poll_interval)
                    continue

                # plan-04：维护 sync_market_metrics 专属 owner lock（try-acquire / ping）
                await self._maintain_mm_owner_lock()
                # 第 17 期 plan-04：并列维护 sync_market_margin 专属 owner lock
                await self._maintain_margin_owner_lock()

                async with self._session_factory() as db:
                    manager = TaskManager(db)

                    # plan-04：并发 gate 前消费本类型 stop 请求（cancel/timeout 胜出者）
                    # 两把锁各自判断，互不阻塞。
                    if self._mm_lock_held and self._mm_owner_token:
                        await self._consume_mm_stop_requests(manager)
                    if self._margin_lock_held and self._margin_owner_token:
                        await self._consume_margin_stop_requests(manager)

                    # 检查并发限制（包括本地正在运行的任务）
                    running_count = await manager.get_running_tasks_count()
                    local_running = len(self._running_tasks)
                    if running_count + local_running >= self.max_concurrent_tasks:
                        await asyncio.sleep(self.poll_interval)
                        continue

                    # 获取待处理任务
                    tasks_to_execute = await self._get_executable_tasks(
                        manager,
                        self.max_concurrent_tasks - running_count - local_running
                    )

                    # 执行任务并跟踪
                    for task in tasks_to_execute:
                        # plan-04：未持对应 owner lock 不拉取 fenced 类型 pending
                        # （其他类型不受影响；两把锁按类型各自判断）
                        if (
                            task.task_type in _FENCED_TYPES
                            and not self._lock_held_for(task.task_type)
                        ):
                            continue
                        task_coro = self._execute_task(task.task_id)
                        async_task = asyncio.create_task(task_coro)
                        self._running_tasks.add(async_task)
                        # 添加完成回调以清理
                        async_task.add_done_callback(lambda t: self._running_tasks.discard(t))
                        # plan-04：fenced 类型维护 task_id -> asyncio.Task 映射
                        if task.task_type == _MARKET_METRICS_TYPE:
                            self._mm_task_coroutines[task.task_id] = async_task
                            async_task.add_done_callback(
                                lambda t, tid=task.task_id: self._mm_task_coroutines.pop(tid, None)
                            )
                        elif task.task_type == _MARGIN_TYPE:
                            self._margin_task_coroutines[task.task_id] = async_task
                            async_task.add_done_callback(
                                lambda t, tid=task.task_id: self._margin_task_coroutines.pop(tid, None)
                            )

            except Exception as e:
                if self._is_retryable_db_error(e):
                    logger.warning(
                        "Poll loop DB transient error: %s. Will retry after %.1fs",
                        str(e),
                        self.poll_interval,
                    )
                    await self._reset_session_factory()
                else:
                    logger.exception("Error in poll loop")

            await asyncio.sleep(self.poll_interval)

    async def _get_executable_tasks(
        self,
        manager: TaskManager,
        limit: int,
    ) -> list[AsyncTask]:
        """
        获取可执行的任务（检查超时和重试）

        Args:
            manager: 任务管理器
            limit: 数量限制

        Returns:
            可执行的任务列表
        """
        tasks = []

        # 检查正在运行的任务是否超时
        running_tasks = await manager.list_tasks(status="running", limit=limit)
        for task in running_tasks:
            if await manager.check_task_timeout(task.task_id):
                if task.task_type in _FENCED_TYPES:
                    # plan-04：fenced 类型超时改走条件更新 request_timeout
                    # （不再直接置 failed）；market_metrics 保持原日志口径。
                    label = (
                        "market_metrics"
                        if task.task_type == _MARKET_METRICS_TYPE
                        else "margin"
                    )
                    logger.warning(f"Task {task.task_id} timed out ({label})")
                    await manager.request_timeout(task.task_id)
                else:
                    logger.warning(f"Task {task.task_id} timed out")
                    await self._handle_task_timeout(manager, task)

        # 空闲轮询时不再刷日志；仅在确有任务时记录
        if running_tasks:
            logger.info(f"Found {len(running_tasks)} running tasks")

        # 获取待处理任务
        pending = await manager.get_pending_tasks(limit=limit)
        for task in pending:
            # plan-04：未持对应 owner lock 时跳过 fenced 类型 pending
            # （_poll_and_execute 兜底再过滤一次）
            if (
                task.task_type in _FENCED_TYPES
                and not self._lock_held_for(task.task_type)
            ):
                continue
            # 检查是否需要延迟重试
            if task.retry_count > 0:
                retry_delay = min(2 ** task.retry_count, 60)  # 指数退避，最多60秒
                if task.started_at:
                    elapsed = (datetime.now(timezone.utc) - task.started_at).total_seconds()
                    if elapsed < retry_delay:
                        continue

            tasks.append(task)
        if tasks:
            logger.info(f"Found {len(tasks)} tasks to execute")

        return tasks

    async def _execute_task(self, task_id: str):
        """
        执行单个任务

        Args:
            task_id: 任务ID
        """
        # 使用任务执行器专用的会话工厂
        if self._session_factory is None:
            logger.error(f"Session factory not initialized, cannot execute task {task_id}")
            return

        async with self._session_factory() as db:
            manager = TaskManager(db)
            task = None
            is_mm = False
            is_margin = False
            is_fenced = False

            try:
                # 获取任务信息
                task = await manager.get_task(task_id)
                if not task:
                    logger.warning(f"Task {task_id} not found")
                    return

                # 检查任务状态
                if task.status != "pending":
                    return

                is_mm = task.task_type == _MARKET_METRICS_TYPE
                is_margin = task.task_type == _MARGIN_TYPE
                is_fenced = task.task_type in _FENCED_TYPES

                # plan-04：fenced 类型派发——同事务写 acquisition token
                # （仅当前对应 owner；按类型取对应 owner token）
                acquisition_token = (
                    self._owner_token_for(task.task_type) if is_fenced else None
                )
                await manager.start_task(task_id, acquisition_token=acquisition_token)

                # plan-04：注入 TaskFenceContext 供 handler 取用（不改三参签名）
                if is_mm and self._mm_guard is not None and self._mm_owner_token:
                    ctx = TaskFenceContext(
                        task_id, self._mm_owner_token, self._mm_guard
                    )
                    TaskFenceRegistry.set(task_id, ctx)
                if (
                    is_margin
                    and self._margin_guard is not None
                    and self._margin_owner_token
                ):
                    margin_ctx = TaskFenceContext(
                        task_id, self._margin_owner_token, self._margin_guard
                    )
                    TaskFenceRegistry.set(task_id, margin_ctx)

                # 获取任务处理器
                handler = TaskRegistry.get_handler(task.task_type)
                if not handler:
                    error_msg = f"No handler registered for task type: {task.task_type}"
                    logger.error(error_msg)
                    await manager.complete_task(task_id, success=False, error_message=error_msg)
                    return

                # 获取任务参数
                params = await manager.get_task_params(task_id)

                # 执行任务
                logger.info(
                    f"Executing task {task_id} (type: {task.task_type})",
                    extra={
                        "task_id": task_id,
                        "task_type": task.task_type,
                        "retry_count": task.retry_count,
                    },
                )
                await handler(task_id, params, manager)

                # 标记任务完成
                await manager.complete_task(task_id, success=True)
                logger.info(f"Task {task_id} completed successfully")

            except asyncio.CancelledError:
                if is_fenced:
                    # plan-04：fenced 类型（sync_market_metrics / sync_market_margin）
                    # 停止终态由 handler finalize_with_result 或 recovery 落地；
                    # 不在此立即置 cancelled（避免绕过 fence/原子终态）。
                    logger.info(
                        "Task %s coroutine cancelled; stop finalize deferred to handler/recovery",
                        task_id,
                    )
                    raise
                # 任务被取消 - 设置正确的取消状态
                logger.info(f"Task {task_id} was cancelled")
                await manager.cancel_task(task_id)

            except Exception as e:
                logger.error(
                    f"Error executing task {task_id}: {e}",
                    extra={
                        "task_id": task_id,
                        "task_type": getattr(task, "task_type", None),
                        "retry_count": getattr(task, "retry_count", None),
                        "error_class": type(e).__name__,
                    },
                )

                if is_fenced:
                    # plan-04：fenced 类型固定 max_retries=0，失败不自动重试，直接落 failed。
                    await manager.complete_task(task_id, success=False, error_message=str(e))
                else:
                    # 检查是否需要重试
                    task = await manager.get_task(task_id)
                    if task and task.retry_count < task.max_retries:
                        await manager.increment_retry(task_id)
                        await manager.reset_for_retry(task_id)
                        logger.info(
                            f"Task {task_id} will be retried (attempt {task.retry_count + 1}/{task.max_retries})",
                            extra={
                                "task_id": task_id,
                                "task_type": task.task_type,
                                "retry_count": task.retry_count + 1,
                                "error_class": type(e).__name__,
                            },
                        )
                    else:
                        await manager.complete_task(task_id, success=False, error_message=str(e))
            finally:
                if is_fenced:
                    TaskFenceRegistry.pop(task_id)

    async def _handle_task_timeout(self, manager: TaskManager, task: AsyncTask):
        """
        处理任务超时

        Args:
            manager: 任务管理器
            task: 超时的任务
        """
        # 检查是否需要重试
        if task.retry_count < task.max_retries:
            await manager.increment_retry(task.task_id)
            await manager.reset_for_retry(task.task_id)
            logger.info(
                f"Task {task.task_id} timed out, will be retried (attempt {task.retry_count + 1}/{task.max_retries})",
                extra={
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "retry_count": task.retry_count + 1,
                    "error_class": "TimeoutError",
                },
            )
        else:
            await manager.complete_task(
                task.task_id,
                success=False,
                error_message=f"Task timed out after {task.timeout_seconds} seconds"
            )

    async def _shutdown_running_tasks(self, timeout: float = 10.0):
        """关闭前收敛后台任务，避免数据库连接在任务中途被销毁。"""
        self._running_tasks = {task for task in self._running_tasks if not task.done()}
        if not self._running_tasks:
            return

        logger.info(f"Shutting down {len(self._running_tasks)} running task(s)")
        for task in self._running_tasks:
            task.cancel()

        try:
            await asyncio.wait_for(
                asyncio.gather(*self._running_tasks, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout while shutting down running tasks after {timeout}s")
        finally:
            self._running_tasks.clear()

    async def _reset_session_factory(self):
        """连接异常后重建任务执行器的数据库引擎和会话工厂。"""
        logger.warning("Resetting task executor database engine after connection loss")
        await close_task_executor_engine()
        _engine, self._session_factory = get_task_executor_engine()
        self._mm_lock_engine = _engine
        self._margin_lock_engine = _engine

    # ------------------------------------------------------------------
    # plan-04：sync_market_metrics 专属 owner lock / token / guard / recovery
    # ------------------------------------------------------------------

    async def _ensure_mm_lock_connection(self):
        """惰性建立 owner lock 专用长连接（会话级 advisory lock 绑定该连接）。"""
        if self._mm_lock_conn is not None:
            return
        if self._mm_lock_engine is None:
            return
        try:
            self._mm_lock_conn = await self._mm_lock_engine.connect()
        except Exception:
            logger.exception("market_metrics owner lock connection setup failed")
            self._mm_lock_conn = None

    async def _close_mm_lock_connection(self):
        """释放 owner lock 连接（含显式 unlock，避免依赖连接断开）。"""
        if self._mm_lock_conn is None:
            return
        conn = self._mm_lock_conn
        self._mm_lock_conn = None
        try:
            # 若仍持锁，显式释放（与 commit 配合，确保会话锁释放）。
            if self._mm_lock_held:
                try:
                    await conn.execute(
                        text("SELECT pg_advisory_unlock(:key)"),
                        {"key": MARKET_METRICS_OWNER_LOCK_KEY},
                    )
                    await conn.commit()
                except Exception:
                    logger.debug("pg_advisory_unlock on close failed (connection may be gone)")
        finally:
            try:
                await conn.close()
            except Exception:
                pass

    async def _maintain_mm_owner_lock(self):
        """每轮 poll 维护 owner lock：已持锁则 ping 校验；未持锁则 try-acquire。

        架构 §6.2.5/§8.5：try-acquire 非阻塞；另一实例持锁时本实例 standby，
        不影响其他任务类型。acquisition 成功后生成新 token+guard、跑 recovery、激活。
        """
        if self._mm_lock_held:
            # 校验持锁连接仍存活；断开视为锁丢失（会话级锁随连接断开自动释放）。
            try:
                await self._mm_lock_conn.execute(text("SELECT 1"))
                await self._mm_lock_conn.commit()
            except Exception:
                logger.warning(
                    "market_metrics owner lock connection lost; invalidating owner"
                )
                await self._lose_mm_owner_lock()
            return

        # 未持锁：惰性建连 + try-acquire
        await self._ensure_mm_lock_connection()
        if self._mm_lock_conn is None:
            return
        try:
            result = await self._mm_lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MARKET_METRICS_OWNER_LOCK_KEY},
            )
            # 先读取结果再 commit：asyncpg 结果在 commit 后失效会返回 None
            acquired = bool(result.scalar())
            await self._mm_lock_conn.commit()
        except Exception:
            logger.exception("market_metrics owner lock acquire failed; will retry")
            await self._close_mm_lock_connection()
            return

        if not acquired:
            # 另一实例持锁；standby，仅首次记日志避免噪声。
            if not self._mm_standby_logged:
                logger.info(
                    "market_metrics owner lock held by another instance; standby"
                )
                self._mm_standby_logged = True
            return

        self._mm_standby_logged = False
        await self._on_mm_owner_acquired()

    async def _on_mm_owner_acquired(self):
        """acquisition 成功：生成新 token+guard → recovery → 激活 guard。

        设计为独立可测单元（无需真实 advisory lock 即可验证 token 轮换/recovery）。
        失败时释放 owner lock，避免持有锁但 guard 未激活的死锁态。
        """
        new_token = str(uuid.uuid4())
        new_guard = OwnerGenerationGuard(new_token)
        self._mm_owner_token = new_token
        self._mm_guard = new_guard
        self._mm_lock_held = True
        logger.info(
            "market_metrics owner lock acquired; running recovery (token=%s)",
            new_token,
        )

        # orphan recovery（独立 session）：回收旧/NULL token 的本类型 running。
        try:
            if self._session_factory is not None:
                async with self._session_factory() as db:
                    recovery_manager = TaskManager(db)
                    stats = await recovery_manager.recover_stale_market_metrics_tasks(new_token)
                if stats.get("recovered"):
                    logger.info("market_metrics recovery completed: %s", stats)
        except Exception:
            logger.exception(
                "market_metrics recovery failed; releasing owner lock (token=%s)",
                new_token,
            )
            await self._lose_mm_owner_lock()
            return

        new_guard.activate()
        logger.info("market_metrics guard activated (token=%s)", new_token)

    async def _lose_mm_owner_lock(self):
        """锁丢失：失效旧 guard（cancel 旧 token 全部协程）、清状态、释放连接。

        重连后 _maintain_mm_owner_lock 会走新 acquisition（生成新 token）。
        """
        if self._mm_guard is not None:
            self._mm_guard.invalidate()
        self._mm_guard = None
        self._mm_owner_token = None
        self._mm_lock_held = False
        self._mm_task_coroutines.clear()
        await self._close_mm_lock_connection()

    async def _consume_mm_stop_requests(self, manager: TaskManager):
        """并发 gate 前消费当前 owner 的本类型 running 停止请求（架构 §6.2.5）。

        读 cancel/timeout 胜出首因 → cancel 对应协程（handler 感知后走 finalize）。
        若协程已不在映射中（如尚未派发或已结束），仅记录日志，停止终态由 fence 拒绝
        或 recovery 兜底。
        """
        running = await manager.list_tasks(
            task_type=_MARKET_METRICS_TYPE, status="running", limit=50
        )
        for task in running:
            # 只消费当前 owner 的任务（旧 token 由 recovery 回收）。
            if task.executor_acquisition_token != self._mm_owner_token:
                continue
            cancel_at = task.cancel_requested_at
            timeout_at = task.timeout_requested_at
            if cancel_at is None and timeout_at is None:
                continue
            # 首因胜出：cancel/timeout 同时存在时按较早数据库时间（同刻 cancel 优先）。
            if cancel_at is not None and (
                timeout_at is None or cancel_at <= timeout_at
            ):
                cause = "cancel"
            else:
                cause = "timeout"
            coro = self._mm_task_coroutines.get(task.task_id)
            if coro is not None and not coro.done():
                logger.info(
                    "consuming stop request (%s) for market_metrics task %s",
                    cause,
                    task.task_id,
                )
                coro.cancel()
            else:
                logger.debug(
                    "stop request (%s) for task %s has no live coroutine; "
                    "finalize via fence/recovery",
                    cause,
                    task.task_id,
                )

    # ------------------------------------------------------------------
    # 第 17 期 plan-04：sync_market_margin 专属 owner lock / token / guard / recovery
    # （与上方 _mm_* 方法族同款范式，锁 key 独立为 MARGIN_OWNER_LOCK_KEY=9001004，
    # 与 market_metrics 两把 owner lock 互不阻塞）
    # ------------------------------------------------------------------

    async def _ensure_margin_lock_connection(self):
        """惰性建立 margin owner lock 专用长连接（会话级 advisory lock 绑定该连接）。"""
        if self._margin_lock_conn is not None:
            return
        if self._margin_lock_engine is None:
            return
        try:
            self._margin_lock_conn = await self._margin_lock_engine.connect()
        except Exception:
            logger.exception("margin owner lock connection setup failed")
            self._margin_lock_conn = None

    async def _close_margin_lock_connection(self):
        """释放 margin owner lock 连接（含显式 unlock，避免依赖连接断开）。"""
        if self._margin_lock_conn is None:
            return
        conn = self._margin_lock_conn
        self._margin_lock_conn = None
        try:
            # 若仍持锁，显式释放（与 commit 配合，确保会话锁释放）。
            if self._margin_lock_held:
                try:
                    await conn.execute(
                        text("SELECT pg_advisory_unlock(:key)"),
                        {"key": MARGIN_OWNER_LOCK_KEY},
                    )
                    await conn.commit()
                except Exception:
                    logger.debug("pg_advisory_unlock on close failed (connection may be gone)")
        finally:
            try:
                await conn.close()
            except Exception:
                pass

    async def _maintain_margin_owner_lock(self):
        """每轮 poll 维护 margin owner lock：已持锁则 ping 校验；未持锁则 try-acquire。

        与 _maintain_mm_owner_lock 同范式（架构 §6.2.5/§8.5）：try-acquire 非阻塞；
        另一实例持锁时本实例 standby，不影响其他任务类型。acquisition 成功后生成
        新 token+guard、跑 margin recovery、激活。
        """
        if self._margin_lock_held:
            # 校验持锁连接仍存活；断开视为锁丢失（会话级锁随连接断开自动释放）。
            try:
                await self._margin_lock_conn.execute(text("SELECT 1"))
                await self._margin_lock_conn.commit()
            except Exception:
                logger.warning(
                    "margin owner lock connection lost; invalidating owner"
                )
                await self._lose_margin_owner_lock()
            return

        # 未持锁：惰性建连 + try-acquire
        await self._ensure_margin_lock_connection()
        if self._margin_lock_conn is None:
            return
        try:
            result = await self._margin_lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": MARGIN_OWNER_LOCK_KEY},
            )
            # 先读取结果再 commit：asyncpg 结果在 commit 后失效会返回 None
            acquired = bool(result.scalar())
            await self._margin_lock_conn.commit()
        except Exception:
            logger.exception("margin owner lock acquire failed; will retry")
            await self._close_margin_lock_connection()
            return

        if not acquired:
            # 另一实例持锁；standby，仅首次记日志避免噪声。
            if not self._margin_standby_logged:
                logger.info(
                    "margin owner lock held by another instance; standby"
                )
                self._margin_standby_logged = True
            return

        self._margin_standby_logged = False
        await self._on_margin_owner_acquired()

    async def _on_margin_owner_acquired(self):
        """margin acquisition 成功：生成新 token+guard → recovery → 激活 guard。

        设计为独立可测单元（无需真实 advisory lock 即可验证 token 轮换/recovery）。
        失败时释放 owner lock，避免持有锁但 guard 未激活的死锁态。
        """
        new_token = str(uuid.uuid4())
        new_guard = OwnerGenerationGuard(new_token)
        self._margin_owner_token = new_token
        self._margin_guard = new_guard
        self._margin_lock_held = True
        logger.info(
            "margin owner lock acquired; running recovery (token=%s)",
            new_token,
        )

        # orphan recovery（独立 session）：回收旧/NULL token 的本类型 running。
        try:
            if self._session_factory is not None:
                async with self._session_factory() as db:
                    recovery_manager = TaskManager(db)
                    stats = await recovery_manager.recover_stale_fenced_tasks(
                        _MARGIN_TYPE, new_token
                    )
                if stats.get("recovered"):
                    logger.info("margin recovery completed: %s", stats)
        except Exception:
            logger.exception(
                "margin recovery failed; releasing owner lock (token=%s)",
                new_token,
            )
            await self._lose_margin_owner_lock()
            return

        new_guard.activate()
        logger.info("margin guard activated (token=%s)", new_token)

    async def _lose_margin_owner_lock(self):
        """margin 锁丢失：失效旧 guard（cancel 旧 token 全部协程）、清状态、释放连接。

        重连后 _maintain_margin_owner_lock 会走新 acquisition（生成新 token）。
        """
        if self._margin_guard is not None:
            self._margin_guard.invalidate()
        self._margin_guard = None
        self._margin_owner_token = None
        self._margin_lock_held = False
        self._margin_task_coroutines.clear()
        await self._close_margin_lock_connection()

    async def _consume_margin_stop_requests(self, manager: TaskManager):
        """并发 gate 前消费当前 owner 的 sync_market_margin running 停止请求。

        读 cancel/timeout 胜出首因 → cancel 对应协程（handler 感知后走 finalize）。
        若协程已不在映射中（如尚未派发或已结束），仅记录日志，停止终态由 fence 拒绝
        或 recovery 兜底。
        """
        running = await manager.list_tasks(
            task_type=_MARGIN_TYPE, status="running", limit=50
        )
        for task in running:
            # 只消费当前 owner 的任务（旧 token 由 recovery 回收）。
            if task.executor_acquisition_token != self._margin_owner_token:
                continue
            cancel_at = task.cancel_requested_at
            timeout_at = task.timeout_requested_at
            if cancel_at is None and timeout_at is None:
                continue
            # 首因胜出：cancel/timeout 同时存在时按较早数据库时间（同刻 cancel 优先）。
            if cancel_at is not None and (
                timeout_at is None or cancel_at <= timeout_at
            ):
                cause = "cancel"
            else:
                cause = "timeout"
            coro = self._margin_task_coroutines.get(task.task_id)
            if coro is not None and not coro.done():
                logger.info(
                    "consuming stop request (%s) for margin task %s",
                    cause,
                    task.task_id,
                )
                coro.cancel()
            else:
                logger.debug(
                    "stop request (%s) for margin task %s has no live coroutine; "
                    "finalize via fence/recovery",
                    cause,
                    task.task_id,
                )

    @staticmethod
    def _is_retryable_db_error(exc: Exception) -> bool:
        """判断是否为可重试的数据库瞬时错误。"""
        if isinstance(exc, (ConnectionError, OSError)):
            return True
        if isinstance(exc, SQLAlchemyError):
            return True

        msg = str(exc).lower()
        return (
            "connection_lost" in msg
            or "connection was closed" in msg
            or "server closed the connection" in msg
            or "connection reset" in msg
            or "cannotconnectnowerror" in msg
            or "database system is starting up" in msg
            or "the database system is starting up" in msg
        )

    async def _wait_for_database_ready(self, max_wait_seconds: float = 60.0):
        """启动时等待数据库可用，减少冷启动期噪声。"""
        start = time.time()
        while self._running and (time.time() - start) < max_wait_seconds:
            try:
                if self._session_factory is None:
                    await asyncio.sleep(1.0)
                    continue
                async with self._session_factory() as db:
                    await db.execute(text("SELECT 1"))
                    logger.info("TaskExecutor database readiness check passed")
                    return
            except Exception as e:
                if not self._is_retryable_db_error(e):
                    logger.exception("Unexpected DB error during readiness check")
                    return
                await asyncio.sleep(2.0)

        logger.warning("TaskExecutor database readiness check timed out after %.1fs", max_wait_seconds)

    @property
    def is_running(self) -> bool:
        """检查执行器是否正在运行"""
        return self._running


# 全局任务执行器实例
_global_executor: Optional[TaskExecutor] = None


def get_task_executor() -> Optional[TaskExecutor]:
    """获取全局任务执行器实例"""
    return _global_executor


def init_task_executor(
    poll_interval: float = 1.0,
    max_concurrent_tasks: int = 2,
) -> TaskExecutor:
    """
    初始化全局任务执行器

    Args:
        poll_interval: 轮询间隔（秒）
        max_concurrent_tasks: 最大并发任务数

    Returns:
        任务执行器实例
    """
    global _global_executor

    if _global_executor is not None:
        logger.warning("TaskExecutor already initialized, returning existing instance")
        return _global_executor

    _global_executor = TaskExecutor(
        poll_interval=poll_interval,
        max_concurrent_tasks=max_concurrent_tasks,
    )

    return _global_executor


def start_task_executor():
    """启动全局任务执行器"""
    executor = get_task_executor()
    if executor:
        executor.start()


def stop_task_executor():
    """停止全局任务执行器"""
    executor = get_task_executor()
    if executor:
        executor.stop()
