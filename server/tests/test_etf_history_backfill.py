"""
ETF 历史回填（BACKFILL_ETF_HISTORY）执行验证测试 — plan-02

本测试是 plan-02「历史回填」功能的 E2E「执行验证」（验收标准 §5 的执行验证项）。
本功能无 UI，是纯后端 task handler 功能（历史数据写入唯一执行者 = BACKFILL_ETF_HISTORY），
按 auto-dev / test-e2e skill 规则不允许豁免执行验证，因此用 pytest 集成测试替代 Playwright。

验证链路（架构 §6.2）：
  POST 触发 BACKFILL_ETF_HISTORY 任务（start_date/end_date）→ 任务 status 流转到 completed、
  progress 逐日推进 → etf_daily 表有该日期范围的记录、share_change 正确依赖上一日、
  曲线无断裂（同口径复用 sync_etf_daily）。

Red 阶段（功能未实现）预期失败：失败原因必须是「目标功能尚未实现」——
  - EtfDataInitService.backfill_etf_history 方法不存在
  - BACKFILL_ETF_HISTORY 未注册到 TaskType 枚举 / TaskRegistry（创建任务或取 handler 失败）
  - backfill_etf_history_task 未加入 __all__
  - admin 历史回填端点（init_etf_history router）未注册

实现（implementer）后，本测试应全部通过并产出 green 证据。

时钟解耦（吸取 plan-01 red 测试教训）：
  backfill 接受显式 start_date/end_date 参数（与 plan-01「当日采集」从墙钟取当日不同），
  因此测试天然与时钟解耦。start/end 用固定日期（BACKFILL_START/BACKFILL_END），mock
  数据的 trade_date 与 start/end 对齐，断言查的也是这些固定日期，与系统墙钟无关。
"""

import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.task_manager import TaskManager
from src.services.task_executor import TaskRegistry


# ---------------------------------------------------------------------------
# 固定回填日期范围（与时钟解耦）
# ---------------------------------------------------------------------------
# 用一组确定的工作日作为 backfill 范围。与系统墙钟完全无关：
# backfill 接受显式 start_date/end_date 参数，mock 数据的 trade_date 与
# start/end 对齐，断言查的也是这些固定日期。
#
# 2026-07-20(周一) ~ 2026-07-24(周五) 共 5 个工作日。mock 交易日历也只
# 返回这 5 天（get_trading_calendar），保证 backfill 的 TradingCalendar
# 筛选结果确定。
BACKFILL_START = date(2026, 7, 20)
BACKFILL_END = date(2026, 7, 24)
# 升序交易日列表（backfill 按日期升序逐日处理）
BACKFILL_TRADING_DAYS = [
    date(2026, 7, 20),
    date(2026, 7, 21),
    date(2026, 7, 22),
    date(2026, 7, 23),
    date(2026, 7, 24),
]


# ---------------------------------------------------------------------------
# 构建校验（前置存在性）：证明目标功能尚未实现是当前状态，实现后这些用例会通过
# ---------------------------------------------------------------------------


class TestBackfillEtfHistoryImportable:
    """验证 plan-02 待实现方法/枚举/handler/端点的前置存在性。"""

    def test_backfill_etf_history_method_exists(self):
        """EtfDataInitService.backfill_etf_history 已定义（plan-02 §3 #1）。"""
        from src.services.data_init_etf import EtfDataInitService

        assert hasattr(EtfDataInitService, "backfill_etf_history"), (
            "EtfDataInitService 缺方法 backfill_etf_history"
        )

    def test_backfill_etf_history_task_type_registered(self):
        """TaskType.BACKFILL_ETF_HISTORY 已定义（plan-02 §3 #2）。"""
        from src.services.task_handlers import TaskType

        assert hasattr(TaskType, "BACKFILL_ETF_HISTORY"), (
            "TaskType 未定义 BACKFILL_ETF_HISTORY"
        )
        assert TaskType.BACKFILL_ETF_HISTORY.value == "backfill_etf_history"

    def test_backfill_etf_history_handler_registered(self):
        """backfill_etf_history_task handler 已注册到 TaskRegistry（plan-02 §3 #2）。"""
        handler = TaskRegistry.get_handler("backfill_etf_history")
        assert handler is not None, (
            "backfill_etf_history handler 未注册到 TaskRegistry"
        )
        assert callable(handler)

    def test_backfill_etf_history_handler_exported(self):
        """backfill_etf_history_task 已加入 task_handlers.__all__（plan-02 §3 #2）。"""
        from src.services import task_handlers

        assert "backfill_etf_history_task" in task_handlers.__all__, (
            "backfill_etf_history_task 未加入 __all__"
        )

    def test_admin_init_etf_history_router_registered(self):
        """admin 历史回填端点 router 已注册到 admin（plan-02 §3 #3 #4）。

        校验 api/admin 包导出了 init_etf_history_router 并 include。
        """
        from src.api import admin as admin_pkg

        assert hasattr(admin_pkg, "init_etf_history_router"), (
            "api/admin 未导出 init_etf_history_router"
        )

    def test_admin_init_etf_history_router_has_endpoint(self):
        """init_etf_history_router 暴露 POST /init/etf-history 端点（plan-02 §3 #3）。"""
        from src.api.admin import init_etf_history

        paths = {getattr(r, "path", None) for r in init_etf_history.router.routes}
        assert "/init/etf-history" in paths, (
            f"init_etf_history_router 未暴露 /init/etf-history 端点，实际路径: {paths}"
        )
        # 校验方法为 POST
        methods = set()
        for r in init_etf_history.router.routes:
            if getattr(r, "path", None) == "/init/etf-history":
                methods.update(getattr(r, "methods", set()) or set())
        assert "POST" in methods, (
            f"/init/etf-history 不是 POST，实际方法: {methods}"
        )


# ---------------------------------------------------------------------------
# Mock 数据源工厂（注入确定性 ETF 数据 + 交易日历）
# ---------------------------------------------------------------------------
# backfill 内部会：
#   1. 调 sync_etf_basic() → get_fund_basic_etf()
#   2. 用 TradingCalendar.get_trading_days_between() 取交易日 → get_trading_calendar()
#   3. 逐日调 sync_etf_daily(trade_date) → get_fund_share(trade_date) + get_fund_nav(ts_code)
#
# 用一个 fake client 同时提供 ETF 数据与交易日历，使整条链路不依赖外部 Tushare。
# mock 数据刻意构造覆盖 §5 执行验证的确定性断言：份额逐日递增，便于断言 share_change。


# 三只宽基 ETF，与 plan-01 测试同口径，便于 cross-check。
_ETF_CODES = ["510300.SH", "512100.SH", "159915.SZ"]


def _fake_fund_basic_etf():
    """模拟 get_fund_basic_etf() 返回（架构 §7.2 EtfBasicRecord 口径）。"""
    return [
        {
            "ts_code": "510300.SH", "name": "华泰柏瑞沪深300ETF",
            "management": "华泰柏瑞", "fund_type": "ETF", "list_date": "2012-05-28",
            "benchmark": "沪深300指数收益率×100%", "status": "I",
        },
        {
            "ts_code": "512100.SH", "name": "南方中证1000ETF",
            "management": "南方基金", "fund_type": "ETF", "list_date": "2016-09-29",
            "benchmark": "中证1000指数收益率×100%", "status": "I",
        },
        {
            "ts_code": "159915.SZ", "name": "易方达创业板ETF",
            "management": "易方达", "fund_type": "ETF", "list_date": "2011-09-20",
            "benchmark": "创业板指收益率×100%", "status": "I",
        },
    ]


def _fake_fund_share(trade_date: str):
    """模拟 get_fund_share(trade_date)，按日返回确定性递增份额（万份）。

    每只 ETF 每日份额 = 基线 + 日序号 × 步长，保证升序逐日回填时
    share_change = 当日 − 前日 = 固定步长（确定性可断言）。

    trade_date 可能是 'YYYYMMDD' 或 'YYYY-MM-DD'，统一归一化后取日序号。
    """
    d = datetime.strptime(trade_date.replace("-", ""), "%Y%m%d").date()
    day_index = BACKFILL_TRADING_DAYS.index(d)  # 0..4

    base = {
        "510300.SH": 1200000.0,
        "512100.SH": 800000.0,
        "159915.SZ": 500000.0,
    }
    step = {
        "510300.SH": 50000.0,
        "512100.SH": 10000.0,
        "159915.SZ": 5000.0,
    }

    return [
        {
            "ts_code": code, "trade_date": trade_date,
            "fd_share": base[code] + day_index * step[code],
            "fund_type": "ETF", "market": "E",
        }
        for code in _ETF_CODES
    ]


def _fake_fund_nav_factory():
    """模拟 get_fund_nav(ts_code)，返回覆盖整个回填范围的历史净值列表。

    backfill 每日调用 sync_etf_daily → 对每只 ts_code 取 nav_date==trade_date 的 unit_nav。
    为支持范围内任意交易日匹配，这里返回覆盖全部 5 天的净值记录（unit_nav 固定，便于断言）。
    """
    nav_records = {
        "510300.SH": [
            {"ts_code": "510300.SH", "nav_date": d.isoformat(), "unit_nav": 4.0000}
            for d in BACKFILL_TRADING_DAYS
        ],
        "512100.SH": [
            {"ts_code": "512100.SH", "nav_date": d.isoformat(), "unit_nav": 2.5000}
            for d in BACKFILL_TRADING_DAYS
        ],
        "159915.SZ": [
            {"ts_code": "159915.SZ", "nav_date": d.isoformat(), "unit_nav": 3.0000}
            for d in BACKFILL_TRADING_DAYS
        ],
    }

    def _get_nav(ts_code: str):
        return nav_records.get(ts_code, [])

    return _get_nav


def _fake_trading_calendar():
    """模拟 get_trading_calendar() 返回，只含回填范围的 5 个工作日。

    backfill 用 TradingCalendar.get_trading_days_between(start, end) 筛交易日，
    TradingCalendar 内部调 source.get_trading_calendar()。返回确定的 5 天，
    保证 backfill 处理的交易日列表确定、与时钟无关。
    """
    return list(BACKFILL_TRADING_DAYS)


def _build_fake_client():
    """构造确定性 mock 数据源客户端（ETF 数据 + 交易日历）。"""
    fake_client = AsyncMock()
    fake_client.get_fund_basic_etf = _fake_fund_basic_etf
    fake_client.get_fund_share = _fake_fund_share
    fake_client.get_fund_nav = _fake_fund_nav_factory()
    fake_client.get_trading_calendar = _fake_trading_calendar
    return fake_client


# ---------------------------------------------------------------------------
# 执行验证：触发 BACKFILL_ETF_HISTORY → completed → etf_daily 有范围数据、share_change 依赖上一日
# 数据源用 mock 注入，避免依赖外部 Tushare（与 task handler 的数据写入契约无关）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backfill_etf_history_task_completes_and_writes_range(db_session):
    """
    执行验证主用例（plan-02 §5 执行验证项）：
      触发回填（start_date/end_date）→ 任务 completed → etf_daily 有该范围交易日记录。

    覆盖：
      - 任务创建成功（TaskType.BACKFILL_ETF_HISTORY 可创建、带 start/end params）
      - 任务执行成功（status=completed）
      - 目标表数据正确（范围内每个交易日 3 条记录、share/unit_nav 有值）
    """
    from src.services.task_handlers import TaskType

    manager = TaskManager(db_session)
    task = await manager.create_task(
        task_type=TaskType.BACKFILL_ETF_HISTORY.value,
        params={
            "start_date": BACKFILL_START.isoformat(),
            "end_date": BACKFILL_END.isoformat(),
        },
    )
    assert task is not None
    assert task.task_type == "backfill_etf_history"
    assert task.status == "pending"

    handler = TaskRegistry.get_handler("backfill_etf_history")
    assert handler is not None

    # mock 数据源后执行 handler（注入确定性 ETF 数据 + 交易日历）
    with patch("src.services.data_acquisition.DataSourceFactory.create",
               return_value=_build_fake_client()):
        await manager.start_task(task.task_id)
        await handler(
            task.task_id,
            {"start_date": BACKFILL_START.isoformat(),
             "end_date": BACKFILL_END.isoformat()},
            manager,
        )
        await manager.complete_task(task.task_id, success=True)

    completed = await manager.get_task(task.task_id)
    assert completed.status == "completed", (
        f"任务未完成: status={completed.status}"
    )

    # etf_daily 表有范围内每个交易日的记录
    from src.models.etf import EtfDaily

    for trade_day in BACKFILL_TRADING_DAYS:
        result = await db_session.execute(
            select(func.count()).select_from(EtfDaily)
            .where(EtfDaily.trade_date == trade_day)
        )
        count = result.scalar_one()
        assert count == 3, (
            f"etf_daily {trade_day} 记录数 != 3: {count}"
        )

    # share / unit_nav 有值（抽查首尾两日）
    for trade_day in (BACKFILL_TRADING_DAYS[0], BACKFILL_TRADING_DAYS[-1]):
        rows = (await db_session.execute(
            select(EtfDaily).where(EtfDaily.trade_date == trade_day)
        )).scalars().all()
        for row in rows:
            assert row.share is not None, f"{row.ts_code}@{trade_day} share 为空"
            assert row.unit_nav is not None, f"{row.ts_code}@{trade_day} unit_nav 为空"


@pytest.mark.asyncio
async def test_backfill_share_change_depends_on_previous_day(db_session):
    """
    执行验证 — 曲线无断裂 / share_change 依赖上一日（plan-02 §5 曲线无断裂验证项）：
      回填按日期升序逐日写，当日 share_change 应 = 当日 share − 上一日 share。
      覆盖范围内连续两日抽查（day2 - day1），share_change/net_inflow 计算正确。

    这是 plan-02 的核心验收点（ADR-5：同口径复用 + 按日期升序保证前日依赖就地满足）。
    """
    from src.models.etf import EtfDaily
    from src.services.task_handlers import TaskType

    manager = TaskManager(db_session)
    task = await manager.create_task(
        task_type=TaskType.BACKFILL_ETF_HISTORY.value,
        params={
            "start_date": BACKFILL_START.isoformat(),
            "end_date": BACKFILL_END.isoformat(),
        },
    )
    handler = TaskRegistry.get_handler("backfill_etf_history")

    with patch("src.services.data_acquisition.DataSourceFactory.create",
               return_value=_build_fake_client()):
        await manager.start_task(task.task_id)
        await handler(
            task.task_id,
            {"start_date": BACKFILL_START.isoformat(),
             "end_date": BACKFILL_END.isoformat()},
            manager,
        )
        await manager.complete_task(task.task_id, success=True)

    # 抽查 day1(首日) 与 day2(第二日) 的 share_change
    day1, day2 = BACKFILL_TRADING_DAYS[0], BACKFILL_TRADING_DAYS[1]

    # 首日：无前日份额 → share_change / net_inflow 为 null（ADR-3 预期，非断裂）
    day1_rows = (await db_session.execute(
        select(EtfDaily).where(EtfDaily.trade_date == day1)
    )).scalars().all()
    for row in day1_rows:
        assert row.share_change is None, (
            f"{row.ts_code}@{day1} 首日 share_change 应为 null: {row.share_change}"
        )
        assert row.net_inflow is None, (
            f"{row.ts_code}@{day1} 首日 net_inflow 应为 null: {row.net_inflow}"
        )

    # 第二日：share_change = day2 share − day1 share（= 固定步长）
    day2_rows = (await db_session.execute(
        select(EtfDaily).where(EtfDaily.trade_date == day2)
    )).scalars().all()
    by_code = {r.ts_code: r for r in day2_rows}

    # 510300: 步长 50000.0；net_inflow = 50000 × 4.0 / 10000 = 20.0
    assert by_code["510300.SH"].share_change == Decimal("50000.0"), (
        f"510300 share_change 错误: {by_code['510300.SH'].share_change}"
    )
    assert by_code["510300.SH"].net_inflow == Decimal("20.0000"), (
        f"510300 net_inflow 错误: {by_code['510300.SH'].net_inflow}"
    )
    # 512100: 步长 10000.0；net_inflow = 10000 × 2.5 / 10000 = 2.5
    assert by_code["512100.SH"].share_change == Decimal("10000.0")
    assert by_code["512100.SH"].net_inflow == Decimal("2.5000")


@pytest.mark.asyncio
async def test_backfill_progress_increments_per_day(db_session):
    """
    覆盖 plan-02 §5 后端验收 + 可观测性（架构 §8.5）：
      任务 progress 逐日推进（progress/total 随交易日推进）。

    backfill 完成后任务 progress 字段推进到 total（交易日数 = 5），
    且有逐日 AsyncTaskLog 记录（manager.log_message）。
    """
    from src.models.async_task import AsyncTaskLog
    from src.services.task_handlers import TaskType

    manager = TaskManager(db_session)
    task = await manager.create_task(
        task_type=TaskType.BACKFILL_ETF_HISTORY.value,
        params={
            "start_date": BACKFILL_START.isoformat(),
            "end_date": BACKFILL_END.isoformat(),
        },
    )
    handler = TaskRegistry.get_handler("backfill_etf_history")

    with patch("src.services.data_acquisition.DataSourceFactory.create",
               return_value=_build_fake_client()):
        await manager.start_task(task.task_id)
        await handler(
            task.task_id,
            {"start_date": BACKFILL_START.isoformat(),
             "end_date": BACKFILL_END.isoformat()},
            manager,
        )
        await manager.complete_task(task.task_id, success=True)

    # 任务 total/progress 写入（total = 交易日数 = 5）
    completed = await manager.get_task(task.task_id)
    assert completed.total == len(BACKFILL_TRADING_DAYS), (
        f"任务 total != {len(BACKFILL_TRADING_DAYS)}: {completed.total}"
    )
    assert completed.progress == len(BACKFILL_TRADING_DAYS), (
        f"任务 progress 未推进到 total: progress={completed.progress}, "
        f"total={completed.total}"
    )

    # 可观测性：任务有逐日日志记录（manager.log_message）
    log_result = await db_session.execute(
        select(func.count()).select_from(AsyncTaskLog)
        .where(AsyncTaskLog.task_id == task.task_id)
    )
    log_count = log_result.scalar_one()
    assert log_count >= 1, "任务无任何日志记录"


@pytest.mark.asyncio
async def test_backfill_etf_history_service_direct(db_session):
    """
    覆盖 plan-02 §3 #1 实现规格 — 直接调 service 层验证 backfill_etf_history 契约：
      backfill_etf_history(start_date, end_date) 返回 {total_days, processed_days, failed_days}，
      且逐日升序写入 etf_daily。

    这是对 service 方法的直接契约验证（不经过 task handler），确保实现复用 sync_etf_daily 同口径。
    """
    from src.models.etf import EtfDaily
    from src.services.data_init_etf import EtfDataInitService

    service = EtfDataInitService(db_session)

    with patch("src.services.data_acquisition.DataSourceFactory.create",
               return_value=_build_fake_client()):
        result = await service.backfill_etf_history(
            BACKFILL_START.isoformat(),
            BACKFILL_END.isoformat(),
        )

    # 返回契约：包含 total_days / processed_days / failed_days
    assert isinstance(result, dict)
    assert "total_days" in result, f"返回缺 total_days: {result}"
    assert "processed_days" in result, f"返回缺 processed_days: {result}"
    assert "failed_days" in result, f"返回缺 failed_days: {result}"
    assert result["total_days"] == len(BACKFILL_TRADING_DAYS), (
        f"total_days != 交易日数({len(BACKFILL_TRADING_DAYS)}): {result['total_days']}"
    )
    assert result["processed_days"] == len(BACKFILL_TRADING_DAYS), (
        f"processed_days != 交易日数: {result['processed_days']}"
    )
    assert result["failed_days"] == 0, f"failed_days != 0: {result['failed_days']}"

    # 范围内每个交易日都有 3 条记录
    for trade_day in BACKFILL_TRADING_DAYS:
        count_result = await db_session.execute(
            select(func.count()).select_from(EtfDaily)
            .where(EtfDaily.trade_date == trade_day)
        )
        assert count_result.scalar_one() == 3, (
            f"{trade_day} 记录数 != 3"
        )


@pytest.mark.asyncio
async def test_backfill_reuses_sync_etf_daily_same_caliber(db_session):
    """
    覆盖 plan-02 ADR-5（同口径复用）：backfill 逐日调用 sync_etf_daily，
    与 plan-01 当日采集字段/计算逻辑一致。

    断言：回填范围内连续两日的 share_change 公式（= 当日 − 前日）、
    net_inflow 公式（= share_change × unit_nav / 10000）与 plan-01 一致。
    同时验证回填范围内不含 etf_daily 之外的口径断裂（首日 null 为预期）。
    """
    from src.models.etf import EtfDaily
    from src.services.task_handlers import TaskType

    manager = TaskManager(db_session)
    task = await manager.create_task(
        task_type=TaskType.BACKFILL_ETF_HISTORY.value,
        params={
            "start_date": BACKFILL_START.isoformat(),
            "end_date": BACKFILL_END.isoformat(),
        },
    )
    handler = TaskRegistry.get_handler("backfill_etf_history")

    with patch("src.services.data_acquisition.DataSourceFactory.create",
               return_value=_build_fake_client()):
        await manager.start_task(task.task_id)
        await handler(
            task.task_id,
            {"start_date": BACKFILL_START.isoformat(),
             "end_date": BACKFILL_END.isoformat()},
            manager,
        )
        await manager.complete_task(task.task_id, success=True)

    # 全范围逐日验证：每个非首日的 share_change 都 = 当日 − 前日（曲线连续无断裂）
    for i in range(1, len(BACKFILL_TRADING_DAYS)):
        prev_day = BACKFILL_TRADING_DAYS[i - 1]
        curr_day = BACKFILL_TRADING_DAYS[i]

        prev_rows = {r.ts_code: r for r in (await db_session.execute(
            select(EtfDaily).where(EtfDaily.trade_date == prev_day)
        )).scalars().all()}
        curr_rows = {r.ts_code: r for r in (await db_session.execute(
            select(EtfDaily).where(EtfDaily.trade_date == curr_day)
        )).scalars().all()}

        for code in _ETF_CODES:
            assert code in curr_rows, f"{code}@{curr_day} 缺记录"
            expected_change = curr_rows[code].share - prev_rows[code].share
            assert curr_rows[code].share_change == expected_change, (
                f"{code}@{curr_day} share_change={curr_rows[code].share_change} "
                f"!= 当日-前日 {expected_change}"
            )
            # net_inflow = share_change × unit_nav / 10000（亿元，4 位小数）
            if curr_rows[code].unit_nav is not None:
                expected_inflow = (
                    curr_rows[code].share_change
                    * curr_rows[code].unit_nav
                    / Decimal("10000")
                ).quantize(Decimal("0.0001"))
                assert curr_rows[code].net_inflow == expected_inflow, (
                    f"{code}@{curr_day} net_inflow={curr_rows[code].net_inflow} "
                    f"!= 预期 {expected_inflow}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--no-cov"])
