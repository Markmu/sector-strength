"""融资融券查询 API 测试 — plan-06（查询 API）

覆盖端点：GET /api/v1/margin/trend（spec REQ-6 + plan-06 §5）：
- AC-5：range=30/90/250 服务端裁剪；range=50 → 422
- AC-5：5 日轴 + 3 日数据 → 5 点、缺失日六项指标全 null、hasMissingDates=true、
  latest 为最后一个有值日（无 0/前值填充）；points 长度=区间交易日数
- 契约：camelCase 字段、Decimal → float、日期 ISO 字符串、{success,data} 包裹、
  point 七键 tradeDate/rzye/rqye/rzmre/rzche/rqmcl/rzrqye（rqyl 不输出）
- 空态：日历空表 → success=False + 未初始化 message；日历有开市日但两融全空
- 鉴权：未登录（无 token）→ 401；普通登录用户可读
- 零 Provider：文件级断言 margin.py 不 import Provider 模块 + 运行时
  mock DataSourceFactory / TradingCalendar / TushareDataSource 调用计数为零
- 性能：250 日查询单次 < 500ms（种子 250 行数据，测试内计时断言）

时钟解耦：固定 BASE_DATE=2026-06-01 向前构造交易日轴，不依赖系统时钟。

conftest / loop 说明（同 test_market_metrics.py）：
- 父目录 tests/api/conftest.py 的 autouse ``api_auth_override`` 在当前双层中间件
  （ResponseLoggingMiddleware → ProcessTimeMiddleware → FastAPI）下会 AttributeError
  （``app.app`` 取到 ProcessTimeMiddleware，无 dependency_overrides）。本文件以同名
  fixture 覆盖之（pytest 取最近定义），鉴权改由 auth_client（依赖覆盖）与裸 client
  （无 token → 401）显式控制。
- ``asyncio_default_fixture_loop_scope = session`` 下 async fixture 与 async 测试体
  运行在不同事件循环，直接在测试体内复用 fixture 的 test_session 会触发 asyncpg
  "another operation is in progress"。因此所有种子写入都放在 async fixture 内
  （同 test_etf_monitor_api.py 的既有范式），测试体只发 HTTP 请求 + 断言。
"""

import ast
import inspect
from datetime import date, timedelta
from decimal import Decimal
from time import perf_counter
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from main import app
from src.api.deps import get_current_user, get_session
from src.api.v1 import margin as margin_module
from src.models import MarketMarginDaily, TradingCalendarDay
from src.models.user import User


def _resolve_fastapi_app(wrapped_app):
    """逐层解开中间件 .app 取到底层 FastAPI 实例（同 tests/api/admin/conftest.py）。"""
    current = wrapped_app
    for _ in range(10):
        if hasattr(current, "dependency_overrides"):
            return current
        inner = getattr(current, "app", None)
        if inner is None:  # pragma: no cover - 防御性
            break
        current = inner
    return current


_fastapi_app = _resolve_fastapi_app(app)

# 固定日期（时钟解耦）：交易日轴自 BASE_DATE 向前构造
BASE_DATE = date(2026, 6, 1)

POINT_KEYS = {
    "tradeDate",
    "rzye",
    "rqye",
    "rzmre",
    "rzche",
    "rqmcl",
    "rzrqye",
}


@pytest.fixture(autouse=True)
def api_auth_override():
    """覆盖父目录同名（已损坏的）autouse fixture：仅占位，鉴权由本文件控制。"""
    yield


# ============== 用户 / 客户端 fixtures（范式同 test_market_metrics.py）==============


@pytest_asyncio.fixture
async def normal_user(test_session):
    user = User(
        email="normal_margin@example.com",
        password_hash="hash",
        role="user",
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
    """登录态客户端：get_session 指向测试 schema，get_current_user 返回普通用户。"""
    over_session, over_user = _override_auth(normal_user)
    _fastapi_app.dependency_overrides[get_session] = over_session
    _fastapi_app.dependency_overrides[get_current_user] = over_user
    yield client
    _fastapi_app.dependency_overrides.pop(get_session, None)
    _fastapi_app.dependency_overrides.pop(get_current_user, None)


# ============== 种子 fixtures（全部在 fixture 内写入，见模块 docstring loop 说明）==============


def _open_days(n: int, base: date = BASE_DATE) -> list[date]:
    """自 base 起向前构造 n 个连续开市日（升序，日期仅作轴，不与真实周历挂钩）。"""
    return [base - timedelta(days=n - 1 - i) for i in range(n)]


async def _seed_calendar(test_session, open_dates: list[date]):
    """种本地交易日历（全部开市日；缺口轴只依赖开市日）。"""
    for d in open_dates:
        test_session.add(
            TradingCalendarDay(cal_date=d, is_open=True, refresh_batch_id="test")
        )
    await test_session.commit()


async def _seed_margins(test_session, margin_dates: list[date]):
    """种两融日汇总行；数值随日期递增，便于断言 latest 取值正确。

    量级取真实口径（rzye 万亿级 ~1.8e12 元、rqye 千亿级 ~3e11 元），
    rzrqye 按 spec D2 = rzye + rqye 重算（种子侧同样重算而非独立递增）。
    """
    for i, d in enumerate(margin_dates):
        rzye = Decimal("1800000000000") * (i + 1)
        rqye = Decimal("300000000000") * (i + 1)
        test_session.add(
            MarketMarginDaily(
                trade_date=d,
                rzye=rzye,
                rqye=rqye,
                rzmre=Decimal("150000000000") * (i + 1),
                rzche=Decimal("140000000000") * (i + 1),
                rqmcl=Decimal("200000000") * (i + 1),
                rzrqye=rzye + rqye,
            )
        )
    await test_session.commit()


@pytest_asyncio.fixture
async def seed_full_5(test_session):
    """5 个开市日，全部有两融数据。"""
    days = _open_days(5)
    await _seed_calendar(test_session, days)
    await _seed_margins(test_session, days)
    return days


@pytest_asyncio.fixture
async def seed_gap_5x3(test_session):
    """5 个开市日，仅前 3 日有两融数据（后 2 日缺口）。"""
    days = _open_days(5)
    await _seed_calendar(test_session, days)
    await _seed_margins(test_session, days[:3])
    return days


@pytest_asyncio.fixture
async def seed_calendar_only_4(test_session):
    """4 个开市日，无任何两融行（指标全空）。"""
    days = _open_days(4)
    await _seed_calendar(test_session, days)
    return days


@pytest_asyncio.fixture
async def seed_full_3(test_session):
    """3 个开市日，全部有两融数据（range 大于已有开市日数场景）。"""
    days = _open_days(3)
    await _seed_calendar(test_session, days)
    await _seed_margins(test_session, days)
    return days


@pytest_asyncio.fixture
async def seed_full_100(test_session):
    """100 个开市日，全部有两融数据（AC-5 裁剪场景）。"""
    days = _open_days(100)
    await _seed_calendar(test_session, days)
    await _seed_margins(test_session, days)
    return days


@pytest_asyncio.fixture
async def seed_full_250(test_session):
    """250 个开市日，全部有两融数据（性能场景）。"""
    days = _open_days(250)
    await _seed_calendar(test_session, days)
    await _seed_margins(test_session, days)
    return days


# ============== 契约测试（camelCase / Decimal→float / ISO 日期 / 七键）==============


class TestContract:
    async def test_full_data_contract(self, auth_client, seed_full_5):
        """全部有数：字段契约 + camelCase + Decimal→float + ISO 日期 + hasMissingDates=false"""
        days = seed_full_5
        resp = await auth_client.get("/api/v1/margin/trend")
        assert resp.status_code == 200
        body = resp.json()

        assert body["success"] is True
        data = body["data"]
        assert set(data.keys()) == {"latest", "points", "range", "hasMissingDates"}
        assert data["range"] == 30  # 默认 range=30
        assert data["hasMissingDates"] is False
        assert len(data["points"]) == 5

        for p in data["points"]:
            # point 恰为七键（rqyl 不落库不输出）
            assert set(p.keys()) == POINT_KEYS
            # Decimal → float（不得是字符串）、日期 ISO 字符串
            assert isinstance(p["rzye"], float)
            assert isinstance(p["rqye"], float)
            assert isinstance(p["rzmre"], float)
            assert isinstance(p["rzche"], float)
            assert isinstance(p["rqmcl"], float)
            assert isinstance(p["rzrqye"], float)
            date.fromisoformat(p["tradeDate"])  # ISO 格式合法

        # 升序 + 值与种子一致（首日 i=0 → rzye=1.8e12 元原始值，不 ÷1e8）
        assert [p["tradeDate"] for p in data["points"]] == [
            d.isoformat() for d in days
        ]
        assert data["points"][0]["rzye"] == 1800000000000.0
        assert data["points"][0]["rqye"] == 300000000000.0
        # rzrqye = rzye + rqye 重算（spec D2）
        assert data["points"][0]["rzrqye"] == 2100000000000.0

        # latest = 最后一个有值点（即最后一日），结构与 point 一致
        assert data["latest"]["tradeDate"] == days[-1].isoformat()
        assert set(data["latest"].keys()) == POINT_KEYS
        assert data["latest"]["rzye"] == 9000000000000.0
        assert data["latest"]["rzrqye"] == 10500000000000.0


# ============== 缺口契约（AC-5）==============


class TestGapContract:
    async def test_gap_points_are_null(self, auth_client, seed_gap_5x3):
        """5 日轴 + 3 日数据：5 点、缺失 2 点六项指标全 null、latest 为最后有值日"""
        days = seed_gap_5x3
        resp = await auth_client.get("/api/v1/margin/trend")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert len(data["points"]) == 5
        assert data["hasMissingDates"] is True

        missing = data["points"][3:]
        assert len(missing) == 2
        for p in missing:
            # 缺失日六项指标全 null —— 不补 0 / 前值（AC-5）
            assert p["rzye"] is None
            assert p["rqye"] is None
            assert p["rzmre"] is None
            assert p["rzche"] is None
            assert p["rqmcl"] is None
            assert p["rzrqye"] is None
            # 但日期本身不缺失（缺口轴锚点仍在）
            assert p["tradeDate"] is not None

        # latest 取最近"有结果"日 = 第 3 日（不是轴上最后一日，也不是今天）
        assert data["latest"]["tradeDate"] == days[2].isoformat()
        assert data["latest"]["rzye"] == 5400000000000.0
        assert data["latest"]["tradeDate"] != days[-1].isoformat()

    async def test_all_metrics_missing(self, auth_client, seed_calendar_only_4):
        """日历有开市日但两融全空：points 六指标全 null、latest=null、hasMissingDates=true"""
        resp = await auth_client.get("/api/v1/margin/trend")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert len(data["points"]) == 4
        assert data["latest"] is None
        assert data["hasMissingDates"] is True
        assert all(p["rzye"] is None for p in data["points"])


# ============== 空态与裁剪（AC-5）==============


class TestEmptyAndRange:
    async def test_calendar_empty_returns_uninitialized(self, auth_client):
        """本地日历空表：success=False + 未初始化 message + data=null（HTTP 200）"""
        resp = await auth_client.get("/api/v1/margin/trend")
        assert resp.status_code == 200
        body = resp.json()

        assert body["success"] is False
        assert body["data"] is None
        assert "未初始化" in body["message"]

    async def test_range_exceeds_available_open_days(self, auth_client, seed_full_3):
        """range=30 但仅有 3 个开市日：返回全部已有 3 个交易日点"""
        resp = await auth_client.get("/api/v1/margin/trend")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["points"]) == 3
        assert data["hasMissingDates"] is False

    async def test_range_30_90_250_cropping(self, auth_client, seed_full_100):
        """AC-5：100 个开市日全有数据 → range=30/90 返回 30/90 点，250 返回全部 100 点"""
        days = seed_full_100
        for rng, expected in ((30, 30), (90, 90), (250, 100)):
            resp = await auth_client.get(
                "/api/v1/margin/trend", params={"range": rng}
            )
            assert resp.status_code == 200, f"range={rng}"
            data = resp.json()["data"]
            assert len(data["points"]) == expected
            assert data["range"] == rng
            # 裁剪取"最近" N 日：尾部对齐最后一日
            assert data["points"][-1]["tradeDate"] == days[-1].isoformat()

    async def test_invalid_range_rejected_422(self, auth_client, seed_full_5):
        """非法 range=50 被 Query 校验拒绝（422）"""
        resp = await auth_client.get(
            "/api/v1/margin/trend", params={"range": 50}
        )
        assert resp.status_code == 422

    async def test_non_numeric_range_rejected_422(self, auth_client, seed_full_5):
        """非法 range=abc 被 Query pattern 校验拒绝（422）"""
        resp = await auth_client.get(
            "/api/v1/margin/trend", params={"range": "abc"}
        )
        assert resp.status_code == 422


# ============== 鉴权 ==============


class TestAuth:
    async def test_requires_authentication(self, client):
        """未登录（无 token）→ 401"""
        resp = await client.get("/api/v1/margin/trend")
        assert resp.status_code == 401

    async def test_normal_user_can_read(self, auth_client, seed_full_3):
        """普通登录用户（role=user）可读（非 admin 专属）"""
        resp = await auth_client.get("/api/v1/margin/trend")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ============== 零 Provider 调用（spec REQ-6：GET 路径硬约束）==============


class TestZeroProviderCalls:
    async def test_get_path_never_touches_providers(self, auth_client, seed_gap_5x3):
        """运行时调用计数：DataSourceFactory / TradingCalendar / TushareDataSource
        全部 mock，断言从未被调用/实例化"""
        with (
            patch(
                "src.services.data_acquisition.DataSourceFactory.create"
            ) as mock_factory,
            patch("src.services.trading_calendar.TradingCalendar") as mock_calendar,
            patch(
                "src.services.data_acquisition.tushare_client.TushareDataSource"
            ) as mock_tushare,
        ):
            resp = await auth_client.get(
                "/api/v1/margin/trend", params={"range": 30}
            )

        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_factory.assert_not_called()
        mock_calendar.assert_not_called()  # 含实例化（类被调用即失败）
        mock_tushare.assert_not_called()

    def test_margin_module_does_not_import_providers(self):
        """文件级断言：margin.py 的 import 语句不引入任何 Provider 侧模块
        （trading_calendar / data_acquisition / tushare —— 含间接符号引用；
        docstring 中的警示性文字不作数，以 ast 解析 import 为准）"""
        source = inspect.getsource(margin_module)
        tree = ast.parse(source)
        banned_prefixes = (
            "src.services.trading_calendar",
            "src.services.data_acquisition",
            "services.trading_calendar",
            "services.data_acquisition",
        )
        banned_names = {"TradingCalendar", "DataSourceFactory", "TushareDataSource"}

        imported_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name)
                    assert not alias.name.startswith(banned_prefixes), (
                        f"margin.py 不得 import Provider 模块 {alias.name!r}"
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith(banned_prefixes), (
                    f"margin.py 不得 from Provider 模块 import：{module!r}"
                )
                for alias in node.names:
                    imported_names.add(alias.name)
        assert not (imported_names & banned_names), (
            "margin.py 不得引入 Provider 侧符号 "
            f"{sorted(imported_names & banned_names)}"
        )


# ============== 性能（plan-06 §5：P95 ≤ 500ms）==============


class TestPerformance:
    async def test_250_day_query_under_500ms(self, auth_client, seed_full_250):
        """250 日全量查询单次 < 500ms（种子 250 行，只走索引，0 次 Provider 调用）"""
        start = perf_counter()
        resp = await auth_client.get(
            "/api/v1/margin/trend", params={"range": 250}
        )
        elapsed_ms = (perf_counter() - start) * 1000

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["points"]) == 250
        assert data["hasMissingDates"] is False
        assert elapsed_ms < 500, f"250 日查询耗时 {elapsed_ms:.1f}ms 超过 500ms"
