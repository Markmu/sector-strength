"""
数据状态 API 端点

提供数据状态查询和一键补齐触发接口，需要管理员权限。
"""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.services.data_status import DataStatusService
from src.services.task_manager import TaskManager
from src.services.task_handlers import TaskType
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["Admin - Data Status"])

# 数据类型到 TaskType 的映射
_DATA_TYPE_TO_TASK_TYPE = {
    "history": TaskType.BACKFILL_HISTORY,
    "ma": TaskType.BACKFILL_MA,
    "strength": TaskType.BACKFILL_STRENGTH,
}


@router.get("/status")
async def get_data_status(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    获取三类板块数据（历史、均线、强度）的时效性状态

    返回每类数据的最新日期、状态标记、缺失范围和活跃任务信息。
    """
    service = DataStatusService(db)
    result = await service.get_status()
    return ApiResponse(success=True, data=result)


@router.post("/backfill/{type}")
async def trigger_backfill(
    type: Literal["history", "ma", "strength"],
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    触发指定类型数据的补齐任务

    自动检测缺失范围并创建补齐任务。
    - 同类型已有活跃任务时返回 409
    - 无缺失数据时返回 400
    """
    service = DataStatusService(db)

    # 检查是否有活跃任务
    if await service.has_active_task(type):
        raise HTTPException(
            status_code=409,
            detail="该类数据已有补齐任务正在执行",
        )

    # 获取补齐范围
    backfill_range = await service.get_backfill_range(type)
    if backfill_range is None:
        raise HTTPException(
            status_code=400,
            detail="该类数据无缺失",
        )

    start, end = backfill_range

    # 创建补齐任务
    task_manager = TaskManager(db)
    task_type = _DATA_TYPE_TO_TASK_TYPE[type]
    task = await task_manager.create_task(
        task_type=task_type,
        params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        created_by=str(_admin.id) if _admin else None,
    )

    # 提交事务以持久化任务
    await db.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message=f"已创建{type}补齐任务",
    )
