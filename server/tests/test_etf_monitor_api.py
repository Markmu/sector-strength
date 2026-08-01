"""
ETF 监控查询 API 集成测试 — plan-03（查询 API）

覆盖端点（架构 §7.3 API 边界）：
- GET /api/v1/etf-monitor/index-rankings   — 指数排行（按 index_code 聚合/排序/分页）
- GET /api/v1/etf-monitor/index-detail      — 指数下 ETF 明细（按 netInflow 降序）
- GET /api/v1/etf-monitor/trend             — 指数/单只 × 指标 × 区间 / 完全无数据 hasData=false
- GET /api/v1/etf-monitor/latest-date       — 最新有数据交易日
- POST /api/v1/admin/init/etf-daily         — 管理员当日采集（并发保护 + 返回 task_id）
- POST /api/v1/admin/init/etf-basic         — 管理员基础信息同步（并发保护 + 返回 task_id）

时钟解耦：测试用固定日期 TRADE_DATE=2026-07-28，预置 EtfBasic（含 index_code/index_name）
+ EtfDaily（含 share/share_change/net_inflow），不依赖系统时钟，任意时刻结论一致。
断言指数汇总值 = 该指数各 ETF 之和（归集正确性核心验证）。
"""

import pytest
import pytest_asyncio
from datetime import date
from decimal import Decimal

from httpx import AsyncClient

from main import app
from src.models.user import User
from src.models.etf import EtfBasic, EtfDaily
from src.api.deps import get_current_user, get_session


def _resolve_fastapi_app(wrapped_app):
    """逐层解开中间件 .app 取到底层 FastAPI 实例。"""
    current = wrapped_app
    for _ in range(8):
        if hasattr(current, "dependency_overrides"):
            return current
        inner = getattr(current, "app", None)
        if inner is None:
            break
        current = inner
    return current


_fastapi_app = _resolve_fastapi_app(app)


# ============== 固定日期（时钟解耦）==============
TRADE_DATE = date(2026, 7, 28)
PREV_DATE = date(2026, 7, 21)


# ============== User fixtures ==============


@pytest_asyncio.fixture
async def normal_user(test_session):
    user = User(
        email="normal_etf_monitor@example.com",
        password_hash="hash",
        role="user",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(test_session):
    user = User(
        email="admin_etf_monitor@example.com",
        password_hash="hash",
        role="admin",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


def _override_auth(user):
    from src.db import database as db_module

    test_session_factory = db_module.AsyncSessionLocal

    async def _override_get_session():
        async with test_session_factory() as s:
            yield s

    async def _override_current_user():
        return user

    return _override_get_session, _override_current_user


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, test_session, normal_user):
    over_session, over_user = _override_auth(normal_user)
    _fastapi_app.dependency_overrides[get_session] = over_session
    _fastapi_app.dependency_overrides[get_current_user] = over_user
    yield client
    _fastapi_app.dependency_overrides.pop(get_session, None)
    _fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, test_session, admin_user):
    over_session, over_user = _override_auth(admin_user)
    _fastapi_app.dependency_overrides[get_session] = over_session
    _fastapi_app.dependency_overrides[get_current_user] = over_user
    yield client
    _fastapi_app.dependency_overrides.pop(get_session, None)
    _fastapi_app.dependency_overrides.pop(get_current_user, None)


# ============== 测试数据 fixture ==============
#
# 预置 etf_basic（含 index_code/index_name）+ etf_daily（含 share/share_change/net_inflow），
# 让聚合查询有数据可测。份额存储单位 = 万份，API 输出 ÷10000 转亿份。
#
# 指数（按 index_code 聚合）：
#   - 沪深300（000300.SH）：510300.SH + 510310.SH
#     → totalShareChange=+40000万（÷10000=4.0亿份）、totalNetInflow=+19.6亿
#   - 中证1000（000852.SH）：512100.SH
#     → totalShareChange=+30000万（3.0亿份）、totalNetInflow=+7.5亿
# 无数据指数（用于 trend 完全无数据）：中证500（000905.SH，仅 etf_basic，无 etf_daily）
#
# 数值刻意选择可精确断言。


@pytest_asyncio.fixture
async def etf_seed(test_session):
    """预置 ETF 基础信息 + 当日份额数据（含趋势历史点）。"""

    basics = [
        # 沪深300（2 只）
        EtfBasic(
            ts_code="510300.SH", name="华泰柏瑞沪深300ETF",
            index_code="000300.SH", index_name="沪深300",
            list_status="L", exchange="SH",
        ),
        EtfBasic(
            ts_code="510310.SH", name="易方达沪深300ETF",
            index_code="000300.SH", index_name="沪深300",
            list_status="L", exchange="SH",
        ),
        # 中证1000（1 只）
        EtfBasic(
            ts_code="512100.SH", name="南方中证1000ETF",
            index_code="000852.SH", index_name="中证1000",
            list_status="L", exchange="SH",
        ),
        # 中证500（无 daily 记录，用于 trend 完全无数据）
        EtfBasic(
            ts_code="510500.SH", name="南方中证500ETF",
            index_code="000905.SH", index_name="中证500",
            list_status="L", exchange="SH",
        ),
    ]
    test_session.add_all(basics)

    # 当日 etf_daily（total_share 万份 / total_size 万元 / nav 元 / net_inflow 亿元）
    daily_today = [
        EtfDaily(
            trade_date=TRADE_DATE, ts_code="510300.SH",
            total_share=Decimal("1200000.0"), total_size=Decimal("4800000.0"),
            nav=Decimal("4.0000"),
            share_change=Decimal("50000.0"), net_inflow=Decimal("20.0000"),
        ),
        EtfDaily(
            trade_date=TRADE_DATE, ts_code="510310.SH",
            total_share=Decimal("200000.0"), total_size=Decimal("800000.0"),
            nav=Decimal("4.0000"),
            share_change=Decimal("-10000.0"), net_inflow=Decimal("-0.4000"),
        ),
        EtfDaily(
            trade_date=TRADE_DATE, ts_code="512100.SH",
            total_share=Decimal("800000.0"), total_size=Decimal("2000000.0"),
            nav=Decimal("2.5000"),
            share_change=Decimal("30000.0"), net_inflow=Decimal("7.5000"),
        ),
    ]
    test_session.add_all(daily_today)

    # 趋势历史点（PREV_DATE，用于多日 trend 序列断言）
    daily_prev = [
        EtfDaily(
            trade_date=PREV_DATE, ts_code="510300.SH",
            total_share=Decimal("1150000.0"), total_size=Decimal("4542500.0"),
            nav=Decimal("3.9500"),
            share_change=Decimal("40000.0"), net_inflow=Decimal("15.8000"),
        ),
        EtfDaily(
            trade_date=PREV_DATE, ts_code="510310.SH",
            total_share=Decimal("210000.0"), total_size=Decimal("829500.0"),
            nav=Decimal("3.9500"),
            share_change=Decimal("-5000.0"), net_inflow=Decimal("-0.1975"),
        ),
        EtfDaily(
            trade_date=PREV_DATE, ts_code="512100.SH",
            total_share=Decimal("770000.0"), total_size=Decimal("1886500.0"),
            nav=Decimal("2.4500"),
            share_change=Decimal("25000.0"), net_inflow=Decimal("6.1250"),
        ),
    ]
    test_session.add_all(daily_prev)
    await test_session.commit()
    return {
        "basics": basics,
        "daily_today": daily_today,
        "daily_prev": daily_prev,
    }


# ============== 构建校验（前置存在性）==============


class TestEtfMonitorImportable:
    """验证 service / 路由的前置存在性。"""

    def test_etf_monitor_service_importable(self):
        from src.services.etf_monitor_service import EtfMonitorService

        for method in (
            "get_index_rankings",
            "get_index_detail",
            "get_trend",
            "get_latest_date",
        ):
            assert hasattr(EtfMonitorService, method), (
                f"EtfMonitorService 缺方法 {method}"
            )

    def test_etf_monitor_router_registered(self):
        paths = {route.path for route in _fastapi_app.routes}
        assert "/api/v1/etf-monitor/index-rankings" in paths, (
            "etf-monitor/index-rankings 路由未注册"
        )

    def test_admin_init_etf_daily_router_registered(self):
        paths = {route.path for route in _fastapi_app.routes}
        assert "/api/v1/admin/init/etf-daily" in paths, (
            "admin/init/etf-daily 路由未注册"
        )

    def test_admin_init_etf_basic_router_registered(self):
        paths = {route.path for route in _fastapi_app.routes}
        assert "/api/v1/admin/init/etf-basic" in paths, (
            "admin/init/etf-basic 路由未注册"
        )


# ============== GET /index-rankings — 指数排行 ==============


@pytest.mark.asyncio
async def test_index_rankings_aggregates_sum_of_etfs(auth_client, etf_seed):
    """
    指数排行：核心归集正确性——指数汇总值 = 该指数各 ETF 之和。

    沪深300（510300 + 510310）：
      - totalShare = (1200000 + 200000)万 ÷10000 = 140.0 亿份
      - totalShareChange = (50000 + -10000)万 ÷10000 = 4.0 亿份
      - totalNetInflow = 20.0 + -0.4 = 19.6 亿元
      - totalSize = (1200000×4 + 200000×4)万 ÷10000 = 560.0 亿元
      - etfCount = 2
    中证1000（512100）：
      - totalShare = 800000万 ÷10000 = 80.0 亿份
      - totalShareChange = 30000万 ÷10000 = 3.0 亿份
      - totalNetInflow = 7.5 亿元
      - totalSize = (800000×2.5)万 ÷10000 = 200.0 亿元
      - etfCount = 1
    """
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={"trade_date": TRADE_DATE.isoformat()},
    )
    assert resp.status_code == 200, f"index-rankings 状态码: {resp.status_code}"
    body = resp.json()
    assert body["success"] is True
    data = body["data"]

    assert data["hasData"] is True
    assert data["tradeDate"] == TRADE_DATE.isoformat()
    assert data["page"] == 1
    assert data["pageSize"] == 20

    items = {it["indexCode"]: it for it in data["items"]}
    assert "000300.SH" in items
    assert "000852.SH" in items

    hs300 = items["000300.SH"]
    assert hs300["indexName"] == "沪深300"
    assert hs300["etfCount"] == 2
    assert hs300["totalShare"] == pytest.approx(140.0), hs300["totalShare"]
    assert hs300["totalShareChange"] == pytest.approx(4.0), hs300["totalShareChange"]
    assert hs300["totalNetInflow"] == pytest.approx(19.6), hs300["totalNetInflow"]
    assert hs300["totalSize"] == pytest.approx(560.0), hs300["totalSize"]

    zz1000 = items["000852.SH"]
    assert zz1000["indexName"] == "中证1000"
    assert zz1000["etfCount"] == 1
    assert zz1000["totalShare"] == pytest.approx(80.0), zz1000["totalShare"]
    assert zz1000["totalShareChange"] == pytest.approx(3.0), zz1000["totalShareChange"]
    assert zz1000["totalNetInflow"] == pytest.approx(7.5), zz1000["totalNetInflow"]
    assert zz1000["totalSize"] == pytest.approx(200.0), zz1000["totalSize"]


@pytest.mark.asyncio
async def test_index_rankings_sort_by_net_inflow_desc(auth_client, etf_seed):
    """排行默认按 netInflow 降序：沪深300(19.6) > 中证1000(7.5)。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={
            "trade_date": TRADE_DATE.isoformat(),
            "sort_by": "netInflow",
            "order": "desc",
        },
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 2
    assert items[0]["totalNetInflow"] >= items[1]["totalNetInflow"]
    assert items[0]["indexCode"] == "000300.SH"


@pytest.mark.asyncio
async def test_index_rankings_sort_by_share_change(auth_client, etf_seed):
    """排序切换 shareChange 降序：沪深300(4.0) > 中证1000(3.0)。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={
            "trade_date": TRADE_DATE.isoformat(),
            "sort_by": "shareChange",
            "order": "desc",
        },
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert items[0]["indexCode"] == "000300.SH"
    assert items[0]["totalShareChange"] >= items[1]["totalShareChange"]


@pytest.mark.asyncio
async def test_index_rankings_pagination(auth_client, etf_seed):
    """分页 page_size=1：第一页 1 条、total=2（2 个有数据的指数）。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={
            "trade_date": TRADE_DATE.isoformat(),
            "page": 1,
            "page_size": 1,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page"] == 1
    assert data["pageSize"] == 1
    # 中证500 无 daily 不入聚合 → total=2
    assert data["total"] == 2, f"total != 2（中证500 无 daily 不入聚合）: {data['total']}"
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_index_rankings_no_data_date(auth_client, etf_seed):
    """所选日期无数据：hasData=false（边界场景）。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={"trade_date": "2020-01-01"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["hasData"] is False
    assert data["items"] == []


# ============== GET /index-detail — 指数明细 ==============


@pytest.mark.asyncio
async def test_index_detail_returns_etfs_sorted_by_net_inflow(auth_client, etf_seed):
    """指数明细：返回该指数 ETF 明细，按 netInflow 降序。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-detail",
        params={
            "index_code": "000300.SH",
            "trade_date": TRADE_DATE.isoformat(),
        },
    )
    assert resp.status_code == 200, f"index-detail 状态码: {resp.status_code}"
    data = resp.json()["data"]
    assert data["hasData"] is True
    items = data["items"]
    assert len(items) == 2

    by_code = {it["tsCode"]: it for it in items}
    assert by_code["510300.SH"]["share"] == pytest.approx(120.0)
    assert by_code["510300.SH"]["totalSize"] == pytest.approx(480.0)
    assert by_code["510300.SH"]["shareChange"] == pytest.approx(5.0)
    assert by_code["510300.SH"]["netInflow"] == pytest.approx(20.0)
    assert by_code["510300.SH"]["name"] == "华泰柏瑞沪深300ETF"

    # 按 netInflow 降序：510300(20.0) 在 510310(-0.4) 之前
    assert items[0]["tsCode"] == "510300.SH"
    assert items[0]["netInflow"] >= items[1]["netInflow"]


# ============== GET /trend — 历史趋势 ==============


@pytest.mark.asyncio
async def test_trend_index_metric_share(auth_client, etf_seed):
    """趋势：target_type=index + metric=share，返回升序序列。

    沪深300 份额曲线（亿份，÷10000）：
      - 2026-07-21：(1150000 + 210000)万 ÷10000 = 136.0 亿份
      - 2026-07-28：(1200000 + 200000)万 ÷10000 = 140.0 亿份
    """
    resp = await auth_client.get(
        "/api/v1/etf-monitor/trend",
        params={
            "target_type": "index",
            "target_code": "000300.SH",
            "metric": "share",
            "days": 30,
            "end_date": TRADE_DATE.isoformat(),
        },
    )
    assert resp.status_code == 200, f"trend 状态码: {resp.status_code}"
    data = resp.json()["data"]
    assert data["hasData"] is True
    assert data["metric"] == "share"
    assert data["unit"] == "亿份"

    series = data["series"]
    assert len(series) == 2
    assert series[0]["tradeDate"] == PREV_DATE.isoformat()
    assert series[1]["tradeDate"] == TRADE_DATE.isoformat()
    assert series[0]["value"] == pytest.approx(136.0), series[0]["value"]
    assert series[1]["value"] == pytest.approx(140.0), series[1]["value"]


@pytest.mark.asyncio
async def test_trend_etf_single_metric_net_inflow(auth_client, etf_seed):
    """趋势：target_type=etf + metric=netInflow，单只 ETF 净流入额曲线。

    510300.SH netInflow 曲线（亿元）：2026-07-21=15.8、2026-07-28=20.0
    """
    resp = await auth_client.get(
        "/api/v1/etf-monitor/trend",
        params={
            "target_type": "etf",
            "target_code": "510300.SH",
            "metric": "netInflow",
            "days": 30,
            "end_date": TRADE_DATE.isoformat(),
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["hasData"] is True
    assert data["metric"] == "netInflow"
    assert data["unit"] == "亿元"

    series = data["series"]
    assert len(series) == 2
    assert series[0]["value"] == pytest.approx(15.8), series[0]["value"]
    assert series[1]["value"] == pytest.approx(20.0), series[1]["value"]


@pytest.mark.asyncio
async def test_trend_no_data_has_data_false(auth_client, etf_seed):
    """趋势对象完全无数据点：hasData=false + 空 series（边界）。

    中证500（000905.SH）仅 etf_basic 有记录，etf_daily 无任何数据点。
    """
    resp = await auth_client.get(
        "/api/v1/etf-monitor/trend",
        params={
            "target_type": "index",
            "target_code": "000905.SH",
            "metric": "share",
            "days": 30,
            "end_date": TRADE_DATE.isoformat(),
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["hasData"] is False
    assert data["series"] == []


# ============== GET /latest-date — 最新交易日 ==============


@pytest.mark.asyncio
async def test_latest_date(auth_client, etf_seed):
    """最新有数据交易日：返回 etf_daily 最大 trade_date。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/latest-date",
    )
    assert resp.status_code == 200, f"latest-date 状态码: {resp.status_code}"
    data = resp.json()["data"]
    assert data["hasData"] is True
    assert data["tradeDate"] == TRADE_DATE.isoformat()


# ============== POST /admin/init/etf-daily — 当日采集 ==============


@pytest.mark.asyncio
async def test_admin_init_etf_daily_returns_task_id(admin_client, etf_seed):
    """admin 当日采集：返回 task_id（并发保护：无 pending/running 时创建成功）。"""
    resp = await admin_client.post("/api/v1/admin/init/etf-daily")
    assert resp.status_code == 200, f"init etf-daily 状态码: {resp.status_code}"
    body = resp.json()
    assert body["success"] is True
    task_id = body["data"]["task_id"]
    assert task_id, "应返回非空 task_id"


@pytest.mark.asyncio
async def test_admin_init_etf_daily_concurrency_protection(admin_client, etf_seed):
    """并发保护：已存在 pending/running SYNC_ETF_DAILY 时拒绝。"""
    from src.models.async_task import AsyncTask
    from src.db import database as db_module

    session_factory = db_module.AsyncSessionLocal
    async with session_factory() as s:
        s.add(AsyncTask(task_id="red-concurrency-stub", task_type="sync_etf_daily",
                        status="pending"))
        await s.commit()

    resp = await admin_client.post("/api/v1/admin/init/etf-daily")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False, "已有运行中任务时应被并发保护拒绝"


# ============== POST /admin/init/etf-basic — ETF 基础信息同步 ==============


@pytest.mark.asyncio
async def test_admin_init_etf_basic_returns_task_id(admin_client, etf_seed):
    """admin 基础信息同步：返回 task_id（并发保护：无 pending/running 时创建成功）。"""
    resp = await admin_client.post("/api/v1/admin/init/etf-basic")
    assert resp.status_code == 200, f"init etf-basic 状态码: {resp.status_code}"
    body = resp.json()
    assert body["success"] is True
    task_id = body["data"]["task_id"]
    assert task_id, "应返回非空 task_id"


@pytest.mark.asyncio
async def test_admin_init_etf_basic_concurrency_protection(admin_client, etf_seed):
    """并发保护：已存在 pending/running SYNC_ETF_BASIC 时拒绝。"""
    from src.models.async_task import AsyncTask
    from src.db import database as db_module

    session_factory = db_module.AsyncSessionLocal
    async with session_factory() as s:
        s.add(AsyncTask(task_id="red-concurrency-stub-basic",
                        task_type="sync_etf_basic", status="pending"))
        await s.commit()

    resp = await admin_client.post("/api/v1/admin/init/etf-basic")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False, "已有运行中任务时应被并发保护拒绝"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--no-cov"])
