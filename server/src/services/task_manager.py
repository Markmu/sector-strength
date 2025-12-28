"""异步任务管理器

负责任务的创建、查询、取消等操作。
"""

import uuid
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.async_task import AsyncTask, AsyncTaskParam, AsyncTaskLog


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
                    value=json.dumps(value) if not isinstance(value, str) else value
                )
                self.db.add(param)

        await self.db.commit()
        await self.db.refresh(task)

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

    async def start_task(self, task_id: str) -> bool:
        """
        标记任务开始执行

        Args:
            task_id: 任务ID

        Returns:
            是否成功标记
        """
        result = await self.db.execute(
            update(AsyncTask)
            .where(AsyncTask.task_id == task_id)
            .values(
                status="running",
                started_at=datetime.now(timezone.utc),
            )
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
        limit: int = 50,
        offset: int = 0,
    ) -> List[AsyncTask]:
        """
        列出任务

        Args:
            status: 状态过滤
            task_type: 任务类型过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            任务列表
        """
        query = select(AsyncTask)

        if status:
            query = query.where(AsyncTask.status == status)
        if task_type:
            query = query.where(AsyncTask.task_type == task_type)

        query = query.order_by(AsyncTask.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_tasks(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> int:
        """
        统计任务数量

        Args:
            status: 状态过滤
            task_type: 任务类型过滤

        Returns:
            任务数量
        """
        from sqlalchemy import func

        query = select(func.count(AsyncTask.id))

        if status:
            query = query.where(AsyncTask.status == status)
        if task_type:
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
