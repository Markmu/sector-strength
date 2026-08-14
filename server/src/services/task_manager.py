"""异步任务管理器

负责任务的创建、查询、取消等操作。

plan-04 扩展：为 ``sync_market_metrics`` 提供单 owner 任务执行的互斥创建、条件停止
写入（首因胜出）、原子终态（行锁 + 双检 token + partial result 同事务）与 orphan
recovery（三分支 + 双标记 critical 告警）。其他约 28 类任务保持原语义、新字段恒 NULL。

第 17 期 plan-04 扩展：上述 fencing 基础设施按 task_type 参数化支持第二个任务类型
``sync_market_margin``（专属锁 key 9001003/9001004、锁 key 映射、stale 恢复参数化
``recover_stale_fenced_tasks``）；``sync_market_metrics`` 行为语义不变。
"""

import uuid
import json
import logging
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any, List
from sqlalchemy import select, update, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.async_task import AsyncTask, AsyncTaskParam, AsyncTaskLog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# plan-04 常量（架构 §6.2.5 / §7.4 / line 148）
# ---------------------------------------------------------------------------
# 保留任务类型：通用 POST /api/v1/admin/tasks 必须拒绝，专用入口（plan-05）调用
# create_exclusive_task 创建。
RESERVED_TASK_TYPES = {"sync_market_metrics", "sync_market_margin"}

# 同类创建互斥用 PostgreSQL advisory lock key（事务级）。
# 设计澄清：架构 line 148 明确“事务级 lock 保证同类创建原子性，专属会话级 lock
# 只保证 sync_market_metrics 单 owner”是两个不同锁目的。若创建互斥锁与执行器 owner
# 锁共用同一 key，执行器持会话级锁期间 create_exclusive_task 的 pg_advisory_xact_lock
# 会无限阻塞。因此本实现使用两个互不冲突的 key：
#   - MARKET_METRICS_LOCK_KEY：创建互斥（create_exclusive_task 内 pg_advisory_xact_lock，
#     commit 即释放，串行化并发同类创建）
#   - MARKET_METRICS_OWNER_LOCK_KEY：执行器单 owner（pg_try_advisory_lock 会话级长连接）
MARKET_METRICS_LOCK_KEY = 9001001
MARKET_METRICS_OWNER_LOCK_KEY = 9001002

# 融资融券专属锁 key（第 17 期 plan-04，沿用 16 期“创建互斥锁与 owner 锁分 key”
# 裁定，不与 9001001/9001002 冲突）：
#   - MARGIN_LOCK_KEY：创建互斥（事务级 xact lock）
#   - MARGIN_OWNER_LOCK_KEY：执行器单 owner（会话级 try lock）
MARGIN_LOCK_KEY = 9001003
MARGIN_OWNER_LOCK_KEY = 9001004

# 仅本类型走 fencing 路径。
_MARKET_METRICS_TYPE = "sync_market_metrics"
_MARGIN_TYPE = "sync_market_margin"

# 走 fencing 路径的任务类型集合（与 task_fence.FENCED_TASK_TYPES 对齐）。
_FENCED_TASK_TYPES = {_MARKET_METRICS_TYPE, _MARGIN_TYPE}

# create_exclusive_task 的创建互斥锁 key 按 task_type 解析（缺省回落
# MARKET_METRICS_LOCK_KEY，保持既有行为不变）。
_EXCLUSIVE_TASK_LOCK_KEYS: Dict[str, int] = {
    _MARKET_METRICS_TYPE: MARKET_METRICS_LOCK_KEY,
    _MARGIN_TYPE: MARGIN_LOCK_KEY,
}


class TaskManager:
    """异步任务管理器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        timeout_seconds: int = 14400,
        created_by: Optional[str] = None,
    ) -> AsyncTask:
        """
        创建新任务

        Args:
            task_type: 任务类型
            params: 任务参数
            max_retries: 最大重试次数
            timeout_seconds: 超时时间（秒）
            created_by: 创建者用户ID

        Returns:
            创建的任务对象
        """
        # 生成唯一的任务ID
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        # 创建任务记录
        task = AsyncTask(
            task_id=task_id,
            task_type=task_type,
            status="pending",
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            created_by=created_by,
        )

        self.db.add(task)
        await self.db.flush()

        # 创建任务参数
        if params:
            for key, value in params.items():
                param = AsyncTaskParam(
                    task_id=task_id,
                    key=key,
                    value=json.dumps(value)
                )
                self.db.add(param)

        await self.db.commit()
        await self.db.refresh(task, ["params"])

        # 记录创建日志
        await self._log_message(
            task_id,
            "INFO",
            f"Task created: {task_type} with params {params}"
        )

        return task

    async def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务对象或None
        """
        result = await self.db.execute(
            select(AsyncTask)
            .options(selectinload(AsyncTask.params))
            .where(AsyncTask.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_task_params(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务参数

        Args:
            task_id: 任务ID

        Returns:
            参数字典
        """
        result = await self.db.execute(
            select(AsyncTaskParam)
            .where(AsyncTaskParam.task_id == task_id)
        )
        params = result.scalars().all()

        param_dict = {}
        for param in params:
            try:
                param_dict[param.key] = json.loads(param.value)
            except (json.JSONDecodeError, TypeError):
                param_dict[param.key] = param.value

        return param_dict

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        task = await self.get_task(task_id)
        if not task:
            return False

        # 只能取消 pending 或 running 状态的任务
        if task.status not in ["pending", "running"]:
            return False

        task.status = "cancelled"
        task.cancelled_at = datetime.now(timezone.utc)
        await self.db.commit()

        await self._log_message(
            task_id,
            "INFO",
            "Task cancelled by user"
        )

        return True

    async def update_progress(
        self,
        task_id: str,
        progress: int,
        total: Optional[int] = None,
    ) -> bool:
        """
        更新任务进度

        Args:
            task_id: 任务ID
            progress: 当前进度
            total: 总数（可选）

        Returns:
            是否成功更新
        """
        result = await self.db.execute(
            update(AsyncTask)
            .where(AsyncTask.task_id == task_id)
            .values(progress=progress)
        )

        if total is not None:
            await self.db.execute(
                update(AsyncTask)
                .where(AsyncTask.task_id == task_id)
                .values(total=total)
            )

        await self.db.commit()
        return result.rowcount > 0

    async def start_task(
        self,
        task_id: str,
        acquisition_token: Optional[str] = None,
    ) -> bool:
        """
        标记任务开始执行

        Args:
            task_id: 任务ID
            acquisition_token: plan-04 sync_market_metrics 派发时写入的 fencing token
                （其他类型不传，保持 executor_acquisition_token 为 NULL）

        Returns:
            是否成功标记
        """
        values: Dict[str, Any] = {
            "status": "running",
            "started_at": datetime.now(timezone.utc),
        }
        if acquisition_token is not None:
            values["executor_acquisition_token"] = acquisition_token
        result = await self.db.execute(
            update(AsyncTask)
            .where(AsyncTask.task_id == task_id)
            .values(**values)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def complete_task(
        self,
        task_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        标记任务完成

        Args:
            task_id: 任务ID
            success: 是否成功
            error_message: 错误信息

        Returns:
            是否成功标记
        """
        status = "completed" if success else "failed"

        result = await self.db.execute(
            update(AsyncTask)
            .where(AsyncTask.task_id == task_id)
            .values(
                status=status,
                completed_at=datetime.now(timezone.utc),
                error_message=error_message,
            )
        )
        await self.db.commit()

        if error_message:
            await self._log_message(task_id, "ERROR", error_message)

        return result.rowcount > 0

    async def increment_retry(self, task_id: str) -> bool:
        """
        增加重试计数

        Args:
            task_id: 任务ID

        Returns:
            是否成功更新
        """
        from sqlalchemy import func

        result = await self.db.execute(
            update(AsyncTask)
            .where(AsyncTask.task_id == task_id)
            .values(retry_count=AsyncTask.retry_count + 1)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def reset_for_retry(self, task_id: str) -> bool:
        """
        重置任务状态以便重试

        Args:
            task_id: 任务ID

        Returns:
            是否成功重置
        """
        result = await self.db.execute(
            update(AsyncTask)
            .where(AsyncTask.task_id == task_id)
            .values(
                status="pending",
                started_at=None,
                error_message=None,
            )
        )
        await self.db.commit()

        await self._log_message(
            task_id,
            "INFO",
            "Task reset for retry"
        )

        return result.rowcount > 0

    async def log_message(
        self,
        task_id: str,
        level: str,
        message: str,
    ) -> bool:
        """
        记录任务日志

        Args:
            task_id: 任务ID
            level: 日志级别 (INFO, WARNING, ERROR)
            message: 日志消息

        Returns:
            是否成功记录
        """
        return await self._log_message(task_id, level, message)

    async def _log_message(
        self,
        task_id: str,
        level: str,
        message: str,
    ) -> bool:
        """内部日志记录方法"""
        log = AsyncTaskLog(
            task_id=task_id,
            level=level,
            message=message,
        )
        self.db.add(log)
        await self.db.commit()
        return True

    async def get_task_logs(
        self,
        task_id: str,
        level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AsyncTaskLog]:
        """
        获取任务日志

        Args:
            task_id: 任务ID
            level: 日志级别过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            日志列表
        """
        query = select(AsyncTaskLog).where(AsyncTaskLog.task_id == task_id)

        if level:
            query = query.where(AsyncTaskLog.level == level)

        query = query.order_by(AsyncTaskLog.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_tasks(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        task_types: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AsyncTask]:
        """
        列出任务

        Args:
            status: 状态过滤
            task_type: 任务类型过滤（单值，向后兼容）
            task_types: 任务类型过滤（多值，优先于 task_type）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            任务列表
        """
        query = select(AsyncTask).options(selectinload(AsyncTask.params))

        if status:
            query = query.where(AsyncTask.status == status)
        if task_types:
            query = query.where(AsyncTask.task_type.in_(task_types))
        elif task_type:
            query = query.where(AsyncTask.task_type == task_type)

        query = query.order_by(AsyncTask.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_tasks(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        task_types: Optional[List[str]] = None,
    ) -> int:
        """
        统计任务数量

        Args:
            status: 状态过滤
            task_type: 任务类型过滤（单值，向后兼容）
            task_types: 任务类型过滤（多值，优先于 task_type）

        Returns:
            任务数量
        """
        from sqlalchemy import func

        query = select(func.count(AsyncTask.id))

        if status:
            query = query.where(AsyncTask.status == status)
        if task_types:
            query = query.where(AsyncTask.task_type.in_(task_types))
        elif task_type:
            query = query.where(AsyncTask.task_type == task_type)

        result = await self.db.execute(query)
        return result.scalar()

    async def get_pending_tasks(self, limit: int = 10) -> List[AsyncTask]:
        """
        获取待处理的任务

        Args:
            limit: 返回数量限制

        Returns:
            待处理任务列表
        """
        result = await self.db.execute(
            select(AsyncTask)
            .where(AsyncTask.status == "pending")
            .order_by(AsyncTask.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_running_tasks_count(self) -> int:
        """获取正在运行的任务数量"""
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count(AsyncTask.id))
            .where(AsyncTask.status == "running")
        )
        return result.scalar()

    async def check_task_timeout(self, task_id: str) -> bool:
        """
        检查任务是否超时

        Args:
            task_id: 任务ID

        Returns:
            是否超时
        """
        task = await self.get_task(task_id)
        if not task or not task.started_at:
            return False

        elapsed = (datetime.now(timezone.utc) - task.started_at).total_seconds()
        return elapsed > task.timeout_seconds

    # ------------------------------------------------------------------
    # plan-04：sync_market_metrics 互斥创建 / 条件停止 / 原子终态 / recovery
    # ------------------------------------------------------------------

    async def create_exclusive_task(
        self,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
        timeout_seconds: int = 14400,
    ) -> Optional[AsyncTask]:
        """互斥创建 ``sync_market_metrics`` / ``sync_market_margin`` 任务。

        单数据库事务内先 ``pg_advisory_xact_lock(key)``（key 按 task_type 查
        ``_EXCLUSIVE_TASK_LOCK_KEYS`` 映射，缺省回落 ``MARKET_METRICS_LOCK_KEY``
        保持既有行为不变）串行化同类创建，再查同类型 ``status IN
        ('pending','running')``（running 含停止中/待 recovery，命中则返回
        ``None`` 表示互斥拒绝）；创建任务固定 ``max_retries=0``。
        锁随 commit 释放，等待者随后看到已提交任务并被拒。

        Returns:
            创建的 AsyncTask；若同类型已有 pending/running 则返回 None。
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        # 事务级 advisory lock 串行化同类创建（锁随本事务 commit/rollback 释放）。
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": self._exclusive_lock_key(task_type)},
        )

        # 同类互斥检查：pending 或 running（含停止中/待 recovery）任一存在即拒绝。
        existing = await self.db.execute(
            select(AsyncTask.id).where(
                AsyncTask.task_type == task_type,
                AsyncTask.status.in_(["pending", "running"]),
            )
        )
        if existing.scalar_one_or_none() is not None:
            await self.db.rollback()
            return None

        # 创建任务（固定 max_retries=0；本类型失败不自动重试）。
        task = AsyncTask(
            task_id=task_id,
            task_type=task_type,
            status="pending",
            max_retries=0,
            timeout_seconds=timeout_seconds,
            created_by=created_by,
        )
        self.db.add(task)
        await self.db.flush()

        if params:
            for key, value in params.items():
                self.db.add(
                    AsyncTaskParam(
                        task_id=task_id,
                        key=key,
                        value=json.dumps(value),
                    )
                )

        # commit 释放 xact advisory lock；等待者随后看到已提交任务被拒。
        await self.db.commit()
        await self.db.refresh(task, ["params"])

        await self._log_message(
            task_id,
            "INFO",
            f"Exclusive task created: {task_type} (max_retries=0)",
        )

        return task

    @staticmethod
    def _exclusive_lock_key(task_type: str) -> int:
        """按 task_type 解析创建互斥锁 key（缺省回落 MARKET_METRICS_LOCK_KEY）。"""
        return _EXCLUSIVE_TASK_LOCK_KEYS.get(task_type, MARKET_METRICS_LOCK_KEY)

    async def request_cancel(self, task_id: str) -> bool:
        """条件写入 ``cancel_requested_at``（首因胜出，架构 §6.2.5 / §7.4）。

        running 且 ``cancel_requested_at`` 与 ``timeout_requested_at`` 均空时写
        cancel 标记；返回是否成为首因。pending 任务仍由 :meth:`cancel_task`
        立即置 cancelled（调用方按状态分流）。

        Returns:
            True 表示本次写入成为停止首因；False 表示已有首因或非 running。
        """
        result = await self.db.execute(
            update(AsyncTask)
            .where(
                AsyncTask.task_id == task_id,
                AsyncTask.status == "running",
                AsyncTask.cancel_requested_at.is_(None),
                AsyncTask.timeout_requested_at.is_(None),
            )
            .values(cancel_requested_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        wrote = result.rowcount > 0
        if wrote:
            logger.info("cancel requested for task %s (first-cause)", task_id)
        return wrote

    async def request_timeout(self, task_id: str) -> bool:
        """对称条件更新 ``timeout_requested_at``（首因胜出，架构 §6.2.5）。

        Returns:
            True 表示本次写入成为停止首因；False 表示已有首因或非 running。
        """
        result = await self.db.execute(
            update(AsyncTask)
            .where(
                AsyncTask.task_id == task_id,
                AsyncTask.status == "running",
                AsyncTask.timeout_requested_at.is_(None),
                AsyncTask.cancel_requested_at.is_(None),
            )
            .values(timeout_requested_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        wrote = result.rowcount > 0
        if wrote:
            logger.info("timeout requested for task %s (first-cause)", task_id)
        return wrote

    async def finalize_cancel_with_result(
        self,
        task_id: str,
        token: Optional[str],
        result: Optional[Dict[str, Any]],
    ) -> bool:
        """原子终态：``cancelled`` + partial result（行锁 + 双检，架构 §7.4）。

        ``token`` 非 None 时校验 ``executor_acquisition_token == token``（handler 当前
        owner 路径，fencing）；``token`` 为 None 时跳过 token 校验（recovery 回收旧 token
        任务路径，由专属 owner lock 保证权威性）。
        """
        return await self._finalize_with_result(
            task_id=task_id,
            final_status="cancelled",
            result=result,
            error_message=None,
            expected_token=token,
        )

    async def finalize_timeout_with_result(
        self,
        task_id: str,
        token: Optional[str],
        result: Optional[Dict[str, Any]],
    ) -> bool:
        """原子终态：``failed(task_timeout)`` + partial result。"""
        return await self._finalize_with_result(
            task_id=task_id,
            final_status="failed",
            result=result,
            error_message="task_timeout",
            expected_token=token,
        )

    async def finalize_restarted_with_result(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]],
    ) -> bool:
        """原子终态：``failed(executor_restarted)`` + partial result（仅 recovery 调用）。

        不校验 token（被回收任务持有旧/NULL token，新 owner 由专属 owner lock 授权）。
        """
        return await self._finalize_with_result(
            task_id=task_id,
            final_status="failed",
            result=result,
            error_message="executor_restarted",
            expected_token=None,
        )

    async def _finalize_with_result(
        self,
        task_id: str,
        final_status: str,
        result: Optional[Dict[str, Any]],
        error_message: Optional[str],
        expected_token: Optional[str],
    ) -> bool:
        """行锁 + 双检 + partial result 同事务原子终态。

        - ``SELECT ... FOR UPDATE`` 串行化“旧事务提交”与“recovery”。
        - 双检类型/running；``expected_token`` 非 None 时校验 token（fencing）。
        - 写终态、result、completed_at（cancelled 另写 cancelled_at），同事务提交。
        """
        locked = await self.db.execute(
            select(AsyncTask).where(AsyncTask.task_id == task_id).with_for_update()
        )
        task = locked.scalar_one_or_none()
        if task is None:
            await self.db.rollback()
            return False
        if task.task_type not in _FENCED_TASK_TYPES or task.status != "running":
            await self.db.rollback()
            return False
        if expected_token is not None and task.executor_acquisition_token != expected_token:
            # 旧 token 不允许终态写入（fencing）。
            await self.db.rollback()
            return False

        now = datetime.now(timezone.utc)
        task.status = final_status
        task.result = result
        task.error_message = error_message
        task.completed_at = now
        if final_status == "cancelled":
            task.cancelled_at = now

        # 日志与终态同事务提交（_log_message 内部 commit）。
        await self._log_message(
            task_id,
            "INFO",
            f"Task finalized: {final_status}"
            + (f" ({error_message})" if error_message else ""),
        )
        return True

    async def recover_stale_market_metrics_tasks(
        self,
        current_token: str,
    ) -> Dict[str, int]:
        """回收旧 token（含 NULL）的 sync_market_metrics running（架构 §6.2.3）。

        第 17 期 plan-04 薄包装：委托通用 :meth:`recover_stale_fenced_tasks`
        （既有调用方/测试零改动）。
        """
        return await self.recover_stale_fenced_tasks(
            _MARKET_METRICS_TYPE, current_token
        )

    async def recover_stale_fenced_tasks(
        self,
        task_type: str,
        current_token: str,
    ) -> Dict[str, int]:
        """回收旧 token（含 NULL）的指定 fenced 类型 running（架构 §6.2.3）。

        由持对应专属 owner lock 的当前 acquisition 调用。逐行独立事务
        ``SELECT FOR UPDATE`` 后复核类型/running/旧 token；以任务参数、本地日历
        与已提交 ``dateResults`` 重建计数（``unprocessedDates`` = 范围交易日 −
        已处理日；未处理日不计入 failedCount）；按已持久化停止首因执行唯一终态
        （cancel/timeout/restarted 三分支；双字段同非空 critical 告警并按较早
        数据库时间选首因，同刻 cancel 优先）。

        Args:
            task_type: fenced 任务类型（``sync_market_metrics`` /
                ``sync_market_margin``）。
            current_token: 当前 owner 的 acquisition token。

        Returns:
            回收统计 ``{recovered, cancel, timeout, restarted, double_mark, skipped}``。
        """
        stats: Dict[str, int] = {
            "recovered": 0,
            "cancel": 0,
            "timeout": 0,
            "restarted": 0,
            "double_mark": 0,
            "skipped": 0,
        }

        # 候选：本类型 running 且 token IS DISTINCT FROM current_token（含 NULL）。
        candidate_rows = await self.db.execute(
            select(AsyncTask.task_id).where(
                AsyncTask.task_type == task_type,
                AsyncTask.status == "running",
                AsyncTask.executor_acquisition_token.is_distinct_from(current_token),
            )
        )
        candidate_ids = [row[0] for row in candidate_rows.all()]
        # 结束只读事务，确保逐行 recovery 各自独立事务。
        await self.db.commit()

        for tid in candidate_ids:
            branch = await self._recover_one_stale(tid, current_token, task_type)
            if branch in ("cancel", "timeout", "restarted"):
                stats["recovered"] += 1
                stats[branch] += 1
            else:
                stats[branch] += 1  # "skipped" 或 "double_mark"
        if stats["recovered"]:
            logger.info("%s recovery summary: %s", task_type, stats)
        return stats

    async def _recover_one_stale(
        self,
        task_id: str,
        current_token: str,
        task_type: str,
    ) -> str:
        """回收单条 stale running 任务，返回分支名。

        返回 ``cancel`` / ``timeout`` / ``restarted`` / ``double_mark`` / ``skipped``。
        ``double_mark`` 表示已按首因落终态（不变量破坏，仅记 critical 告警）。
        """
        locked = await self.db.execute(
            select(AsyncTask).where(AsyncTask.task_id == task_id).with_for_update()
        )
        task = locked.scalar_one_or_none()
        # 复核：类型/running/旧 token；不再 stale 则跳过。
        if (
            task is None
            or task.task_type != task_type
            or task.status != "running"
            or task.executor_acquisition_token == current_token
        ):
            await self.db.rollback()
            return "skipped"

        # 重建 partial result（任务参数 + 本地日历 + 已提交 dateResults）。
        result = await self._rebuild_recovery_result(task, task_type)

        cancel_at = task.cancel_requested_at
        timeout_at = task.timeout_requested_at
        double_mark = cancel_at is not None and timeout_at is not None
        double_mark_branch: Optional[str] = None
        if double_mark:
            # 不变量破坏：critical 告警，按较早数据库时间选首因（同刻 cancel 优先）。
            logger.critical(
                "INVARIANT BROKEN: task %s has both cancel_requested_at=%s and "
                "timeout_requested_at=%s; choosing earlier (cancel wins ties)",
                task_id,
                cancel_at,
                timeout_at,
            )
            branch = "cancel" if cancel_at <= timeout_at else "timeout"
            double_mark_branch = branch
        elif cancel_at is not None:
            branch = "cancel"
        elif timeout_at is not None:
            branch = "timeout"
        else:
            branch = "restarted"

        now = datetime.now(timezone.utc)
        task.result = result
        task.completed_at = now
        if branch == "cancel":
            task.status = "cancelled"
            task.cancelled_at = now
            task.error_message = None
            msg = "recovered as cancelled (cancel_requested_at set)"
        elif branch == "timeout":
            task.status = "failed"
            task.error_message = "task_timeout"
            msg = "recovered as failed(task_timeout)"
        else:
            task.status = "failed"
            task.error_message = "executor_restarted"
            msg = "recovered as failed(executor_restarted)"

        if double_mark_branch:
            msg += f" [double-mark invariant broken; chose {double_mark_branch}]"

        # 日志 + 终态同事务提交。
        await self._log_message(task_id, "WARNING", msg)
        if double_mark_branch:
            return "double_mark"
        return branch

    async def _rebuild_recovery_result(
        self,
        task: AsyncTask,
        task_type: str,
    ) -> Dict[str, Any]:
        """以任务参数、本地日历与已提交 ``dateResults`` 重建计数（按 task_type 参数化）。

        margin 与 market_metrics 的 dateResults 共用 ``tradeDate/status`` 口径
        （margin 无四类计数），计数重建逻辑一致：
        - range trading days = 本地日历 [start_date, end_date] 闭区间开市日
        - processed days = 已提交 result.dateResults 的 tradeDate 集合
        - unprocessedDates = range trading days − processed days
        - successCount/failedCount 只来自已处理 dateResults；未处理日不计入 failedCount
        - skippedCount 在 recovery 视角恒 0（休市日不在 trading days 内）

        缺失日历/参数时退化为仅基于已提交 dateResults 的计数，避免 recovery 阻塞。
        """
        existing_result = task.result if isinstance(task.result, dict) else {}
        date_results = existing_result.get("dateResults") or []

        success_count = sum(1 for d in date_results if d.get("status") == "success")
        failed_count = sum(1 for d in date_results if d.get("status") == "failed")

        # 计算未处理日（需要日期范围 + 本地日历）。
        unprocessed: List[str] = []
        processed_iso = {
            d.get("tradeDate") for d in date_results if d.get("tradeDate")
        }
        try:
            params = await self.get_task_params(task.task_id)
            start_raw = params.get("start_date")
            end_raw = params.get("end_date")
            if start_raw and end_raw:
                start = date.fromisoformat(str(start_raw))
                end = date.fromisoformat(str(end_raw))
                # 本地日历查询（同事务，不同表，无行锁冲突）。
                from src.services.trading_calendar_repository import (
                    TradingCalendarRepository,
                )
                cal = TradingCalendarRepository(self.db)
                trading_days = await cal.get_trading_days(start, end)
                unprocessed = [
                    d.isoformat() for d in trading_days if d.isoformat() not in processed_iso
                ]
        except Exception:
            # 日历/参数不可用时不阻塞 recovery；unprocessed 退化为空。
            logger.warning(
                "%s recovery rebuild: unable to compute unprocessedDates for task %s; "
                "falling back to committed dateResults only",
                task_type,
                task.task_id,
                exc_info=True,
            )
            unprocessed = []

        return {
            "successCount": success_count,
            "skippedCount": 0,
            "failedCount": failed_count,
            "dateResults": date_results,
            "unprocessedDates": unprocessed,
        }

    async def count_task_logs(
        self,
        task_id: str,
        level: Optional[str] = None,
    ) -> int:
        """统计任务日志真实总数（plan-04 admin logs total 修正，架构 §7.3）。"""
        query = select(func.count(AsyncTaskLog.id)).where(AsyncTaskLog.task_id == task_id)
        if level:
            query = query.where(AsyncTaskLog.level == level)
        result = await self.db.execute(query)
        return int(result.scalar() or 0)
