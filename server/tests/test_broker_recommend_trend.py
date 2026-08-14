"""
券商荐股「推荐趋势」后端 API（plan-01 / 10 期）pytest 测试 — RED 阶段

对应 plan-01 §5 验收标准（AC-02/03/04/07/08/09/11/12）+
GET /trend-ranking 端点契约（响应包裹 {success, data} + camelCase + 无 month 参数）。

本功能为纯后端 API（无前端 UI），E2E 形态为 pytest
（参照 MEMORY「后端 FEAT E2E 适配 pytest」+ 09 期既有
test_broker_recommend_analysis_api.py 的 fixture/断言范式 +
server/tests/conftest.py 的 test_session/client fixture）。

RED 阶段原则（参照 08 期 plan-01-08-pytest-red 证据范式）：
- 测试只针对「尚未实现的真实功能」断言：
  * BrokerRecommendRepository 新增 3 方法（get_trend_aggregations /
    get_trend_cumulative_counts / get_trend_brokers）
  * BrokerRecommendAnalysisService 新增 get_trend_ranking（连续性计算 +
    多级排序 + 分页 + 行业 JOIN + 展开券商预加载）
  * GET /api/v1/broker-recommend-analysis/trend-ranking 端点
- 失败原因必须是「目标功能尚未实现」（404 路由未注册 / 方法不存在），
  而不是测试自身错误或环境错误。
- 断言强度不放宽：实现后跑同一组用例应全部通过。

09 已就绪（BrokerRecommend 模型 + broker_recommend 表 + 既有 service/repo），
故测试可直接通过 test_session INSERT 多月份 broker_recommend 测试数据，
做真实跨月聚合验证（含断档场景 AC-07）。

主测试数据 sample_trend_data：3 个已同步月份 [2026-05, 2026-04, 2026-03]，7 只股票，
刻意构造以同时覆盖多级排序的全部 4 级 tiebreak + AC-07 断档：
  600519 consec=3 (3→2→1)              consec=3, cum=3, latest=3
  600036 consec=2 (05:中信海通, 04:国泰中信)  consec=2, cum=3, latest=2   ← cum tiebreak
  000001 consec=2 (05:招商中信, 04:招商)    consec=2, cum=2, latest=2   ← latest tiebreak (win)
  600000 consec=2 (05:中信, 04:中信招商)    consec=2, cum=2, latest=1   ← latest tiebreak (lose)
  000888 consec=1 GAP(05:招商, 03:招商中信, 04 无)  consec=1, cum=2, latest=1  ← AC-07 断档
  600001 consec=1 (05:中信)               consec=1, cum=1, latest=1   ← symbol tiebreak (win)
  600002 consec=1 (05:海通)               consec=1, cum=1, latest=1   ← symbol tiebreak (lose)
预期排序：[600519, 600036, 000001, 600000, 000888, 600001, 600002]（total=7）
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


# ============== User fixtures（照搬 09 既有范式）==============


@pytest_asyncio.fixture
async def normal_user(test_session):
    """创建普通用户并写入 DB（用户侧只读 API，与 09 一致）"""
    user = User(
        email="normal_broker_trend@example.com",
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
    """构造 BrokerRecommend 记录（09 模型已就绪）"""
    from src.models.broker_recommend import BrokerRecommend

    ts_code = f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
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
async def sample_trend_data(test_session):
    """
    跨 3 个已同步月份 [2026-05, 2026-04, 2026-03]（降序）的多股趋势数据。

    构造以同时覆盖：
      - AC-02 跨月聚合 + 连续月数 + 四指标字段齐全
      - AC-03 多级排序全部 4 级 tiebreak（consec↓→cum↓→latest↓→symbol↑）
      - AC-04 latestMonthBrokerCount 与 09 股票维度同月口径一致
      - AC-07 断档股（000888：05 与 03 有推荐、04 断档）
      - AC-08 分页 total=全窗口股票数

    各股票的连续月数 / 累计家数 / 最新月家数（窗口月份序列 months DESC = [05,04,03]）：
      600519: 05(中信海通国泰=3) 04(中信海通=2) 03(中信=1)
              consec=3  cum=3  latest=3
      600036: 05(中信海通=2) 04(国泰中信=2) 03(无)
              consec=2  cum=3  latest=2
      000001: 05(招商中信=2) 04(招商=1) 03(无)
              consec=2  cum=2  latest=2
      600000: 05(中信=1) 04(中信招商=2) 03(无)
              consec=2  cum=2  latest=1
      000888: 05(招商=1) 04(无 断档) 03(招商中信=2)   ← AC-07 断档
              consec=1  cum=2  latest=1
      600001: 05(中信=1)
              consec=1  cum=1  latest=1
      600002: 05(海通=1)
              consec=1  cum=1  latest=1

    预期多级排序结果（consec↓, cum↓, latest↓, symbol↑）：
      [600519, 600036, 000001, 600000, 000888, 600001, 600002]   total=7
    """
    stocks = [
        Stock(symbol="600519", name="贵州茅台"),
        Stock(symbol="600036", name="招商银行"),
        Stock(symbol="000001", name="平安银行"),
        Stock(symbol="600000", name="浦发银行"),
        Stock(symbol="000888", name="丽珠集团"),
        Stock(symbol="600001", name="邯郸钢铁"),
        Stock(symbol="600002", name="齐鲁退市"),
    ]
    records = [
        # ---- 600519：连续 3 月（consec=3）----
        _rec("600519", "中信证券", date(2026, 5, 1), date(2026, 5, 31), reason="业绩稳健"),
        _rec("600519", "海通证券", date(2026, 5, 1), date(2026, 5, 20), reason="估值修复"),
        _rec("600519", "国泰君安", date(2026, 5, 1), date(2026, 5, 15), reason="品牌护城河"),
        _rec("600519", "中信证券", date(2026, 4, 1), date(2026, 4, 30), reason="一季报超预期"),
        _rec("600519", "海通证券", date(2026, 4, 1), date(2026, 4, 25), reason="估值修复"),
        _rec("600519", "中信证券", date(2026, 3, 1), date(2026, 3, 31), reason="年报稳健"),
        # ---- 600036：consec=2, cum=3（cumulative tiebreak 最高）----
        _rec("600036", "中信证券", date(2026, 5, 1), date(2026, 5, 30)),
        _rec("600036", "海通证券", date(2026, 5, 1), date(2026, 5, 28)),
        _rec("600036", "国泰君安", date(2026, 4, 1), date(2026, 4, 29)),
        _rec("600036", "中信证券", date(2026, 4, 1), date(2026, 4, 30)),
        # ---- 000001：consec=2, cum=2, latest=2（latest tiebreak 胜）----
        _rec("000001", "招商证券", date(2026, 5, 1), date(2026, 5, 26)),
        _rec("000001", "中信证券", date(2026, 5, 1), date(2026, 5, 31)),
        _rec("000001", "招商证券", date(2026, 4, 1), date(2026, 4, 28)),
        # ---- 600000：consec=2, cum=2, latest=1（latest tiebreak 负）----
        _rec("600000", "中信证券", date(2026, 5, 1), date(2026, 5, 31)),
        _rec("600000", "中信证券", date(2026, 4, 1), date(2026, 4, 30)),
        _rec("600000", "招商证券", date(2026, 4, 1), date(2026, 4, 27)),
        # ---- 000888：consec=1 断档（AC-07：05 与 03 有、04 断档）----
        _rec("000888", "招商证券", date(2026, 5, 1), date(2026, 5, 25)),
        _rec("000888", "招商证券", date(2026, 3, 1), date(2026, 3, 30)),
        _rec("000888", "中信证券", date(2026, 3, 1), date(2026, 3, 28)),
        # ---- 600001：consec=1, cum=1, latest=1（symbol tiebreak 胜）----
        _rec("600001", "中信证券", date(2026, 5, 1), date(2026, 5, 31)),
        # ---- 600002：consec=1, cum=1, latest=1（symbol tiebreak 负）----
        _rec("600002", "海通证券", date(2026, 5, 1), date(2026, 5, 29)),
    ]
    test_session.add_all(stocks + records)
    await test_session.commit()
    return {"stocks": stocks, "records": records}


@pytest_asyncio.fixture
async def sample_trend_data_with_industry(test_session, sample_trend_data):
    """在 sample_trend_data 基础上插入行业映射（验证 AC-02 industries 字段）：
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
    ]
    test_session.add_all(sector_stocks)
    await test_session.commit()
    return {"sectors": sectors, "sector_stocks": sector_stocks}


@pytest_asyncio.fixture
async def sample_trend_data_single_month(test_session):
    """仅 1 个已同步月份（2026-05-01），验证 AC-11 单月降级：
    所有股票 consecutiveMonths 均为 1，monthlySeries 仅一个数据点。"""
    stocks = [
        Stock(symbol="600519", name="贵州茅台"),
        Stock(symbol="000001", name="平安银行"),
    ]
    records = [
        _rec("600519", "中信证券", date(2026, 5, 1), date(2026, 5, 31)),
        _rec("600519", "海通证券", date(2026, 5, 1), date(2026, 5, 28)),
        _rec("000001", "中信证券", date(2026, 5, 1), date(2026, 5, 31)),
    ]
    test_session.add_all(stocks + records)
    await test_session.commit()
    return {"stocks": stocks, "records": records}


# ============== Helpers ==============


def _find_item(items: list, symbol: str) -> dict:
    """按 symbol 字段查找 trend-ranking item（camelCase）"""
    for it in items:
        if it.get("symbol") == symbol:
            return it
    raise AssertionError(f"未找到 symbol={symbol} 的 item，items={items}")


def _series_point(month: str, count: int) -> dict:
    """构造预期 monthlySeries 点（用于比较）"""
    return {"month": month, "brokerCount": count}


# ============== AC-02/04：跨月聚合 + 字段齐全 + 口径一致 ==============


class TestTrendRankingAggregation:
    """AC-02/04 — 跨全部已同步月份聚合；每项含四指标字段齐全；
    latestMonthBrokerCount 与 09 股票维度同月家数一致。

    red 预期：404 Not Found（路由 /trend-ranking 未注册）。
    """

    @pytest.mark.asyncio
    async def test_endpoint_exists_and_wrapper(
        self, auth_client, sample_trend_data
    ):
        """端点存在性 + 响应包裹 {success:true, data:{...}}"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        data = body["data"]
        assert data["hasData"] is True
        assert data["total"] == 7
        assert data["page"] == 1
        assert data["pageSize"] == 20  # 默认 page_size

    @pytest.mark.asyncio
    async def test_no_month_param_full_window(self, auth_client, sample_trend_data):
        """无 month 参数（趋势固定全窗口）：monthlySeries 跨全部 3 个已同步月份。
        证明趋势端点不接受 month、固定全窗口（架构 §7.3）。"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item_519 = _find_item(items, "600519")
        # monthlySeries 应覆盖全部 3 个窗口月份（旧→新升序）
        series = item_519["monthlySeries"]
        assert [p["month"] for p in series] == [
            "2026-03-01",
            "2026-04-01",
            "2026-05-01",
        ], f"monthlySeries 应为全窗口升序，实际: {series}"

    @pytest.mark.asyncio
    async def test_fields_complete_camel_case(
        self, auth_client, sample_trend_data
    ):
        """AC-02：每项含四指标字段齐全 + 输出 camelCase（无 snake_case 泄漏）。
        600519: consecutiveMonths=3, cumulativeBrokerCount=3,
        latestMonthBrokerCount=3"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item = _find_item(items, "600519")
        # 四指标 + 标识字段必须齐全（camelCase）
        for key in (
            "symbol",
            "name",
            "industries",
            "consecutiveMonths",
            "cumulativeBrokerCount",
            "latestMonthBrokerCount",
            "monthlySeries",
            "monthlyBrokers",
        ):
            assert key in item, f"缺少字段 {key}，item={item}"
        # 不应出现 snake_case 残留
        for bad_key in (
            "consecutive_months",
            "cumulative_broker_count",
            "latest_month_broker_count",
            "monthly_series",
            "monthly_brokers",
            "has_data",
            "page_size",
        ):
            assert bad_key not in resp.json()["data"], f"响应不应含 snake_case: {bad_key}"
        # 600519 数值断言
        assert item["consecutiveMonths"] == 3
        assert item["cumulativeBrokerCount"] == 3
        assert item["latestMonthBrokerCount"] == 3

    @pytest.mark.asyncio
    async def test_continuous_months_desc_top(self, auth_client, sample_trend_data):
        """AC-02：items 按 consecutiveMonths 降序；榜首 600519 连续 3 月"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert items[0]["symbol"] == "600519"
        assert items[0]["consecutiveMonths"] == 3

    @pytest.mark.asyncio
    async def test_latest_month_count_matches_stock_ranking(
        self, auth_client, sample_trend_data
    ):
        """AC-04：latestMonthBrokerCount 与 09 股票维度排行同月 broker_count 一致
        （均按券商名称 COUNT DISTINCT 去重）。
        600519 最新月 2026-05：趋势 latestMonthBrokerCount=3，
        09 stock-ranking?month=2026-05-01 同股 brokerCount=3。"""
        trend_resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert trend_resp.status_code == 200
        trend_items = trend_resp.json()["data"]["items"]

        stock_resp = await auth_client.get(
            f"{BASE_URL}/stock-ranking", params={"month": "2026-05-01", "page_size": 20}
        )
        assert stock_resp.status_code == 200
        stock_items = stock_resp.json()["data"]["items"]

        # 对窗口内每只股票，趋势 latestMonthBrokerCount 应 == 09 同月 brokerCount
        for t_item in trend_items:
            sym = t_item["symbol"]
            stock_item = _find_item(stock_items, sym)
            assert t_item["latestMonthBrokerCount"] == stock_item["brokerCount"], (
                f"{sym}: 趋势 latestMonthBrokerCount={t_item['latestMonthBrokerCount']} "
                f"!= 09 brokerCount={stock_item['brokerCount']}"
            )

    @pytest.mark.asyncio
    async def test_monthly_series_values(self, auth_client, sample_trend_data):
        """AC-02：monthlySeries 旧→新升序，含窗口内全部已同步月份（无推荐月 brokerCount=0）。
        600519: [03:1, 04:2, 05:3]"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item = _find_item(items, "600519")
        assert item["monthlySeries"] == [
            _series_point("2026-03-01", 1),
            _series_point("2026-04-01", 2),
            _series_point("2026-05-01", 3),
        ]

    @pytest.mark.asyncio
    async def test_monthly_brokers_desc_with_top3(
        self, auth_client, sample_trend_data
    ):
        """AC-06：monthlyBrokers 随列表预加载（新→旧降序），每点含 brokerCount 与 topBrokers（前 3）。
        600519 最新月 2026-05：3 家券商（中信/海通/国泰）。"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item = _find_item(items, "600519")
        brokers = item["monthlyBrokers"]
        # 新→旧降序
        assert [b["month"] for b in brokers] == [
            "2026-05-01",
            "2026-04-01",
            "2026-03-01",
        ], f"monthlyBrokers 应新→旧降序，实际: {brokers}"
        latest = brokers[0]
        assert latest["brokerCount"] == 3
        assert set(latest["topBrokers"]) == {"中信证券", "海通证券", "国泰君安"}
        # 每点 topBrokers 不超过 3
        for b in brokers:
            assert len(b["topBrokers"]) <= 3


# ============== AC-03：多级排序 ==============


class TestTrendRankingMultiLevelSort:
    """AC-03 — 多级排序：consecutiveMonths↓→cumulativeBrokerCount↓→
    latestMonthBrokerCount↓→symbol↑。

    预期完整排序：
      [600519, 600036, 000001, 600000, 000888, 600001, 600002]
    red 预期：404 Not Found（路由 /trend-ranking 未注册）。
    """

    @pytest.mark.asyncio
    async def test_full_multi_level_order(self, auth_client, sample_trend_data):
        """完整多级排序验证（覆盖全部 4 级 tiebreak）。
        600519(consec3) > 600036(consec2,cum3) > 000001(consec2,cum2,latest2)
        > 600000(consec2,cum2,latest1) > 000888(consec1,cum2) > 600001(consec1,cum1,sym)
        > 600002(consec1,cum1,sym)"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        symbols = [it["symbol"] for it in items]
        assert symbols == [
            "600519",
            "600036",
            "000001",
            "600000",
            "000888",
            "600001",
            "600002",
        ], f"多级排序不符，实际: {symbols}"

    @pytest.mark.asyncio
    async def test_cumulative_tiebreak(self, auth_client, sample_trend_data):
        """AC-03 level-2：consec 相同时按 cumulativeBrokerCount 降序。
        600036(consec2,cum3) 应排在 000001(consec2,cum2) 之前。"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        symbols = [it["symbol"] for it in items]
        assert symbols.index("600036") < symbols.index("000001")
        assert _find_item(items, "600036")["cumulativeBrokerCount"] == 3
        assert _find_item(items, "000001")["cumulativeBrokerCount"] == 2

    @pytest.mark.asyncio
    async def test_latest_month_count_tiebreak(self, auth_client, sample_trend_data):
        """AC-03 level-3：consec 与 cum 均相同时按 latestMonthBrokerCount 降序。
        000001(consec2,cum2,latest2) 应排在 600000(consec2,cum2,latest1) 之前。"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        symbols = [it["symbol"] for it in items]
        assert symbols.index("000001") < symbols.index("600000")
        assert _find_item(items, "000001")["latestMonthBrokerCount"] == 2
        assert _find_item(items, "600000")["latestMonthBrokerCount"] == 1

    @pytest.mark.asyncio
    async def test_symbol_tiebreak_asc(self, auth_client, sample_trend_data):
        """AC-03 level-4：consec/cum/latest 全相同时按 symbol 升序。
        600001 与 600002 三指标全同，600001 应排在 600002 之前。"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        symbols = [it["symbol"] for it in items]
        assert symbols.index("600001") < symbols.index("600002")
        a = _find_item(items, "600001")
        b = _find_item(items, "600002")
        assert (a["consecutiveMonths"], a["cumulativeBrokerCount"], a["latestMonthBrokerCount"]) == (
            b["consecutiveMonths"],
            b["cumulativeBrokerCount"],
            b["latestMonthBrokerCount"],
        )


# ============== AC-07：断档股 ==============


class TestTrendRankingGap:
    """AC-07 — 连续月数从最新已同步月份向前不间断计数，遇断档即停；
    断档前的更早月份仍参与 cumulativeBrokerCount 与 monthlySeries。

    000888：2026-05(招商=1)、2026-04(无 断档)、2026-03(招商中信=2)
      → consecutiveMonths=1（05 有、04 断档即停）
      → cumulativeBrokerCount=2（含 03 月招商+中信，断档前月份仍计入）
      → monthlySeries=[03:2, 04:0, 05:1]（断档月 04 brokerCount=0 仍出现）
    red 预期：404 Not Found（路由 /trend-ranking 未注册）。
    """

    @pytest.mark.asyncio
    async def test_gap_stock_consecutive_stops_at_gap(
        self, auth_client, sample_trend_data
    ):
        """AC-07：断档股连续月数从最新月向前断档即停（consec=1，不是 2）"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item = _find_item(items, "000888")
        assert item["consecutiveMonths"] == 1, (
            f"断档股连续月数应为 1（05 有/04 断档即停），实际: {item['consecutiveMonths']}"
        )

    @pytest.mark.asyncio
    async def test_gap_stock_cumulative_includes_pre_gap_months(
        self, auth_client, sample_trend_data
    ):
        """AC-07：断档前的更早月份仍参与 cumulativeBrokerCount（000888 cum=2，含 03 月）"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item = _find_item(items, "000888")
        assert item["cumulativeBrokerCount"] == 2, (
            f"断档股累计家数应含断档前月份（招商+中信=2），实际: {item['cumulativeBrokerCount']}"
        )

    @pytest.mark.asyncio
    async def test_gap_stock_monthly_series_includes_gap_month_zero(
        self, auth_client, sample_trend_data
    ):
        """AC-07：monthlySeries 含断档月（04 brokerCount=0）与断档前月份（03 brokerCount=2）"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item = _find_item(items, "000888")
        assert item["monthlySeries"] == [
            _series_point("2026-03-01", 2),
            _series_point("2026-04-01", 0),
            _series_point("2026-05-01", 1),
        ], f"断档股走势序列应含断档月 0 值，实际: {item['monthlySeries']}"


# ============== AC-08：分页 ==============


class TestTrendRankingPagination:
    """AC-08 — total = 全窗口+搜索条件下的股票总数（非当前页条数）；
    page/page_size 分页生效。

    red 预期：404 Not Found（路由 /trend-ranking 未注册）。
    """

    @pytest.mark.asyncio
    async def test_pagination_total_is_full_window(
        self, auth_client, sample_trend_data
    ):
        """AC-08：page_size=2 → 当前页 2 条，但 total=7（全窗口股票数）"""
        resp = await auth_client.get(
            f"{BASE_URL}/trend-ranking", params={"page": 1, "page_size": 2}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 7
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["pageSize"] == 2

    @pytest.mark.asyncio
    async def test_pagination_second_page(self, auth_client, sample_trend_data):
        """AC-08：page=2&page_size=2 → 第 2 页 2 条，total 仍为 7"""
        resp = await auth_client.get(
            f"{BASE_URL}/trend-ranking", params={"page": 2, "page_size": 2}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 7
        assert len(data["items"]) == 2
        assert data["page"] == 2

    @pytest.mark.asyncio
    async def test_pagination_last_page_partial(self, auth_client, sample_trend_data):
        """AC-08：page=4&page_size=2 → 末页 1 条（7 = 2*3 + 1），total=7"""
        resp = await auth_client.get(
            f"{BASE_URL}/trend-ranking", params={"page": 4, "page_size": 2}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 7
        assert len(data["items"]) == 1


# ============== AC-09：搜索（服务端全量重查）==============


class TestTrendRankingSearch:
    """AC-09 — search 服务端全量重查（symbol LIKE 前缀 OR name ILIKE 包含）；
    无匹配 items=[] + total=0。

    red 预期：404 Not Found（路由 /trend-ranking 未注册）。
    """

    @pytest.mark.asyncio
    async def test_search_by_symbol_prefix(self, auth_client, sample_trend_data):
        """AC-09：search=600 → symbol LIKE 前缀命中 600519/600036/600000/600001/600002，total=5"""
        resp = await auth_client.get(
            f"{BASE_URL}/trend-ranking", params={"search": "600"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5
        symbols = {it["symbol"] for it in data["items"]}
        assert symbols == {"600519", "600036", "600000", "600001", "600002"}

    @pytest.mark.asyncio
    async def test_search_by_name_contains(self, auth_client, sample_trend_data):
        """AC-09：search=茅台 → name ILIKE 包含命中 600519（贵州茅台），total=1"""
        resp = await auth_client.get(
            f"{BASE_URL}/trend-ranking", params={"search": "茅台"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["symbol"] == "600519"
        assert data["items"][0]["name"] == "贵州茅台"

    @pytest.mark.asyncio
    async def test_search_no_match_returns_empty(self, auth_client, sample_trend_data):
        """AC-09：search 无匹配 → items=[] + total=0（服务端全量重查，非前端过滤）"""
        resp = await auth_client.get(
            f"{BASE_URL}/trend-ranking", params={"search": "不存在的股票"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_search_escapes_like_wildcards(
        self, auth_client, sample_trend_data
    ):
        """安全（§8.3）：search=% → 不匹配全表（LIKE 通配符转义），total=0"""
        resp = await auth_client.get(
            f"{BASE_URL}/trend-ranking", params={"search": "%"}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_search_keeps_multi_level_order(
        self, auth_client, sample_trend_data
    ):
        """AC-09：搜索结果仍按多级排序（search=600 → 命中 5 只，应保持 consec↓ 排序）"""
        resp = await auth_client.get(
            f"{BASE_URL}/trend-ranking", params={"search": "600"}
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        symbols = [it["symbol"] for it in items]
        # 600 系命中：600519(consec3) 600036(consec2,cum3) 600000(consec2,cum2,latest1) 600001 600002
        assert symbols == ["600519", "600036", "600000", "600001", "600002"], (
            f"搜索结果多级排序不符，实际: {symbols}"
        )


# ============== AC-11：单月数据降级 ==============


class TestTrendRankingSingleMonth:
    """AC-11 — 仅一个已同步月份时正常返回，consecutiveMonths 均为 1，
    monthlySeries 仅一个数据点，落入次级排序。

    red 预期：404 Not Found（路由 /trend-ranking 未注册）。
    """

    @pytest.mark.asyncio
    async def test_single_month_consecutive_all_one(
        self, auth_client, sample_trend_data_single_month
    ):
        """AC-11：单月数据 → 所有股票 consecutiveMonths 均为 1"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hasData"] is True
        for it in data["items"]:
            assert it["consecutiveMonths"] == 1, (
                f"单月数据连续月数应为 1，{it['symbol']} 实际: {it['consecutiveMonths']}"
            )

    @pytest.mark.asyncio
    async def test_single_month_series_single_point(
        self, auth_client, sample_trend_data_single_month
    ):
        """AC-11：单月数据 → monthlySeries 仅一个数据点（最新月=该月）"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        item = _find_item(items, "600519")
        assert item["monthlySeries"] == [_series_point("2026-05-01", 2)]
        assert item["latestMonthBrokerCount"] == 2

    @pytest.mark.asyncio
    async def test_single_month_latest_equals_cumulative(
        self, auth_client, sample_trend_data_single_month
    ):
        """AC-11：单月数据 → latestMonthBrokerCount == cumulativeBrokerCount（仅 1 月）"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        for it in items:
            assert it["latestMonthBrokerCount"] == it["cumulativeBrokerCount"]


# ============== AC-12：空状态 ==============


class TestTrendRankingEmptyState:
    """AC-12 — broker_recommend 表无数据时 hasData=false（前端整页空状态，复用 09）。

    red 预期：404 Not Found（路由 /trend-ranking 未注册）。
    """

    @pytest.mark.asyncio
    async def test_empty_table_has_data_false(self, auth_client):
        """AC-12：表无数据 → hasData=false, items=[], total=0"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["hasData"] is False
        assert data["items"] == []
        assert data["total"] == 0


# ============== 行业 JOIN（AC-02 industries 字段）==============


class TestTrendRankingIndustry:
    """AC-02 — industries 字段经行业 JOIN 展示（600519→食品饮料，000001→[]）。"""

    @pytest.mark.asyncio
    async def test_industries_joined(self, auth_client, sample_trend_data_with_industry):
        """600519→['食品饮料']，000001→[]（无映射）"""
        resp = await auth_client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert _find_item(items, "600519")["industries"] == ["食品饮料"]
        assert _find_item(items, "000001")["industries"] == []


# ============== 构建校验：新方法存在性（red 信号：AttributeError）==============


class TestTrendImportable:
    """构建校验 — repository 新增 3 方法 + service 新增 get_trend_ranking。

    来源：plan-01 §3 实现规格（#1 #2 #4）、§Task 列表。
    red 预期：AssertionError（新方法尚未实现 → hasattr 返回 False）。
    """

    def test_repository_trend_methods_exist(self):
        """BrokerRecommendRepository 含 3 个新增跨月聚合方法"""
        from src.repositories.broker_recommend_repository import (
            BrokerRecommendRepository,
        )

        for method in (
            "get_trend_aggregations",
            "get_trend_cumulative_counts",
            "get_trend_brokers",
        ):
            assert hasattr(BrokerRecommendRepository, method), (
                f"BrokerRecommendRepository 缺趋势方法: {method}"
            )

    def test_service_trend_method_exists(self):
        """BrokerRecommendAnalysisService 含 get_trend_ranking"""
        from src.services.broker_recommend_analysis_service import (
            BrokerRecommendAnalysisService,
        )

        assert hasattr(
            BrokerRecommendAnalysisService, "get_trend_ranking"
        ), "BrokerRecommendAnalysisService 缺方法 get_trend_ranking"


# ============== 安全：未认证 401 ==============


class TestTrendRankingAuth:
    """安全（§8.3）— 未认证访问 GET /trend-ranking 应返回 401。

    red 预期：404 Not Found（路由 /trend-ranking 未注册，FastAPI 优先返回 404
    而非触发认证依赖；实现后应返回 401）。
    """

    @pytest.mark.asyncio
    async def test_trend_ranking_requires_auth(self, client):
        """未认证 → 401（实现后）/ 404（red 阶段路由未注册）"""
        resp = await client.get(f"{BASE_URL}/trend-ranking")
        assert resp.status_code == 401
