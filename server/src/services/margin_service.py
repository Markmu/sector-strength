"""融资融券全市场日汇总服务（第 17 期 融资融券数据同步与首页曲线图 plan-03）

本模块实现单交易日完整闭环（spec REQ-3 / D2 / D3）：

1. 日历守卫：本地 ``trading_calendar_days`` 查 ``T``——休市 → ``"skipped"``
   （零 Provider 调用，不浪费积分配额）；无覆盖记录 → 抛
   :class:`MarginSyncError`（拒绝按自然日/工作日猜测，16 期同款范式）。
2. 拉取：``DataSourceFactory.create().get_margin(T)`` 取全部交易所行
   （实测 SSE/SZSE/BSE 三行，行数以接口实际返回为准，无分页）；空结果
   抛错整日失败。
3. 聚合（全 Decimal，禁止 binary float）：``rzye/rqye/rzmre/rzche/rqmcl``
   五字段对全部行求和（spec 冻结 D2）；``rzrqye = Σrzye + Σrqye`` 服务层
   重算，**禁止直接 Σ 行 rzrqye**；各结果 ``quantize(0.01)`` 对齐
   Numeric(20,2)。
4. 原子 upsert：``on_conflict_do_update(trade_date)`` 单事务写
   ``market_margin_daily``；成功立即 commit、任何异常 rollback 后 raise
   （当日不留半成品）；``set_`` 显式写 ``func.now()`` 刷新 ``updated_at``
   （16 期 S1 教训：``on_conflict_do_update`` 不触发 ORM onupdate）。
5. 可观测性：结构化日志 ``trade_date/exchange_count/row_count/rzrqye/
   duration_ms/status``；交易所集合缺 SSE 或 SZSE 记 WARNING（含交易所
   集合）后继续——口径对全部返回行求和（2026-08-14 用户裁定），BSE 缺席
   不告警。

不建仓储层：market-metrics 无仓储层先例（MarketMetricsService 直查直写），
本期同样 service 内直查。

``task_context`` 为 ``TYPE_CHECKING`` 前向引用（``TaskFenceContext`` 由
16 期 plan-04 ``task_fence.py`` 落地，本期直接复用协议），运行时仅判
None / 调 ``lock_and_validate(session)``，不导入。
"""

from __future__ import annotations

import logging
import time
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, Dict, List, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from src.models.market_margin_daily import MarketMarginDaily
from src.services.data_acquisition import DataSourceFactory
from src.services.trading_calendar_repository import TradingCalendarRepository

if TYPE_CHECKING:
    # 16 期 plan-04 落地 TaskFenceContext；本模块运行时不导入，仅类型/协议调用。
    from src.services.task_fence import TaskFenceContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 模块常量（spec D2 / D3）
# ---------------------------------------------------------------------------

# 五个直接求和字段（spec 冻结 D2：对全部交易所行求和，行数以接口实际返回为准）。
MARGIN_SUM_FIELDS: tuple = (
    "rzye",
    "rqye",
    "rzmre",
    "rzche",
    "rqmcl",
)

# Numeric(20,2) 对齐量化粒度。
_CENT_QUANTUM = Decimal("0.01")

# 必须出现的交易所（缺席记 WARNING 后继续；BSE 缺席不告警——口径对全部
# 返回行求和，2026-08-14 用户裁定）。
_REQUIRED_EXCHANGES = frozenset({"SSE", "SZSE"})


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------


class MarginSyncError(Exception):
    """融资融券单日同步完整性错误（spec REQ-3）。

    ``message`` 携带 trade_date 与原因；两融无参与集合概念，无需 16 期的
    四类计数结构（``dateResults`` 逐日明细 ``{tradeDate, status, reason?}``
    由 plan-04 handler 构造）。
    """

    def __init__(self, message: str) -> None:
        self.raw_message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# MarginService
# ---------------------------------------------------------------------------


class MarginService:
    """融资融券全市场单日汇总服务（spec REQ-3 / D2 / D3）。

    对一个交易日 T 调用 :meth:`sync_date` 后，``market_margin_daily``
    恰好新增/覆盖一行：五指标为全部交易所行求和、``rzrqye`` 为
    ``Σrzye + Σrqye`` 重算值。
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.data_source = DataSourceFactory.create()

    async def sync_date(
        self,
        trade_date: date,
        task_context: Optional["TaskFenceContext"] = None,
    ) -> str:
        """单交易日完整闭环。

        Args:
            trade_date: 目标交易日 T。
            task_context: 可选 ``TaskFenceContext``（管理员任务必传，自动
                日更传 ``None``）；非 None 时 upsert 前先
                ``lock_and_validate(session)``，与业务写共用同一事务。

        Returns:
            ``"success"`` / ``"skipped"``（休市）；抛 :class:`MarginSyncError`
            或其他异常表示当日失败（``"failed"``，由 plan-04 handler 判定）。
        """
        started = time.monotonic()

        # ---- 1. 日历守卫（休市零 Provider 调用，不浪费积分配额）----
        cal_repo = TradingCalendarRepository(self.session)
        cal_record = await cal_repo.get_record(trade_date)
        if cal_record is None:
            raise MarginSyncError(
                f"本地日历无覆盖记录 trade_date={trade_date}"
                f"（拒绝按自然日/工作日猜测）"
            )
        if not cal_record.is_open:
            logger.info(
                "[Margin] sync_date skipped trade_date=%s (休市)", trade_date
            )
            return "skipped"

        # ---- 2. 拉取全部交易所行（空结果整日失败）----
        rows: List[dict] = self.data_source.get_margin(trade_date)
        if not rows:
            raise MarginSyncError(f"融资融券数据为空 trade_date={trade_date}")

        exchanges = {
            str(row.get("exchange_id") or "").strip().upper() for row in rows
        }
        missing_required = sorted(_REQUIRED_EXCHANGES - exchanges)
        if missing_required:
            # 护栏：缺 SSE/SZSE 记 WARNING 后继续（口径对全部返回行求和）
            logger.warning(
                "[Margin] 交易所行缺席 trade_date=%s exchanges=%s "
                "missing=%s（口径对全部返回行求和，继续）",
                trade_date,
                sorted(exchanges),
                missing_required,
            )

        # ---- 3. 聚合（全 Decimal）----
        totals = self._aggregate(rows, trade_date)

        # ---- 4. 原子 upsert（D3）----
        await self._atomic_upsert(
            trade_date=trade_date,
            rzye=totals["rzye"],
            rqye=totals["rqye"],
            rzmre=totals["rzmre"],
            rzche=totals["rzche"],
            rqmcl=totals["rqmcl"],
            rzrqye=totals["rzrqye"],
            task_context=task_context,
        )

        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "[Margin] sync_date success trade_date=%s exchange_count=%d "
            "row_count=%d rzrqye=%s duration_ms=%d status=success",
            trade_date,
            len(exchanges),
            len(rows),
            totals["rzrqye"],
            duration_ms,
        )
        return "success"

    # ------------------------------------------------------------------
    # 步骤实现
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate(rows: List[dict], trade_date: date) -> Dict[str, Decimal]:
        """五字段对全部行求和 + ``rzrqye`` 重算（全 Decimal，spec D2）。

        - ``rzye/rqye/rzmre/rzche/rqmcl``：对全部交易所行求和（行数以接口
          实际返回为准）；
        - ``rzrqye = Σrzye + Σrqye``：服务层重算，不读行内 ``rzrqye``
          （上游字段仅供排查参考）；
        - 各结果 ``quantize(0.01, ROUND_HALF_UP)`` 对齐 Numeric(20,2)；
        - 任何字段非 Decimal（采集层 Decimal 强约束被破坏）→ 抛错整日
          失败，宁失败不猜测。
        """
        totals: Dict[str, Decimal] = {f: Decimal("0") for f in MARGIN_SUM_FIELDS}
        for row in rows:
            for field in MARGIN_SUM_FIELDS:
                value = row.get(field)
                if not isinstance(value, Decimal):
                    raise MarginSyncError(
                        f"margin 行字段 {field} 非 Decimal: {value!r} "
                        f"(exchange_id={row.get('exchange_id')}, "
                        f"trade_date={trade_date})"
                    )
                totals[field] += value

        totals["rzrqye"] = totals["rzye"] + totals["rqye"]

        return {
            k: v.quantize(_CENT_QUANTUM, rounding=ROUND_HALF_UP)
            for k, v in totals.items()
        }

    async def _atomic_upsert(
        self,
        trade_date: date,
        rzye: Decimal,
        rqye: Decimal,
        rzmre: Decimal,
        rzche: Decimal,
        rqmcl: Decimal,
        rzrqye: Decimal,
        task_context: Optional["TaskFenceContext"],
    ) -> None:
        """单事务原子 upsert（spec D3 / 16 期 market_metrics 同款范式）。

        ``task_context`` 非 None 时先 ``lock_and_validate(session)``（同事务
        ``SELECT ... FOR UPDATE`` AsyncTask 行，实现于 16 期 plan-04
        ``task_fence.py``），再 ``on_conflict_do_update(trade_date)``；成功
        立即 commit，任何异常整体 rollback，不保留半成品。
        """
        values = {
            "trade_date": trade_date,
            "rzye": rzye,
            "rqye": rqye,
            "rzmre": rzmre,
            "rzche": rzche,
            "rqmcl": rqmcl,
            "rzrqye": rzrqye,
        }
        try:
            if task_context is not None:
                # 协议调用：TaskFenceContext.lock_and_validate(session)
                await task_context.lock_and_validate(self.session)
            stmt = pg_insert(MarketMarginDaily).values(**values)
            update_cols = {
                k: getattr(stmt.excluded, k) for k in values if k != "trade_date"
            }
            # 显式刷新 updated_at：on_conflict_do_update 不会触发 ORM onupdate，
            # 必须在 set_ 中显式赋 func.now()，使覆盖写更新时间戳（16 期 S1 教训）
            update_cols["updated_at"] = func.now()
            stmt = stmt.on_conflict_do_update(
                index_elements=["trade_date"],
                set_=update_cols,
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
