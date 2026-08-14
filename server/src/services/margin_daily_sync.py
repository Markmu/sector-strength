"""融资融券每日早间增量同步入口（定时任务专用）

背景（2026-08-15 Tushare 官网核实 + 镜像实测）：

- ``margin`` 为 T+1 接口：官方 doc_id=58 原文"交易所于每天8点30左右更新上一日
  数据，本接口最晚9点05分会更新完数据"——T 日数据在**次一交易日**早晨发布。
- 2026-08-15（周六）实测镜像：周五 08-14 返回 0 行、周四 08-13 正常 3 行，
  证实非交易日早晨不发布，周五数据须等周一早晨。
- 因此与 18:00 盘后 job（指数/量价，当日 15:00~17:00 入库）分离，本入口只在
  **今日为交易日**时执行，目标为上一交易日及近 14 个自然日内的缺口。

流程（全部复用 17 期既有交付，本模块不直接写库）：

1. ``refresh_range(today-13, today)`` 刷新本地日历（Provider 失败/响应不完整
   → 抛错不建任务，16 期 §8.2-5 护栏；次日自愈）。
2. 交易日守卫：今日休市 → ``skipped_closed``（零任务、零 Provider 配额消耗）。
3. 缺口计算：``market_margin_daily`` 最大 trade_date 之后到上一交易日的开市日，
   下界不早于窗口起点（覆盖春节/国庆最长连休；更早缺口走管理面板 bulk 同步）。
4. ``create_exclusive_task("sync_market_margin")`` 建互斥任务（与手动面板互斥、
   max_retries=0；TaskExecutor 轮询自动拾起执行，逐日 upsert 幂等可重入）。
"""

import logging
from datetime import date, timedelta
from typing import Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.market_margin_daily import MarketMarginDaily
from src.services.task_manager import TaskManager
from src.services.trading_calendar_repository import TradingCalendarRepository

logger = logging.getLogger(__name__)

# 缺口回看窗口（自然日，闭区间含 today）：14 天覆盖 A 股最长连续休市；
# 更早的历史缺口由管理面板手动范围同步承担，早间 job 只做增量与近期自愈。
MARGIN_DAILY_LOOKBACK_DAYS = 14


async def run_margin_daily_sync(
    session: AsyncSession,
    today: Optional[date] = None,
) -> Dict[str, object]:
    """融资融券每日早间增量同步的守卫 + 缺口计算 + 互斥建任务。

    Args:
        session: 数据库会话（只用于日历刷新、max 查询与任务创建）。
        today: 可注入的"今天"（测试用），缺省取系统日期。

    Returns:
        ``{"status": "skipped_closed" | "noop" | "mutex_rejected" | "created", ...}``，
        ``created`` 时含 ``task_id`` / ``start_date`` / ``end_date`` /
        ``trading_days``。

    Raises:
        日历刷新失败（Provider 异常 / ``ValueError`` 响应不完整）原样透传，
        调用方（JobManager 回调）记日志后放弃本轮，次日缺口自愈。
    """
    today = today or date.today()
    cal_repo = TradingCalendarRepository(session)

    # 1. 刷新日历窗口（闭区间 today-13 ~ today，覆盖守卫与缺口计算所需日期）。
    window_start = today - timedelta(days=MARGIN_DAILY_LOOKBACK_DAYS - 1)
    await cal_repo.refresh_range(window_start, today)

    # 2. 交易日守卫：Tushare margin 于次一交易日早晨发布，今日休市则无新数据。
    today_record = await cal_repo.get_record(today)
    if today_record is None or not today_record.is_open:
        logger.info("[MarginDaily] 今日休市/无开市记录，跳过: today=%s", today)
        return {"status": "skipped_closed", "today": today.isoformat()}

    # 3. 缺口计算：终点 = 上一交易日（today 前最后一个开市日）。
    prev_days = await cal_repo.get_trading_days(
        window_start, today - timedelta(days=1)
    )
    if not prev_days:
        logger.info("[MarginDaily] 窗口内无历史开市日，跳过: today=%s", today)
        return {"status": "noop", "today": today.isoformat()}
    target_end = prev_days[-1]

    max_result = await session.execute(
        select(func.max(MarketMarginDaily.trade_date))
    )
    db_max: Optional[date] = max_result.scalar_one_or_none()

    # 下界 = max(db_max+1, 窗口起点)；db_max 超前（>= target_end）时缺口为空。
    plan_start = window_start
    if db_max is not None:
        plan_start = max(db_max + timedelta(days=1), window_start)

    missing = await cal_repo.get_trading_days(plan_start, target_end)
    if not missing:
        logger.info(
            "[MarginDaily] 无缺口，跳过: today=%s db_max=%s target_end=%s",
            today,
            db_max,
            target_end,
        )
        return {
            "status": "noop",
            "today": today.isoformat(),
            "db_max": db_max.isoformat() if db_max else None,
        }

    # 4. 建互斥任务（与手动面板同一 advisory lock；执行器自动拾起逐日同步）。
    manager = TaskManager(session)
    task = await manager.create_exclusive_task(
        task_type="sync_market_margin",
        params={
            "start_date": missing[0].isoformat(),
            "end_date": missing[-1].isoformat(),
        },
    )
    if task is None:
        logger.info(
            "[MarginDaily] 互斥拒绝建任务（已有 sync_market_margin "
            "pending/running）: today=%s range=%s~%s",
            today,
            missing[0],
            missing[-1],
        )
        return {"status": "mutex_rejected", "today": today.isoformat()}

    logger.info(
        "[MarginDaily] 任务已创建: task_id=%s range=%s~%s trading_days=%d",
        task.task_id,
        missing[0],
        missing[-1],
        len(missing),
    )
    return {
        "status": "created",
        "task_id": task.task_id,
        "start_date": missing[0].isoformat(),
        "end_date": missing[-1].isoformat(),
        "trading_days": len(missing),
    }
