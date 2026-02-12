"""异步任务执行器

负责轮询任务表并执行待处理的任务。
在后台线程中运行，支持并发控制、超时处理和重试机制。
"""

import asyncio
import threading
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from src.db.database import AsyncSessionLocal, get_task_executor_engine, close_task_executor_engine
from src.services.task_manager import TaskManager
from src.models.async_task import AsyncTask

logger = logging.getLogger(__name__)


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
        logger.info("TaskExecutor database engine initialized in background thread")

        try:
            self._loop.run_until_complete(self._wait_for_database_ready())
            self._loop.run_until_complete(self._poll_and_execute())
        except Exception as e:
            logger.exception("TaskExecutor loop error")
        finally:
            # 先收敛正在执行的任务，再关闭数据库引擎，避免连接被动断开
            self._loop.run_until_complete(self._shutdown_running_tasks())
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

                async with self._session_factory() as db:
                    manager = TaskManager(db)

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
                        task_coro = self._execute_task(task.task_id)
                        async_task = asyncio.create_task(task_coro)
                        self._running_tasks.add(async_task)
                        # 添加完成回调以清理
                        async_task.add_done_callback(lambda t: self._running_tasks.discard(t))

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
                logger.warning(f"Task {task.task_id} timed out")
                await self._handle_task_timeout(manager, task)

        logger.info(f"Found {len(running_tasks)} running tasks")

        # 获取待处理任务
        pending = await manager.get_pending_tasks(limit=limit)
        for task in pending:
            # 检查是否需要延迟重试
            if task.retry_count > 0:
                retry_delay = min(2 ** task.retry_count, 60)  # 指数退避，最多60秒
                if task.started_at:
                    elapsed = (datetime.now(timezone.utc) - task.started_at).total_seconds()
                    if elapsed < retry_delay:
                        continue

            tasks.append(task)
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

            try:
                # 获取任务信息
                task = await manager.get_task(task_id)
                if not task:
                    logger.warning(f"Task {task_id} not found")
                    return

                # 检查任务状态
                if task.status != "pending":
                    return

                # 标记任务开始
                await manager.start_task(task_id)

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
