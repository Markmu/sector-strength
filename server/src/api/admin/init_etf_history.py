"""
ETF 历史数据回填管理 API 端点（第 14 期 plan-02）

提供按日期范围回填历史 ETF 数据的手动入口，需要管理员权限。

复用声明：
- admin 触发范式：src/api/admin/init_sector_fund_flow.py（AsyncTask + TaskManager +
  require_admin + 并发保护）+ src/api/admin/init_funds.py（Pydantic 请求体）
- TaskType：src/services/task_handlers.py BACKFILL_ETF_HISTORY（plan-02 §3 #2）
- 任务 handler：src/services/task_handlers.py backfill_etf_history_task（plan-02 §3 #2）
- 回填实现：src/services/data_init_etf.py EtfDataInitService.backfill_etf_history
  （复用 plan-01 的 sync_etf_daily 同口径，ADR-5）

契约（架构 §2.4 AC-14 + plan-02 §3 #3）：
- 路径：admin 路由 router.py 以 include_router(admin_router, prefix="/v1/admin") 挂载，
  admin/__init__.py 的 APIRouter 无 prefix，init 子路由 prefix=/init + /etf-history
  = /api/v1/admin/init/etf-history
- 安全（架构 §8.3）：require_admin 鉴权；并发保护防重复回填；日期范围上限防滥用。
- 可观测性（架构 §8.5）：AsyncTask 记录 progress/total 与逐日 log_message。
"""

import logging
from datetime import date

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

router = APIRouter(prefix="/init", tags=["Admin - ETF History"])

# 回填日期范围上限（10 年），与 service 层 / 架构 §8.3 防滥用约束一致
_MAX_BACKSPAN_DAYS = 3650


class EtfHistoryPayload(BaseModel):
    """ETF 历史回填请求参数。"""

    start_date: str = Field(
        ...,
        description="起始日期，格式 YYYY-MM-DD",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    end_date: str = Field(
        ...,
        description="结束日期，格式 YYYY-MM-DD",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )


@router.post("/etf-history", response_model=ApiResponse[dict])
async def init_etf_history(
    payload: EtfHistoryPayload,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动触发 ETF 历史数据回填（AC-14）。

    创建 BACKFILL_ETF_HISTORY 异步任务，按日期升序逐日复用 sync_etf_daily
    同口径回填 etf_daily（on_conflict 覆盖），保证趋势曲线无断裂。
    """
    # 日期校验：start/end 非空（Pydantic 已保证），start <= end，范围上限防滥用
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

    # 并发保护：检查是否有同类型 pending/running 任务（仿 init_sector_fund_flow.py:46-59）
    running = await session.execute(
        select(AsyncTask).where(
            and_(
                AsyncTask.task_type == TaskType.BACKFILL_ETF_HISTORY.value,
                AsyncTask.status.in_(["pending", "running"]),
            )
        )
    )
    if running.scalar_one_or_none():
        return ApiResponse(
            success=False,
            data=None,
            message="已有 ETF 历史回填任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.BACKFILL_ETF_HISTORY.value,
        params={
            "start_date": payload.start_date,
            "end_date": payload.end_date,
        },
        max_retries=1,
        timeout_seconds=14400,
        created_by=_admin.id,
    )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message=f"ETF 历史回填任务已创建（{payload.start_date} ~ {payload.end_date}）",
    )
