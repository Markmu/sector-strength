"""
券商月度金股后端查询服务与 API（plan-02）pytest 测试 — RED 阶段

对应 plan-02 §5 验收标准（AC-02/03/04/05/06/07/09/10/11/12/13）+
「构建与类型」（import 校验 / pytest 不回归）。

本功能为纯后端查询 API（无前端 UI），E2E 形态为 pytest
（参照 MEMORY「后端 FEAT E2E 适配 pytest」+ plan-01 已建立的
test_broker_recommend_sync.py 范式 + server/tests/test_fund_crowd_api.py 的
HTTP client URL 模式 /api/v1/... + conftest.py 的 test_session/client fixture）。

RED 阶段原则（参照 test_broker_recommend_sync.py red 证据范式）：
- 测试只针对「尚未实现的真实功能」断言：BrokerRecommendRepository（4 聚合方法）、
  BrokerRecommendAnalysisService（latest_month 兜底 + 行业 JOIN + 序列化）、
  4 个用户侧 v1 端点 GET /months / /stock-ranking / /broker-list / /broker-detail。
- 失败原因必须是「目标功能尚未实现」（ModuleNotFoundError service/repo 未创建 /
  ImportError repository 未导出 / 404 路由未注册），而不是测试自身错误或环境错误。
- 断言强度不放宽：实现后跑同一组用例应全部通过。

plan-01 已就绪（BrokerRecommend 模型 + broker_recommend 表已建），故测试可直接
通过 test_session INSERT broker_recommend 测试数据做真实聚合查询验证。
"""

import pytest
import pytest_asyncio
from datetime import date
from httpx import AsyncClient

from main import app
from src.models.user import User
from src.models.stock import Stock
from src.models.sector import Sector
from src.models.sector_stock import SectorStock
from src.api.deps import get_current_user, get_session

def _unwrap_fastapi(app_obj):
    """沿 ``.app`` 链解包到持 ``dependency_overrides`` 的 FastAPI 实例。

    ``main.app`` 为 ``ResponseLoggingMiddleware`` → ``ProcessTimeMiddleware`` → FastAPI
    （双层），单层 ``app.app`` 取到 ``ProcessTimeMiddleware``（无 ``dependency_overrides``）
    会报 ``AttributeError``。复制自 ``tests/api/admin/conftest.py``。
    """
    cur = app_obj
    for _ in range(10):
        if hasattr(cur, "dependency_overrides"):
            return cur
        if hasattr(cur, "app"):
            cur = cur.app
        else:  # pragma: no cover - 防御性
            break
    return cur


# app 被双层中间件（ResponseLoggingMiddleware → ProcessTimeMiddleware）包装，
# 需要沿 .app 链解包到真正持 dependency_overrides 的 FastAPI 实例
_fastapi_app = _unwrap_fastapi(app)

BASE_URL = "/api/v1/broker-recommend-analysis"


# ============== User fixtures（参照 test_fund_crowd_api.py）==============


@pytest_asyncio.fixture
async def normal_user(test_session):
    """创建普通用户并写入 DB（普通用户即可访问用户侧只读 API，与 fund-crowd 一致）"""
    user = User(
        email="normal_broker_analysis@example.com",
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
    """注入普通用户认证 + override get_session。
    API 请求使用独立 session（同 schema），避免 asyncpg 连接冲突。
    测试数据通过 fixture 写入并 commit 后，API session 可见。"""
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


def _rec(symbol, broker, month, trade_date, reason=None):
    """构造 BrokerRecommend 记录（plan-01 模型已就绪）"""
    from src.models.broker_recommend import BrokerRecommend

    ts_code = (
        f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
    )
    return BrokerRecommend(
        month=month,
        trade_date=trade_date,
        ts_code=ts_code,
        symbol=symbol,
        broker=broker,
        name=None,  # name 快照字段；查询以 stocks JOIN 为准
        reason=reason,
    )


@pytest_asyncio.fixture
async def sample_broker_data(test_session):
    """
    插入测试数据：覆盖双视图、排序、分页、搜索、月份切换、行业 JOIN、空状态。

    月份 2026-05-01（最新）：
      - 600519 被 3 家券商推荐（中信/海通/国泰）→ broker_count=3
      - 000001 被 2 家券商推荐（中信/招商）→ broker_count=2
      - 600000 被 1 家券商推荐（中信）→ broker_count=1
      券商维度：
        - 中信 3 股（600519/000001/600000）→ stock_count=3
        - 海通 1 股（600519）→ stock_count=1
        - 国泰 1 股（600519）→ stock_count=1
        - 招商 1 股（000001）→ stock_count=1
    月份 2026-04-01（上一月，用于月份切换 / months 降序）：
      - 600519 被 中信 1 家推荐
    """
    from src.models.broker_recommend import BrokerRecommend

    stocks = [
        Stock(symbol="600519", name="贵州茅台"),
        Stock(symbol="000001", name="平安银行"),
        Stock(symbol="600000", name="浦发银行"),
    ]
    records = [
        # 2026-05-01（最新月）
        _rec("600519", "中信证券", date(2026, 5, 1), date(2026, 5, 31), reason="业绩稳健"),
        _rec("600519", "海通证券", date(2026, 5, 1), date(2026, 5, 20), reason="估值修复"),
        _rec("600519", "国泰君安", date(2026, 5, 1), date(2026, 5, 15), reason="品牌护城河"),
        _rec("000001", "中信证券", date(2026, 5, 1), date(2026, 5, 31), reason="分红稳定"),
        _rec("000001", "招商证券", date(2026, 5, 1), date(2026, 5, 28), reason="零售转型"),
        _rec("600000", "中信证券", date(2026, 5, 1), date(2026, 5, 31), reason="息差改善"),
        # 2026-04-01（上一月）
        _rec("600519", "中信证券", date(2026, 4, 1), date(2026, 4, 30), reason="一季度超预期"),
    ]
    test_session.add_all(stocks + records)
    await test_session.commit()
    return {"stocks": stocks, "records": records}


@pytest_asyncio.fixture
async def sample_broker_data_with_industry(test_session, sample_broker_data):
    """
    在 sample_broker_data 基础上插入行业映射：
      - 600519 → 食品饮料（industry）
      - 000001 无行业映射（验证 industries=[]）
    """
    sectors = [
        Sector(name="食品饮料", code="IND_FOOD", type="industry"),
    ]
    test_session.add_all(sectors)
    await test_session.flush()

    sector_stocks = [
        SectorStock(sector_code="IND_FOOD", stock_code="600519"),
        # 000001 / 600000 无行业映射
    ]
    test_session.add_all(sector_stocks)
    await test_session.commit()
    return {"sectors": sectors, "sector_stocks": sector_stocks}


@pytest_asyncio.fixture
async def sample_broker_null_stocks_table(test_session):
    """持仓股票不在 stocks 表中（验证 name=null 降级，AC/边界场景）"""
    from src.models.broker_recommend import BrokerRecommend

    records = [
        _rec("999999", "中信证券", date(2026, 5, 1), date(2026, 5, 31), reason="冷门股"),
    ]
    # 故意不插入 999999 的 Stock 记录
    test_session.add_all(records)
    await test_session.commit()
    return {"records": records}


@pytest_asyncio.fixture
async def sample_broker_null_reason(test_session):
    """broker 推荐记录的 reason 为 NULL（验证 reasons=[] 降级，AC-13 边界场景）。
    数据写入在 fixture setup 阶段完成，避免与 API 请求 session 并发。"""
    records = [
        _rec("600519", "中信证券", date(2026, 5, 1), date(2026, 5, 31), reason=None),
    ]
    stocks = [Stock(symbol="600519", name="贵州茅台")]
    test_session.add_all(records + stocks)
    await test_session.commit()
    return {"records": records}


# ============== Helper ==============


def _find_stock_item(items: list, symbol: str) -> dict:
    """按 symbol 字段查找 stock-ranking item（camelCase）"""
    for it in items:
        if it.get("symbol") == symbol:
            return it
    raise AssertionError(f"未找到 symbol={symbol} 的 item，items={items}")


def _find_broker_item(items: list, broker: str) -> dict:
    """按 broker 字段查找 broker-list item（camelCase）"""
    for it in items:
        if it.get("broker") == broker:
            return it
    raise AssertionError(f"未找到 broker={broker} 的 item，items={items}")


# ============== AC-02/03/06/07/10/11：GET /stock-ranking ==============


class TestStockRanking:
    """AC-02/03/06/07/10/11 — 股票维度排行（默认最新月 + broker_count DESC + 双字段排序 +
    brokers 预加载 + 搜索 + 分页 + name/industries JOIN）。

    来源：plan-02 §5 股票维度验收、§实现规格 #1/#2/#3。
    red 预期：404 Not Found（路由 /stock-ranking 未注册）。
    """

    @pytest.mark.asyncio
    async def test_ranking_default_latest_month(
        self, auth_client, sample_broker_data
    ):
        """AC-02/AC-10：默认（不传 month）取 MAX(month) 最新月=2026-05-01；
        items 按 broker_count 降序"""
        resp = await auth_client.get(f"{BASE_URL}/stock-ranking")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["hasData"] is True
        assert data["month"] == "2026-05-01"  # AC-10 默认月份 MAX(month)
        # 600519(3) > 000001(2) > 600000(1)
        symbols = [it["symbol"] for it in data["items"]]
        assert symbols.index("600519") < symbols.index("000001")
        assert symbols.index("000001") < symbols.index("600000")

    @pytest.mark.asyncio
    async def test_ranking_broker_count_correct(self, auth_client, sample_broker_data):
        """AC-02：broker_count = COUNT DISTINCT broker（600519=3, 000001=2, 600000=1）"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"page_size": 20}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item_519 = _find_stock_item(items, "600519")
        item_001 = _find_stock_item(items, "000001")
        item_000 = _find_stock_item(items, "600000")
        assert item_519["brokerCount"] == 3
        assert item_001["brokerCount"] == 2
        assert item_000["brokerCount"] == 1

    @pytest.mark.asyncio
    async def test_ranking_tiebreaker_by_symbol_asc(
        self, auth_client, sample_broker_data
    ):
        """AC-07：broker_count 相同按 symbol ASC（海通&国泰&招商 stock_count 不直接可比，
        但可验证 broker_count=1 的 600000 排在 broker_count=1 类之后；这里验证
        整体排序稳定：相同 broker_count 内 symbol 升序）。
        构造 600000 与另一 broker_count=1 的股票时按 symbol 排序。"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"page_size": 20}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        # 按 broker_count DESC, symbol ASC 整体验证
        def sort_key(it):
            return (-it["brokerCount"], it["symbol"])
        assert items == sorted(items, key=sort_key), (
            f"应按 broker_count DESC, symbol ASC 排序，实际: {items}"
        )

    @pytest.mark.asyncio
    async def test_ranking_brokers_preloaded(self, auth_client, sample_broker_data):
        """AC-03：brokers 预加载随列表返回（无二次请求）；每项含 brokers 数组。
        600519 的 brokers 应含 3 家券商"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"page_size": 20}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item_519 = _find_stock_item(items, "600519")
        assert "brokers" in item_519
        brokers = item_519["brokers"]
        assert len(brokers) == 3
        broker_names = {b["broker"] for b in brokers}
        assert broker_names == {"中信证券", "海通证券", "国泰君安"}
        # reasons 数组（去空去重，AC-03 不丢弃）
        for b in brokers:
            assert "reasons" in b
            assert isinstance(b["reasons"], list)

    @pytest.mark.asyncio
    async def test_ranking_pagination_total(
        self, auth_client, sample_broker_data
    ):
        """AC-06：total = 当前月份不同 symbol 总数（3），page/page_size 分页生效"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"page": 1, "page_size": 2}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 3  # 600519/000001/600000
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["pageSize"] == 2

        resp2 = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"page": 2, "page_size": 2}
        )
        assert resp2.status_code == 200
        data2 = resp2.json()["data"]
        assert len(data2["items"]) == 1  # 剩 1 条

    @pytest.mark.asyncio
    async def test_ranking_search_by_symbol_prefix(
        self, auth_client, sample_broker_data
    ):
        """AC-11：search=600 → symbol LIKE 前缀命中 600519/600000，total=2"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"search": "600"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        symbols = {it["symbol"] for it in data["items"]}
        assert symbols == {"600519", "600000"}

    @pytest.mark.asyncio
    async def test_ranking_search_by_name_contains(
        self, auth_client, sample_broker_data
    ):
        """AC-11：search=茅台 → name ILIKE 包含命中 600519，total=1"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"search": "茅台"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["symbol"] == "600519"
        assert data["items"][0]["name"] == "贵州茅台"

    @pytest.mark.asyncio
    async def test_ranking_search_no_match(self, auth_client, sample_broker_data):
        """AC-11 边界：search 无匹配 → items=[] + total=0"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"search": "不存在的股票"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_ranking_search_escapes_like_wildcards(
        self, auth_client, sample_broker_data
    ):
        """安全（§8.3）：search=% → 不匹配全表（LIKE 通配符转义），total=0"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"search": "%"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_ranking_name_null_when_stocks_table_missing(
        self, auth_client, sample_broker_null_stocks_table
    ):
        """边界：stocks 表无该 symbol → name=null（前端 "—"），不影响 broker_count"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"page_size": 20}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) == 1
        assert items[0]["symbol"] == "999999"
        assert items[0]["name"] is None
        assert items[0]["brokerCount"] == 1

    @pytest.mark.asyncio
    async def test_ranking_industries_joined(
        self, auth_client, sample_broker_data_with_industry
    ):
        """行业 JOIN：600519→食品饮料（industry），000001→[]（无映射）"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"page_size": 20}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item_519 = _find_stock_item(items, "600519")
        assert item_519["industries"] == ["食品饮料"]
        item_001 = _find_stock_item(items, "000001")
        assert item_001["industries"] == []

    @pytest.mark.asyncio
    async def test_ranking_month_switch(self, auth_client, sample_broker_data):
        """AC-05：传 month=2026-04-01 → 取该月数据（600519 broker_count=1）"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"month": "2026-04-01"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hasData"] is True
        assert data["month"] == "2026-04-01"
        assert data["total"] == 1
        item = _find_stock_item(data["items"], "600519")
        assert item["brokerCount"] == 1

    @pytest.mark.asyncio
    async def test_ranking_month_no_data_returns_empty(
        self, auth_client, sample_broker_data
    ):
        """AC-09 所选月无数据分支：传一个有同步数据但无该月记录的月份（2026-03-01）
        → items=[] + total=0（注意 hasData 仍 true，因表有数据）"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"month": "2026-03-01"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_ranking_requires_auth(self, client):
        """安全（§8.3）：未认证 → 401"""
        resp = await client.get(f"{BASE_URL}/stock-ranking")
        assert resp.status_code == 401


# ============== AC-04/06/07/12：GET /broker-list ==============


class TestBrokerList:
    """AC-04/06/07/12 — 券商维度分组（broker 分组 + stock_count DESC + 双字段排序 +
    搜索 + 分页）。

    来源：plan-02 §5 券商维度验收、§实现规格 #1/#2/#3。
    red 预期：404 Not Found（路由 /broker-list 未注册）。
    """

    @pytest.mark.asyncio
    async def test_broker_list_default_latest_month(
        self, auth_client, sample_broker_data
    ):
        """AC-04/AC-10：默认取最新月 2026-05-01；按 broker 分组、stock_count 降序"""
        resp = await auth_client.get(f"{BASE_URL}/broker-list")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["hasData"] is True
        assert data["month"] == "2026-05-01"
        # 中信(3) > 海通(1)=国泰(1)=招商(1)
        item_zhongxin = _find_broker_item(data["items"], "中信证券")
        assert item_zhongxin["stockCount"] == 3
        # 中信应在最前
        assert data["items"][0]["broker"] == "中信证券"

    @pytest.mark.asyncio
    async def test_broker_list_stock_count_correct(
        self, auth_client, sample_broker_data
    ):
        """AC-04：stock_count = COUNT DISTINCT symbol（中信=3, 海通=1, 国泰=1, 招商=1）"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-list", params={"page_size": 20}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert _find_broker_item(items, "中信证券")["stockCount"] == 3
        assert _find_broker_item(items, "海通证券")["stockCount"] == 1
        assert _find_broker_item(items, "国泰君安")["stockCount"] == 1
        assert _find_broker_item(items, "招商证券")["stockCount"] == 1

    @pytest.mark.asyncio
    async def test_broker_list_tiebreaker_by_broker_asc(
        self, auth_client, sample_broker_data
    ):
        """AC-07：stock_count 相同按 broker ASC（海通=国泰=招商=1，
        升序应为：国泰君安 < 海通证券 < 招商证券）"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-list", params={"page_size": 20}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        # 取 stock_count=1 的券商子集，验证按 broker ASC
        one_count = [it["broker"] for it in items if it["stockCount"] == 1]
        assert one_count == sorted(one_count), (
            f"stock_count 相同应按 broker ASC，实际: {one_count}"
        )

    @pytest.mark.asyncio
    async def test_broker_list_pagination_total(
        self, auth_client, sample_broker_data
    ):
        """AC-06：total = 不同 broker 总数（4），分页生效"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-list", params={"page": 1, "page_size": 2}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 4
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["pageSize"] == 2

    @pytest.mark.asyncio
    async def test_broker_list_search(self, auth_client, sample_broker_data):
        """AC-12：search=中信 → broker ILIKE 包含命中中信证券，total=1"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-list", params={"search": "中信"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["broker"] == "中信证券"
        assert data["items"][0]["stockCount"] == 3

    @pytest.mark.asyncio
    async def test_broker_list_search_no_match(self, auth_client, sample_broker_data):
        """AC-12 边界：search 无匹配 → items=[] + total=0"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-list", params={"search": "不存在的券商"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_broker_list_requires_auth(self, client):
        """安全（§8.3）：未认证 → 401"""
        resp = await client.get(f"{BASE_URL}/broker-list")
        assert resp.status_code == 401


# ============== AC-13：GET /broker-detail ==============


class TestBrokerDetail:
    """AC-13 — 券商明细懒加载（month+broker 必填，broker 精确匹配 =，
    返回 {items:[{symbol,name,reasons}]}，同 symbol 多 reason 合并去空去重）。

    来源：plan-02 §5 AC-13、§实现规格 #1/#2/#3。
    red 预期：404 Not Found（路由 /broker-detail 未注册）。
    """

    @pytest.mark.asyncio
    async def test_broker_detail_returns_items(self, auth_client, sample_broker_data):
        """AC-13：month=2026-05-01&broker=中信证券 → 3 股（600519/000001/600000），
        按 symbol ASC"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-detail",
            params={"month": "2026-05-01", "broker": "中信证券"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        items = data["items"]
        assert len(items) == 3
        symbols = [it["symbol"] for it in items]
        assert symbols == sorted(symbols), f"应按 symbol ASC，实际: {symbols}"
        assert set(symbols) == {"600519", "000001", "600000"}
        # 每项含 name（JOIN）+ reasons
        for it in items:
            assert "name" in it
            assert "reasons" in it
            assert isinstance(it["reasons"], list)

    @pytest.mark.asyncio
    async def test_broker_detail_reasons_aggregated(
        self, auth_client, sample_broker_data
    ):
        """AC-13：同 symbol 多 reason 合并到 reasons 数组去空去重不丢弃。
        中信证券对 600519 的 reason = '业绩稳健'"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-detail",
            params={"month": "2026-05-01", "broker": "中信证券"},
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item_519 = _find_stock_item(items, "600519")
        assert item_519["name"] == "贵州茅台"
        assert "业绩稳健" in item_519["reasons"]

    @pytest.mark.asyncio
    async def test_broker_detail_broker_exact_match(
        self, auth_client, sample_broker_data
    ):
        """安全（§8.3）：broker 精确匹配 =，不做 LIKE。
        broker='中信'（仅前缀）→ 不应命中 '中信证券'，items=[]"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-detail",
            params={"month": "2026-05-01", "broker": "中信"},  # 精确匹配，不命中
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_broker_detail_empty_reasons_when_null(
        self, auth_client, sample_broker_null_reason
    ):
        """AC-13：reason 为 NULL → reasons=[]（前端 "—"），不报错。
        数据由 sample_broker_null_reason fixture 在 setup 阶段写入（避免与
        API 请求 session 并发抢占同一 asyncpg 连接）。"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-detail",
            params={"month": "2026-05-01", "broker": "中信证券"},
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item_519 = _find_stock_item(items, "600519")
        assert item_519["reasons"] == []

    @pytest.mark.asyncio
    async def test_broker_detail_month_required(self, auth_client, sample_broker_data):
        """AC-13：month 必填（Query(...)），缺省 → 422"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-detail",
            params={"broker": "中信证券"},  # 缺 month
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_broker_detail_broker_required(
        self, auth_client, sample_broker_data
    ):
        """AC-13：broker 必填（Query(...)），缺省 → 422"""
        resp = await auth_client.get(
            f"{BASE_URL}/broker-detail",
            params={"month": "2026-05-01"},  # 缺 broker
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_broker_detail_requires_auth(self, client):
        """安全（§8.3）：未认证 → 401"""
        resp = await client.get(
            f"{BASE_URL}/broker-detail",
            params={"month": "2026-05-01", "broker": "中信证券"},
        )
        assert resp.status_code == 401


# ============== AC-05/09：GET /months ==============


class TestMonths:
    """AC-05/09 — 月份列表（已同步月份降序 + has_data；空状态 has_data=false）。

    来源：plan-02 §5 月份与空状态验收、§实现规格 #1/#2/#3。
    red 预期：404 Not Found（路由 /months 未注册）。
    """

    @pytest.mark.asyncio
    async def test_months_returns_desc_with_has_data(
        self, auth_client, sample_broker_data
    ):
        """AC-05：返回已同步月份降序 [2026-05-01, 2026-04-01] + has_data=true"""
        resp = await auth_client.get(f"{BASE_URL}/months")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["hasData"] is True
        months = data["months"]
        assert months == ["2026-05-01", "2026-04-01"], (
            f"月份应降序，实际: {months}"
        )

    @pytest.mark.asyncio
    async def test_months_empty_state(self, auth_client):
        """AC-09：表无数据 → has_data=false + months=[]"""
        resp = await auth_client.get(f"{BASE_URL}/months")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hasData"] is False
        assert data["months"] == []

    @pytest.mark.asyncio
    async def test_months_requires_auth(self, client):
        """安全（§8.3）：未认证 → 401"""
        resp = await client.get(f"{BASE_URL}/months")
        assert resp.status_code == 401


# ============== AC-09：空状态（表无数据）==============


class TestEmptyState:
    """AC-09 — 表无数据时 months/stock-ranking/broker-list 返回 has_data=false。

    来源：plan-02 §5 月份与空状态验收。
    red 预期：404 Not Found（路由未注册）。
    """

    @pytest.mark.asyncio
    async def test_stock_ranking_empty_table_has_data_false(self, auth_client):
        """AC-09：表无数据 → stock-ranking has_data=false, month=null, items=[], total=0"""
        resp = await auth_client.get(f"{BASE_URL}/stock-ranking")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hasData"] is False
        assert data["month"] is None
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_broker_list_empty_table_has_data_false(self, auth_client):
        """AC-09：表无数据 → broker-list has_data=false"""
        resp = await auth_client.get(f"{BASE_URL}/broker-list")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hasData"] is False


# ============== 构建与类型：import 校验（plan-02 §验收标准「构建与类型」）==============


class TestImportable:
    """构建校验 — repository / service / router 模块可 import（plan-02 验收标准）。

    来源：plan-02 §验收标准「构建与类型」、§实现规格 #1/#2/#3。
    red 预期：ModuleNotFoundError（repository/service 模块未创建）/
              ImportError（repository 未导出 BrokerRecommendRepository）。
    """

    def test_repository_importable(self):
        """BrokerRecommendRepository 可从 src.repositories 导入"""
        from src.repositories.broker_recommend_repository import (
            BrokerRecommendRepository,
        )
        assert BrokerRecommendRepository is not None

    def test_service_importable(self):
        """BrokerRecommendAnalysisService 可从 src.services 导入"""
        from src.services.broker_recommend_analysis_service import (
            BrokerRecommendAnalysisService,
        )
        assert BrokerRecommendAnalysisService is not None

    def test_router_importable(self):
        """broker_recommend_analysis router 可从 src.api.v1 导入"""
        from src.api.v1.broker_recommend_analysis import router
        assert router is not None

    def test_repository_methods_exist(self):
        """BrokerRecommendRepository 含 4 个聚合方法（+ get_stock_brokers 预加载）"""
        from src.repositories.broker_recommend_repository import (
            BrokerRecommendRepository,
        )
        for method in (
            "get_months",
            "get_latest_month",
            "get_stock_ranking",
            "get_stock_brokers",
            "get_broker_list",
            "get_broker_detail",
            "get_distinct_symbol_count",
            "get_sector_ranking",
        ):
            assert hasattr(BrokerRecommendRepository, method), (
                f"BrokerRecommendRepository 缺方法: {method}"
            )

    def test_service_methods_exist(self):
        """BrokerRecommendAnalysisService 含查询方法"""
        from src.services.broker_recommend_analysis_service import (
            BrokerRecommendAnalysisService,
        )
        for method in (
            "get_months",
            "get_stock_ranking",
            "get_broker_list",
            "get_broker_detail",
            "get_sector_rankings",
        ):
            assert hasattr(BrokerRecommendAnalysisService, method), (
                f"BrokerRecommendAnalysisService 缺方法: {method}"
            )


# ============================================================================
# 板块排行榜测试（行业/概念/地域，各 Top5）
# ============================================================================


@pytest_asyncio.fixture
async def sample_broker_data_with_sectors(test_session, sample_broker_data):
    """
    在 sample_broker_data 基础上注入三类板块映射（用于板块排行榜测试）。

    sample_broker_data 最新月 2026-05-01 有 3 只股票：600519 / 000001 / 600000。
    板块映射（独立计数：一股多板块各计 1 次）：
      行业（industry）：
        - 600519 → 食品饮料
        - 000001 → 银行
        - 600000 → 银行
        ⇒ 银行 2、食品饮料 1
      概念（concept）：
        - 600519 → 白酒
        - 000001 → 融资融券（应被 EXCLUDED_CONCEPTS 排除）
        - 600000 → 融资融券（应被排除）
        ⇒ 白酒 1（融资融券被排除后不计）
      地域（region）：
        - 600519 → 贵州
        - 000001 → 广东
        ⇒ 贵州 1、广东 1
    """
    sectors = [
        Sector(name="食品饮料", code="IND_FOOD", type="industry"),
        Sector(name="银行", code="IND_BANK", type="industry"),
        Sector(name="白酒", code="CON_LIQ", type="concept"),
        Sector(name="融资融券", code="CON_MGN", type="concept"),
        Sector(name="贵州", code="REG_GZ", type="region"),
        Sector(name="广东", code="REG_GD", type="region"),
    ]
    test_session.add_all(sectors)
    await test_session.flush()

    sector_stocks = [
        # 行业
        SectorStock(sector_code="IND_FOOD", stock_code="600519"),
        SectorStock(sector_code="IND_BANK", stock_code="000001"),
        SectorStock(sector_code="IND_BANK", stock_code="600000"),
        # 概念（含应排除的融资融券）
        SectorStock(sector_code="CON_LIQ", stock_code="600519"),
        SectorStock(sector_code="CON_MGN", stock_code="000001"),
        SectorStock(sector_code="CON_MGN", stock_code="600000"),
        # 地域
        SectorStock(sector_code="REG_GZ", stock_code="600519"),
        SectorStock(sector_code="REG_GD", stock_code="000001"),
    ]
    test_session.add_all(sector_stocks)
    await test_session.commit()
    return {"sectors": sectors, "sector_stocks": sector_stocks}


class TestSectorRankings:
    """板块排行榜（行业/概念/地域，各 Top5）"""

    async def test_sector_rankings_three_types(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """返回 industry/concept/region 三类各 Top5"""
        resp = await auth_client.get(f"{BASE_URL}/sector-rankings")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "industry" in data
        assert "concept" in data
        assert "region" in data
        assert len(data["industry"]) <= 5
        assert len(data["concept"]) <= 5
        assert len(data["region"]) <= 5

    async def test_sector_rankings_industry_desc(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """行业维度按 stock_count 降序：银行(2) > 食品饮料(1)"""
        resp = await auth_client.get(f"{BASE_URL}/sector-rankings")
        data = resp.json()["data"]
        industry = data["industry"]
        assert len(industry) == 2
        assert industry[0]["sectorName"] == "银行"
        assert industry[0]["stockCount"] == 2
        assert industry[1]["sectorName"] == "食品饮料"
        assert industry[1]["stockCount"] == 1

    async def test_sector_rankings_concept_excluded(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """概念维度排除融资融券：只剩白酒(1)"""
        resp = await auth_client.get(f"{BASE_URL}/sector-rankings")
        data = resp.json()["data"]
        concept = data["concept"]
        assert len(concept) == 1
        assert concept[0]["sectorName"] == "白酒"
        assert concept[0]["stockCount"] == 1
        # 融资融券不应出现
        assert all(c["sectorName"] != "融资融券" for c in concept)

    async def test_sector_rankings_region(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """地域维度：贵州(1) 与广东(1)，按 stock_count 降序 + name 升序"""
        resp = await auth_client.get(f"{BASE_URL}/sector-rankings")
        data = resp.json()["data"]
        region = data["region"]
        assert len(region) == 2
        # stock_count 相同时按 name 升序：广东 < 贵州
        assert region[0]["sectorName"] == "广东"
        assert region[1]["sectorName"] == "贵州"

    async def test_sector_rankings_percentage(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """percentage = stock_count / 该月不同被推荐股票总数（3 只）"""
        resp = await auth_client.get(f"{BASE_URL}/sector-rankings")
        data = resp.json()["data"]
        bank = next(s for s in data["industry"] if s["sectorName"] == "银行")
        # 2 / 3 ≈ 66.6667
        assert abs(bank["percentage"] - round(2 / 3 * 100, 4)) < 0.01

    async def test_sector_rankings_month_fallback(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """不传 month 时取最新月（2026-05）"""
        resp = await auth_client.get(f"{BASE_URL}/sector-rankings")
        data = resp.json()["data"]
        assert data["hasData"] is True
        assert data["month"].startswith("2026-05")

    async def test_sector_rankings_empty_when_no_data(self, auth_client):
        """无金股数据时 has_data=false，三类均为空"""
        resp = await auth_client.get(f"{BASE_URL}/sector-rankings")
        data = resp.json()["data"]
        assert data["hasData"] is False
        assert data["industry"] == []
        assert data["concept"] == []
        assert data["region"] == []

    async def test_sector_rankings_requires_auth(self, client):
        """未认证返回 401"""
        resp = await client.get(f"{BASE_URL}/sector-rankings")
        assert resp.status_code == 401


@pytest_asyncio.fixture
async def sample_broker_data_with_index_concepts(test_session, sample_broker_data):
    """
    在 sample_broker_data 基础上注入指数成分概念（验证指数成分类被排除）。

    概念名称使用数据源里常见的命名变体（含"样本股""成份股"后缀），
    验证子串模糊匹配（非精确匹配）能正确排除：
      - 600519 → 白酒（保留，真实主题概念）
      - 000001 → 沪深300样本股（应排除，含"沪深300"）
      - 600000 → 中证500成份股（应排除，含"中证500"）
    """
    sectors = [
        Sector(name="白酒", code="CON_LIQ", type="concept"),
        Sector(name="沪深300样本股", code="CON_HS300", type="concept"),
        Sector(name="中证500成份股", code="CON_ZZ500", type="concept"),
    ]
    test_session.add_all(sectors)
    await test_session.flush()

    sector_stocks = [
        SectorStock(sector_code="CON_LIQ", stock_code="600519"),
        SectorStock(sector_code="CON_HS300", stock_code="000001"),
        SectorStock(sector_code="CON_ZZ500", stock_code="600000"),
    ]
    test_session.add_all(sector_stocks)
    await test_session.commit()
    return {"sectors": sectors, "sector_stocks": sector_stocks}


class TestSectorRankingsIndexExclusion:
    """概念板块排除指数成分（沪深300/中证500 等，子串模糊匹配）"""

    async def test_concept_excludes_index_constituents_by_substring(
        self, auth_client, sample_broker_data_with_index_concepts
    ):
        """指数成分类概念（含命名变体"沪深300样本股"/"中证500成份股"）
        通过子串模糊匹配被排除，只剩白酒"""
        resp = await auth_client.get(f"{BASE_URL}/sector-rankings")
        data = resp.json()["data"]
        concept = data["concept"]
        # 仅剩白酒（沪深300样本股、中证500成份股 经子串匹配被排除）
        assert len(concept) == 1
        assert concept[0]["sectorName"] == "白酒"
        names = [c["sectorName"] for c in concept]
        assert "沪深300样本股" not in names
        assert "中证500成份股" not in names


# ============================================================================
# 股票维度排行榜板块筛选测试（行业/概念/地域）
# ============================================================================


class TestStockRankingSectorFilter:
    """股票维度排行榜板块筛选（复用 sample_broker_data_with_sectors）"""

    async def test_filter_by_industry_sector(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """按行业"银行"过滤：只返回 000001/600000（归属银行），不含 600519"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking",
            params={"sector_type": "industry", "sector_name": "银行"},
        )
        data = resp.json()["data"]
        symbols = [it["symbol"] for it in data["items"]]
        assert "000001" in symbols
        assert "600000" in symbols
        assert "600519" not in symbols  # 600519 归属食品饮料，被排除
        assert data["total"] == 2

    async def test_filter_by_industry_food(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """按行业"食品饮料"过滤：只返回 600519"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking",
            params={"sector_type": "industry", "sector_name": "食品饮料"},
        )
        data = resp.json()["data"]
        symbols = [it["symbol"] for it in data["items"]]
        assert symbols == ["600519"]
        assert data["total"] == 1

    async def test_filter_by_region_sector(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """按地域"贵州"过滤：只返回 600519"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking",
            params={"sector_type": "region", "sector_name": "贵州"},
        )
        data = resp.json()["data"]
        symbols = [it["symbol"] for it in data["items"]]
        assert symbols == ["600519"]

    async def test_filter_by_concept_excludes_excluded(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """按概念"白酒"过滤：只返回 600519（融资融券被排除规则不影响显式筛选）"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking",
            params={"sector_type": "concept", "sector_name": "白酒"},
        )
        data = resp.json()["data"]
        symbols = [it["symbol"] for it in data["items"]]
        assert symbols == ["600519"]

    async def test_filter_no_match_returns_empty(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """筛选不匹配的板块名：返回空"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking",
            params={"sector_type": "industry", "sector_name": "不存在的行业"},
        )
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0

    async def test_filter_combined_with_search(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """板块筛选 + 搜索组合：银行 + 搜索"平安"→ 只剩 000001"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking",
            params={
                "sector_type": "industry",
                "sector_name": "银行",
                "search": "平安",
            },
        )
        data = resp.json()["data"]
        symbols = [it["symbol"] for it in data["items"]]
        assert symbols == ["000001"]
        assert data["total"] == 1

    async def test_filter_industries_column_follows_sector_type(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """industries 列按当前 sector_type 维度展示（选概念维度时展示概念归属）"""
        resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking",
            params={"sector_type": "concept"},
        )
        data = resp.json()["data"]
        # 600519 在概念维度归属"白酒"，industries 应含白酒而非食品饮料
        moutai = next(it for it in data["items"] if it["symbol"] == "600519")
        assert "白酒" in moutai["industries"]

    async def test_no_sector_filter_returns_all(
        self, auth_client, sample_broker_data_with_sectors
    ):
        """不传 sector_name 时返回全部（不过滤）"""
        resp = await auth_client.get(f"{BASE_URL}/stock-ranking")
        data = resp.json()["data"]
        symbols = {it["symbol"] for it in data["items"]}
        assert symbols == {"600519", "000001", "600000"}


@pytest_asyncio.fixture
async def sample_broker_data_with_constituent_suffix(test_session, sample_broker_data):
    """
    验证指数成分后缀关键字（样本股/成份股/成分股）独立匹配：
      - 600519 → 白酒（保留，真实主题）
      - 000001 → 上证180样本股（应排除，含"样本股"后缀）
      - 600000 → 中证100成份股（应排除，含"成份股"后缀）
    这些概念名不含已排除的指数名前缀（沪深300 等），仅靠后缀关键字匹配。
    """
    sectors = [
        Sector(name="白酒", code="CON_LIQ2", type="concept"),
        Sector(name="上证180样本股", code="CON_SUF1", type="concept"),
        Sector(name="中证100成份股", code="CON_SUF2", type="concept"),
        Sector(name="创业板成分股", code="CON_SUF3", type="concept"),
    ]
    test_session.add_all(sectors)
    await test_session.flush()

    sector_stocks = [
        SectorStock(sector_code="CON_LIQ2", stock_code="600519"),
        SectorStock(sector_code="CON_SUF1", stock_code="000001"),
        SectorStock(sector_code="CON_SUF2", stock_code="600000"),
        SectorStock(sector_code="CON_SUF3", stock_code="000001"),
    ]
    test_session.add_all(sector_stocks)
    await test_session.commit()
    return {"sectors": sectors, "sector_stocks": sector_stocks}


class TestSectorRankingsConstituentSuffixExclusion:
    """概念板块排除指数成分后缀（样本股/成份股/成分股，独立关键字匹配）"""

    async def test_concept_excludes_constituent_suffix(
        self, auth_client, sample_broker_data_with_constituent_suffix
    ):
        """指数成分后缀概念（上证180样本股/中证100成份股/创业板成分股）
        通过后缀关键字子串匹配被排除，只剩白酒"""
        resp = await auth_client.get(f"{BASE_URL}/sector-rankings")
        data = resp.json()["data"]
        concept = data["concept"]
        names = [c["sectorName"] for c in concept]
        # 三类成分后缀概念全部被排除
        assert "上证180样本股" not in names
        assert "中证100成份股" not in names
        assert "创业板成分股" not in names
        # 仅剩白酒（真实主题）
        assert concept == [] or all(n == "白酒" for n in names)
