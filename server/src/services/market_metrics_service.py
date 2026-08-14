"""市场量价汇总服务与生命周期同步（第 16 期 A股全市场量价指标 plan-03）

本模块实现单交易日完整闭环（架构 §4.2 模块 2 / §5 ADR-2/3/4 / §6.1 / §7.1 /
§8.2-8.6）：

1. ``LifecycleSnapshot``：不可变快照，承载 ``init_stocks_lifecycle`` 拉回的 L/D/P/G
   四状态全集，提供 ``expected_codes(T)`` 计算 T 日应参与集合（G 固定排除、
   L/P 需 ``list_date<=T``、D 另需 ``T<delist_date``）。
2. ``MarketMetricsService.sync_date``：日历守卫 → 快照校验 → 全市场行情拉取过滤 →
   停牌确认（客户端 ``suspend_date==T`` 过滤 + ``suspend_type='S'``/全天判定）→
   分块有界前收盘补价（60 日窗向前、下界 ``list_date``、≤250 窗/批、预算常量、
   ``close_cache``）→ 补值与集合平衡 → Decimal 计算 → ``task_context`` 协议调用 +
   单事务原子 upsert。
3. ``MarketMetricsSyncError``：四类计数（expected/daily/suspended/final）+ ≤50
   问题代码样本。

护栏（架构 §6.1 实现原则 / §8.6）：

- 任何不完整场景（缺行、重复、集合不平衡、补价失败、越界代码、关键值非法）整日
  不落库并抛出；失败不留半成品（AC-01/03/07）。
- 全天停牌补值：``suspend_type='S'`` 且 ``suspend_timing`` 为空（或明确识别为全天），
  无法判定一律失败，宁失败不猜测（AC-13 / §8.6）。
- ``suspend_d`` 上游代理忽略日期过滤、返回跨多日全量行——必须按
  ``record.suspend_date == trade_date`` 客户端过滤后才能作为当日停牌证据。
- 补价禁止 qfq 后备与逐股无界 N+1；扫描到底未命中整日失败。
- ``task_context`` 为 ``TYPE_CHECKING`` 前向引用（``TaskFenceContext`` 由 plan-04
  ``task_fence.py`` 落地），运行时仅判 None / 调 ``lock_and_validate``，不导入。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, Dict, List, Mapping, MutableMapping, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from src.models.market_daily_metric import MarketDailyMetric
from src.models.stock import Stock
from src.services.data_acquisition import DataSourceFactory
from src.services.data_acquisition.models import (
    A_STOCK_EXCHANGES,
    LifecycleStock,
    MarketDailyQuote,
)
from src.services.trading_calendar_repository import TradingCalendarRepository

if TYPE_CHECKING:
    # plan-04 落地 TaskFenceContext；本模块运行时不导入，仅类型/协议调用。
    from src.services.task_fence import TaskFenceContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 模块常量（架构 §6.1.6 / §8.4）
# ---------------------------------------------------------------------------

# 有界前收盘补价：60 自然日窗口、每批 ≤100 代码、每批最多 250 个窗口。
CLOSE_LOOKBACK_WINDOW_DAYS = 60
CLOSE_LOOKBACK_MAX_CODES_PER_BATCH = 100
CLOSE_LOOKBACK_MAX_WINDOWS_PER_BATCH = 250
# 整日补价总请求预算（架构 §8.4：写入配置常量，命中预算仍有未决代码则该日失败）。
MAX_CLOSE_LOOKBACK_REQUESTS = 16
# 错误样本截断（架构 §6.2：日志/响应最多 50 个问题代码）。
PROBLEM_CODE_SAMPLE_LIMIT = 50

# ts_code 后缀 → 交易所映射（exchange 字段缺失时以后缀兜底，架构 §6.1.2）。
_TS_CODE_SUFFIX_TO_EXCHANGE: Dict[str, str] = {
    ".SH": "SSE",
    ".SZ": "SZSE",
    ".BJ": "BSE",
}
_VALID_A_STOCK_EXCHANGES: Set[str] = set(A_STOCK_EXCHANGES)


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------


class MarketMetricsSyncError(Exception):
    """市场量价单日同步完整性错误（架构 §6.2 / AC-07）。

    携带 ``expected/daily/suspended/final`` 四类计数与最多
    ``PROBLEM_CODE_SAMPLE_LIMIT`` 个问题代码样本；``message`` 截断展示。
    任何不完整场景（缺行、重复、集合不平衡、补价失败、越界代码、关键值非法）
    均以本异常抛出，调用方判定整日失败。
    """

    def __init__(
        self,
        message: str,
        *,
        expected: int = 0,
        daily: int = 0,
        suspended: int = 0,
        final: int = 0,
        problem_codes: Optional[List[str]] = None,
    ) -> None:
        self.raw_message = message
        self.expected = expected
        self.daily = daily
        self.suspended = suspended
        self.final = final
        codes = sorted(set(problem_codes or []))
        self.problem_codes = codes[:PROBLEM_CODE_SAMPLE_LIMIT]
        sample = ", ".join(self.problem_codes)
        full = (
            f"{message} | expected={expected} daily={daily} "
            f"suspended={suspended} final={final}"
        )
        if codes:
            full += f" | problem_codes_sample=[{sample}]"
        # 截断展示，避免日志/响应失控（架构 §6.2）
        super().__init__(full[:2000])


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def resolve_a_stock_exchange(ts_code: str, exchange: Optional[str]) -> Optional[str]:
    """解析记录所属 A 股交易所（exchange 字段优先，缺失时以 ts_code 后缀兜底）。

    返回 ``SSE/SZSE/BSE`` 之一；非 A 股返回 ``None``（架构 §6.1.2）。
    """
    ex = (exchange or "").strip().upper()
    if ex in _VALID_A_STOCK_EXCHANGES:
        return ex
    for suffix, mapped in _TS_CODE_SUFFIX_TO_EXCHANGE.items():
        if ts_code.endswith(suffix):
            return mapped
    return None


def _symbol_from_ts_code(ts_code: str) -> str:
    """从 ts_code（如 ``000001.SZ``）取短码 symbol（如 ``000001``）。"""
    return ts_code.split(".", 1)[0]


def validate_lifecycle_records(
    records: List[LifecycleStock],
) -> Tuple[List[str], List[str]]:
    """L/D/P/G 记录级校验（架构 §6.1.2 / §8.6 首行 / ADR-2）。

    规则：
      - 所有记录 ``ts_code`` 必填，且须能解析为 A 股交易所；
      - L/D/P 必须有 ``list_date``；D 还必须有 ``delist_date``；
      - G 允许两日期为空；
      - 未知 ``list_status`` 视为违规。

    返回 ``(violations, code_samples)``；两者均为空表示全部合法。
    """
    violations: List[str] = []
    samples: List[str] = []
    for rec in records:
        if not rec.ts_code:
            violations.append("ts_code 缺失")
            samples.append("<空>")
            continue
        if resolve_a_stock_exchange(rec.ts_code, rec.exchange) is None:
            violations.append(
                f"非 A 股交易所 ts_code={rec.ts_code} exchange={rec.exchange}"
            )
            samples.append(rec.ts_code)
            continue
        status = (rec.list_status or "").strip().upper()
        if status == "G":
            continue  # G 两日期可空
        if status in ("L", "P"):
            if rec.list_date is None:
                violations.append(
                    f"{status} 状态缺 list_date (ts_code={rec.ts_code})"
                )
                samples.append(rec.ts_code)
        elif status == "D":
            if rec.list_date is None:
                violations.append(
                    f"D 状态缺 list_date (ts_code={rec.ts_code})"
                )
                samples.append(rec.ts_code)
            if rec.delist_date is None:
                violations.append(
                    f"D 状态缺 delist_date (ts_code={rec.ts_code})"
                )
                samples.append(rec.ts_code)
        else:
            violations.append(
                f"未知 list_status={status!r} (ts_code={rec.ts_code})"
            )
            samples.append(rec.ts_code)
    return violations, samples


# ---------------------------------------------------------------------------
# LifecycleSnapshot（架构 §6.1.2 / ADR-2）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LifecycleSnapshot:
    """不可变生命周期快照：L/D/P/G 四状态全集 + 四类成功标记。

    范围任务与自动日更各只构建一次，传给各 ``sync_date`` 复用，避免重复拉
    ``stock_basic``（架构 §6.2.4 / §6.3.2）。
    """

    records: Tuple[LifecycleStock, ...]
    status_flags: Mapping[str, bool] = field(default_factory=dict)

    def expected_codes(self, trade_date: date) -> Set[str]:
        """计算 ``trade_date`` 当日应参与集合（架构 §6.1.2）。

        - 交易所 ∈ {SSE, SZSE, BSE}（exchange 字段优先，缺失以 ts_code 后缀兜底）；
        - L/P：``list_date <= T``；
        - D：``list_date <= T`` 且 ``T < delist_date``；
        - G：**无论日期字段是否为空固定排除**。
        """
        result: Set[str] = set()
        for rec in self.records:
            if resolve_a_stock_exchange(rec.ts_code, rec.exchange) is None:
                continue
            status = (rec.list_status or "").strip().upper()
            if status == "G":
                continue
            if status in ("L", "P"):
                if rec.list_date is not None and rec.list_date <= trade_date:
                    result.add(rec.ts_code)
            elif status == "D":
                if (
                    rec.list_date is not None
                    and rec.list_date <= trade_date
                    and rec.delist_date is not None
                    and trade_date < rec.delist_date
                ):
                    result.add(rec.ts_code)
        return result

    def list_date_of(self, ts_code: str) -> Optional[date]:
        """取指定 ts_code 的 list_date（补价窗口下界，架构 §6.1.6）。"""
        for rec in self.records:
            if rec.ts_code == ts_code:
                return rec.list_date
        return None


async def build_lifecycle_snapshot(session: AsyncSession) -> LifecycleSnapshot:
    """构造不可变 ``LifecycleSnapshot``（架构 §6.1.2 / §6.2.4 / §6.3.2）。

    流程：
      1. 调 ``DataInitService.init_stocks_lifecycle()`` 完成四状态联合 upsert +
         四状态全集 set-diff 清理；
      2. 从库读回 A 股四状态全集（本地查询，零 Provider 调用），构造
         ``LifecycleStock`` 记录；
      3. ``init_stocks_lifecycle`` 成功即代表四状态均成功拉取，``status_flags``
         四类全真。

    快照不可变，范围任务与自动日更各只构建一次。
    """
    # 局部导入避免循环依赖（data_init 不导入本模块，防御性保留）
    from src.services.data_init import DataInitService

    service = DataInitService(session)
    await service.init_stocks_lifecycle()

    rows = (
        await session.execute(
            select(
                Stock.ts_code,
                Stock.exchange,
                Stock.list_status,
                Stock.list_date,
                Stock.delist_date,
                Stock.name,
            ).where(Stock.exchange.in_(A_STOCK_EXCHANGES))
        )
    ).all()

    records: List[LifecycleStock] = []
    for ts_code, exchange, list_status, list_date, delist_date, name in rows:
        if not ts_code:
            continue
        ex = resolve_a_stock_exchange(ts_code, exchange)
        if ex is None:
            continue
        records.append(
            LifecycleStock(
                ts_code=ts_code,
                exchange=ex,
                list_status=(list_status or "").strip().upper(),
                name=name,
                list_date=list_date,
                delist_date=delist_date,
            )
        )

    status_flags = {s: True for s in ("L", "D", "P", "G")}
    snapshot = LifecycleSnapshot(
        records=tuple(records), status_flags=status_flags
    )
    logger.info(
        "[MarketMetrics] 构建生命周期快照: records=%d, status_flags=%s",
        len(records),
        status_flags,
    )
    return snapshot


# ---------------------------------------------------------------------------
# MarketMetricsService
# ---------------------------------------------------------------------------


class MarketMetricsService:
    """市场量价单日汇总服务（架构 §6.1 全链 / ADR-3/4）。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.data_source = DataSourceFactory.create()

    async def sync_date(
        self,
        trade_date: date,
        lifecycle_snapshot: LifecycleSnapshot,
        task_context: Optional["TaskFenceContext"] = None,
        close_cache: Optional[MutableMapping[str, Tuple[date, Decimal]]] = None,
    ) -> str:
        """单交易日完整闭环（架构 §6.1.1-9）。

        Args:
            trade_date: 目标交易日 T。
            lifecycle_snapshot: 调用方已完成 preflight 的不可变生命周期快照。
            task_context: 可选 ``TaskFenceContext``（管理员任务必传，自动日更传
                ``None``）；非 None 时 upsert 前先 ``lock_and_validate(session)``，
                与业务写共用同一事务（实现于 plan-04）。
            close_cache: 范围任务跨日缓存 ``ts_code -> (date, close)``，命中免请求。

        Returns:
            ``"success"`` / ``"skipped"``（休市）；抛 ``MarketMetricsSyncError`` /
            其他异常表示当日失败（``"failed"``）。
        """
        import time

        started = time.monotonic()
        expected = lifecycle_snapshot.expected_codes(trade_date)
        expected_count = len(expected)

        # ---- 1. 日历守卫（AC-09）----
        cal_repo = TradingCalendarRepository(self.session)
        cal_record = await cal_repo.get_record(trade_date)
        if cal_record is None:
            raise MarketMetricsSyncError(
                f"本地日历无覆盖记录 trade_date={trade_date}（拒绝按自然日/工作日猜测）",
                expected=expected_count,
            )
        if not cal_record.is_open:
            logger.info(
                "[MarketMetrics] sync_date skipped trade_date=%s (休市, "
                "expected=%d)",
                trade_date,
                expected_count,
            )
            return "skipped"

        # ---- 2. 快照校验（架构 §6.1.2）----
        self._validate_snapshot(lifecycle_snapshot, expected_count)

        # ---- 3. 拉取全市场行情（架构 §6.1.3）----
        raw_quotes = self.data_source.get_market_daily_quotes(
            trade_date, expected_count=expected_count
        )
        if not raw_quotes:
            raise MarketMetricsSyncError(
                f"全市场行情为空 trade_date={trade_date}",
                expected=expected_count,
            )

        # ---- 4. 过滤与数值复验（架构 §6.1.4）----
        daily_map = self._filter_and_validate_quotes(
            raw_quotes, expected, trade_date, expected_count
        )
        daily_count = len(daily_map)

        # ---- 5. 停牌确认（AC-13 / 架构 §6.1.5）----
        missing = expected - set(daily_map.keys())
        full_day_suspended, suspension_undeterminable, missing_no_record = (
            self._confirm_suspensions(trade_date, missing, expected_count, daily_count)
        )

        # ---- 6. 分块有界前收盘补价（ADR-3 / 架构 §6.1.6）----
        problem_codes: List[str] = []
        problem_codes.extend(suspension_undeterminable)
        problem_codes.extend(missing_no_record)

        supplemented: Dict[str, Decimal] = {}
        if full_day_suspended:
            resolved, unresolved = await self._supplement_close_prices(
                trade_date=trade_date,
                supplement_codes=full_day_suspended,
                lifecycle_snapshot=lifecycle_snapshot,
                close_cache=close_cache,
                expected_count=expected_count,
                daily_count=daily_count,
                suspended_count=len(full_day_suspended),
            )
            supplemented = resolved
            problem_codes.extend(sorted(unresolved))

        suspended_count = len(supplemented)
        final_count = daily_count + suspended_count

        # ---- 7. 补值与集合平衡（架构 §6.1.7）----
        self._validate_balance(
            expected=expected,
            expected_count=expected_count,
            daily_map=daily_map,
            supplemented=supplemented,
            suspended_count=suspended_count,
            final_count=final_count,
            problem_codes=problem_codes,
            lifecycle_snapshot=lifecycle_snapshot,
            trade_date=trade_date,
        )

        # ---- 8. 计算（全 Decimal，架构 §6.1.8）----
        volume_shares, amount_yuan, average_price = self._compute_metrics(
            daily_map, supplemented, final_count
        )

        # ---- 9. 原子 upsert（ADR-4 / 架构 §6.1.9）----
        await self._atomic_upsert(
            trade_date=trade_date,
            volume_shares=volume_shares,
            amount_yuan=amount_yuan,
            average_price=average_price,
            expected_count=expected_count,
            daily_count=daily_count,
            suspended_count=suspended_count,
            final_count=final_count,
            task_context=task_context,
        )

        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "[MarketMetrics] sync_date success trade_date=%s expected=%d "
            "daily=%d suspended=%d final=%d duration_ms=%d status=success",
            trade_date,
            expected_count,
            daily_count,
            suspended_count,
            final_count,
            duration_ms,
        )
        return "success"

    # ------------------------------------------------------------------
    # 步骤实现
    # ------------------------------------------------------------------

    def _validate_snapshot(
        self,
        snapshot: LifecycleSnapshot,
        expected_count: int,
    ) -> None:
        """快照四类标记全真 + 逐记录字段校验（架构 §6.1.2）。"""
        flags = snapshot.status_flags or {}
        missing_flags = [
            s for s in ("L", "D", "P", "G") if not flags.get(s, False)
        ]
        if missing_flags:
            raise MarketMetricsSyncError(
                f"快照四类标记不全: 缺 {missing_flags}（拒绝用当前 L 集合降级）",
                expected=expected_count,
            )
        violations, samples = validate_lifecycle_records(list(snapshot.records))
        if violations:
            raise MarketMetricsSyncError(
                "快照记录校验失败: "
                + "; ".join(violations[:5])
                + f" | 样本={samples[:10]}",
                expected=expected_count,
            )

    def _filter_and_validate_quotes(
        self,
        raw_quotes: List[MarketDailyQuote],
        expected: Set[str],
        trade_date: date,
        expected_count: int,
    ) -> Dict[str, MarketDailyQuote]:
        """仅保留 A 股且 ∈ 预期集合的行；越界/重复/日期不符/关键值非法 → 抛错。"""
        daily_map: Dict[str, MarketDailyQuote] = {}
        for q in raw_quotes:
            ts_code = q.ts_code
            if ts_code in daily_map:
                raise MarketMetricsSyncError(
                    f"行情出现重复 ts_code={ts_code} trade_date={trade_date}",
                    expected=expected_count,
                )
            if resolve_a_stock_exchange(ts_code, None) is None or ts_code not in expected:
                raise MarketMetricsSyncError(
                    f"越界代码 ts_code={ts_code}（不在预期 A 股集合内）",
                    expected=expected_count,
                    daily=len(daily_map),
                    problem_codes=[ts_code],
                )
            if q.trade_date != trade_date:
                raise MarketMetricsSyncError(
                    f"日期不符 ts_code={ts_code} 期望 {trade_date} 实际 {q.trade_date}",
                    expected=expected_count,
                    daily=len(daily_map),
                    problem_codes=[ts_code],
                )
            # 数值复验：finite / close>0 / vol>=0 / amount>=0
            if not self._is_valid_quote_value(q):
                raise MarketMetricsSyncError(
                    f"关键值非法 ts_code={ts_code} close={q.close} "
                    f"vol={q.vol} amount={q.amount}",
                    expected=expected_count,
                    daily=len(daily_map),
                    problem_codes=[ts_code],
                )
            daily_map[ts_code] = q
        return daily_map

    @staticmethod
    def _is_valid_quote_value(q: MarketDailyQuote) -> bool:
        """复验数值：close>0 / vol>=0 / amount>=0 且均 finite。"""
        for v in (q.close, q.vol, q.amount):
            if not isinstance(v, Decimal):
                return False
            if not v.is_finite():
                return False
        return q.close > 0 and q.vol >= 0 and q.amount >= 0

    def _confirm_suspensions(
        self,
        trade_date: date,
        missing: Set[str],
        expected_count: int,
        daily_count: int,
    ) -> Tuple[Set[str], List[str], List[str]]:
        """对预期集合中无 daily 的代码做停牌确认（AC-13 / 架构 §6.1.5）。

        上游 ``suspend_d`` 代理忽略日期过滤、返回跨多日全量行，必须按
        ``record.suspend_date == trade_date`` 客户端过滤后才能作为当日停牌证据。
        仅 ``suspend_type == 'S'`` 且 ``suspend_timing`` 为空（明确全天）进补价集合；
        无法判定者整日失败（§8.6 宁失败不猜测）。

        Returns:
            ``(full_day_suspended, suspension_undeterminable, missing_no_record)``
        """
        full_day: Set[str] = set()
        undeterminable: List[str] = []
        no_record: List[str] = []

        if not missing:
            return full_day, undeterminable, no_record

        # 客户端按 suspend_date == trade_date 过滤当日停牌证据
        all_suspensions = self.data_source.get_suspensions(trade_date)
        susp_by_code: Dict[str, List] = {}
        for rec in all_suspensions:
            if rec.suspend_date != trade_date:
                continue  # 跨多日全量行过滤
            susp_by_code.setdefault(rec.ts_code, []).append(rec)

        for code in sorted(missing):
            records = susp_by_code.get(code, [])
            if not records:
                # 既无 daily 也无当日停牌证据 → 缺失
                no_record.append(code)
                continue
            # 判定是否全天停牌：suspend_type=='S' 且 suspend_timing 为空
            is_full_day = any(
                (r.suspend_type or "").strip().upper() == "S"
                and (r.suspend_timing is None or r.suspend_timing.strip() == "")
                for r in records
            )
            if is_full_day:
                full_day.add(code)
            else:
                # 有停牌证据但无法判定为全天（盘中临停或类型不符）→ 整日失败
                undeterminable.append(code)

        if undeterminable or no_record:
            logger.warning(
                "[MarketMetrics] 停牌确认存在问题 trade_date=%s "
                "undeterminable=%d missing_no_record=%d samples=%s",
                trade_date,
                len(undeterminable),
                len(no_record),
                (undeterminable + no_record)[:PROBLEM_CODE_SAMPLE_LIMIT],
            )
        return full_day, undeterminable, no_record

    async def _supplement_close_prices(
        self,
        trade_date: date,
        supplement_codes: Set[str],
        lifecycle_snapshot: LifecycleSnapshot,
        close_cache: Optional[MutableMapping[str, Tuple[date, Decimal]]],
        expected_count: int,
        daily_count: int,
        suspended_count: int,
    ) -> Tuple[Dict[str, Decimal], Set[str]]:
        """分块有界前收盘补价（ADR-3 / 架构 §6.1.6）。

        补价集合按 ≤100 代码分块；从 ``[T-60日, T-1日]``（自然日窗口）起向前调
        ``get_close_quotes_in_window``；逐代码取 ``<T`` 的最大有效
        ``trade_date/close``；扫描下界 = 各股 ``list_date``；每批最多 250 个窗口；
        总请求预算 ``MAX_CLOSE_LOOKBACK_REQUESTS``；先查 ``close_cache`` 命中则免请求；
        扫描到底未命中 → 未决（调用方判整日失败）。**禁止 qfq 后备/逐股无界 N+1**。

        Returns:
            ``(resolved: ts_code -> last_close, unresolved: set)``
        """
        resolved: Dict[str, Decimal] = {}
        unresolved: Set[str] = set()

        if not supplement_codes:
            return resolved, unresolved

        # 先消费缓存命中（免 Provider 请求）
        pending: Set[str] = set()
        for code in supplement_codes:
            cached = close_cache.get(code) if close_cache is not None else None
            if cached is not None and cached[0] < trade_date:
                resolved[code] = cached[1]
            else:
                pending.add(code)

        if not pending:
            return resolved, unresolved

        requests_made = 0
        budget_exhausted = False
        pending_sorted = sorted(pending)

        for chunk_start in range(
            0, len(pending_sorted), CLOSE_LOOKBACK_MAX_CODES_PER_BATCH
        ):
            if budget_exhausted:
                break
            chunk = pending_sorted[
                chunk_start : chunk_start + CLOSE_LOOKBACK_MAX_CODES_PER_BATCH
            ]
            chunk_pending: Set[str] = {c for c in chunk if c not in resolved}

            for block_i in range(CLOSE_LOOKBACK_MAX_WINDOWS_PER_BATCH):
                if not chunk_pending:
                    break
                if requests_made >= MAX_CLOSE_LOOKBACK_REQUESTS:
                    budget_exhausted = True
                    break
                # 第 block_i 个 60 自然日窗口：[T-60*(i+1), T-60*i-1]
                block_end = trade_date - timedelta(
                    days=CLOSE_LOOKBACK_WINDOW_DAYS * block_i + 1
                )
                block_start = trade_date - timedelta(
                    days=CLOSE_LOOKBACK_WINDOW_DAYS * (block_i + 1)
                )
                # 扫描下界 = 各股 list_date：整块早于全部未决代码的最早 list_date 则停止
                list_dates = [
                    lifecycle_snapshot.list_date_of(c)
                    for c in chunk_pending
                    if lifecycle_snapshot.list_date_of(c) is not None
                ]
                if list_dates and block_end < min(list_dates):
                    break  # 任何剩余代码都不可能在更早窗口有数据

                requests_made += 1
                quotes = self.data_source.get_close_quotes_in_window(
                    sorted(chunk_pending), block_start, block_end
                )
                # 逐代码取 <T 的最大有效 trade_date/close
                best: Dict[str, Tuple[date, Decimal]] = {}
                for q in quotes:
                    if q.trade_date >= trade_date:
                        continue
                    if not (
                        isinstance(q.close, Decimal) and q.close.is_finite() and q.close > 0
                    ):
                        continue
                    cur = best.get(q.ts_code)
                    if cur is None or q.trade_date > cur[0]:
                        best[q.ts_code] = (q.trade_date, q.close)
                for code in list(chunk_pending):
                    if code in best:
                        hit_date, hit_close = best[code]
                        resolved[code] = hit_close
                        if close_cache is not None:
                            close_cache[code] = (hit_date, hit_close)
                        chunk_pending.discard(code)

        unresolved = set(supplement_codes) - set(resolved)
        if unresolved:
            logger.warning(
                "[MarketMetrics] 补价未决 trade_date=%s unresolved=%d "
                "requests_made=%d budget_exhausted=%s samples=%s",
                trade_date,
                len(unresolved),
                requests_made,
                budget_exhausted,
                sorted(unresolved)[:PROBLEM_CODE_SAMPLE_LIMIT],
            )
        return resolved, unresolved

    def _validate_balance(
        self,
        expected: Set[str],
        expected_count: int,
        daily_map: Dict[str, MarketDailyQuote],
        supplemented: Dict[str, Decimal],
        suspended_count: int,
        final_count: int,
        problem_codes: List[str],
        lifecycle_snapshot: LifecycleSnapshot,
        trade_date: date,
    ) -> None:
        """补值与集合平衡（架构 §6.1.7）：daily+suspended==expected==final。"""
        # 存在任何问题代码（停牌无法判定/缺失/补价未决）即整日失败
        if problem_codes:
            raise MarketMetricsSyncError(
                "存在无法解析的预期代码（停牌无法判定/缺失/补价未决）",
                expected=expected_count,
                daily=len(daily_map),
                suspended=suspended_count,
                final=final_count,
                problem_codes=problem_codes,
            )
        # 集合平衡：daily + suspended == expected == final
        final_codes = set(daily_map.keys()) | set(supplemented.keys())
        if len(final_codes) != expected_count or final_count != expected_count:
            raise MarketMetricsSyncError(
                "集合不平衡: daily + suspended != expected",
                expected=expected_count,
                daily=len(daily_map),
                suspended=suspended_count,
                final=final_count,
                problem_codes=sorted(expected - final_codes),
            )
        # 单交易所整体缺失校验：某交易所预期非空但补齐后最终参与为 0 → 整日失败
        per_exchange_expected: Dict[str, Set[str]] = {}
        for code in expected:
            ex = resolve_a_stock_exchange(code, None)
            if ex is None:
                continue
            per_exchange_expected.setdefault(ex, set()).add(code)
        per_exchange_final: Dict[str, int] = {}
        for code in final_codes:
            ex = resolve_a_stock_exchange(code, None)
            if ex is None:
                continue
            per_exchange_final[ex] = per_exchange_final.get(ex, 0) + 1
        missing_exchanges = [
            ex
            for ex, codes in per_exchange_expected.items()
            if codes and per_exchange_final.get(ex, 0) == 0
        ]
        if missing_exchanges:
            raise MarketMetricsSyncError(
                f"交易所整体缺失: {missing_exchanges}（预期非空但最终参与为 0）",
                expected=expected_count,
                daily=len(daily_map),
                suspended=suspended_count,
                final=final_count,
            )

    @staticmethod
    def _compute_metrics(
        daily_map: Dict[str, MarketDailyQuote],
        supplemented: Dict[str, Decimal],
        final_count: int,
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """Decimal 计算（架构 §6.1.8）：vol×100 / amount×1000 / Σclose/final（4 位）。"""
        volume_shares = Decimal(0)
        amount_yuan = Decimal(0)
        sum_close = Decimal(0)
        for q in daily_map.values():
            volume_shares += Decimal(q.vol) * Decimal(100)
            amount_yuan += Decimal(q.amount) * Decimal(1000)
            sum_close += Decimal(q.close)
        for last_close in supplemented.values():
            # 全天停牌：量额为 0、close=最近有效收盘
            sum_close += Decimal(last_close)
        if final_count <= 0:
            # 防御性：平衡校验已先失败，不应到达（架构 §6.1 边界）
            raise MarketMetricsSyncError(
                "final_count=0 无法计算平均价（集合平衡应已先失败）",
                final=final_count,
            )
        average_price = (sum_close / Decimal(final_count)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        return volume_shares, amount_yuan, average_price

    async def _atomic_upsert(
        self,
        trade_date: date,
        volume_shares: Decimal,
        amount_yuan: Decimal,
        average_price: Decimal,
        expected_count: int,
        daily_count: int,
        suspended_count: int,
        final_count: int,
        task_context: Optional["TaskFenceContext"],
    ) -> None:
        """单事务原子 upsert（ADR-4 / 架构 §6.1.9）。

        ``task_context`` 非 None 时先 ``lock_and_validate(session)``（同事务
        ``SELECT ... FOR UPDATE`` AsyncTask 行，实现于 plan-04），再
        ``on_conflict_do_update(trade_date)``；任何异常整体 rollback，不保留半成品。
        """
        values = {
            "trade_date": trade_date,
            "volume_shares": volume_shares,
            "amount_yuan": amount_yuan,
            "average_price": average_price,
            "expected_stock_count": expected_count,
            "daily_quote_count": daily_count,
            "suspended_stock_count": suspended_count,
            "final_stock_count": final_count,
        }
        try:
            if task_context is not None:
                # 协议调用：TaskFenceContext.lock_and_validate(session)（plan-04 落地）
                await task_context.lock_and_validate(self.session)
            stmt = pg_insert(MarketDailyMetric).values(**values)
            update_cols = {k: getattr(stmt.excluded, k) for k in values if k != "trade_date"}
            # 显式刷新 updated_at：on_conflict_do_update 不会触发 ORM onupdate，
            # 必须在 set_ 中显式赋 func.now()，使覆盖写更新时间戳（S1 后补丁）
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
