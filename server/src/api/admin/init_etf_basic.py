"""ETF 基础信息同步管理 API 端点

提供手动触发 ETF 基础信息（代码/名称/跟踪指数/分类）同步的入口，需要管理员权限。

复用声明：
- admin 触发范式：src/api/admin/init_etf_daily.py（AsyncTask + TaskManager +
  require_admin + 并发保护）
- TaskType：src/services/task_handlers.py SYNC_ETF_BASIC
- 任务 handler：src/services/task_handlers.py sync_etf_basic_task
- 采集实现：src/services/data_init_etf.py EtfDataInitService.sync_etf_basic

契约：
- 路径：/api/v1/admin/init/etf-basic（admin 路由 prefix=/v1/admin，init 子路由
  prefix=/init + /etf-basic）
- 安全：require_admin 鉴权；并发保护防重复同步。
- 可观测性：AsyncTask 记录 progress/total 与逐 ETF log_message。
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

router = APIRouter(prefix="/init", tags=["Admin - ETF Basic"])


@router.post("/etf-basic", response_model=ApiResponse[dict])
async def init_etf_basic(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动触发 ETF 基础信息同步。

    创建 SYNC_ETF_BASIC 异步任务，从 Tushare 拉取全市场 ETF 基础信息，
    跟踪指数用官方 index_code / index_name 直接入库（etf_basic 接口）。
    与当日份额采集独立，便于单独刷新指数归类或补全新上市 ETF。
    """
    # 并发保护：检查是否有同类型 pending/running 任务
    running = await session.execute(
        select(AsyncTask).where(
            and_(
                AsyncTask.task_type == TaskType.SYNC_ETF_BASIC.value,
                AsyncTask.status.in_(["pending", "running"]),
            )
        )
    )
    if running.scalar_one_or_none():
        return ApiResponse(
            success=False,
            data=None,
            message="已有 ETF 基础信息同步任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_ETF_BASIC.value,
        params={},
        max_retries=3,
        timeout_seconds=3600,
        created_by=_admin.id,
    )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message="ETF 基础信息同步任务已创建",
    )
