"""
券商月度金股同步管理 API 端点

提供券商月度金股数据的手动同步入口，需要管理员权限。
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.models.async_task import AsyncTask
from src.models.user import User
from src.services.task_handlers import TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/init", tags=["Admin - Broker Recommend Init"])


class InitBrokerRecommendRequest(BaseModel):
    """券商月度金股同步请求模型"""
    month: str = Field(
        ...,
        description="月份，格式 YYYYMM",
        pattern=r"^\d{6}$",
    )


@router.post("/broker-recommend", response_model=ApiResponse[dict])
async def init_broker_recommend(
    request: InitBrokerRecommendRequest,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动同步券商月度金股数据

    创建 SYNC_BROKER_RECOMMEND 异步任务，从 Tushare 按月拉取券商金股数据。
    """
    # 并发保护：检查是否有同类型 running 任务
    running = await session.execute(
        select(AsyncTask).where(
            and_(
                AsyncTask.task_type == TaskType.SYNC_BROKER_RECOMMEND.value,
                AsyncTask.status.in_(["pending", "running"]),
            )
        )
    )
    if running.scalar_one_or_none():
        return ApiResponse(
            success=False,
            data=None,
            message="已有券商金股同步任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_BROKER_RECOMMEND.value,
        params={"month": request.month},
        max_retries=3,
        timeout_seconds=3600,
        created_by=_admin.id,
    )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message=f"券商金股同步任务已创建（月份: {request.month}）",
    )
