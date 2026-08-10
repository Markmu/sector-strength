"""涨停专题数据同步管理 API 端点

提供手动触发涨停专题三表（limit_list_d / limit_step / limit_cpt_list）同步的入口，
需要管理员权限。

复用声明：
- admin 触发范式：src/api/admin/init_etf_history.py（Pydantic 请求体 + AsyncTask +
  TaskManager + require_admin + 并发保护 + 日期范围校验）
- TaskType：src/services/task_handlers.py SYNC_LIMIT_DATA
- 任务 handler：src/services/task_handlers.py sync_limit_data_task

契约：
- 路径：admin 路由 router.py 以 include_router(admin_router, prefix="/v1/admin") 挂载，
  admin/__init__.py 的 APIRouter 无 prefix，init 子路由 prefix=/init + /limit
  = /api/v1/admin/init/limit
- 安全：require_admin 鉴权；并发保护防重复同步；日期范围上限防滥用。
- 可选参数 start_date/end_date（YYYY-MM-DD）：
  - 同时出现 → 按日期范围逐交易日同步；
  - 同时缺省 → 自动取最新交易日（单日）；
  - 仅出现其一 → 拒绝（400 success=False）。
"""

import logging
from datetime import date
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

router = APIRouter(prefix="/init", tags=["Admin - Limit"])

# 同步日期范围上限（10 年），与 service 层 / init_etf_history 防滥用约束一致
_MAX_BACKSPAN_DAYS = 3650


class LimitSyncPayload(BaseModel):
    """涨停专题同步请求参数。"""

    start_date: Optional[str] = Field(
        None,
        description="起始日期，格式 YYYY-MM-DD；与 end_date 同时出现=范围同步",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    end_date: Optional[str] = Field(
        None,
        description="结束日期，格式 YYYY-MM-DD；与 start_date 同时出现=范围同步",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )


@router.post("/limit", response_model=ApiResponse[dict])
async def init_limit(
    payload: LimitSyncPayload,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动触发涨停专题三表同步。

    创建 SYNC_LIMIT_DATA 异步任务，从 Tushare 拉取涨跌停明细、连板天梯、
    涨停最强板块，按 trade_date 删旧插新写入三张表。

    - start_date + end_date 都给 → 按日期范围逐交易日同步；
    - 都不给 → 自动取最新交易日（单日）。
    """
    has_start = payload.start_date is not None
    has_end = payload.end_date is not None

    # 起止必须同时出现或同时缺省
    if has_start != has_end:
        return ApiResponse(
            success=False,
            data=None,
            message="请同时选择起止日期，或都留空同步最新交易日",
        )

    params: dict = {}
    message_suffix = "最新交易日"

    if has_start and has_end:
        # 日期解析 + 顺序 + 范围上限校验
        try:
            start = date.fromisoformat(payload.start_date)
            end = date.fromisoformat(payload.end_date)
        except ValueError:
            return ApiResponse(
                success=False,
                data=None,
                message="日期格式无效，要求 YYYY-MM-DD",
            )

        if start > end:
            return ApiResponse(
                success=False,
                data=None,
                message="开始日期不能晚于结束日期",
            )

        if (end - start).days > _MAX_BACKSPAN_DAYS:
            return ApiResponse(
                success=False,
                data=None,
                message=f"日期范围不能超过 10 年（{_MAX_BACKSPAN_DAYS} 天）",
            )

        params = {
            "start_date": payload.start_date,
            "end_date": payload.end_date,
        }
        message_suffix = f"{payload.start_date} ~ {payload.end_date}"

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
        message=f"涨停专题同步任务已创建（{message_suffix}）",
    )
