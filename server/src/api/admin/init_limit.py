"""涨停专题数据同步管理 API 端点

提供手动触发涨停专题三表（limit_list_d / limit_step / limit_cpt_list）同步的入口，
需要管理员权限。

复用声明：
- admin 触发范式：src/api/admin/init_etf_daily.py（AsyncTask + TaskManager +
  require_admin + 并发保护）
- TaskType：src/services/task_handlers.py SYNC_LIMIT_DATA
- 任务 handler：src/services/task_handlers.py sync_limit_data_task

契约：
- 路径：admin 路由 router.py 以 include_router(admin_router, prefix="/v1/admin") 挂载，
  admin/__init__.py 的 APIRouter 无 prefix，init 子路由 prefix=/init + /limit
  = /api/v1/admin/init/limit
- 安全：require_admin 鉴权；并发保护防重复同步。
- 可选参数 trade_date（YYYYMMDD），未传时 handler 自动取最新交易日。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Body
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.models.async_task import AsyncTask
from src.models.user import User
from src.services.task_handlers import TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/init", tags=["Admin - Limit"])


@router.post("/limit", response_model=ApiResponse[dict])
async def init_limit(
    trade_date: Optional[str] = Body(None, embed=True),
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动触发涨停专题三表同步。

    创建 SYNC_LIMIT_DATA 异步任务，从 Tushare 拉取指定交易日的涨跌停明细、
    连板天梯、涨停最强板块，按 trade_date 删旧插新写入三张表。

    Args:
        trade_date: 可选交易日（YYYYMMDD），未传时自动取最新交易日。
    """
    # 并发保护：检查是否有同类型 pending/running 任务
    running = await session.execute(
        select(AsyncTask).where(
            and_(
                AsyncTask.task_type == TaskType.SYNC_LIMIT_DATA.value,
                AsyncTask.status.in_(["pending", "running"]),
            )
        )
    )
    if running.scalar_one_or_none():
        return ApiResponse(
            success=False,
            data=None,
            message="已有涨停专题同步任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    params = {"trade_date": trade_date} if trade_date else {}

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_LIMIT_DATA.value,
        params=params,
        max_retries=3,
        timeout_seconds=600,
        created_by=_admin.id,
    )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message=f"涨停专题同步任务已创建{f' (trade_date={trade_date})' if trade_date else ' (最新交易日)'}",
    )
