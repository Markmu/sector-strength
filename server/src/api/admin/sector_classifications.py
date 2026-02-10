"""
板块分类管理 API 端点

提供板块分类数据初始化、增量更新和状态查询的管理接口，需要管理员权限。
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.api.schemas.sector_classification import (
    InitializeClassificationRequest,
    UpdateDailyClassificationRequest,
    ClassificationStatusResponse
)
from src.services.task_manager import TaskManager
from src.services.task_handlers import TaskType
from src.services.sector_classification_service import SectorClassificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sector-classification", tags=["Admin - Sector Classification"])


# ============== 辅助函数 ==============

async def _check_duplicate_task(
    manager: TaskManager,
    task_type: str,
    params: dict
) -> bool:
    """检查是否有相同参数的任务正在运行"""
    running_tasks = await manager.list_tasks(status="running", task_type=task_type)

    for task in running_tasks:
        # 获取任务参数进行比较
        task_params = task.params if hasattr(task, 'params') else {}
        # 简化比较：只比较关键字段
        if task_type == TaskType.INIT_SECTOR_CLASSIFICATIONS:
            if (task_params.get("start_date") == params.get("start_date") and
                task_params.get("overwrite") == params.get("overwrite")):
                return True
        elif task_type == TaskType.UPDATE_SECTOR_CLASSIFICATION_DAILY:
            if (task_params.get("target_date") == params.get("target_date") and
                task_params.get("overwrite") == params.get("overwrite")):
                return True

    return False


# ============== API 端点 ==============

@router.post("/initialize", response_model=ApiResponse[dict])
async def initialize_classifications(
    request: InitializeClassificationRequest,
    session: AsyncSession = Depends(get_session),
    _admin = Depends(require_admin),
):
    """
    初始化板块分类历史数据

    从指定起始日期（或每个板块最早日期）开始计算并保存所有板块的分类数据。

    Args:
        request: 初始化请求参数
        session: 数据库会话
        _admin: 管理员权限验证

    Returns:
        包含任务ID的响应

    Raises:
        400: 相同参数的任务正在运行
    """
    # 准备任务参数
    params = {
        "start_date": request.start_date,
        "overwrite": request.overwrite
    }

    # 检查是否有相同参数的任务正在运行
    manager = TaskManager(session)
    if await _check_duplicate_task(manager, TaskType.INIT_SECTOR_CLASSIFICATIONS.value, params):
        return ApiResponse(
            success=False,
            data=None,
            message="相同参数的初始化任务正在运行中，请勿重复发起"
        )

    # 创建异步任务
    task = await manager.create_task(
        task_type=TaskType.INIT_SECTOR_CLASSIFICATIONS.value,
        params=params,
        max_retries=1,  # 初始化任务失败后不自动重试
        timeout_seconds=3600,  # 1小时超时
        created_by=str(_admin.id) if _admin else None,
    )

    logger.info(
        f"板块分类初始化任务已创建: task_id={task.task_id}, "
        f"start_date={request.start_date or 'earliest'}, overwrite={request.overwrite}"
    )

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message=f"板块分类初始化任务已创建，任务ID: {task.task_id}。请通过任务管理接口查看进度。"
    )


@router.post("/update-daily", response_model=ApiResponse[dict])
async def update_daily_classification(
    request: UpdateDailyClassificationRequest,
    session: AsyncSession = Depends(get_session),
    _admin = Depends(require_admin),
):
    """
    每日增量更新板块分类

    计算并保存指定日期（默认为今天）的板块分类数据。

    Args:
        request: 更新请求参数
        session: 数据库会话
        _admin: 管理员权限验证

    Returns:
        包含任务ID的响应
    """
    # 准备任务参数
    params = {
        "target_date": request.target_date,
        "overwrite": request.overwrite
    }

    # 检查是否有相同参数的任务正在运行
    manager = TaskManager(session)
    if await _check_duplicate_task(manager, TaskType.UPDATE_SECTOR_CLASSIFICATION_DAILY.value, params):
        return ApiResponse(
            success=False,
            data=None,
            message="相同日期的更新任务正在运行中，请勿重复发起"
        )

    # 创建异步任务
    task = await manager.create_task(
        task_type=TaskType.UPDATE_SECTOR_CLASSIFICATION_DAILY.value,
        params=params,
        max_retries=1,
        timeout_seconds=600,  # 10分钟超时
        created_by=str(_admin.id) if _admin else None,
    )

    logger.info(
        f"板块分类每日更新任务已创建: task_id={task.task_id}, "
        f"target_date={request.target_date or 'today'}, overwrite={request.overwrite}"
    )

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message=f"板块分类每日更新任务已创建，任务ID: {task.task_id}。请通过任务管理接口查看进度。"
    )


@router.get("/status", response_model=ApiResponse[ClassificationStatusResponse])
async def get_classification_status(
    session: AsyncSession = Depends(get_session),
    _admin = Depends(require_admin),
):
    """
    获取板块分类数据状态

    返回最新分类日期、板块数量统计等信息。

    Args:
        session: 数据库会话
        _admin: 管理员权限验证

    Returns:
        分类状态统计信息
    """
    service = SectorClassificationService(session)
    status = await service.get_classification_status()

    return ApiResponse(
        success=True,
        data=status,
        message="获取分类状态成功"
    )
