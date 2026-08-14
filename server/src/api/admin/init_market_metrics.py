"""市场量价范围同步管理 API 端点（第 16 期 plan-05）

提供手动触发全市场量价范围同步的唯一合法入口，需要管理员权限。
``sync_market_metrics`` 任务类型在 ``admin/tasks.py`` 的 ``RESERVED_TASK_TYPES``
中封堵，必须经本专用路由创建（架构 §7.3 / AC-11）。

复用声明：
- admin 触发范式：``src/api/admin/init_index_basic.py``（require_admin + ApiResponse
  包裹 + 日期范围校验链）。
- 互斥创建：``TaskManager.create_exclusive_task``（plan-04 专属 advisory lock）。
- 采集/汇总：``MarketMetricsService``（plan-03）、``TradingCalendarRepository``（plan-01）。

契约（架构 §6.2.1-2、§7.3、§8.3）：
- 路径：admin 路由 router.py 以 ``include_router(admin_router, prefix="/v1/admin")``
  挂载，本路由 ``prefix="/init"`` + ``/market-metrics`` =
  ``/api/v1/admin/init/market-metrics``。
- 校验链（任一失败 ``ApiResponse(success=False)``，**不建任务**）：
  1. ``start_date <= end_date <= today``（AC-10）
  2. 跨度 ≤ 10 年（``_MAX_BACKSPAN_DAYS=3650``，§8.2）
  3. ``TradingCalendarRepository.refresh_range(start, end)``（Provider 失败/响应不完整
     → 失败提示，不降级旧批次）
  4. 本地日历拆分交易日；**零交易日 → 明确提示不建任务**（§3.2 分支表）
- 安全（§8.3）：``require_admin`` 依赖；日期用 Pydantic ``date`` 类型天然防注入；
  不透传 ``max_retries``（``create_exclusive_task`` 固定 ``max_retries=0``）。
- 可观测性（§8.5）：任务 ``progress/total`` 只计交易日；``result`` 携带逐日四类计数。
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.models.user import User
from src.services.trading_calendar_repository import TradingCalendarRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/init", tags=["Admin - Market Metrics"])

# 回填日期范围上限（10 年），与 service 层 / 架构 §8.3 防滥用约束一致。
_MAX_BACKSPAN_DAYS = 3650


class MarketMetricsRangePayload(BaseModel):
    """市场量价范围同步请求参数（body snake_case）。"""

    start_date: date = Field(
        ...,
        description="起始日期 YYYY-MM-DD（闭区间，含）",
    )
    end_date: date = Field(
        ...,
        description="结束日期 YYYY-MM-DD（闭区间，含，不能晚于今天）",
    )


@router.post("/market-metrics", response_model=ApiResponse[dict])
async def init_market_metrics(
    payload: MarketMetricsRangePayload,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动触发全市场量价范围同步（AC-02/AC-10/AC-11）。

    创建 ``sync_market_metrics`` 互斥任务，逐交易日串行执行完整闭环（L/D/P/G
    生命周期 + suspend_d 停牌证据 + Decimal 原子 upsert）。任务 ``max_retries=0``，
    成功日立即提交、失败日回滚并继续，失败数 >0 时任务落 failed 但成功日保留。

    校验链任一失败均返回 ``success=False`` 且 **不建任务**：
    起止倒置 / end>today / 跨度>10 年 / 日历刷新失败 / 零交易日。
    """
    today = date.today()

    # 1. start <= end <= today（AC-10）
    if payload.start_date > payload.end_date:
        return ApiResponse(
            success=False,
            data=None,
            message="开始日期不能晚于结束日期",
        )
    if payload.end_date > today:
        return ApiResponse(
            success=False,
            data=None,
            message="结束日期不能晚于今天",
        )

    # 2. 跨度 ≤ 10 年（§8.2 / §8.3 防滥用）
    if (payload.end_date - payload.start_date).days > _MAX_BACKSPAN_DAYS:
        return ApiResponse(
            success=False,
            data=None,
            message=f"日期范围不能超过 10 年（{_MAX_BACKSPAN_DAYS} 天）",
        )

    # 3. 刷新本地交易日历（Provider 失败/响应不完整 → 失败提示，不降级旧批次）
    cal_repo = TradingCalendarRepository(session)
    try:
        await cal_repo.refresh_range(payload.start_date, payload.end_date)
    except Exception as e:
        await session.rollback()
        logger.warning("[market-metrics] 日历刷新失败: %s", e)
        return ApiResponse(
            success=False,
            data=None,
            message=f"交易日历刷新失败，未创建任务：{e}",
        )

    # 4. 本地日历拆分交易日；零交易日 → 明确提示不建任务（§3.2 分支表）
    trading_days = await cal_repo.get_trading_days(
        payload.start_date, payload.end_date
    )
    if not trading_days:
        return ApiResponse(
            success=False,
            data=None,
            message="所选范围内没有交易日，未创建任务",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_exclusive_task(
        task_type="sync_market_metrics",
        params={
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat(),
        },
        created_by=_admin.id,
    )

    if task is None:
        # 互斥命中：同类型已有 pending/running（HTTP 200，与锚点一致）
        return ApiResponse(
            success=False,
            data=None,
            message="已有市场量价同步任务正在运行，请等待当前任务完成",
        )

    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message=(
            f"市场量价同步任务已创建"
            f"（{payload.start_date} ~ {payload.end_date}，交易日 {len(trading_days)} 个）"
        ),
    )
