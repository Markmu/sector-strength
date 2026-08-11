"""关键指数数据同步管理 API 端点（第 15 期 plan-02）

提供手动触发关键指数基础信息同步、历史回填与当日增量采集的入口，
需要管理员权限。

复用声明：
- admin 触发范式：src/api/admin/init_etf_daily.py（AsyncTask + TaskManager +
  require_admin + 并发保护）+ src/api/admin/init_etf_history.py（Pydantic 请求体）
- TaskType：src/services/task_handlers.py SYNC_INDEX_BASIC /
  BACKFILL_INDEX_HISTORY / SYNC_INDEX_DAILY（plan-02 §3 #3 已建）
- 任务 handler：src/services/task_handlers.py sync_index_basic_task /
  backfill_index_history_task / sync_index_daily_task（plan-02 §3 #3 已建）
- 采集实现：src/services/data_init_index.py IndexDataInitService

契约（架构 §7.3 + plan-02 §3 #2）：
- 路径：admin 路由 router.py 以 include_router(admin_router, prefix="/v1/admin") 挂载，
  admin/__init__.py 的 APIRouter 无 prefix，init 子路由 prefix=/init + /index-*
  = /api/v1/admin/init/index-basic / index-history / index-daily
- 安全（架构 §8.3）：require_admin 鉴权；并发保护防重复采集；回填日期范围上限防滥用。
- 可观测性（架构 §8.5）：AsyncTask 记录 progress/total 与逐指数 log_message。
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

router = APIRouter(prefix="/init", tags=["Admin - Index"])

# 回填日期范围上限（10 年），与 service 层 / 架构 §8.3 防滥用约束一致
_MAX_BACKSPAN_DAYS = 3650


class IndexHistoryPayload(BaseModel):
    """指数历史回填请求参数。"""

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


async def _check_running(
    session: AsyncSession, task_type: TaskType
) -> bool:
    """检查是否有同类型 pending/running 任务，返回 True 表示有任务在运行。"""
    running = await session.execute(
        select(AsyncTask).where(
            and_(
                AsyncTask.task_type == task_type.value,
                AsyncTask.status.in_(["pending", "running"]),
            )
        )
    )
    return running.scalar_one_or_none() is not None


@router.post("/index-basic", response_model=ApiResponse[dict])
async def init_index_basic(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动触发关键指数基础信息同步（AC-08a）。

    创建 SYNC_INDEX_BASIC 异步任务，从 Tushare 拉取全市场指数基础信息
    （约 1 万条），upsert index_basic 表（on_conflict 排除 is_watched 字段），
    完成后将 14 只预置关注指数置为 true。
    """
    if await _check_running(session, TaskType.SYNC_INDEX_BASIC):
        return ApiResponse(
            success=False,
            data=None,
            message="已有指数清单同步任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_INDEX_BASIC.value,
        params={},
        max_retries=3,
        timeout_seconds=3600,
        created_by=_admin.id,
    )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message="指数清单同步任务已创建",
    )


@router.post("/index-history", response_model=ApiResponse[dict])
async def init_index_history(
    payload: IndexHistoryPayload,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动触发关键指数历史数据回填（AC-08b）。

    创建 BACKFILL_INDEX_HISTORY 异步任务，按日期升序逐交易日回填
    index_daily / index_dailybasic / index_weight（on_conflict 覆盖），
    权重数据按月缓存（同月只拉一次，用当月 1 日至月末宽窗口）。
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

    if await _check_running(session, TaskType.BACKFILL_INDEX_HISTORY):
        return ApiResponse(
            success=False,
            data=None,
            message="已有指数历史回填任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.BACKFILL_INDEX_HISTORY.value,
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
        message=f"指数历史回填任务已创建（{payload.start_date} ~ {payload.end_date}）",
    )


@router.post("/index-daily", response_model=ApiResponse[dict])
async def init_index_daily(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动触发关键指数当日增量采集。

    创建 SYNC_INDEX_DAILY 异步任务，从 Tushare 拉取关注指数当日的
    index_daily / index_dailybasic 数据，权重数据当月未入库时用当月宽窗口拉取。
    """
    if await _check_running(session, TaskType.SYNC_INDEX_DAILY):
        return ApiResponse(
            success=False,
            data=None,
            message="已有指数当日采集任务正在运行，请等待当前任务完成",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_INDEX_DAILY.value,
        params={},
        max_retries=3,
        timeout_seconds=3600,
        created_by=_admin.id,
    )
    await session.commit()

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message="指数当日采集任务已创建",
    )
