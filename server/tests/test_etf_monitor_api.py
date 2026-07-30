"""
ETF 监控查询 API 集成测试 — plan-03（查询 API）

本测试是 plan-03「查询 API」功能的 red E2E（pytest API 测试）。
plan-03 是纯后端 API 功能（无 UI）：4 个 GET 查询端点 + 1 个 admin 当日采集端点。
按 auto-dev / test-e2e skill 规则，API 功能的 red 验证用 pytest API 测试
（FastAPI TestClient / httpx async client），不用 Playwright（参照 plan-01/02
后端 pytest red 先例 + MEMORY「后端 FEAT E2E 适配 pytest」）。

覆盖端点（架构 §7.3 API 边界）：
- GET /api/v1/etf-monitor/index-rankings        — 指数排行（维度/排序/分页/聚合=各ETF之和/单位亿份）
- GET /api/v1/etf-monitor/index-detail           — 指数下 ETF 明细（按 netInflow 降序）
- GET /api/v1/etf-monitor/trend                  — 指数/单只 × 指标 × 区间 / 完全无数据 hasData=false
- GET /api/v1/etf-monitor/latest-date            — 最新有数据交易日
- POST /api/v1/admin/init/etf-daily              — 管理员当日采集（并发保护 + 返回 task_id）

Red 阶段（功能未实现）预期失败：失败原因必须是「目标功能尚未实现」——
  - 路由未注册 → 端点 404（etf_monitor_router / init_etf_daily_router 未 include）
  - EtfMonitorService 不存在（src.services.etf_monitor_service 未实现）
  - admin init_etf_daily 端点不存在（404）

实现（implementer）后，本测试应全部通过并产出 green 证据。

时钟解耦（吸取 plan-01 red 教训）：测试用固定日期 TRADE_DATE=2026-07-28，
预置 EtfBasic（含 index_name/category）+ EtfDaily（含 share/share_change/net_inflow），
不依赖系统时钟，任意时刻结论一致。断言指数汇总值 = 该指数各 ETF 之和（归集正确性核心验证）。
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
    """
    main.py 末尾把 ``app`` 重新赋值为多层中间件：
    ``ResponseLoggingMiddleware(ProcessTimeMiddleware(<FastAPI>))``。
    逐层解开 ``.app`` 取到底层 FastAPI 实例（dependency_overrides 挂在它上面）。
    """
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
#
# 预置数据与断言全部围绕固定日期展开，与系统墙钟完全无关。
# - TRADE_DATE：最新有数据的交易日（latest-date / index-rankings / index-detail / trend end_date）
# - PREV_DATE：趋势历史点（trend 多日序列）
TRADE_DATE = date(2026, 7, 28)
PREV_DATE = date(2026, 7, 21)


# ============== User fixtures ==============


@pytest_asyncio.fixture
async def normal_user(test_session):
    """创建普通登录用户（业务 GET 端点用 get_current_user）。"""
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
    """创建管理员用户（admin POST 用 require_admin，内部 Depends(get_current_user)）。"""
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
    """构造 get_current_user + get_session 的 dependency_overrides。

    require_admin 内部 Depends(get_current_user)，故覆盖 get_current_user 即同时满足
    业务 GET 与 admin POST 的鉴权。
    """
    from src.db import database as db_module

    test_session_factory = db_module.AsyncSessionLocal  # conftest 已替换为测试 schema

    async def _override_get_session():
        async with test_session_factory() as s:
            yield s

    async def _override_current_user():
        return user

    return _override_get_session, _override_current_user


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, test_session, normal_user):
    """注入普通用户认证 + override get_session（GET 端点鉴权）。"""
    over_session, over_user = _override_auth(normal_user)
    _fastapi_app.dependency_overrides[get_session] = over_session
    _fastapi_app.dependency_overrides[get_current_user] = over_user
    yield client
    _fastapi_app.dependency_overrides.pop(get_session, None)
    _fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, test_session, admin_user):
    """注入管理员认证 + override get_session（admin POST 鉴权）。"""
    over_session, over_user = _override_auth(admin_user)
    _fastapi_app.dependency_overrides[get_session] = over_session
    _fastapi_app.dependency_overrides[get_current_user] = over_user
    yield client
    _fastapi_app.dependency_overrides.pop(get_session, None)
    _fastapi_app.dependency_overrides.pop(get_current_user, None)


# ============== 测试数据 fixture ==============
#
# 预置 etf_basic（含 index_name/category）+ etf_daily（含 share/share_change/net_inflow），
# 让聚合查询有数据可测。份额存储单位 = 万份，API 输出 ÷10000 转亿份（架构 §7.6）。
#
# 指数归类（broad 维度，2 个指数）：
#   - 沪深300：510300.SH（份额变化 +50000万、净流入 +20.0亿）+ 510310.SH（-10000万、-0.4亿）
#     → 指数汇总 totalShareChange=+40000万（÷10000=4.0亿份）、totalNetInflow=+19.6亿
#   - 中证1000：512100.SH（+30000万、+7.5亿）
#     → 指数汇总 totalShareChange=+30000万（3.0亿份）、totalNetInflow=+7.5亿
# 行业维度（industry）：
#   - 半导体：512480.SH（+8000万、+1.6亿）
# 无数据指数（用于 trend 完全无数据用例）：中证500（仅 etf_basic，无 etf_daily 记录）
#
# 数值刻意选择可精确断言（净流入额 = share_change × unit_nav / 10000 已落库，聚合直接 SUM）。


@pytest_asyncio.fixture
async def etf_seed(test_session):
    """预置 ETF 基础信息 + 当日份额数据（broad/industry 双维度 + 趋势历史点）。"""

    basics = [
        # 宽基 - 沪深300（2 只）
        EtfBasic(
            ts_code="510300.SH", name="华泰柏瑞沪深300ETF",
            index_name="沪深300", category="broad", status="I", market="E",
        ),
        EtfBasic(
            ts_code="510310.SH", name="易方达沪深300ETF",
            index_name="沪深300", category="broad", status="I", market="E",
        ),
        # 宽基 - 中证1000（1 只）
        EtfBasic(
            ts_code="512100.SH", name="南方中证1000ETF",
            index_name="中证1000", category="broad", status="I", market="E",
        ),
        # 宽基 - 中证500（无 daily 记录，用于 trend 完全无数据）
        EtfBasic(
            ts_code="510500.SH", name="南方中证500ETF",
            index_name="中证500", category="broad", status="I", market="E",
        ),
        # 行业 - 半导体（1 只）
        EtfBasic(
            ts_code="512480.SH", name="国联安半导体ETF",
            index_name="半导体", category="industry", status="I", market="E",
        ),
    ]
    test_session.add_all(basics)

    # 当日 etf_daily（份额万份 / 净流入亿元已落库，share_change 万份）
    daily_today = [
        EtfDaily(
            trade_date=TRADE_DATE, ts_code="510300.SH",
            share=Decimal("1200000.0"), unit_nav=Decimal("4.0000"),
            share_change=Decimal("50000.0"), net_inflow=Decimal("20.0000"),
        ),
        EtfDaily(
            trade_date=TRADE_DATE, ts_code="510310.SH",
            share=Decimal("200000.0"), unit_nav=Decimal("4.0000"),
            share_change=Decimal("-10000.0"), net_inflow=Decimal("-0.4000"),
        ),
        EtfDaily(
            trade_date=TRADE_DATE, ts_code="512100.SH",
            share=Decimal("800000.0"), unit_nav=Decimal("2.5000"),
            share_change=Decimal("30000.0"), net_inflow=Decimal("7.5000"),
        ),
        EtfDaily(
            trade_date=TRADE_DATE, ts_code="512480.SH",
            share=Decimal("150000.0"), unit_nav=Decimal("2.0000"),
            share_change=Decimal("8000.0"), net_inflow=Decimal("1.6000"),
        ),
    ]
    test_session.add_all(daily_today)

    # 趋势历史点（PREV_DATE，用于多日 trend 序列断言）
    daily_prev = [
        EtfDaily(
            trade_date=PREV_DATE, ts_code="510300.SH",
            share=Decimal("1150000.0"), unit_nav=Decimal("3.9500"),
            share_change=Decimal("40000.0"), net_inflow=Decimal("15.8000"),
        ),
        EtfDaily(
            trade_date=PREV_DATE, ts_code="510310.SH",
            share=Decimal("210000.0"), unit_nav=Decimal("3.9500"),
            share_change=Decimal("-5000.0"), net_inflow=Decimal("-0.1975"),
        ),
        EtfDaily(
            trade_date=PREV_DATE, ts_code="512100.SH",
            share=Decimal("770000.0"), unit_nav=Decimal("2.4500"),
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
#
# 证明 plan-03 待实现模块/路由当前不存在，实现后这些用例会通过。
# red 阶段失败原因必须是「目标功能尚未实现」。


class TestEtfMonitorImportable:
    """验证 plan-03 待实现 service / 路由的前置存在性。"""

    def test_etf_monitor_service_importable(self):
        """EtfMonitorService 可导入 + 含 4 个查询方法（plan-03 Task #1）。"""
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
        """etf_monitor_router 已在 api/v1/__init__.py 注册（plan-03 Task #3）。

        v1/admin 子 router 仅含各自 prefix 的路径（/v1/*、/init/*），
        完整 /api/v1/* 路径在 app.include_router(prefix='/api') 组装后才出现，
        故校验解析后的 FastAPI app routes（与 _resolve_fastapi_app 一致）。
        """
        paths = {route.path for route in _fastapi_app.routes}
        assert "/api/v1/etf-monitor/index-rankings" in paths, (
            "etf-monitor/index-rankings 路由未注册"
        )

    def test_admin_init_etf_daily_router_registered(self):
        """init_etf_daily_router 已在 api/admin/__init__.py 注册（plan-03 Task #5）。

        完整 /api/v1/admin/* 路径在 app 级 prefix 组装后才出现，故校验解析后的
        FastAPI app routes。
        """
        paths = {route.path for route in _fastapi_app.routes}
        assert "/api/v1/admin/init/etf-daily" in paths, (
            "admin/init/etf-daily 路由未注册"
        )


# ============== GET /index-rankings — 指数排行 ==============


@pytest.mark.asyncio
async def test_index_rankings_aggregates_sum_of_etfs(auth_client, etf_seed):
    """
    指数排行：核心归集正确性——指数汇总值 = 该指数各 ETF 之和（AC-01/02/03/13）。

    沪深300（510300 + 510310）：
      - totalShare = (1200000 + 200000)万 ÷10000 = 140.0 亿份
      - totalShareChange = (50000 + -10000)万 ÷10000 = 4.0 亿份
      - totalNetInflow = 20.0 + -0.4 = 19.6 亿元
      - etfCount = 2
    中证1000（512100）：
      - totalShare = 800000万 ÷10000 = 80.0 亿份
      - totalShareChange = 30000万 ÷10000 = 3.0 亿份
      - totalNetInflow = 7.5 亿元
      - etfCount = 1
    """
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={"category": "broad", "trade_date": TRADE_DATE.isoformat()},
    )
    assert resp.status_code == 200, f"index-rankings 状态码: {resp.status_code}"
    body = resp.json()
    assert body["success"] is True
    data = body["data"]

    assert data["hasData"] is True
    assert data["tradeDate"] == TRADE_DATE.isoformat()
    assert data["page"] == 1
    assert data["pageSize"] == 20

    items = {it["indexName"]: it for it in data["items"]}
    assert "沪深300" in items
    assert "中证1000" in items

    hs300 = items["沪深300"]
    assert hs300["etfCount"] == 2
    # 份额输出亿份（÷10000）；归集 = 各 ETF 之和
    assert hs300["totalShare"] == pytest.approx(140.0), hs300["totalShare"]
    assert hs300["totalShareChange"] == pytest.approx(4.0), hs300["totalShareChange"]
    assert hs300["totalNetInflow"] == pytest.approx(19.6), hs300["totalNetInflow"]
    assert hs300["category"] == "broad"

    zz1000 = items["中证1000"]
    assert zz1000["etfCount"] == 1
    assert zz1000["totalShare"] == pytest.approx(80.0), zz1000["totalShare"]
    assert zz1000["totalShareChange"] == pytest.approx(3.0), zz1000["totalShareChange"]
    assert zz1000["totalNetInflow"] == pytest.approx(7.5), zz1000["totalNetInflow"]


@pytest.mark.asyncio
async def test_index_rankings_sort_by_net_inflow_desc(auth_client, etf_seed):
    """排行默认按 netInflow 降序：沪深300(19.6) > 中证1000(7.5)（AC-03）。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={
            "category": "broad",
            "trade_date": TRADE_DATE.isoformat(),
            "sort_by": "netInflow",
            "order": "desc",
        },
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) >= 2
    # 降序：第一个的 totalNetInflow >= 第二个
    assert items[0]["totalNetInflow"] >= items[1]["totalNetInflow"]
    assert items[0]["indexName"] == "沪深300"


@pytest.mark.asyncio
async def test_index_rankings_sort_by_share_change(auth_client, etf_seed):
    """排序切换 shareChange 降序：沪深300(4.0) > 中证1000(3.0)（AC-03）。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={
            "category": "broad",
            "trade_date": TRADE_DATE.isoformat(),
            "sort_by": "shareChange",
            "order": "desc",
        },
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert items[0]["indexName"] == "沪深300"
    assert items[0]["totalShareChange"] >= items[1]["totalShareChange"]


@pytest.mark.asyncio
async def test_index_rankings_category_industry(auth_client, etf_seed):
    """维度切换 industry：只返回半导体指数（AC-02）。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={"category": "industry", "trade_date": TRADE_DATE.isoformat()},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["indexName"] == "半导体"
    assert items[0]["category"] == "industry"
    assert items[0]["etfCount"] == 1
    assert items[0]["totalNetInflow"] == pytest.approx(1.6)


@pytest.mark.asyncio
async def test_index_rankings_pagination(auth_client, etf_seed):
    """分页 page_size=1：第一页 1 条、total=3（broad 3 个指数）（AC-13）。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={
            "category": "broad",
            "trade_date": TRADE_DATE.isoformat(),
            "page": 1,
            "page_size": 1,
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page"] == 1
    assert data["pageSize"] == 1
    # broad 维度有 3 个指数（沪深300/中证1000/中证500-无数据不入聚合）
    assert data["total"] == 2, f"total != 2（中证500 无 daily 不入聚合）: {data['total']}"
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_index_rankings_no_data_date(auth_client, etf_seed):
    """所选日期无数据：hasData=false（后端边界场景 / 前端走空态）。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-rankings",
        params={"category": "broad", "trade_date": "2020-01-01"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["hasData"] is False
    assert data["items"] == []


# ============== GET /index-detail — 指数明细 ==============


@pytest.mark.asyncio
async def test_index_detail_returns_etfs_sorted_by_net_inflow(auth_client, etf_seed):
    """指数明细：返回该指数 ETF 明细，按 netInflow 降序（AC-04）。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/index-detail",
        params={
            "index_name": "沪深300",
            "category": "broad",
            "trade_date": TRADE_DATE.isoformat(),
        },
    )
    assert resp.status_code == 200, f"index-detail 状态码: {resp.status_code}"
    data = resp.json()["data"]
    assert data["hasData"] is True
    items = data["items"]
    assert len(items) == 2

    by_code = {it["tsCode"]: it for it in items}
    # 份额输出亿份（÷10000）
    assert by_code["510300.SH"]["share"] == pytest.approx(120.0)
    assert by_code["510300.SH"]["shareChange"] == pytest.approx(5.0)
    assert by_code["510300.SH"]["netInflow"] == pytest.approx(20.0)
    assert by_code["510300.SH"]["name"] == "华泰柏瑞沪深300ETF"

    # 按 netInflow 降序：510300(20.0) 在 510310(-0.4) 之前
    assert items[0]["tsCode"] == "510300.SH"
    assert items[0]["netInflow"] >= items[1]["netInflow"]


# ============== GET /trend — 历史趋势 ==============


@pytest.mark.asyncio
async def test_trend_index_metric_share(auth_client, etf_seed):
    """趋势：target_type=index + metric=share，返回升序序列（AC-06/07）。

    沪深300 份额曲线（亿份，÷10000）：
      - 2026-07-21：(1150000 + 210000)万 ÷10000 = 136.0 亿份
      - 2026-07-28：(1200000 + 200000)万 ÷10000 = 140.0 亿份
    """
    resp = await auth_client.get(
        "/api/v1/etf-monitor/trend",
        params={
            "target_type": "index",
            "target_code": "沪深300",
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
    # 升序
    assert series[0]["tradeDate"] == PREV_DATE.isoformat()
    assert series[1]["tradeDate"] == TRADE_DATE.isoformat()
    # 归集 = 各 ETF 之和（亿份）
    assert series[0]["value"] == pytest.approx(136.0), series[0]["value"]
    assert series[1]["value"] == pytest.approx(140.0), series[1]["value"]


@pytest.mark.asyncio
async def test_trend_etf_single_metric_net_inflow(auth_client, etf_seed):
    """趋势：target_type=etf + metric=netInflow，单只 ETF 净流入额曲线（AC-07/08）。

    510300.SH netInflow 曲线（亿元）：
      - 2026-07-21：15.8
      - 2026-07-28：20.0
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
    """趋势对象完全无数据点：hasData=false + 空 series（AC-09 边界 / 架构 §6.5）。

    中证500 仅 etf_basic 有记录，etf_daily 无任何数据点。
    """
    resp = await auth_client.get(
        "/api/v1/etf-monitor/trend",
        params={
            "target_type": "index",
            "target_code": "中证500",
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
    """最新有数据交易日：返回 etf_daily 最大 trade_date（日期选择器默认定位）。"""
    resp = await auth_client.get(
        "/api/v1/etf-monitor/latest-date",
        params={"category": "broad"},
    )
    assert resp.status_code == 200, f"latest-date 状态码: {resp.status_code}"
    data = resp.json()["data"]
    assert data["hasData"] is True
    assert data["tradeDate"] == TRADE_DATE.isoformat()


# ============== POST /admin/init/etf-daily — 当日采集 ==============


@pytest.mark.asyncio
async def test_admin_init_etf_daily_returns_task_id(admin_client, etf_seed):
    """admin 当日采集：返回 task_id（AC-12 / 架构 §7.3）。

    复用 plan-01 的 SYNC_ETF_DAILY task handler。并发保护：无 pending/running 时创建成功。
    """
    resp = await admin_client.post("/api/v1/admin/init/etf-daily")
    assert resp.status_code == 200, f"init etf-daily 状态码: {resp.status_code}"
    body = resp.json()
    assert body["success"] is True
    task_id = body["data"]["task_id"]
    assert task_id, "应返回非空 task_id"


@pytest.mark.asyncio
async def test_admin_init_etf_daily_concurrency_protection(admin_client, etf_seed):
    """并发保护：已存在 pending/running SYNC_ETF_DAILY 时拒绝（AC-12 / 架构 §6.1）。

    预置一个 pending 的 SYNC_ETF_DAILY AsyncTask，再触发应被拒绝（success=false）。
    """
    from src.models.async_task import AsyncTask
    from src.db import database as db_module

    # 通过 API session 写入 pending 任务（与端点查询同一 schema）
    session_factory = db_module.AsyncSessionLocal
    async with session_factory() as s:
        s.add(AsyncTask(task_id="red-concurrency-stub", task_type="sync_etf_daily",
                        status="pending"))
        await s.commit()

    resp = await admin_client.post("/api/v1/admin/init/etf-daily")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False, "已有运行中任务时应被并发保护拒绝"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--no-cov"])
