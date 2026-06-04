"""
基金数据同步管理 API 端点

提供基金基本信息和持仓明细的手动同步入口，需要管理员权限。
"""

import logging
from typing import Optional

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

router = APIRouter(prefix="/init", tags=["Admin - Fund Init"])


class InitFundPortfolioRequest(BaseModel):
    """基金持仓同步请求模型"""
    period: str = Field(
        ...,
        description="报告期，格式 YYYYMMDD",
        pattern=r"^\d{8}$",
    )


@router.post("/funds", response_model=ApiResponse[dict])
async def init_fund_basic(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动同步基金基本信息

    创建 SYNC_FUND_BASIC 异步任务，从 Tushare 拉取基金列表并 upsert 到 funds 表。
    """
    # 并发保护：检查是否有同类型 running 任务
    running = await session.execute(
        select(AsyncTask).where(
            and_(
                AsyncTask.task_type == TaskType.SYNC_FUND_BASIC.value,
                AsyncTask.status.in_(["pending", "running"]),
            )
        )
    )
    if running.scalar_one_or_none():
        return ApiResponse(
            success=False,
            data=None,
            message="已有基金基本信息同步任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_FUND_BASIC.value,
        params={},
        max_retries=3,
        timeout_seconds=14400,
        created_by=_admin.id,
    )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message="基金基本信息同步任务已创建",
    )


@router.post("/fund-portfolio", response_model=ApiResponse[dict])
async def init_fund_portfolio(
    request: InitFundPortfolioRequest,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动同步基金持仓明细

    创建 SYNC_FUND_PORTFOLIO 异步任务，从 Tushare 拉取指定报告期的持仓数据。
    """
    # 并发保护：检查是否有同类型 running 任务
    running = await session.execute(
        select(AsyncTask).where(
            and_(
                AsyncTask.task_type == TaskType.SYNC_FUND_PORTFOLIO.value,
                AsyncTask.status.in_(["pending", "running"]),
            )
        )
    )
    if running.scalar_one_or_none():
        return ApiResponse(
            success=False,
            data=None,
            message="已有基金持仓同步任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_FUND_PORTFOLIO.value,
        params={"period": request.period},
        max_retries=3,
        timeout_seconds=28800,  # 8小时，逐基金拉取约需5-6小时
        created_by=_admin.id,
    )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message=f"基金持仓同步任务已创建（报告期: {request.period}）",
    )