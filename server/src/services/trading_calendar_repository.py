"""本地交易日历仓库（第 16 期 A股全市场量价指标）

``TradingCalendarRepository`` 是本地交易日历的唯一入口（架构 §4.2 模块 1 / §6.2.1 /
§8.2-5 / §8.6）。职责：

1. 写侧 ``refresh_range(start, end)``：从 Provider 拉取闭区间全量开/休市记录，
   内存严格校验（一一对应 / 无重复 / 无越界）后单事务原子 upsert 到
   ``trading_calendar_days`` 表，以 ``refresh_batch_id`` / ``refreshed_at`` 标识批次。
2. 读侧只读查询：``get_record`` / ``get_trading_days`` / ``get_recent_open_days``
   / ``has_any_open_day``，供 plan-03/05/06 复用（同步日历守卫、非交易日拆分、
   最近 N 开市日左连接）。

护栏（架构 §8.2-5 / §8.6 末行）：

- 写侧禁止用旧批次降级：Provider 失败 / 响应不完整时直接失败，不建任务、不执行日更；
  旧行仅供读侧继续使用。
- GET 读路径零 Provider 调用，首页与查询一律读本地表（架构 ADR-6）。
"""

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.trading_calendar_day import TradingCalendarDay
from src.services.data_acquisition import DataSourceFactory
from src.services.data_acquisition.models import TradingCalendarEntry

logger = logging.getLogger(__name__)


class TradingCalendarRepository:
    """本地交易日历仓库：闭区间刷新 + 只读查询"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def refresh_range(self, start: date, end: date) -> Tuple[int, int]:
        """刷新闭区间 ``[start, end]`` 的本地交易日历。

        流程（架构 §8.2-5）：

        1. 调 ``DataSourceFactory.create().get_trading_calendar_range(start, end)``
           拉取闭区间全量开/休市记录；Provider 失败直接抛，不提交、不改旧行。
        2. 内存集合严格校验：闭区间每个自然日一一对应（行数相等且 ``set(cal_date)``
           等于全部自然日）；无重复、无越界。任一不满足抛 ``ValueError``（带缺失/
           重复/越界样本），不建任务、不执行日更。
        3. 单事务内生成 ``refresh_batch_id = uuid4()``、``refreshed_at = now()``，
           对区间全部自然日 ``on_conflict_do_update(cal_date)`` upsert（开/休市都写）。
        4. 返回 ``(open_count, closed_count)``；结构化日志记录刷新范围、开/休市行数、
           refreshed_at（架构 §8.5）。

        Args:
            start: 开始日期（闭区间，含）
            end: 结束日期（闭区间，含）

        Returns:
            ``(open_count, closed_count)`` 开市/休市行数

        Raises:
            ValueError: 响应不完整（缺日 / 重复 / 越界），不提交任何行
            DataFetchError / RetryExhaustedError: Provider 失败透传
        """
        # 1. Provider 拉取（失败直接抛，不提交）
        source = DataSourceFactory.create()
        entries: List[TradingCalendarEntry] = source.get_trading_calendar_range(
            start, end
        )

        # 2. 内存集合严格校验
        self._validate_closed_range(entries, start, end)

        # 3. 单事务原子 upsert（开/休市都写）
        batch_id = str(uuid.uuid4())
        refreshed_at = datetime.now()

        rows = [
            {
                "cal_date": e.cal_date,
                "is_open": e.is_open,
                "refresh_batch_id": batch_id,
                "refreshed_at": refreshed_at,
            }
            for e in entries
        ]

        stmt = pg_insert(TradingCalendarDay).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["cal_date"],
            set_={
                "is_open": stmt.excluded.is_open,
                "refresh_batch_id": stmt.excluded.refresh_batch_id,
                "refreshed_at": stmt.excluded.refreshed_at,
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

        # 4. 统计与结构化日志
        open_count = sum(1 for e in entries if e.is_open)
        closed_count = len(entries) - open_count

        logger.info(
            "[TradingCalendar] 刷新完成: range=%s~%s, open=%d, closed=%d, "
            "batch_id=%s, refreshed_at=%s",
            start.isoformat(),
            end.isoformat(),
            open_count,
            closed_count,
            batch_id,
            refreshed_at.isoformat(),
        )

        return (open_count, closed_count)

    @staticmethod
    def _validate_closed_range(
        entries: List[TradingCalendarEntry], start: date, end: date
    ) -> None:
        """闭区间一一对应 / 无重复 / 无越界校验（不满足抛 ValueError，不提交）。"""
        expected_days = (end - start).days + 1
        expected_dates = {
            start + timedelta(days=i) for i in range(expected_days)
        }

        received = [e.cal_date for e in entries]
        received_set = set(received)

        missing = sorted(expected_dates - received_set)
        out_of_range = sorted(received_set - expected_dates)
        has_duplicates = len(received) != len(received_set)

        errors: List[str] = []
        if has_duplicates:
            errors.append(
                f"响应含重复 cal_date（行数 {len(received)} > 去重后 {len(received_set)}）"
            )
        if missing:
            errors.append(
                f"缺失日期样本 {[d.isoformat() for d in missing[:5]]}"
            )
        if out_of_range:
            errors.append(
                f"越界日期样本 {[d.isoformat() for d in out_of_range[:5]]}"
            )
        if len(entries) != expected_days:
            errors.append(
                f"行数 {len(entries)} 不等于自然日数 {expected_days}"
            )

        if errors:
            raise ValueError(
                "交易日历闭区间校验失败: " + "; ".join(errors)
            )

    # ------------------------------------------------------------------
    # 只读查询（供 plan-03/05/06 复用，零 Provider 调用）
    # ------------------------------------------------------------------

    async def get_record(self, day: date) -> Optional[TradingCalendarDay]:
        """取单个自然日的本地日历记录（不存在返回 None）。"""
        stmt = select(TradingCalendarDay).where(
            TradingCalendarDay.cal_date == day
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_trading_days(self, start: date, end: date) -> List[date]:
        """取闭区间内所有开市日（is_open=true），按日期升序返回。"""
        stmt = (
            select(TradingCalendarDay.cal_date)
            .where(TradingCalendarDay.is_open.is_(True))
            .where(TradingCalendarDay.cal_date >= start)
            .where(TradingCalendarDay.cal_date <= end)
            .order_by(TradingCalendarDay.cal_date.asc())
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_recent_open_days(self, n: int) -> List[date]:
        """取最近 N 个开市日，按日期升序返回（降序取 N 再反转升序）。

        走 ``idx_trading_calendar_days_cal_date_is_open`` 索引：按 cal_date 降序扫描
        索引并过滤 is_open=true，命中 N 条即停（架构 §8.1 性能验收）。
        """
        stmt = (
            select(TradingCalendarDay.cal_date)
            .where(TradingCalendarDay.is_open.is_(True))
            .order_by(TradingCalendarDay.cal_date.desc())
            .limit(n)
        )
        result = await self._session.execute(stmt)
        rows = [row[0] for row in result.all()]
        rows.reverse()
        return rows

    async def has_any_open_day(self) -> bool:
        """本地表是否存在任意开市日（用于判定日历是否已初始化）。"""
        stmt = (
            select(TradingCalendarDay.id)
            .where(TradingCalendarDay.is_open.is_(True))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None
