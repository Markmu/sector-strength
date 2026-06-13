"""
股东分析面板 — 用户侧聚合查询 API 集成测试（plan-02）

覆盖端点（参照 plan-02 §3.6 / §7.3 / 架构 §7.3）：
- GET /api/v1/shareholder-analysis/overview          — 监控组概览（AC-01 / AC-09 / AC-11）
- GET /api/v1/shareholder-analysis/summary           — 汇总统计 + 变动趋势（AC-02 / AC-03 / AC-04 / AC-05 / AC-11）
- GET /api/v1/shareholder-analysis/industry-distribution — 行业分布（AC-02 / AC-05）
- GET /api/v1/shareholder-analysis/holdings          — 分页持仓列表（AC-02 / AC-03 / AC-04 / AC-05 / AC-11）

测试模式：
- 参照 server/tests/test_fund_api.py 的 client + 认证 fixture 模式
- 用户侧 API 需登录态：override get_current_user
- `_fastapi_app = app.app if hasattr(app, "app") else app` 解包中间件
- conftest 已注入 5 个预定义 shareholder_groups；本文件 fixture 补充
  top10_float_holders（两期）+ sectors(type=industry) + sector_stocks + stocks

Red 关键原则：
- 测试只通过 HTTP client 调用端点，不 import 未实现的
  src.services.shareholder_analysis_service / src.api.v1.shareholder_analysis
- 失败原因必须是端点未实现 → 404
"""

import pytest
import pytest_asyncio
from datetime import date
from decimal import Decimal
from httpx import AsyncClient

from main import app
from src.models.user import User
from src.models.stock import Stock
from src.models.top10_float_holder import Top10FloatHolder
from src.models.sector import Sector
from src.models.sector_stock import SectorStock
from src.api.deps import get_current_user, get_session

# app 被 ProcessTimeMiddleware 包装，需要获取底层 FastAPI 实例
_fastapi_app = app.app if hasattr(app, "app") else app


# ============== User fixtures ==============


@pytest_asyncio.fixture
async def normal_user(test_session):
    """创建普通用户并写入 DB"""
    user = User(
        email="normal_shareholder@example.com",
        password_hash="hash",
        role="user",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, test_session, normal_user):
    """
    注入普通用户认证 + override get_session。
    API 请求使用独立的 session（同一 schema），避免 asyncpg 连接冲突。
    """
    from src.db import database as db_module

    test_session_factory = db_module.AsyncSessionLocal  # conftest 已替换

    async def _override_get_session():
        async with test_session_factory() as s:
            yield s

    async def _override_current_user():
        return normal_user

    _fastapi_app.dependency_overrides[get_session] = _override_get_session
    _fastapi_app.dependency_overrides[get_current_user] = _override_current_user
    yield client
    _fastapi_app.dependency_overrides.pop(get_session, None)
    _fastapi_app.dependency_overrides.pop(get_current_user, None)


# ============== Sample data fixtures ==============
#
# top10_float_holders / sectors(industry) / sector_stocks / stocks
# 需要本文件 fixture 注入（conftest 只注入了 5 个 shareholder_groups）。
#
# 数据设计：覆盖 增持/减持/新进/退出 四种变动方向 + 多组匹配去重。
#   报告期 1：2024-12-31（current_period，最新期）
#   报告期 2：2024-09-30（prev_period）
#   国家队（组1）：中央汇金 → 关键词「中央汇金」
#   外资投行（组2）：高盛 / 摩根士丹利 → 关键词「高盛」/「摩根士丹利」
# 社保基金（组3）：全国社保基金 → 关键词「全国社保基金」


@pytest_asyncio.fixture
async def sample_stocks(test_session):
    """创建测试用 Stock（holdings/industry JOIN 依赖）"""
    stocks = [
        Stock(symbol="600519", name="贵州茅台"),
        Stock(symbol="000858", name="五粮液"),
        Stock(symbol="601318", name="中国平安"),
        Stock(symbol="600036", name="招商银行"),
        Stock(symbol="601398", name="工商银行"),
        Stock(symbol="600000", name="浦发银行"),  # 退出股票：只在 prev 期出现
    ]
    test_session.add_all(stocks)
    await test_session.commit()
    for s in stocks:
        await test_session.refresh(s)
    return stocks


@pytest_asyncio.fixture
async def sample_industry_sectors(test_session):
    """创建行业板块（type=industry），用于行业 JOIN/筛选"""
    sectors = [
        Sector(name="银行", code="IND_BANK", type="industry", strength_score=70.0),
        Sector(name="白酒", code="IND_BAIJIU", type="industry", strength_score=80.0),
        Sector(name="保险", code="IND_INSURANCE", type="industry", strength_score=65.0),
        Sector(name="证券", code="IND_SECURITIES", type="industry", strength_score=60.0),
    ]
    test_session.add_all(sectors)
    await test_session.commit()
    for s in sectors:
        await test_session.refresh(s)
    return sectors


@pytest_asyncio.fixture
async def sample_sector_stocks(test_session, sample_industry_sectors):
    """建立股票 ↔ 行业板块关联（SectorStock 通过 code 字符串关联）"""
    relations = [
        # 工商银行/招商银行/浦发银行 → 银行
        SectorStock(sector_code="IND_BANK", stock_code="601398"),
        SectorStock(sector_code="IND_BANK", stock_code="600036"),
        SectorStock(sector_code="IND_BANK", stock_code="600000"),
        # 贵州茅台/五粮液 → 白酒
        SectorStock(sector_code="IND_BAIJIU", stock_code="600519"),
        SectorStock(sector_code="IND_BAIJIU", stock_code="000858"),
        # 中国平安 → 保险
        SectorStock(sector_code="IND_INSURANCE", stock_code="601318"),
    ]
    test_session.add_all(relations)
    await test_session.commit()
    return relations


@pytest_asyncio.fixture
async def sample_holders(test_session, sample_stocks):
    """
    构造 top10_float_holders 测试数据，覆盖 4 种变动场景：

    现期 2024-12-31（current）：
      600519 贵州茅台 — 中央汇金 持 1000（prev 持 800 → 增持）
      000858 五粮液   — 中央汇金 持 500（prev 持 800 → 减持）
      601318 中国平安 — 中央汇金 持 200（prev 无 → 新进）
      600036 招商银行 — 高盛     持 300（prev 持 300 → 不变）
      601398 工商银行 — 中央汇金 + 高盛 持 400（prev 无 → 新进；多股东聚合）

    上一期 2024-09-30（prev）：
      600519 贵州茅台 — 中央汇金 持 800
      000858 五粮液   — 中央汇金 持 800
      600000 浦发银行 — 中央汇金 持 600（current 无 → 退出）
      600036 招商银行 — 高盛     持 300

    返回 holders 列表（含两期数据）。
    """
    records = [
        # === 现期 2024-12-31 ===
        Top10FloatHolder(
            symbol="600519",
            ts_code="600519.SH",
            report_period=date(2024, 12, 31),
            ann_date=date(2025, 1, 20),
            holder_name="中央汇金投资有限责任公司",
            hold_amount=Decimal("1000.00"),
            hold_ratio=Decimal("0.0800"),
            hold_float_ratio=Decimal("0.1000"),
        ),
        Top10FloatHolder(
            symbol="000858",
            ts_code="000858.SZ",
            report_period=date(2024, 12, 31),
            ann_date=date(2025, 1, 20),
            holder_name="中央汇金资产管理有限责任公司",
            hold_amount=Decimal("500.00"),
            hold_ratio=Decimal("0.0500"),
            hold_float_ratio=Decimal("0.0600"),
        ),
        Top10FloatHolder(
            symbol="601318",
            ts_code="601318.SH",
            report_period=date(2024, 12, 31),
            ann_date=date(2025, 1, 20),
            holder_name="中央汇金投资有限责任公司",
            hold_amount=Decimal("200.00"),
            hold_ratio=Decimal("0.0200"),
            hold_float_ratio=Decimal("0.0300"),
        ),
        Top10FloatHolder(
            symbol="600036",
            ts_code="600036.SH",
            report_period=date(2024, 12, 31),
            ann_date=date(2025, 1, 20),
            holder_name="高盛（亚洲）有限责任公司",
            hold_amount=Decimal("300.00"),
            hold_ratio=Decimal("0.0300"),
            hold_float_ratio=Decimal("0.0400"),
        ),
        Top10FloatHolder(
            symbol="601398",
            ts_code="601398.SH",
            report_period=date(2024, 12, 31),
            ann_date=date(2025, 1, 20),
            holder_name="中央汇金投资有限责任公司",
            hold_amount=Decimal("200.00"),
            hold_ratio=Decimal("0.0100"),
            hold_float_ratio=Decimal("0.0200"),
        ),
        Top10FloatHolder(
            symbol="601398",
            ts_code="601398.SH",
            report_period=date(2024, 12, 31),
            ann_date=date(2025, 1, 20),
            holder_name="高盛（亚洲）有限责任公司",
            hold_amount=Decimal("200.00"),
            hold_ratio=Decimal("0.0100"),
            hold_float_ratio=Decimal("0.0200"),
        ),
        # === 上一期 2024-09-30 ===
        Top10FloatHolder(
            symbol="600519",
            ts_code="600519.SH",
            report_period=date(2024, 9, 30),
            ann_date=date(2024, 10, 25),
            holder_name="中央汇金投资有限责任公司",
            hold_amount=Decimal("800.00"),
            hold_ratio=Decimal("0.0700"),
            hold_float_ratio=Decimal("0.0900"),
        ),
        Top10FloatHolder(
            symbol="000858",
            ts_code="000858.SZ",
            report_period=date(2024, 9, 30),
            ann_date=date(2024, 10, 25),
            holder_name="中央汇金资产管理有限责任公司",
            hold_amount=Decimal("800.00"),
            hold_ratio=Decimal("0.0800"),
            hold_float_ratio=Decimal("0.0900"),
        ),
        Top10FloatHolder(
            symbol="600000",
            ts_code="600000.SH",
            report_period=date(2024, 9, 30),
            ann_date=date(2024, 10, 25),
            holder_name="中央汇金投资有限责任公司",
            hold_amount=Decimal("600.00"),
            hold_ratio=Decimal("0.0400"),
            hold_float_ratio=Decimal("0.0500"),
        ),
        Top10FloatHolder(
            symbol="600036",
            ts_code="600036.SH",
            report_period=date(2024, 9, 30),
            ann_date=date(2024, 10, 25),
            holder_name="高盛（亚洲）有限责任公司",
            hold_amount=Decimal("300.00"),
            hold_ratio=Decimal("0.0300"),
            hold_float_ratio=Decimal("0.0400"),
        ),
    ]
    test_session.add_all(records)
    await test_session.commit()
    return records


@pytest_asyncio.fixture
async def low_percentage_dataset(test_session):
    """UC-014 回归：构造低占比行业场景。

    1 只股票关联 21 个行业板块 → 每个行业 count=1、total=21、占比≈4.76% < 5% 阈值。
    修复前：所有行业 < 阈值且未合并 → distribution 恒空；修复后：低占比行业合并到"未分类"。
    国家队（group 1，预定义关键词"中央汇金"）匹配该股票。
    """
    test_session.add(Stock(symbol="600999", name="低占比测试"))
    for i in range(21):
        test_session.add(
            Sector(
                name=f"低占比行业{i}",
                code=f"IND_LP_{i:02d}",
                type="industry",
                strength_score=50.0,
            )
        )
        test_session.add(SectorStock(sector_code=f"IND_LP_{i:02d}", stock_code="600999"))
    test_session.add(
        Top10FloatHolder(
            symbol="600999",
            ts_code="600999.SH",
            report_period=date(2024, 12, 31),
            ann_date=date(2025, 1, 20),
            holder_name="中央汇金投资有限责任公司",
            hold_amount=Decimal("1000.00"),
            hold_ratio=Decimal("0.0100"),
            hold_float_ratio=Decimal("0.0200"),
        )
    )
    await test_session.commit()


@pytest_asyncio.fixture
async def full_dataset(
    sample_stocks, sample_industry_sectors, sample_sector_stocks, sample_holders
):
    """聚合所有依赖数据 fixture，便于测试一次性引入"""
    return {
        "stocks": sample_stocks,
        "sectors": sample_industry_sectors,
        "sector_stocks": sample_sector_stocks,
        "holders": sample_holders,
    }


def _resolve_group_ids(test_session, names):
    """通过 group_name 解析出 group_id 列表（conftest 注入了 5 个预定义组）"""
    # 不直接 query DB（避免 async 上下文问题），由 API 层负责；
    # 这里仅提供工具方法骨架，实际断言通过 API 返回的 groupId 校验。
    return names


# ============== Test: GET /overview — 监控组概览 ==============


class TestOverview:
    """监控组概览端点测试（AC-01 / AC-09 / AC-11）"""

    @pytest.mark.asyncio
    async def test_overview_returns_200(
        self, auth_client, full_dataset
    ):
        """overview 返回 200 + ApiResponse 包裹（AC-01）"""
        resp = await auth_client.get("/api/v1/shareholder-analysis/overview")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body

    @pytest.mark.asyncio
    async def test_overview_top_level_fields(
        self, auth_client, full_dataset
    ):
        """顶层字段 reportPeriods / currentPeriod / hasPrevPeriod / groups（AC-01）"""
        resp = await auth_client.get("/api/v1/shareholder-analysis/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert "reportPeriods" in data
        assert "currentPeriod" in data
        assert "hasPrevPeriod" in data
        assert "groups" in data
        # currentPeriod 为 YYYY-MM-DD 字符串
        assert data["currentPeriod"] == "2024-12-31"
        # 至少有 2 个报告期数据
        assert "2024-12-31" in data["reportPeriods"]
        assert data["hasPrevPeriod"] is True

    @pytest.mark.asyncio
    async def test_overview_group_camel_case_fields(
        self, auth_client, full_dataset
    ):
        """每个 group 含 groupId/groupName/stockCount/increaseCount/decreaseCount/newCount/exitCount（AC-01 / §7.2 camelCase）"""
        resp = await auth_client.get("/api/v1/shareholder-analysis/overview")
        assert resp.status_code == 200
        groups = resp.json()["data"]["groups"]
        assert len(groups) > 0

        required = {
            "groupId", "groupName", "stockCount",
            "increaseCount", "decreaseCount", "newCount", "exitCount",
        }
        for g in groups:
            assert required.issubset(g.keys()), f"group 缺少字段: {required - set(g.keys())}"

    @pytest.mark.asyncio
    async def test_overview_groups_sorted_by_stock_count_desc(
        self, auth_client, full_dataset
    ):
        """groups 按 stockCount 降序排列（AC-01 / 架构 §6.1）"""
        resp = await auth_client.get("/api/v1/shareholder-analysis/overview")
        assert resp.status_code == 200
        groups = resp.json()["data"]["groups"]

        counts = [g["stockCount"] for g in groups]
        assert counts == sorted(counts, reverse=True), f"未按 stockCount 降序: {counts}"

    @pytest.mark.asyncio
    async def test_overview_specific_group_stats(
        self, auth_client, full_dataset
    ):
        """国家队的统计正确（中央汇金 → 600519/000858/601318/601398）"""
        resp = await auth_client.get("/api/v1/shareholder-analysis/overview")
        assert resp.status_code == 200
        groups = resp.json()["data"]["groups"]

        # 找国家队
        guojia = next((g for g in groups if g["groupName"] == "国家队"), None)
        assert guojia is not None, "未找到国家队分组"
        # 现期匹配 4 只股票（600519/000858/601318/601398）
        assert guojia["stockCount"] == 4
        # 增持：600519（800→1000）；新进：601318 / 601398（无→有）
        assert guojia["increaseCount"] == 1
        assert guojia["newCount"] == 2
        # 减持：000858（800→500）
        assert guojia["decreaseCount"] == 1
        # 退出：600000（prev 有 current 无）
        assert guojia["exitCount"] == 1

    @pytest.mark.asyncio
    async def test_overview_report_period_param(
        self, auth_client, full_dataset
    ):
        """传 report_period 切换到上一期（AC-09）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/overview",
            params={"report_period": "2024-09-30"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["currentPeriod"] == "2024-09-30"
        # 上一期数据存在时 groups 应非空
        assert len(data["groups"]) > 0

    @pytest.mark.asyncio
    async def test_overview_default_latest_period(
        self, auth_client, full_dataset
    ):
        """不传 report_period 默认最新期（AC-09）"""
        resp = await auth_client.get("/api/v1/shareholder-analysis/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        # 最新期应为 2024-12-31
        assert data["currentPeriod"] == "2024-12-31"

    @pytest.mark.asyncio
    async def test_overview_requires_auth(self, client):
        """未认证返回 401（§7.3 用户侧需 JWT）"""
        resp = await client.get("/api/v1/shareholder-analysis/overview")
        assert resp.status_code == 401


# ============== Test: GET /summary — 汇总统计 + 变动趋势 ==============


class TestSummary:
    """汇总统计 + 变动趋势端点测试（AC-02 / AC-03 / AC-04 / AC-05 / AC-11）"""

    @pytest.mark.asyncio
    async def test_summary_single_group(
        self, auth_client, full_dataset
    ):
        """单组 summary：summary + trend + hasPrevPeriod（AC-02）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/summary",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert "summary" in data
        assert "trend" in data
        assert "hasPrevPeriod" in data

        summary = data["summary"]
        assert {"stockCount", "totalHoldAmount", "avgHoldFloatRatio"}.issubset(summary.keys())
        trend = data["trend"]
        assert {"increaseCount", "decreaseCount", "newCount", "exitCount"}.issubset(trend.keys())

    @pytest.mark.asyncio
    async def test_summary_multi_group_dedup(
        self, auth_client, full_dataset
    ):
        """多组联合查询（group_ids=1,2）去重后汇总（AC-03）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/summary",
            params={"group_ids": "1,2", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        # 国家队(1) 匹配 4 只 + 外资投行(2) 匹配 2 只（含 601398 重复）→ 去重后 5 只
        # 国家队: 600519/000858/601318/601398
        # 外资投行: 600036/601398
        # 去重并集: 600519/000858/601318/601398/600036 = 5 只
        assert data["summary"]["stockCount"] == 5

    @pytest.mark.asyncio
    async def test_summary_industry_filter(
        self, auth_client, full_dataset
    ):
        """industry 筛选影响 summary（AC-04）"""
        resp_all = await auth_client.get(
            "/api/v1/shareholder-analysis/summary",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        resp_bank = await auth_client.get(
            "/api/v1/shareholder-analysis/summary",
            params={
                "group_ids": "1", "report_period": "2024-12-31",
                "industry": "银行",
            },
        )
        assert resp_all.status_code == 200
        assert resp_bank.status_code == 200
        # 国家队中仅 601398（工商银行）属于「银行」
        # 600519/000858 = 白酒；601318 = 保险；601398 = 银行
        assert resp_bank.json()["data"]["summary"]["stockCount"] == 1

    @pytest.mark.asyncio
    async def test_summary_trend_not_affected_by_change_direction(
        self, auth_client, full_dataset
    ):
        """trend 不受 change_direction 筛选影响（AC-05 / 架构 §6.2）"""
        resp_no_filter = await auth_client.get(
            "/api/v1/shareholder-analysis/summary",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        resp_with_filter = await auth_client.get(
            "/api/v1/shareholder-analysis/summary",
            params={
                "group_ids": "1", "report_period": "2024-12-31",
                "change_direction": "increase",
            },
        )
        assert resp_no_filter.status_code == 200
        assert resp_with_filter.status_code == 200
        # trend 计数应一致（不受 change_direction 筛选影响）
        trend_a = resp_no_filter.json()["data"]["trend"]
        trend_b = resp_with_filter.json()["data"]["trend"]
        assert trend_a["increaseCount"] == trend_b["increaseCount"]
        assert trend_a["decreaseCount"] == trend_b["decreaseCount"]
        assert trend_a["newCount"] == trend_b["newCount"]
        assert trend_a["exitCount"] == trend_b["exitCount"]

    @pytest.mark.asyncio
    async def test_summary_specific_trend_counts(
        self, auth_client, full_dataset
    ):
        """国家队 trend 计数正确：increase=1/decrease=1/new=2/exit=1"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/summary",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 200
        trend = resp.json()["data"]["trend"]
        assert trend["increaseCount"] == 1  # 600519
        assert trend["decreaseCount"] == 1  # 000858
        assert trend["newCount"] == 2       # 601318/601398
        assert trend["exitCount"] == 1      # 600000

    @pytest.mark.asyncio
    async def test_summary_requires_auth(self, client):
        """未认证返回 401"""
        resp = await client.get(
            "/api/v1/shareholder-analysis/summary",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 401


# ============== Test: GET /industry-distribution — 行业分布 ==============


class TestIndustryDistribution:
    """行业分布端点测试（AC-02 / AC-05）"""

    @pytest.mark.asyncio
    async def test_industry_distribution_returns_distribution(
        self, auth_client, full_dataset
    ):
        """distribution 数组（industry/stockCount/percentage）（AC-02）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/industry-distribution",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "distribution" in data
        assert len(data["distribution"]) > 0

        first = data["distribution"][0]
        assert {"industry", "stockCount", "percentage"}.issubset(first.keys())

    @pytest.mark.asyncio
    async def test_industry_distribution_aggregates_correctly(
        self, auth_client, full_dataset
    ):
        """国家队行业分布：白酒2 / 保险1 / 银行1（共 4 只）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/industry-distribution",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 200
        dist = resp.json()["data"]["distribution"]
        by_industry = {d["industry"]: d["stockCount"] for d in dist}
        assert by_industry.get("白酒") == 2
        assert by_industry.get("保险") == 1
        assert by_industry.get("银行") == 1

    @pytest.mark.asyncio
    async def test_industry_distribution_not_affected_by_industry_filter(
        self, auth_client, full_dataset
    ):
        """industry-distribution 不受 industry 筛选影响（架构 §6.2 — 自身是筛选 UI 数据源）"""
        # 该接口不支持 industry 参数；即使传入也不应过滤分布本身
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/industry-distribution",
            params={
                "group_ids": "1", "report_period": "2024-12-31",
                "industry": "银行",
            },
        )
        assert resp.status_code == 200
        dist = resp.json()["data"]["distribution"]
        # 行业分布应仍包含所有行业（白酒/保险/银行），不被 industry 过滤
        industries = {d["industry"] for d in dist}
        assert "白酒" in industries

    @pytest.mark.asyncio
    async def test_low_percentage_industry_merged_into_undefined(
        self, auth_client, low_percentage_dataset
    ):
        """UC-014 回归：占比 <5% 的行业应合并到'未分类'，distribution 不为空。

        1 只股票 × 21 行业 → 每行业 4.76% < 5% 阈值。修复前 distribution 恒空
        （多行业摊薄 + 阈值过滤 + 低占比未合并）；修复后低占比行业合并到'未分类'项。
        """
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/industry-distribution",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 200
        dist = resp.json()["data"]["distribution"]
        assert len(dist) > 0, "低占比行业应合并到'未分类'，不应导致 distribution 为空"
        assert any(d["industry"] == "未分类" for d in dist), "应含'未分类'合并项"

    @pytest.mark.asyncio
    async def test_industry_distribution_requires_auth(self, client):
        """未认证返回 401"""
        resp = await client.get(
            "/api/v1/shareholder-analysis/industry-distribution",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 401


# ============== Test: GET /holdings — 分页持仓列表 ==============


class TestHoldings:
    """持仓列表端点测试（AC-02 / AC-03 / AC-04 / AC-05 / AC-11）"""

    @pytest.mark.asyncio
    async def test_holdings_returns_holdings_and_total(
        self, auth_client, full_dataset
    ):
        """holdings 数组 + total（AC-02）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/holdings",
            params={
                "group_ids": "1", "report_period": "2024-12-31",
                "page": 1, "page_size": 20,
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "holdings" in data
        assert "total" in data
        assert data["total"] == 4  # 国家队 4 只

    @pytest.mark.asyncio
    async def test_holdings_item_camel_case_fields(
        self, auth_client, full_dataset
    ):
        """每个 holding 含 symbol/stockName/totalHoldAmount/totalHoldFloatRatio/changeDirection/industries（§7.2 camelCase）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/holdings",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 200
        holdings = resp.json()["data"]["holdings"]
        assert len(holdings) > 0

        required = {
            "symbol", "stockName", "totalHoldAmount",
            "totalHoldFloatRatio", "changeDirection", "industries",
        }
        for h in holdings:
            assert required.issubset(h.keys()), f"holding 缺少字段: {required - set(h.keys())}"

    @pytest.mark.asyncio
    async def test_holdings_pagination(
        self, auth_client, full_dataset
    ):
        """分页 page/page_size 生效（AC-02）"""
        resp_p1 = await auth_client.get(
            "/api/v1/shareholder-analysis/holdings",
            params={
                "group_ids": "1", "report_period": "2024-12-31",
                "page": 1, "page_size": 2,
            },
        )
        resp_p2 = await auth_client.get(
            "/api/v1/shareholder-analysis/holdings",
            params={
                "group_ids": "1", "report_period": "2024-12-31",
                "page": 2, "page_size": 2,
            },
        )
        assert resp_p1.status_code == 200
        assert resp_p2.status_code == 200
        d1 = resp_p1.json()["data"]
        d2 = resp_p2.json()["data"]
        # total 不变（4 只），每页 2 条
        assert d1["total"] == 4
        assert len(d1["holdings"]) == 2
        assert len(d2["holdings"]) == 2

    @pytest.mark.asyncio
    async def test_holdings_industry_filter(
        self, auth_client, full_dataset
    ):
        """industry=银行 仅返回银行股票（AC-04）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/holdings",
            params={
                "group_ids": "1", "report_period": "2024-12-31",
                "industry": "银行",
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1  # 仅 601398 工商银行
        for h in data["holdings"]:
            assert "银行" in h["industries"]

    @pytest.mark.asyncio
    async def test_holdings_change_direction_increase(
        self, auth_client, full_dataset
    ):
        """change_direction=increase 仅返回增持股票（AC-05）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/holdings",
            params={
                "group_ids": "1", "report_period": "2024-12-31",
                "change_direction": "increase",
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1  # 600519
        for h in data["holdings"]:
            assert h["changeDirection"] == "increase"

    @pytest.mark.asyncio
    async def test_holdings_change_direction_exit(
        self, auth_client, full_dataset
    ):
        """change_direction=exit 返回退出股票（上期有本期无），展示上期数据（AC-05 / plan-02 §3.5）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/holdings",
            params={
                "group_ids": "1", "report_period": "2024-12-31",
                "change_direction": "exit",
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        # 仅 600000 浦发银行退出
        assert data["total"] == 1
        h = data["holdings"][0]
        assert h["symbol"] == "600000"
        assert h["changeDirection"] == "exit"
        # 退出股票的 totalHoldAmount / totalHoldFloatRatio 取上期值
        assert h["totalHoldAmount"] == 600.0
        assert h["totalHoldFloatRatio"] == 0.05

    @pytest.mark.asyncio
    async def test_holdings_multi_group_dedup_by_symbol(
        self, auth_client, full_dataset
    ):
        """多组联合 holdings 按 symbol 去重（AC-03）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/holdings",
            params={
                "group_ids": "1,2", "report_period": "2024-12-31",
                "page": 1, "page_size": 50,
            },
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        symbols = [h["symbol"] for h in data["holdings"]]
        # 601398 被 1（中央汇金）和 2（高盛）同时匹配 → 应只出现一次
        assert len(symbols) == len(set(symbols)), f"持仓未按 symbol 去重: {symbols}"
        assert data["total"] == 5  # 去重后 5 只

    @pytest.mark.asyncio
    async def test_holdings_requires_auth(self, client):
        """未认证返回 401"""
        resp = await client.get(
            "/api/v1/shareholder-analysis/holdings",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 401


# ============== Test: AC-11 降级（无 prev_period） ==============


@pytest_asyncio.fixture
async def single_period_holders(test_session, sample_stocks, sample_industry_sectors, sample_sector_stocks):
    """构造单一报告期数据（无 prev_period），用于 AC-11 降级测试"""
    records = [
        Top10FloatHolder(
            symbol="600519",
            ts_code="600519.SH",
            report_period=date(2024, 12, 31),
            ann_date=date(2025, 1, 20),
            holder_name="中央汇金投资有限责任公司",
            hold_amount=Decimal("1000.00"),
            hold_ratio=Decimal("0.0800"),
            hold_float_ratio=Decimal("0.1000"),
        ),
    ]
    test_session.add_all(records)
    await test_session.commit()
    return records


class TestDegradation:
    """AC-11 报告期数据不完整降级"""

    @pytest.mark.asyncio
    async def test_overview_no_prev_period(
        self, auth_client, single_period_holders
    ):
        """无 prev_period → hasPrevPeriod=false（AC-11）"""
        resp = await auth_client.get("/api/v1/shareholder-analysis/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hasPrevPeriod"] is False

    @pytest.mark.asyncio
    async def test_summary_trend_zero_when_no_prev(
        self, auth_client, single_period_holders
    ):
        """无 prev_period → trend 计数为 0（AC-11）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/summary",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hasPrevPeriod"] is False
        trend = data["trend"]
        assert trend["increaseCount"] == 0
        assert trend["decreaseCount"] == 0
        assert trend["newCount"] == 0
        assert trend["exitCount"] == 0

    @pytest.mark.asyncio
    async def test_holdings_change_direction_null_when_no_prev(
        self, auth_client, single_period_holders
    ):
        """无 prev_period → holdings 中 changeDirection 为 null（AC-11）"""
        resp = await auth_client.get(
            "/api/v1/shareholder-analysis/holdings",
            params={"group_ids": "1", "report_period": "2024-12-31"},
        )
        assert resp.status_code == 200
        holdings = resp.json()["data"]["holdings"]
        for h in holdings:
            assert h["changeDirection"] is None
