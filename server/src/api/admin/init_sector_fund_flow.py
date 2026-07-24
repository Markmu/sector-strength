"""
板块资金流即时快照同步管理 API 端点（13 期 plan-02）

提供板块资金流（同花顺即时，行业 + 概念）的手动同步入口，需要管理员权限。

复用声明：
- admin 触发范式：src/api/admin/init_funds.py（AsyncTask + TaskManager + require_admin + 并发保护）
- TaskType：src/services/task_handlers.py:71 SYNC_SECTOR_FUND_FLOW（plan-01 已建）
- 任务 handler：src/services/task_handlers.py:313 sync_sector_fund_flow_task（plan-01 已建）

契约（架构 §7.3 + plan-02 §3 #4）：
- 路径：admin 路由 router.py:29 以 include_router(admin_router, prefix="/v1/admin") 挂载，
  admin/__init__.py 的 APIRouter 无 prefix，init 子路由 prefix=/init + /sector-fund-flow
  = /api/v1/admin/init/sector-fund-flow
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.models.async_task import AsyncTask
from src.models.user import User
from src.services.task_handlers import TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/init", tags=["Admin - Sector Fund Flow"])


@router.post("/sector-fund-flow", response_model=ApiResponse[dict])
async def init_sector_fund_flow(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动同步板块资金流即时快照（AC-11）。

    创建 SYNC_SECTOR_FUND_FLOW 异步任务，从同花顺即时接口拉取行业 + 概念板块
    资金流快照并写入 sector_fund_flow 表（on_conflict 覆盖同分钟旧值）。
    """
    # 并发保护：检查是否有同类型 pending/running 任务
    running = await session.execute(
        select(AsyncTask).where(
            and_(
                AsyncTask.task_type == TaskType.SYNC_SECTOR_FUND_FLOW.value,
                AsyncTask.status.in_(["pending", "running"]),
            )
        )
    )
    if running.scalar_one_or_none():
        return ApiResponse(
            success=False,
            data=None,
            message="已有板块资金流同步任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_SECTOR_FUND_FLOW.value,
        params={},
        max_retries=3,
        timeout_seconds=3600,
        created_by=_admin.id,
    )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message="板块资金流同步任务已创建",
    )
