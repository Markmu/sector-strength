"""异步任务 fencing 基础设施（plan-04）

为 ``sync_market_metrics`` 单 owner 任务执行提供 fencing 原语（架构 §6.2.3/§6.2.6/
§7.4/§8.6）：

- :class:`OwnerGenerationGuard`：绑定一次 acquisition token 的活跃守卫。只有持专属
  owner lock 且 orphan recovery 完成后才 ``active``；锁丢失时 :meth:`invalidate`
  置 False 并 cancel 注册到本 guard 的全部 ``asyncio.Task``，使旧 token 协程无法再
  开新 fence 事务。
- :class:`TaskFenceContext`：业务写事务的 fencing 上下文。:meth:`lock_and_validate`
  在 upsert 前对 AsyncTask 行 ``SELECT ... FOR UPDATE``，事务前轻检 + 行锁后双检
  类型/状态/token/停止字段/guard.active；任一不符抛 :class:`FenceValidationError`，
  调用方整体 rollback。
- :class:`TaskFenceRegistry`：进程级 ``task_id -> TaskFenceContext`` 映射。执行器在
  派发本类型任务时注入，handler（plan-05）由此取用而不改三参签名。

护栏：token（而非进程实例 ID）是唯一 fencing 身份；新 acquisition 回收 token 不同
或 NULL 的本类型旧 running。
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# 仅这些类型走 fencing 路径（与 task_manager.RESERVED_TASK_TYPES 对齐）。
# 第 17 期 plan-04：单值扩展为集合，纳入 sync_market_margin。
FENCED_TASK_TYPES = {"sync_market_metrics", "sync_market_margin"}


class FenceValidationError(Exception):
    """Fence 校验失败（类型/状态/token/停止字段/guard 失效）。

    调用方应让当前业务写事务整体 rollback，禁止旧 token 提交。
    """


class OwnerGenerationGuard:
    """绑定一次 acquisition token 的活跃守卫（架构 §6.2.6）。

    生命周期：执行器每次成功取得专属 owner lock 后构造一个新 guard，
    orphan recovery 完成后才 :meth:`activate`；锁断开先 :meth:`invalidate`
    （置 False 并 cancel 注册到本 guard 的全部 ``asyncio.Task``），再重连走新 acquisition。
    """

    def __init__(self, token: str):
        self.token = token
        self._active = False
        # id(asyncio.Task) -> asyncio.Task；cancel 后即移除。
        self._coroutines: Dict[int, asyncio.Task] = {}

    @property
    def active(self) -> bool:
        """是否允许开新 fence 事务（持锁且 recovery 完成）。"""
        return self._active

    def activate(self) -> None:
        """orphan recovery 完成后激活，允许本 token 开 fence 事务。"""
        self._active = True

    def invalidate(self) -> None:
        """锁丢失：置 False 并 cancel 注册到本 guard 的全部协程。

        幂等：重复调用无副作用。已 cancel 的协程不会被重复 cancel。
        """
        self._active = False
        tasks = list(self._coroutines.values())
        self._coroutines.clear()
        cancelled = 0
        for task in tasks:
            if not task.done():
                task.cancel()
                cancelled += 1
        if cancelled:
            logger.warning(
                "OwnerGenerationGuard invalidated for token=%s; cancelled %d coroutine(s)",
                self.token,
                cancelled,
            )
        else:
            logger.info(
                "OwnerGenerationGuard invalidated for token=%s (no live coroutine)",
                self.token,
            )

    def register_coroutine(self, task: asyncio.Task) -> None:
        """注册一个本 token 派发的协程，便于 invalidate 时统一 cancel。"""
        self._coroutines[id(task)] = task

    def unregister(self, task: asyncio.Task) -> None:
        """协程结束后注销（避免持有已完成 Task 强引用）。"""
        self._coroutines.pop(id(task), None)


class TaskFenceContext:
    """业务写事务的 fencing 上下文（架构 §6.2.3/§6.2.6）。

    由执行器在派发本类型任务时构造并注入 :class:`TaskFenceRegistry`；handler
    （plan-05）取用并在每个交易日 upsert 前调用 :meth:`lock_and_validate`，
    与业务写共用同一事务。
    """

    def __init__(
        self,
        task_id: str,
        acquisition_token: str,
        guard: OwnerGenerationGuard,
    ):
        self.task_id = task_id
        self.acquisition_token = acquisition_token
        self.guard = guard

    async def lock_and_validate(self, session: AsyncSession) -> None:
        """事务前轻检 + 行锁后双检（架构 §6.2.6）。

        任一不符抛 :class:`FenceValidationError`；调用方应整体 rollback。
        """
        # 延迟导入避免与 task_manager 产生循环依赖。
        from src.models.async_task import AsyncTask

        # 事务前轻检：guard 必须仍 active 且 token 未变。
        if not self.guard.active or self.guard.token != self.acquisition_token:
            raise FenceValidationError(
                f"fence rejected: guard inactive or token superseded (task={self.task_id})"
            )

        # 行锁：SELECT ... FOR UPDATE 串行化“旧事务提交”与“recovery”。
        result = await session.execute(
            select(AsyncTask)
            .where(AsyncTask.task_id == self.task_id)
            .with_for_update()
        )
        task = result.scalar_one_or_none()
        if task is None:
            raise FenceValidationError(f"fence rejected: task not found (task={self.task_id})")
        if task.task_type not in FENCED_TASK_TYPES:
            raise FenceValidationError(
                f"fence rejected: task type {task.task_type!r} not in "
                f"{sorted(FENCED_TASK_TYPES)}"
            )
        if task.status != "running":
            raise FenceValidationError(
                f"fence rejected: status {task.status!r} != 'running' (task={self.task_id})"
            )
        if task.executor_acquisition_token != self.acquisition_token:
            # 旧 token 的事务写被 fencing 拒绝（token 已被新 owner 回收）。
            raise FenceValidationError(
                f"fence rejected: token mismatch (task={self.task_id})"
            )
        if task.cancel_requested_at is not None or task.timeout_requested_at is not None:
            # 已有停止请求首因胜出，不允许再开新业务写事务。
            raise FenceValidationError(
                f"fence rejected: stop request pending (task={self.task_id})"
            )
        # 行锁后再次确认 guard 未在等待行锁期间被 invalidate。
        if not self.guard.active:
            raise FenceValidationError(
                f"fence rejected: guard invalidated while waiting for row lock "
                f"(task={self.task_id})"
            )


class TaskFenceRegistry:
    """进程级 ``task_id -> TaskFenceContext`` 映射。

    执行器在派发本类型任务（pending→running 同事务写 token）时 :meth:`set`；
    handler（plan-05）通过 :meth:`get` 取用而不改三参签名；任务结束 :meth:`pop`。
    """

    _contexts: Dict[str, TaskFenceContext] = {}

    @classmethod
    def set(cls, task_id: str, ctx: TaskFenceContext) -> None:
        cls._contexts[task_id] = ctx

    @classmethod
    def get(cls, task_id: str) -> Optional[TaskFenceContext]:
        return cls._contexts.get(task_id)

    @classmethod
    def pop(cls, task_id: str) -> Optional[TaskFenceContext]:
        return cls._contexts.pop(task_id, None)

    @classmethod
    def clear(cls) -> None:
        """测试/清理用：清空全部注册项。"""
        cls._contexts.clear()
