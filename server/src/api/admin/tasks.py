"""
异步任务 API 端点

提供异步任务的创建、查询、取消等操作，需要管理员权限。
"""

import logging
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.services.task_manager import TaskManager
from src.services.task_executor import TaskRegistry
from src.models.async_task import AsyncTask
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Admin - Tasks"])
SECTOR_MIGRATION_CONFIRM_KEY = "confirm_truncate_executed"
SECTOR_MIGRATION_TASK_TYPES = {"init_sectors", "init_sector_historical_data"}


# ============== 请求/响应模型 ==============

class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    task_type: str = Field(..., description="任务类型")
    params: Optional[dict] = Field(None, description="任务参数")
    max_retries: int = Field(3, ge=0, le=10, description="最大重试次数")
    timeout_seconds: int = Field(14400, ge=60, le=86400, description="超时时间（秒）")


class TaskResponse(BaseModel):
    """任务响应"""
    taskId: str = Field(..., description="任务ID")
    taskType: str = Field(..., description="任务类型")
    status: str = Field(..., description="任务状态")
    progress: int = Field(0, description="当前进度")
    total: int = Field(0, description="总数")
    percent: int = Field(0, description="进度百分比")
    errorMessage: Optional[str] = Field(None, description="错误信息")
    retryCount: int = Field(0, description="重试次数")
    maxRetries: int = Field(3, description="最大重试次数")
    timeoutSeconds: int = Field(14400, description="超时时间（秒）")
    createdBy: Optional[str] = Field(None, description="创建者ID")
    createdAt: Optional[str] = Field(None, description="创建时间")
    startedAt: Optional[str] = Field(None, description="开始时间")
    completedAt: Optional[str] = Field(None, description="完成时间")
    cancelledAt: Optional[str] = Field(None, description="取消时间")


class TaskDetailResponse(TaskResponse):
    """任务详情响应"""
    params: Optional[dict] = Field(None, description="任务参数")


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")
    page: int = Field(1, description="页码")
    pageSize: int = Field(50, description="每页数量")


class TaskLogResponse(BaseModel):
    """任务日志响应"""
    id: int = Field(..., description="日志ID")
    taskId: str = Field(..., description="任务ID")
    level: str = Field(..., description="日志级别")
    message: str = Field(..., description="日志消息")
    createdAt: Optional[str] = Field(None, description="创建时间")


class TaskLogListResponse(BaseModel):
    """任务日志列表响应"""
    logs: List[TaskLogResponse] = Field(..., description="日志列表")
    total: int = Field(..., description="总数")
    page: int = Field(1, description="页码")


def _validate_task_create_request(request: CreateTaskRequest) -> Optional[str]:
    """校验任务创建参数语义，避免非法迁移任务进入队列。"""
    params = request.params or {}

    if request.task_type in SECTOR_MIGRATION_TASK_TYPES:
        if not params.get(SECTOR_MIGRATION_CONFIRM_KEY, False):
            return (
                f"板块迁移任务必须显式提供 `{SECTOR_MIGRATION_CONFIRM_KEY}=true`，"
                "并确认已人工执行清空脚本。"
            )

    if request.task_type == "init_sectors":
        sector_type = params.get("sector_type")
        if sector_type is not None and sector_type not in {"industry", "concept"}:
            return "init_sectors 的 sector_type 仅支持 industry/concept。"

    if request.task_type == "init_sector_historical_data":
        has_days = params.get("days") is not None
        has_range = bool(params.get("start_date")) and bool(params.get("end_date"))
        if not (has_days or has_range):
            return "init_sector_historical_data 需提供 days 或 start_date+end_date。"
        if has_days:
            days = params.get("days")
            if not isinstance(days, int) or days < 1 or days > 365:
                return "init_sector_historical_data 的 days 必须是 1-365 的整数。"
        if has_range:
            try:
                start_date = date.fromisoformat(params["start_date"])
                end_date = date.fromisoformat(params["end_date"])
            except ValueError:
                return "start_date/end_date 必须是 YYYY-MM-DD 格式。"
            if start_date > end_date:
                return "start_date 不能晚于 end_date。"

    return None


# ============== API 端点 ==============

@router.post("", response_model=ApiResponse[TaskResponse])
async def create_task(
    request: CreateTaskRequest,
    session: AsyncSession = Depends(get_session),
    _admin = Depends(require_admin),
):
    """
    创建新任务

    Args:
        request: 创建任务请求
        session: 数据库会话
        _admin: 管理员权限验证

    Returns:
        创建的任务信息
    """
    # 验证任务类型是否已注册
    registered_tasks = TaskRegistry.list_registered_tasks()
    if request.task_type not in registered_tasks:
        return ApiResponse(
            success=False,
            data=None,
            message=f"未知的任务类型: {request.task_type}。"
                    f"可用类型: {', '.join(registered_tasks)}"
        )

    validation_error = _validate_task_create_request(request)
    if validation_error:
        return ApiResponse(success=False, data=None, message=validation_error)

    manager = TaskManager(session)

    # 获取当前用户ID
    from src.core.deps import get_current_user
    current_user = _admin  # admin is actually the user object
    user_id = str(current_user.id) if current_user else None

    # 创建任务
    task = await manager.create_task(
        task_type=request.task_type,
        params=request.params or {},
        max_retries=request.max_retries,
        timeout_seconds=request.timeout_seconds,
        created_by=user_id,
    )

    logger.info(f"Task created: {task.task_id} (type: {task.task_type}) by user {user_id}")

    return ApiResponse(
        success=True,
        data=task.to_dict(),
        message=f"任务已创建: {task.task_id}"
    )


@router.get("", response_model=ApiResponse[TaskListResponse])
async def list_tasks(
    status: Optional[str] = Query(None, description="状态过滤"),
    task_type: Optional[str] = Query(None, description="任务类型过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    _admin = Depends(require_admin),
):
    """
    获取任务列表

    Args:
        status: 状态过滤
        task_type: 任务类型过滤
        page: 页码
        page_size: 每页数量
        session: 数据库会话
        _admin: 管理员权限验证

    Returns:
        任务列表
    """
    manager = TaskManager(session)

    # 计算偏移量
    offset = (page - 1) * page_size

    # 获取任务列表
    tasks = await manager.list_tasks(
        status=status,
        task_type=task_type,
        limit=page_size,
        offset=offset,
    )

    # 获取总数
    total = await manager.count_tasks(
        status=status,
        task_type=task_type,
    )

    return ApiResponse(
        success=True,
        data=TaskListResponse(
            tasks=[task.to_dict() for task in tasks],
            total=total,
            page=page,
            pageSize=page_size,
        )
    )


@router.get("/registered", response_model=ApiResponse[List[str]])
async def get_registered_tasks(
    _admin = Depends(require_admin),
):
    """
    获取已注册的任务类型列表

    Returns:
        任务类型列表
    """
    registered_tasks = TaskRegistry.list_registered_tasks()
    return ApiResponse(
        success=True,
        data=registered_tasks,
        message=f"已注册 {len(registered_tasks)} 种任务类型"
    )


@router.get("/{task_id}", response_model=ApiResponse[TaskDetailResponse])
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    _admin = Depends(require_admin),
):
    """
    获取任务详情

    Args:
        task_id: 任务ID
        session: 数据库会话
        _admin: 管理员权限验证

    Returns:
        任务详情
    """
    manager = TaskManager(session)

    # 获取任务
    task = await manager.get_task(task_id)
    if not task:
        return ApiResponse(
            success=False,
            data=None,
            message=f"任务不存在: {task_id}"
        )

    # 获取任务参数
    params = await manager.get_task_params(task_id)

    # 组合响应
    task_dict = task.to_dict()
    task_dict["params"] = params

    return ApiResponse(
        success=True,
        data=TaskDetailResponse(**task_dict)
    )


@router.post("/{task_id}/cancel", response_model=ApiResponse[dict])
async def cancel_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    _admin = Depends(require_admin),
):
    """
    取消任务

    Args:
        task_id: 任务ID
        session: 数据库会话
        _admin: 管理员权限验证

    Returns:
        操作结果
    """
    manager = TaskManager(session)

    # 检查任务是否存在
    task = await manager.get_task(task_id)
    if not task:
        return ApiResponse(
            success=False,
            data=None,
            message=f"任务不存在: {task_id}"
        )

    # 尝试取消
    success = await manager.cancel_task(task_id)

    if not success:
        status_msg = f"当前状态为 {task.status}，无法取消"
        return ApiResponse(
            success=False,
            data=None,
            message=status_msg
        )

    logger.info(f"Task cancelled: {task_id} by admin")

    return ApiResponse(
        success=True,
        data={"taskId": task_id, "cancelled": True},
        message=f"任务已取消: {task_id}"
    )


@router.get("/{task_id}/logs", response_model=ApiResponse[TaskLogListResponse])
async def get_task_logs(
    task_id: str,
    level: Optional[str] = Query(None, description="日志级别过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    _admin = Depends(require_admin),
):
    """
    获取任务日志

    Args:
        task_id: 任务ID
        level: 日志级别过滤
        page: 页码
        page_size: 每页数量
        session: 数据库会话
        _admin: 管理员权限验证

    Returns:
        任务日志列表
    """
    manager = TaskManager(session)

    # 检查任务是否存在
    task = await manager.get_task(task_id)
    if not task:
        return ApiResponse(
            success=False,
            data=None,
            message=f"任务不存在: {task_id}"
        )

    # 计算偏移量
    offset = (page - 1) * page_size

    # 获取日志
    logs = await manager.get_task_logs(
        task_id=task_id,
        level=level,
        limit=page_size,
        offset=offset,
    )

    return ApiResponse(
        success=True,
        data=TaskLogListResponse(
            logs=[log.to_dict() for log in logs],
            total=len(logs),
            page=page,
        )
    )


@router.get("/stats/summary", response_model=ApiResponse[dict])
async def get_task_stats(
    session: AsyncSession = Depends(get_session),
    _admin = Depends(require_admin),
):
    """
    获取任务统计信息

    Returns:
        任务统计信息
    """
    manager = TaskManager(session)

    # 统计各状态任务数量
    stats = {
        "pending": await manager.count_tasks(status="pending"),
        "running": await manager.count_tasks(status="running"),
        "completed": await manager.count_tasks(status="completed"),
        "failed": await manager.count_tasks(status="failed"),
        "cancelled": await manager.count_tasks(status="cancelled"),
        "total": await manager.count_tasks(),
    }

    return ApiResponse(
        success=True,
        data=stats,
        message="任务统计信息"
    )
