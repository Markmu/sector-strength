"""ETF 当日份额采集管理 API 端点（第 14 期 plan-03）

提供手动触发 ETF 当日份额/净值采集的入口，需要管理员权限。

复用声明：
- admin 触发范式：src/api/admin/init_sector_fund_flow.py（AsyncTask + TaskManager +
  require_admin + 并发保护）
- TaskType：src/services/task_handlers.py SYNC_ETF_DAILY（plan-01 已建）
- 任务 handler：src/services/task_handlers.py sync_etf_daily_task（plan-01 已建）

契约（架构 §7.3 + plan-03 §3 #4）：
- 路径：admin 路由 router.py 以 include_router(admin_router, prefix="/v1/admin") 挂载，
  admin/__init__.py 的 APIRouter 无 prefix，init 子路由 prefix=/init + /etf-daily
  = /api/v1/admin/init/etf-daily
- 安全（架构 §8.3）：require_admin 鉴权；并发保护防重复采集。
- 可观测性（架构 §8.5）：AsyncTask 记录 progress/total 与逐 ETF log_message。
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

router = APIRouter(prefix="/init", tags=["Admin - ETF Daily"])


@router.post("/etf-daily", response_model=ApiResponse[dict])
async def init_etf_daily(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动触发 ETF 当日份额/净值采集（AC-12）。

    创建 SYNC_ETF_DAILY 异步任务，从 Tushare 拉取当日全量 ETF 的份额/净值，
    计算 share_change / net_inflow 后写入 etf_daily 表（on_conflict 覆盖）。
    复用 plan-01 的 sync_etf_daily 同口径方法（ADR-5）。
    """
    # 并发保护：检查是否有同类型 pending/running 任务（仿 init_sector_fund_flow.py:46-59）
    running = await session.execute(
        select(AsyncTask).where(
            and_(
                AsyncTask.task_type == TaskType.SYNC_ETF_DAILY.value,
                AsyncTask.status.in_(["pending", "running"]),
            )
        )
    )
    if running.scalar_one_or_none():
        return ApiResponse(
            success=False,
            data=None,
            message="已有 ETF 当日采集任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_ETF_DAILY.value,
        params={},
        max_retries=3,
        timeout_seconds=3600,
        created_by=_admin.id,
    )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message="ETF 当日采集任务已创建",
    )
