"""
基金扎堆度聚合查询 API 集成测试（plan-01 / 08 期）

覆盖端点：
- GET /api/v1/fund-crowd-analysis/rankings — 扎堆度排行榜（AC-01/02/03/06/07/08）
- GET /api/v1/fund-crowd-analysis/industry-distribution — 行业分布（AC-04）

参照 server/tests/test_fund_api.py 的 fixture + httpx 风格。
red 阶段原则：测试只通过 HTTP client 调 API 端点（`from main import app`），
不 import 尚未实现的 service / repository；red 失败原因应为「端点 404」或
「service 模块 ImportError」，而非测试代码本身的语法/逻辑错误。
"""

import pytest
import pytest_asyncio
from datetime import date
from decimal import Decimal
from httpx import AsyncClient

from main import app
from src.models.user import User
from src.models.fund import Fund
from src.models.fund_portfolio import FundPortfolio
from src.models.stock import Stock
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
        email="normal_fund_crowd@example.com",
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
    测试数据通过 fixture 写入并 commit 后，API session 可见。
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


@pytest_asyncio.fixture(autouse=True)
async def _isolate_fund_crowd_cache():
    """
    每个测试前后清 fund_crowd 缓存（L2 DB CacheEntry + L1 内存单例），
    防止不同 sample data 共享相同 (period, scope) key 跨测试串数据。

    缓存独立于 test_session（db_cache 用独立 AsyncSessionLocal 真实 commit），
    故必须显式清，不会被测试事务回滚。
    """
    from src.services.cache.fund_crowd_cache import (
        get_fund_crowd_cache,
        reset_fund_crowd_cache,
    )

    await get_fund_crowd_cache().invalidate_all()
    reset_fund_crowd_cache()
    yield
    await get_fund_crowd_cache().invalidate_all()
    reset_fund_crowd_cache()


# ============== Sample data fixtures ==============


@pytest_asyncio.fixture
async def sample_crowd_data(test_session):
    """
    插入测试数据：覆盖主动/被动、跨期、多股东、搜索命中、NULL 边界。

    基金口径：
      - 001001.OF 主动（普通股票型）
      - 001002.OF 被动（被动指数型）
      - 001003.OF 被动（增强指数型）
      - 001004.OF 主动（invest_type IS NULL → 显式归主动，ADR-1）

    持仓数据：
      最新期 2024-12-31：
        - 600519 被 4 只基金全部持有（stk_float_ratio: 2.5 / 1.5 / 0.8 / NULL）
          → scope=active fundCount=2 (001001+001004)
          → scope=all    fundCount=4
        - 000001 被 001001 + 001002 持有（stk_float_ratio: 0.5 / 0.3）
          → scope=active fundCount=1（仅 001001）
          → scope=all    fundCount=2
      上一期 2024-09-30（环比 / 新进）：
        - 600519 被 001001 + 001004 持有
          → scope=active fundCount=2（本期 2 - 上期 2 = 0）
        - 000001 无任何记录 → isNew=true

    注：plan-01 口径已修订（份额去重 + 去掉合计占流通比）。
    fixture 基金名互不相同且无份额后缀，故不影响 fund_count。
    """
    funds = [
        Fund(ts_code="001001.OF", name="华夏成长", invest_type="普通股票型"),
        Fund(ts_code="001002.OF", name="华夏大盘", invest_type="被动指数型"),
        Fund(ts_code="001003.OF", name="易方达蓝筹", invest_type="增强指数型"),
        Fund(ts_code="001004.OF", name="兴全新发", invest_type=None),
    ]
    portfolios = [
        # 最新期 2024-12-31
        FundPortfolio(
            fund_ts_code="001001.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=Decimal("2.5"),
        ),
        FundPortfolio(
            fund_ts_code="001002.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=Decimal("1.5"),
        ),
        FundPortfolio(
            fund_ts_code="001003.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=Decimal("0.8"),
        ),
        FundPortfolio(
            fund_ts_code="001004.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=None,  # NULL → SUM 忽略
        ),
        FundPortfolio(
            fund_ts_code="001001.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="000001",
            stk_float_ratio=Decimal("0.5"),
        ),
        FundPortfolio(
            fund_ts_code="001002.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="000001",
            stk_float_ratio=Decimal("0.3"),
        ),
        # 上一期 2024-09-30（用于环比 + 新进）
        FundPortfolio(
            fund_ts_code="001001.OF",
            report_period=date(2024, 9, 30),
            stock_symbol="600519",
            stk_float_ratio=Decimal("2.0"),
        ),
        FundPortfolio(
            fund_ts_code="001004.OF",
            report_period=date(2024, 9, 30),
            stock_symbol="600519",
            stk_float_ratio=None,
        ),
        # 000001 上期无任何记录 → 新进
    ]
    stocks = [
        Stock(symbol="600519", name="贵州茅台"),
        Stock(symbol="000001", name="平安银行"),
    ]
    test_session.add_all(funds + portfolios + stocks)
    await test_session.commit()
    return {"funds": funds, "portfolios": portfolios, "stocks": stocks}


@pytest_asyncio.fixture
async def sample_crowd_data_single_period(test_session):
    """单报告期数据（验证 hasPrevPeriod=false，环比字段全 null）"""
    funds = [
        Fund(ts_code="002001.OF", name="单期基金A", invest_type="普通股票型"),
    ]
    portfolios = [
        FundPortfolio(
            fund_ts_code="002001.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=Decimal("2.5"),
        ),
    ]
    stocks = [Stock(symbol="600519", name="贵州茅台")]
    test_session.add_all(funds + portfolios + stocks)
    await test_session.commit()
    return {"funds": funds, "portfolios": portfolios, "stocks": stocks}


@pytest_asyncio.fixture
async def sample_industry_data(test_session, sample_crowd_data):
    """
    在 sample_crowd_data 基础上插入行业映射：600519 → 食品饮料 + 消费龙头（一股多行业）
    000001 无行业关联（验证"未分类"桶）。
    """
    sectors = [
        Sector(name="食品饮料", code="IND_FOOD", type="industry"),
        Sector(name="消费龙头", code="IND_CONS", type="industry"),
    ]
    test_session.add_all(sectors)
    await test_session.flush()

    sector_stocks = [
        SectorStock(sector_code="IND_FOOD", stock_code="600519"),
        SectorStock(sector_code="IND_CONS", stock_code="600519"),
        # 000001 无任何行业映射
    ]
    test_session.add_all(sector_stocks)
    await test_session.commit()
    return {"sectors": sectors, "sector_stocks": sector_stocks}


@pytest_asyncio.fixture
async def sample_multi_sector_type_data(test_session, sample_crowd_data):
    """
    多板块类型 fixture：600519 同时关联三种 type 的板块，验证 sector_type 切换。
      - industry: 食品饮料 (IND_FOOD)
      - concept:  新能源 (CON_NEW)、融资融券 (CON_MR，用于验证概念分布默认排除)
      - region:   贵州 (REG_GZ)
    000001 无任何板块关联（验证各 type 下均归「未分类」）。
    scope=active 扎堆股集合 = {600519, 000001}（同 sample_crowd_data）。
    """
    sectors = [
        Sector(name="食品饮料", code="IND_FOOD", type="industry"),
        Sector(name="新能源", code="CON_NEW", type="concept"),
        Sector(name="融资融券", code="CON_MR", type="concept"),
        Sector(name="贵州", code="REG_GZ", type="region"),
    ]
    test_session.add_all(sectors)
    await test_session.flush()

    sector_stocks = [
        SectorStock(sector_code="IND_FOOD", stock_code="600519"),
        SectorStock(sector_code="CON_NEW", stock_code="600519"),
        SectorStock(sector_code="CON_MR", stock_code="600519"),
        SectorStock(sector_code="REG_GZ", stock_code="600519"),
        # 000001 无任何板块映射
    ]
    test_session.add_all(sector_stocks)
    await test_session.commit()
    return {"sectors": sectors, "sector_stocks": sector_stocks}


@pytest_asyncio.fixture
async def sample_null_stocks_table(test_session):
    """持仓的股票不在 stocks 表中（验证 stockName=null 降级）"""
    funds = [Fund(ts_code="003001.OF", name="Null Stocks 基金", invest_type="普通股票型")]
    portfolios = [
        FundPortfolio(
            fund_ts_code="003001.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="999999",
            stk_float_ratio=Decimal("1.0"),
        ),
    ]
    # 故意不插入 999999 的 Stock 记录
    test_session.add_all(funds + portfolios)
    await test_session.commit()
    return {"funds": funds, "portfolios": portfolios}


@pytest_asyncio.fixture
async def sample_share_class_data(test_session):
    """
    份额去重专项 fixture：同一只基金的 A/C/E 三份额，fund_ts_code 不同、
    name 去份额后缀（[ACDEHIR]$）后完全相同，三份额都持 600519。

    期望：份额去重后 fund_count=1（而非 3）。
    """
    funds = [
        Fund(ts_code="005001.OF", name="份额去重基金A", invest_type="普通股票型"),
        Fund(ts_code="005002.OF", name="份额去重基金C", invest_type="普通股票型"),
        Fund(ts_code="005003.OF", name="份额去重基金E", invest_type="普通股票型"),
    ]
    portfolios = [
        FundPortfolio(
            fund_ts_code="005001.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=Decimal("1.0"),
        ),
        FundPortfolio(
            fund_ts_code="005002.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=Decimal("2.0"),
        ),
        FundPortfolio(
            fund_ts_code="005003.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=Decimal("3.0"),
        ),
    ]
    stocks = [Stock(symbol="600519", name="贵州茅台")]
    test_session.add_all(funds + portfolios + stocks)
    await test_session.commit()
    return {"funds": funds, "portfolios": portfolios, "stocks": stocks}


@pytest_asyncio.fixture
async def sample_tiebreaker_data(test_session):
    """
    排序 tiebreaker fixture：两只股票 fund_count 相同（=1，仅被同一只基金持有），
    验证 fund_count 相同时按 stock_symbol ASC 排序。
    """
    funds = [
        Fund(ts_code="006001.OF", name="Tiebreaker 基金", invest_type="普通股票型"),
    ]
    portfolios = [
        FundPortfolio(
            fund_ts_code="006001.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="000002",
            stk_float_ratio=Decimal("1.0"),
        ),
        FundPortfolio(
            fund_ts_code="006001.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600300",
            stk_float_ratio=Decimal("1.0"),
        ),
    ]
    stocks = [
        Stock(symbol="000002", name="万科A"),
        Stock(symbol="600300", name="维维股份"),
    ]
    test_session.add_all(funds + portfolios + stocks)
    await test_session.commit()
    return {"funds": funds, "portfolios": portfolios, "stocks": stocks}


@pytest_asyncio.fixture
async def sample_hk_qdii_exclusion_data(test_session):
    """
    港股持仓 + QDII 基金排除专项 fixture：
      - 007001.OF 沪港深基金（混合型）：持 A 股 600519 + 港股 00700
      - 007002.OF QDII 基金（fund_type=QDII）：持 A 股 600519（应整体排除）
      - 007003.OF 正常基金（普通股票型）：持 A 股 600519

    期望（scope=all）：
      - 600519 fund_count=2（007001 + 007003；007002 QDII 排除）
      - 00700 港股（5位）不出现在榜单
    """
    funds = [
        Fund(ts_code="007001.OF", name="沪港深精选", invest_type="混合型", fund_type="混合型"),
        Fund(ts_code="007002.OF", name="海外QDII基金", invest_type="QDII", fund_type="QDII"),
        Fund(ts_code="007003.OF", name="正常股票基金", invest_type="普通股票型", fund_type="股票型"),
    ]
    portfolios = [
        FundPortfolio(
            fund_ts_code="007001.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=Decimal("1.0"),
        ),
        FundPortfolio(
            fund_ts_code="007001.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="00700",  # 港股（5位）→ 应排除
            stk_float_ratio=Decimal("1.0"),
        ),
        FundPortfolio(
            fund_ts_code="007002.OF",  # QDII 基金 → 整体排除
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=Decimal("1.0"),
        ),
        FundPortfolio(
            fund_ts_code="007003.OF",
            report_period=date(2024, 12, 31),
            stock_symbol="600519",
            stk_float_ratio=Decimal("1.0"),
        ),
    ]
    stocks = [
        Stock(symbol="600519", name="贵州茅台", exchange="SSE"),
        Stock(symbol="00700", name="腾讯控股", exchange="HKEX"),
    ]
    test_session.add_all(funds + portfolios + stocks)
    await test_session.commit()
    return {"funds": funds, "portfolios": portfolios, "stocks": stocks}


# ============== Helper ==============


def _find_item(items: list, stock_symbol: str) -> dict:
    """按 stockSymbol 字段（camelCase）查找 item"""
    for it in items:
        if it.get("stockSymbol") == stock_symbol:
            return it
    raise AssertionError(f"未找到 stockSymbol={stock_symbol} 的 item，items={items}")


# ============== Test: GET /rankings — 扎堆度排行榜 ==============


class TestRankings:
    """扎堆度排行榜端点测试"""

    @pytest.fixture(autouse=True)
    def _disable_crowd_threshold(self, monkeypatch):
        """既有语义测试 fixture 的 fund_count 均为个位数（≤20），
        将扎堆阈值临时降为 0 以排除阈值过滤的干扰；阈值本身由专项测试覆盖。"""
        from src.services import fund_crowd_analysis_service

        monkeypatch.setattr(
            fund_crowd_analysis_service, "MIN_CROWD_FUND_COUNT", 0
        )

    @pytest.mark.asyncio
    async def test_rankings_returns_active_scope_only(
        self, auth_client, sample_crowd_data
    ):
        """AC-01：scope=active 排除被动型，600519 fundCount=2（001001+001004）"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings", params={"scope": "active"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        assert data["hasData"] is True
        assert data["currentPeriod"] == "2024-12-31"

        item = _find_item(data["items"], "600519")
        assert item["fundCount"] == 2
        # 口径修订：已删除 totalFloatRatio 字段，不应再返回
        assert "totalFloatRatio" not in item

    @pytest.mark.asyncio
    async def test_rankings_all_scope_includes_passive(
        self, auth_client, sample_crowd_data
    ):
        """AC-02：scope=all 纳入被动型，600519 fundCount=4（全部 4 只）"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings", params={"scope": "all"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        item = _find_item(data["items"], "600519")
        assert item["fundCount"] == 4

    @pytest.mark.asyncio
    async def test_rankings_order_by_fund_count_desc(
        self, auth_client, sample_crowd_data
    ):
        """AC-01 排序：fund_count DESC, stock_symbol ASC，600519(4) 在 000001(2) 之前（scope=all）"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings",
            params={"scope": "all", "page_size": 20},
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]

        symbols = [it["stockSymbol"] for it in items]
        assert symbols.index("600519") < symbols.index("000001"), (
            f"600519(fundCount=4) 应排在 000001(fundCount=2) 之前，实际顺序: {symbols}"
        )

    @pytest.mark.asyncio
    async def test_rankings_order_tiebreaker_by_stock_symbol_asc(
        self, auth_client, sample_tiebreaker_data
    ):
        """AC-01 tiebreaker：fund_count 相同时按 stock_symbol ASC（同 fundCount 的两只股）"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings",
            params={"scope": "active", "page_size": 20},
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        symbols = [it["stockSymbol"] for it in items]
        # 两只都被同一只基金持有 → fund_count 相同（=1），按 symbol ASC
        assert symbols == sorted(symbols), (
            f"fund_count 相同时应按 stock_symbol ASC，实际顺序: {symbols}"
        )

    @pytest.mark.asyncio
    async def test_rankings_change_computation(
        self, auth_client, sample_crowd_data
    ):
        """AC-03：600519 fundCountChange=0（本期 2 - 上期 2）；000001 isNew=true（上期无记录）"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings", params={"scope": "active"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["hasPrevPeriod"] is True
        assert data["prevPeriod"] == "2024-09-30"

        item_519 = _find_item(data["items"], "600519")
        assert item_519["fundCountChange"] == 0
        assert item_519["isNew"] is False
        # 口径修订：已删除 totalFloatRatioChange
        assert "totalFloatRatioChange" not in item_519

        item_001 = _find_item(data["items"], "000001")
        assert item_001["isNew"] is True
        assert item_001["fundCountChange"] is None

    @pytest.mark.asyncio
    async def test_rankings_no_prev_period_returns_null_changes(
        self, auth_client, sample_crowd_data_single_period
    ):
        """AC-06：只有一期 → hasPrevPeriod=false，所有 change 字段 null"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings", params={"scope": "active"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["hasPrevPeriod"] is False
        assert data["prevPeriod"] is None

        for item in data["items"]:
            assert item["fundCountChange"] is None
            assert item["isNew"] is None

    @pytest.mark.asyncio
    async def test_rankings_empty_portfolio_returns_has_data_false(self, auth_client):
        """AC-07：空表 → hasData=false、items=[]"""
        resp = await auth_client.get("/api/v1/fund-crowd-analysis/rankings")
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["hasData"] is False
        assert data["items"] == []
        assert data["total"] == 0
        assert data["hasPrevPeriod"] is False

    @pytest.mark.asyncio
    async def test_rankings_search_by_code_prefix(
        self, auth_client, sample_crowd_data
    ):
        """AC-08：search=600 → 仅命中 600519，total=1"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings",
            params={"scope": "all", "search": "600"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["stockSymbol"] == "600519"

    @pytest.mark.asyncio
    async def test_rankings_search_by_name_contains(
        self, auth_client, sample_crowd_data
    ):
        """AC-08：search=茅台 → 仅命中 600519（贵州茅台），total=1"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings",
            params={"scope": "all", "search": "茅台"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["stockSymbol"] == "600519"
        assert data["items"][0]["stockName"] == "贵州茅台"

    @pytest.mark.asyncio
    async def test_rankings_search_no_match(self, auth_client, sample_crowd_data):
        """AC-08 边界：search=不存在的股票 → items=[]、total=0"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings",
            params={"scope": "all", "search": "不存在的股票"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_rankings_pagination(self, auth_client, sample_crowd_data):
        """分页：page=1&page_size=1 → items 长度 1、total=2；page=2 → 剩 1 条"""
        resp1 = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings",
            params={"scope": "all", "page": 1, "page_size": 1},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()["data"]
        assert data1["total"] == 2
        assert len(data1["items"]) == 1
        assert data1["page"] == 1
        assert data1["pageSize"] == 1

        resp2 = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings",
            params={"scope": "all", "page": 2, "page_size": 1},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()["data"]
        assert len(data2["items"]) == 1

    @pytest.mark.asyncio
    async def test_rankings_requires_auth(self, client):
        """安全：未认证返回 401"""
        resp = await client.get("/api/v1/fund-crowd-analysis/rankings")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_rankings_stock_name_null_when_stocks_table_missing(
        self, auth_client, sample_null_stocks_table
    ):
        """L2 降级：stocks 表无该 symbol → stockName=null"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings", params={"scope": "active"}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["stockSymbol"] == "999999"
        assert items[0]["stockName"] is None
        # fund_count 应仍正常
        assert items[0]["fundCount"] == 1

    @pytest.mark.asyncio
    async def test_rankings_search_escapes_like_wildcards(
        self, auth_client, sample_crowd_data
    ):
        """安全：search=% → 不匹配全表（LIKE 通配符被转义），total=0"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings",
            params={"scope": "all", "search": "%"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_rankings_dedup_fund_share_classes(
        self, auth_client, sample_share_class_data
    ):
        """份额去重：A/C/E 三份额（不同 fund_ts_code、name 去后缀相同）持 600519
        → fund_count=1（按基金名 regexp_replace 去重，而非 fund_ts_code）"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings", params={"scope": "active"}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        item = items[0]
        assert item["stockSymbol"] == "600519"
        # 关键断言：份额去重后 fund_count=1，而非未去重的 3
        assert item["fundCount"] == 1, (
            f"份额去重后 fund_count 应为 1（同一只基金的 A/C/E 三份额合并），"
            f"实际: {item['fundCount']}"
        )

    @pytest.mark.asyncio
    async def test_rankings_excludes_hk_stock_holdings(
        self, auth_client, sample_hk_qdii_exclusion_data
    ):
        """护栏：港股持仓（5位代码如 00700 腾讯）不计入扎堆，不出现在榜单"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings", params={"scope": "all"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        symbols = [it["stockSymbol"] for it in data["items"]]
        assert "00700" not in symbols, (
            f"港股 00700 不应出现在扎堆榜单，实际: {symbols}"
        )

    @pytest.mark.asyncio
    async def test_rankings_excludes_qdii_fund(
        self, auth_client, sample_hk_qdii_exclusion_data
    ):
        """护栏：QDII 基金（fund_type=QDII）整体排除，其 A 股持仓不计入 fund_count。
        600519 仅被沪港深基金(007001) + 正常基金(007003) 持有 → fund_count=2（不含 QDII 007002）"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings", params={"scope": "all"}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item = _find_item(items, "600519")
        assert item["fundCount"] == 2, (
            f"QDII 基金应被排除，600519 fund_count 应为 2（不含 QDII 007002），"
            f"实际: {item['fundCount']}"
        )

    @pytest.mark.asyncio
    async def test_rankings_industries_field_changes_with_sector_type(
        self, auth_client, sample_multi_sector_type_data
    ):
        """sector_type 切换联动：600519 的 industries 随 type 变，fundCount 不变"""
        # concept → 新能源、融资融券（rankings 不过滤，返回原始概念全量）
        resp_concept = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings",
            params={"scope": "active", "sector_type": "concept"},
        )
        assert resp_concept.status_code == 200
        item_concept = _find_item(resp_concept.json()["data"]["items"], "600519")
        assert item_concept["industries"] == ["新能源", "融资融券"]
        assert item_concept["fundCount"] == 2

        # industry（默认）→ 食品饮料
        resp_industry = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings", params={"scope": "active"}
        )
        assert resp_industry.status_code == 200
        item_industry = _find_item(resp_industry.json()["data"]["items"], "600519")
        assert item_industry["industries"] == ["食品饮料"]
        # sector_type 只影响 industries 列，不影响 fund_count（聚合层不碰 sectors）
        assert item_industry["fundCount"] == 2

    @pytest.mark.asyncio
    async def test_rankings_cache_hit_skips_recomputation(
        self, auth_client, sample_crowd_data, monkeypatch
    ):
        """ADR-6 修订：同 params 二次请求命中缓存，核心聚合不重算"""
        from src.repositories.fund_crowd_repository import FundCrowdRepository

        original = FundCrowdRepository.get_crowd_aggregation
        call_count = 0

        async def _spy(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return await original(self, *args, **kwargs)

        monkeypatch.setattr(FundCrowdRepository, "get_crowd_aggregation", _spy)

        url = "/api/v1/fund-crowd-analysis/rankings"
        params = {"scope": "active", "page": 1, "pageSize": 20}

        resp1 = await auth_client.get(url, params=params)
        assert resp1.status_code == 200
        first_count = call_count
        assert first_count > 0  # 首次 miss 触发计算

        # 同 params 二次请求：应命中缓存，聚合调用次数不再增加
        resp2 = await auth_client.get(url, params=params)
        assert resp2.status_code == 200
        assert call_count == first_count
        # 缓存返回的数据与首次一致
        assert resp2.json()["data"]["items"] == resp1.json()["data"]["items"]
        assert resp2.json()["data"]["total"] == resp2.json()["data"]["total"]

    @pytest.mark.asyncio
    async def test_rankings_filters_below_crowd_threshold(
        self, auth_client, sample_crowd_data, monkeypatch
    ):
        """扎堆阈值：持有基金数 ≤ MIN_CROWD_FUND_COUNT 的不计入排行榜。
        autouse fixture 已把阈值降为 0，此处恢复默认阈值 20 验证过滤。"""
        from src.services import fund_crowd_analysis_service

        monkeypatch.setattr(
            fund_crowd_analysis_service, "MIN_CROWD_FUND_COUNT", 20
        )

        # sample_crowd_data 中 600519 active fund_count=2、000001=1，均 ≤20 → 应被全部过滤
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/rankings", params={"scope": "active"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0


# ============== Test: GET /industry-distribution — 行业分布 ==============


class TestIndustryDistribution:
    """行业分布端点测试"""

    @pytest.mark.asyncio
    async def test_industry_distribution_active_scope(
        self, auth_client, sample_industry_data
    ):
        """AC-04：600519 归食品饮料+消费龙头，000001 无行业→未分类；
        percentage = 扎堆股数 / 总扎堆股数 × 100"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution",
            params={"scope": "active"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]

        assert data["hasData"] is True
        assert data["currentPeriod"] == "2024-12-31"

        dist = data["distribution"]
        by_industry = {d["industry"]: d for d in dist}

        # scope=active: 600519(2 主动基金) + 000001(1 主动基金 001001) = 2 只扎堆股
        # 600519 → 食品饮料 + 消费龙头（一股多行业，各计 1）
        # 000001 → 无行业映射 → 未分类
        assert "食品饮料" in by_industry
        assert "消费龙头" in by_industry
        assert "未分类" in by_industry

        # 占比分母 = 扎堆股总数 2（前端展示「分子/分母」依赖此字段）
        assert data["totalStockCount"] == 2

        food = by_industry["食品饮料"]
        assert food["stockCount"] == 1
        assert abs(food["percentage"] - 50.0) < 0.01  # 1 / 2 * 100

    @pytest.mark.asyncio
    async def test_industry_distribution_multi_industries_per_stock(
        self, auth_client, sample_industry_data
    ):
        """AC-04 一股多行业：600519 同时出现在食品饮料和消费龙头两个桶里"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution",
            params={"scope": "active"},
        )
        assert resp.status_code == 200
        dist = resp.json()["data"]["distribution"]

        industries_with_519 = [
            d for d in dist if d["stockCount"] >= 1 and d["industry"] in ("食品饮料", "消费龙头")
        ]
        assert len(industries_with_519) == 2, (
            f"600519 应同时归属食品饮料+消费龙头，实际 distribution: {dist}"
        )

    @pytest.mark.asyncio
    async def test_industry_distribution_defaults_to_industry(
        self, auth_client, sample_multi_sector_type_data
    ):
        """sector_type 默认 industry：含食品饮料，不含 concept/region 的板块"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution",
            params={"scope": "active"},
        )
        assert resp.status_code == 200
        by_industry = {d["industry"]: d for d in resp.json()["data"]["distribution"]}
        assert "食品饮料" in by_industry
        assert "新能源" not in by_industry
        assert "贵州" not in by_industry

    @pytest.mark.asyncio
    async def test_industry_distribution_concept_type(
        self, auth_client, sample_multi_sector_type_data
    ):
        """sector_type=concept：600519→新能源（融资融券被默认排除）；无概念关联的 000001 归未分类"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution",
            params={"scope": "active", "sector_type": "concept"},
        )
        assert resp.status_code == 200
        by_industry = {d["industry"]: d for d in resp.json()["data"]["distribution"]}
        assert "新能源" in by_industry
        assert by_industry["新能源"]["stockCount"] == 1
        # 分母仍为扎堆股总数 2，新能源占比 50%
        assert by_industry["新能源"]["percentage"] == 50.0
        assert "食品饮料" not in by_industry
        assert "贵州" not in by_industry
        # 默认排除项不出现
        assert "融资融券" not in by_industry
        assert "沪股通" not in by_industry
        assert "深股通" not in by_industry
        # 000001 无概念关联 → 未分类
        assert "未分类" in by_industry

    @pytest.mark.asyncio
    async def test_industry_distribution_concept_excludes_default(
        self, auth_client, sample_multi_sector_type_data
    ):
        """概念分布默认排除 融资融券/沪股通/深股通；industry/region 查询不受影响"""
        # 概念：融资融券 被过滤，新能源 保留
        concept_resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution",
            params={"scope": "active", "sector_type": "concept"},
        )
        assert concept_resp.status_code == 200
        concept_names = {
            d["industry"] for d in concept_resp.json()["data"]["distribution"]
        }
        assert "融资融券" not in concept_names
        assert "新能源" in concept_names

        # industry 查询不受排除项影响：食品饮料 正常出现
        industry_resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution",
            params={"scope": "active", "sector_type": "industry"},
        )
        assert industry_resp.status_code == 200
        industry_names = {
            d["industry"] for d in industry_resp.json()["data"]["distribution"]
        }
        assert "食品饮料" in industry_names

        # region 查询不受排除项影响：贵州 正常出现
        region_resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution",
            params={"scope": "active", "sector_type": "region"},
        )
        assert region_resp.status_code == 200
        region_names = {
            d["industry"] for d in region_resp.json()["data"]["distribution"]
        }
        assert "贵州" in region_names

    @pytest.mark.asyncio
    async def test_industry_distribution_region_type(
        self, auth_client, sample_multi_sector_type_data
    ):
        """sector_type=region：600519→贵州"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution",
            params={"scope": "active", "sector_type": "region"},
        )
        assert resp.status_code == 200
        by_industry = {d["industry"]: d for d in resp.json()["data"]["distribution"]}
        assert "贵州" in by_industry
        assert "食品饮料" not in by_industry
        assert "新能源" not in by_industry

    @pytest.mark.asyncio
    async def test_industry_distribution_invalid_type_falls_back_to_industry(
        self, auth_client, sample_multi_sector_type_data
    ):
        """非法 sector_type 容错回退 industry：200（非 422）+ 含食品饮料"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution",
            params={"scope": "active", "sector_type": "foobar"},
        )
        assert resp.status_code == 200
        by_industry = {d["industry"]: d for d in resp.json()["data"]["distribution"]}
        assert "食品饮料" in by_industry
        assert "新能源" not in by_industry

    @pytest.mark.asyncio
    async def test_industry_distribution_empty_when_no_industry_mapping(
        self, auth_client, sample_crowd_data
    ):
        """AC-04 边界：无任何 sector_stocks 关联 → 全部归入"未分类"桶"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution",
            params={"scope": "active"},
        )
        assert resp.status_code == 200
        dist = resp.json()["data"]["distribution"]

        # 所有扎堆股都应归入"未分类"
        industries = {d["industry"] for d in dist}
        assert industries == {"未分类"}, f"应全部归未分类，实际: {industries}"

    @pytest.mark.asyncio
    async def test_industry_distribution_empty_portfolio(self, auth_client):
        """空表 → hasData=false、distribution=[]"""
        resp = await auth_client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hasData"] is False
        assert data["distribution"] == []
        assert data["totalStockCount"] == 0

    @pytest.mark.asyncio
    async def test_industry_distribution_requires_auth(self, client):
        """安全：未认证返回 401"""
        resp = await client.get(
            "/api/v1/fund-crowd-analysis/industry-distribution"
        )
        assert resp.status_code == 401
