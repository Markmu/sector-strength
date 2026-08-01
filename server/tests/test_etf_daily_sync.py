"""
ETF 当日采集（SYNC_ETF_DAILY）执行验证测试 — plan-01

本测试是 plan-01「数据层与采集」功能的 E2E「执行验证」（验收标准 §5 的执行验证项）。
本功能无 UI，是纯后端 task handler 功能（数据写入唯一执行者 = SYNC_ETF_DAILY），
按 auto-dev / test-e2e skill 规则不允许豁免执行验证，因此用 pytest 集成测试替代 Playwright。

验证链路（架构 §6.1）：
  触发 SYNC_ETF_DAILY 任务 → 任务 status 流转到 completed → etf_daily 表有当日记录
  且 share/unit_nav 有值、share_change/net_inflow 计算正确。

Red 阶段（功能未实现）预期失败：失败原因必须是「目标功能尚未实现」——
  - EtfBasic/EtfDaily 模型不存在（import 失败）
  - SYNC_ETF_DAILY 未注册到 TaskType 枚举 / TaskRegistry（创建任务或取 handler 失败）
  - EtfDataInitService / collector._update_etf_daily 不存在
  - etf_basic / etf_daily 表未建（查询失败）

实现（implementer）后，本测试应全部通过并产出 green 证据。
"""

import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.task_manager import TaskManager
from src.services.task_executor import TaskRegistry


# ---------------------------------------------------------------------------
# 构建校验（前置存在性）：证明目标功能尚未实现是当前状态，实现后这些用例会通过
# ---------------------------------------------------------------------------


class TestEtfDailySyncImportable:
    """验证 plan-01 待实现模块/枚举/方法的前置存在性。"""

    def test_etf_models_importable(self):
        """EtfBasic / EtfDaily 模型可在 src.models.etf 导入（plan-01 Task #1 #2）。"""
        from src.models.etf import EtfBasic, EtfDaily  # noqa: F401
        from src.models import __all__ as models_all

        assert "EtfBasic" in models_all, "EtfBasic 未注册到 models.__all__"
        assert "EtfDaily" in models_all, "EtfDaily 未注册到 models.__all__"

    def test_sync_etf_daily_task_type_registered(self):
        """TaskType.SYNC_ETF_DAILY 已定义（plan-01 Task #9）。"""
        from src.services.task_handlers import TaskType

        assert hasattr(TaskType, "SYNC_ETF_DAILY"), (
            "TaskType 未定义 SYNC_ETF_DAILY"
        )
        assert TaskType.SYNC_ETF_DAILY.value == "sync_etf_daily"

    def test_sync_etf_daily_handler_registered(self):
        """sync_etf_daily_task handler 已注册到 TaskRegistry（plan-01 Task #9）。"""
        handler = TaskRegistry.get_handler("sync_etf_daily")
        assert handler is not None, (
            "sync_etf_daily handler 未注册到 TaskRegistry"
        )
        assert callable(handler)

    def test_sync_etf_daily_handler_exported(self):
        """sync_etf_daily_task 已加入 task_handlers.__all__（plan-01 Task #9）。"""
        from src.services import task_handlers

        assert "sync_etf_daily_task" in task_handlers.__all__, (
            "sync_etf_daily_task 未加入 __all__"
        )

    def test_etf_data_init_service_importable(self):
        """EtfDataInitService.sync_etf_daily 可导入（plan-01 Task #7）。"""
        from src.services.data_init_etf import EtfDataInitService

        assert hasattr(EtfDataInitService, "sync_etf_daily"), (
            "EtfDataInitService 缺方法 sync_etf_daily"
        )
        assert hasattr(EtfDataInitService, "sync_etf_basic"), (
            "EtfDataInitService 缺方法 sync_etf_basic"
        )

    def test_collector_update_etf_daily_exists(self):
        """DataCollector._update_etf_daily 已存在（plan-01 Task #8）。"""
        from src.services.data_updater.collector import DataCollector

        assert hasattr(DataCollector, "_update_etf_daily"), (
            "DataCollector 缺方法 _update_etf_daily"
        )


# ---------------------------------------------------------------------------
# 执行验证：触发 SYNC_ETF_DAILY → completed → etf_daily 有数据
# 数据源用 mock 注入，避免依赖外部 Tushare（与 task handler 的数据写入契约无关）
# ---------------------------------------------------------------------------


# 交易日（前一日 + 当日）。
#
# collector._update_etf_daily 按规格用 ``datetime.now(BJ_TZ).date()`` 取当日采集
# （``trade_date = today.strftime("%Y%m%d")``），与系统墙钟绑定。
# 为避免 red spec 把"今天"硬编码（如 2026-07-29）后跨午夜系统时钟翻日导致
# 查库 KeyError，此处与时钟解耦：动态取 collector 实际会取的那个当日，再据此
# 推前一日。这样测试在任意系统时钟下都断言"collector 实际写入的那个日期"，
# 而非耦合到固定绝对日期。
BJ_TZ = ZoneInfo("Asia/Shanghai")
TRADE_DATE = datetime.now(BJ_TZ).date()
PREV_TRADE_DATE = TRADE_DATE - timedelta(days=1)


def _fake_fund_basic_etf():
    """模拟 get_fund_basic_etf() 返回（etf_basic 接口字段口径）。"""
    return [
        {
            "ts_code": "510300.SH",
            "csname": "华泰柏瑞沪深300ETF",
            "cname": "华泰柏瑞沪深300交易型开放式指数证券投资基金",
            "index_code": "000300.SH",
            "index_name": "沪深300",
            "list_date": "20120528",
            "setup_date": "20120504",
            "list_status": "L",
            "exchange": "SH",
            "mgr_name": "华泰柏瑞",
            "etf_type": "纯境内",
        },
        {
            "ts_code": "512100.SH",
            "csname": "南方中证1000ETF",
            "cname": "南方中证1000交易型开放式指数证券投资基金",
            "index_code": "000852.SH",
            "index_name": "中证1000",
            "list_date": "20160929",
            "setup_date": "20160920",
            "list_status": "L",
            "exchange": "SH",
            "mgr_name": "南方基金",
            "etf_type": "纯境内",
        },
        {
            "ts_code": "159915.SZ",
            "csname": "易方达创业板ETF",
            "cname": "易方达创业板交易型开放式指数证券投资基金",
            "index_code": "399006.SZ",
            "index_name": "创业板指",
            "list_date": "20110920",
            "setup_date": "20110909",
            "list_status": "L",
            "exchange": "SZ",
            "mgr_name": "易方达",
            "etf_type": "纯境内",
        },
    ]


def _fake_etf_share_size(trade_date: str):
    """模拟 get_etf_share_size(trade_date) 返回（etf_share_size 接口字段口径）。

    total_share 万份 / total_size 万元 / nav 元 / close 元，与真实接口一致。
    """
    return [
        {"ts_code": "510300.SH", "trade_date": trade_date,
         "etf_name": "华泰柏瑞沪深300ETF",
         "total_share": 1200000.0, "total_size": 4800000.0,
         "nav": 4.0000, "close": 4.012, "exchange": "SH"},
        {"ts_code": "512100.SH", "trade_date": trade_date,
         "etf_name": "南方中证1000ETF",
         "total_share": 800000.0, "total_size": 2000000.0,
         "nav": 2.5000, "close": 2.518, "exchange": "SH"},
        {"ts_code": "159915.SZ", "trade_date": trade_date,
         "etf_name": "易方达创业板ETF",
         "total_share": 500000.0, "total_size": 1500000.0,
         "nav": 3.0000, "close": 3.015, "exchange": "SZ"},
    ]


def _patch_etf_data_source():
    """
    用 mock 数据源替换 EtfDataInitService 内部获取 Tushare 数据的来源，
    使任务执行链路不依赖外部网络。mock 数据确定性保证可断言 share_change/net_inflow。
    """
    return patch.multiple(
        "src.services.data_init_etf",
        # 这些常量/函数名是 plan-01 实现后 EtfDataInitService 内部会调用的取数方法，
        # 在 DataSourceFactory 返回的 client 上。此处直接 patch 工厂返回的 client 方法。
    )


@pytest.mark.asyncio
async def test_sync_etf_daily_task_completes_and_writes_etf_daily(db_session):
    """
    执行验证主用例：触发 SYNC_ETF_DAILY → 任务 completed → etf_daily 有当日记录。

    覆盖 plan-01 §5 执行验证项：
      - 任务创建成功（TaskType.SYNC_ETF_DAILY 可创建）
      - 任务执行成功（status=completed）
      - 目标表数据正确写入（etf_daily 当日有记录、share/unit_nav 有值、
        share_change/net_inflow 计算正确）

    数据源用 mock 注入（外部 Tushare 与 task handler 的数据写入契约无关）。
    """
    # 1. 创建 SYNC_ETF_DAILY 任务（TaskManager 直调，模拟 admin 触发）
    from src.services.task_handlers import TaskType

    manager = TaskManager(db_session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_ETF_DAILY.value,
        params={},
    )
    assert task is not None
    assert task.task_type == "sync_etf_daily"
    assert task.status == "pending"

    # 2. mock 数据源后执行 handler（直接调 handler，复用 TaskExecutor 的执行流程语义）
    handler = TaskRegistry.get_handler("sync_etf_daily")
    assert handler is not None

    # 用确定性 mock 数据替换数据采集层，避免依赖外部 Tushare
    fake_client = AsyncMock()
    fake_client.get_fund_basic_etf = _fake_fund_basic_etf
    fake_client.get_etf_share_size = _fake_etf_share_size

    with patch("src.services.data_acquisition.DataSourceFactory.create",
               return_value=fake_client):
        await manager.start_task(task.task_id)
        await handler(task.task_id, {}, manager)
        await manager.complete_task(task.task_id, success=True)

    # 3. 任务完成断言
    completed = await manager.get_task(task.task_id)
    assert completed.status == "completed", (
        f"任务未完成: status={completed.status}"
    )

    # 4. etf_daily 表有当日记录
    from src.models.etf import EtfDaily

    result = await db_session.execute(
        select(func.count()).select_from(EtfDaily)
        .where(EtfDaily.trade_date == TRADE_DATE)
    )
    daily_count = result.scalar_one()
    assert daily_count == 3, f"etf_daily 当日记录数 != 3: {daily_count}"

    # 5. total_share / nav / total_size 有值
    rows = (await db_session.execute(
        select(EtfDaily).where(EtfDaily.trade_date == TRADE_DATE)
    )).scalars().all()
    by_code = {r.ts_code: r for r in rows}

    for ts_code, row in by_code.items():
        assert row.total_share is not None, f"{ts_code} total_share 为空"
        assert row.nav is not None, f"{ts_code} nav 为空"
        assert row.total_size is not None, f"{ts_code} total_size 为空"

    # 6. 首日（无前日份额）share_change / net_inflow 为 null（架构 §6.1 实现原则）
    for row in rows:
        assert row.share_change is None, (
            f"{row.ts_code} 首日 share_change 应为 null"
        )
        assert row.net_inflow is None, (
            f"{row.ts_code} 首日 net_inflow 应为 null"
        )


@pytest.mark.asyncio
async def test_sync_etf_daily_computes_share_change_and_net_inflow(db_session):
    """
    覆盖 plan-01 §5 后端验收：
      - share_change = 当日份额 − 前日份额
      - net_inflow = share_change × unit_nav / 10000（亿元）

    通过预置前一日 etf_daily 记录，再触发当日采集，断言计算值。
    """
    from src.models.etf import EtfDaily
    from src.services.task_handlers import TaskType

    # 预置前一日（无 share_change/net_inflow，首日语义）
    prev_rows = [
        EtfDaily(trade_date=PREV_TRADE_DATE, ts_code="510300.SH",
                 total_share=Decimal("1150000.0"), nav=Decimal("3.9500"),
                 close=Decimal("3.960")),
        EtfDaily(trade_date=PREV_TRADE_DATE, ts_code="512100.SH",
                 total_share=Decimal("810000.0"), nav=Decimal("2.4800"),
                 close=Decimal("2.490")),
        EtfDaily(trade_date=PREV_TRADE_DATE, ts_code="159915.SZ",
                 total_share=Decimal("495000.0"), nav=Decimal("2.9800"),
                 close=Decimal("2.990")),
    ]
    db_session.add_all(prev_rows)
    await db_session.commit()

    manager = TaskManager(db_session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_ETF_DAILY.value,
        params={},
    )
    handler = TaskRegistry.get_handler("sync_etf_daily")

    fake_client = AsyncMock()
    fake_client.get_fund_basic_etf = _fake_fund_basic_etf
    fake_client.get_etf_share_size = _fake_etf_share_size

    with patch("src.services.data_acquisition.DataSourceFactory.create",
               return_value=fake_client):
        await manager.start_task(task.task_id)
        await handler(task.task_id, {}, manager)
        await manager.complete_task(task.task_id, success=True)

    rows = (await db_session.execute(
        select(EtfDaily).where(EtfDaily.trade_date == TRADE_DATE)
    )).scalars().all()
    by_code = {r.ts_code: r for r in rows}

    # share_change = 当日 − 前日（万份）
    assert by_code["510300.SH"].share_change == Decimal("50000.0"), (
        f"510300 share_change 错误: {by_code['510300.SH'].share_change}"
    )
    # net_inflow = share_change(万份) × unit_nav / 10000（亿元）
    # 50000 × 4.0 / 10000 = 20.0
    assert by_code["510300.SH"].net_inflow == Decimal("20.0000"), (
        f"510300 net_inflow 错误: {by_code['510300.SH'].net_inflow}"
    )

    # 512100: share_change = 800000 − 810000 = -10000；net_inflow = -10000 × 2.5 / 10000 = -2.5
    assert by_code["512100.SH"].share_change == Decimal("-10000.0")
    assert by_code["512100.SH"].net_inflow == Decimal("-2.5000")


@pytest.mark.asyncio
async def test_sync_etf_daily_idempotent_on_conflict(db_session):
    """
    覆盖 plan-01 §5 后端验收：
      - 重复执行 sync_etf_daily(同日) 不产生重复记录（on_conflict 覆盖）。

    先写入一条当日记录，再触发采集，断言记录数仍为 3（覆盖而非新增）。
    """
    from src.models.etf import EtfDaily
    from src.services.task_handlers import TaskType

    # 预置一条当日旧值
    db_session.add(EtfDaily(
        trade_date=TRADE_DATE, ts_code="510300.SH",
        total_share=Decimal("999999.0"), nav=Decimal("1.0000"),
    ))
    await db_session.commit()

    manager = TaskManager(db_session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_ETF_DAILY.value,
        params={},
    )
    handler = TaskRegistry.get_handler("sync_etf_daily")

    fake_client = AsyncMock()
    fake_client.get_fund_basic_etf = _fake_fund_basic_etf
    fake_client.get_etf_share_size = _fake_etf_share_size

    with patch("src.services.data_acquisition.DataSourceFactory.create",
               return_value=fake_client):
        await manager.start_task(task.task_id)
        await handler(task.task_id, {}, manager)
        await manager.complete_task(task.task_id, success=True)

    result = await db_session.execute(
        select(func.count()).select_from(EtfDaily)
        .where(EtfDaily.trade_date == TRADE_DATE)
    )
    count = result.scalar_one()
    assert count == 3, (
        f"重复执行产生重复记录，当日记录数 != 3: {count}"
    )

    # 510300 应被覆盖为新值（1200000.0），而非旧值 999999.0
    row = (await db_session.execute(
        select(EtfDaily).where(
            EtfDaily.trade_date == TRADE_DATE,
            EtfDaily.ts_code == "510300.SH",
        )
    )).scalar_one()
    assert row.total_share == Decimal("1200000.0"), (
        f"on_conflict 未覆盖旧值: total_share={row.total_share}"
    )


@pytest.mark.asyncio
async def test_sync_etf_daily_writes_etf_basic_with_index_classification(db_session):
    """
    覆盖后端验收：
      - etf_basic 表有 ETF 清单，index_code/index_name 来自官方 etf_basic 接口；
        沪深300/中证1000/创业板指 跟踪指数均已写入。

    触发采集后断言 etf_basic 有 3 条、跟踪指数正确。
    """
    from src.models.etf import EtfBasic
    from src.services.task_handlers import TaskType

    manager = TaskManager(db_session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_ETF_DAILY.value,
        params={},
    )
    handler = TaskRegistry.get_handler("sync_etf_daily")

    fake_client = AsyncMock()
    fake_client.get_fund_basic_etf = _fake_fund_basic_etf
    fake_client.get_etf_share_size = _fake_etf_share_size

    with patch("src.services.data_acquisition.DataSourceFactory.create",
               return_value=fake_client):
        await manager.start_task(task.task_id)
        await handler(task.task_id, {}, manager)
        await manager.complete_task(task.task_id, success=True)

    basics = (await db_session.execute(select(EtfBasic))).scalars().all()
    assert len(basics) == 3, f"etf_basic 记录数 != 3: {len(basics)}"

    by_code = {b.ts_code: b for b in basics}
    # 跟踪指数（官方 etf_basic 接口直取）
    assert by_code["510300.SH"].index_code == "000300.SH"
    assert by_code["510300.SH"].index_name == "沪深300"
    assert by_code["510300.SH"].list_status == "L"
    assert by_code["512100.SH"].index_code == "000852.SH"
    assert by_code["159915.SZ"].index_code == "399006.SZ"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--no-cov"])
