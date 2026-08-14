"""融资融券范围同步管理 API 端点（第 17 期 plan-05）

提供手动触发全市场融资融券范围同步的唯一合法入口，需要管理员权限。
``sync_market_margin`` 任务类型在 ``admin/tasks.py`` 的 ``RESERVED_TASK_TYPES``
中封堵（第 17 期 plan-04），必须经本专用路由创建。

逐行对照母本：``src/api/admin/init_market_metrics.py``（第 16 期 plan-05）。

复用声明：
- admin 触发范式：``src/api/admin/init_market_metrics.py``（require_admin +
  ApiResponse 包裹 + 五项校验链 + 互斥创建响应）。
- 互斥创建：``TaskManager.create_exclusive_task``（plan-04 margin 专属
  advisory lock 9001003/9001004）。
- 范围同步 handler 与 fencing：``sync_market_margin`` handler（plan-04 交付）。
- 交易日历：``TradingCalendarRepository``（16 期交付直接复用）。

契约（第 17 期 spec REQ-5 / 架构 §7.3 同构）：
- 路径：admin 主路由（无统一前缀）→ ``router.py`` ``/v1/admin`` → main.py
  ``/api``，本路由 ``prefix="/init"`` + ``/margin`` =
  ``/api/v1/admin/init/margin``。
- 五项校验链（任一失败 ``ApiResponse(success=False)``，**不建任务**）：
  1. ``start_date <= end_date``（起止倒置拒绝）
  2. ``end_date <= today``（AC-4）
  3. 跨度 ≤ 10 年（``_MAX_BACKSPAN_DAYS=3650``）
  4. ``TradingCalendarRepository.refresh_range(start, end)``（Provider 失败/
     响应不完整 → 失败提示，不降级旧批次）
  5. 本地日历拆分交易日；零交易日 → 明确提示不建任务
- 安全（16 期 §8.3 惯例继承）：``require_admin`` 依赖；日期用 Pydantic ``date``
  类型天然防注入；不透传 ``max_retries``（``create_exclusive_task`` 固定
  ``max_retries=0``）。
- 可观测性：校验拒绝与创建成功均记 INFO/WARNING 日志（含范围与交易日数）；
  任务进度与 result 的可观测性由 plan-04 handler 承担。
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

router = APIRouter(prefix="/init", tags=["Admin - Margin"])

# 回填日期范围上限（10 年），与 16 期 init_market_metrics 防滥用约束一致。
_MAX_BACKSPAN_DAYS = 3650


class MarginRangePayload(BaseModel):
    """融资融券范围同步请求参数（body snake_case）。"""

    start_date: date = Field(
        ...,
        description="起始日期 YYYY-MM-DD（闭区间，含）",
    )
    end_date: date = Field(
        ...,
        description="结束日期 YYYY-MM-DD（闭区间，含，不能晚于今天）",
    )


@router.post("/margin", response_model=ApiResponse[dict])
async def init_margin(
    payload: MarginRangePayload,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """
    手动触发全市场融资融券范围同步（第 17 期 AC-3/AC-4）。

    创建 ``sync_market_margin`` 互斥任务（plan-04 专属 advisory lock），逐交易日
    拉取全部交易所行、五字段求和并重算 ``rzrqye`` 后 Decimal 原子 upsert（plan-03
    服务层 + plan-04 handler）。任务 ``max_retries=0``。

    五项校验链任一失败均返回 ``success=False`` 且 **不建任务**：
    起止倒置 / end>today / 跨度>10 年 / 日历刷新失败 / 零交易日。
    """
    today = date.today()

    # 1. start <= end <= today（AC-4）
    if payload.start_date > payload.end_date:
        logger.info(
            "[margin] 拒绝创建任务（起止倒置）: %s ~ %s",
            payload.start_date,
            payload.end_date,
        )
        return ApiResponse(
            success=False,
            data=None,
            message="开始日期不能晚于结束日期",
        )
    if payload.end_date > today:
        logger.info(
            "[margin] 拒绝创建任务（end>today）: %s ~ %s",
            payload.start_date,
            payload.end_date,
        )
        return ApiResponse(
            success=False,
            data=None,
            message="结束日期不能晚于今天",
        )

    # 2. 跨度 ≤ 10 年（防滥用）
    if (payload.end_date - payload.start_date).days > _MAX_BACKSPAN_DAYS:
        logger.info(
            "[margin] 拒绝创建任务（跨度>10 年）: %s ~ %s",
            payload.start_date,
            payload.end_date,
        )
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
        logger.warning("[margin] 日历刷新失败: %s", e)
        return ApiResponse(
            success=False,
            data=None,
            message=f"交易日历刷新失败，未创建任务：{e}",
        )

    # 4. 本地日历拆分交易日；零交易日 → 明确提示不建任务
    trading_days = await cal_repo.get_trading_days(
        payload.start_date, payload.end_date
    )
    if not trading_days:
        logger.info(
            "[margin] 拒绝创建任务（零交易日）: %s ~ %s",
            payload.start_date,
            payload.end_date,
        )
        return ApiResponse(
            success=False,
            data=None,
            message="所选范围内没有交易日，未创建任务",
        )

    # 延迟导入避免循环依赖
    from src.services.task_manager import TaskManager

    manager = TaskManager(session)
    task = await manager.create_exclusive_task(
        task_type="sync_market_margin",
        params={
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat(),
        },
        created_by=_admin.id,
    )

    if task is None:
        # 互斥命中：同类型已有 pending/running（HTTP 200，与 16 期锚点一致）
        logger.info(
            "[margin] 互斥拒绝创建任务: %s ~ %s（已有同类任务 pending/running）",
            payload.start_date,
            payload.end_date,
        )
        return ApiResponse(
            success=False,
            data=None,
            message="已有融资融券同步任务正在运行，请等待当前任务完成",
        )

    logger.info(
        "[margin] 任务已创建 %s: %s ~ %s，交易日 %d 个",
        task.task_id,
        payload.start_date,
        payload.end_date,
        len(trading_days),
    )
    return ApiResponse(
        success=True,
        data={"task_id": task.task_id},
        message=(
            f"融资融券同步任务已创建"
            f"（{payload.start_date} ~ {payload.end_date}，交易日 {len(trading_days)} 个）"
        ),
    )
