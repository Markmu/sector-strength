"""
股东监控组管理 Admin API 集成测试（plan-01）

对应 plan-01 §5 验收标准与 §3 实现规格，覆盖 5 个端点：
- GET    /api/v1/admin/shareholder-groups            列表（含预定义 5 组 + camelCase 字段）
- GET    /api/v1/admin/shareholder-groups/{id}       单条详情（编辑页按 id 独立加载）
- POST   /api/v1/admin/shareholder-groups            新增分组（AC-06，重复 name 返回 400/409）
- PATCH  /api/v1/admin/shareholder-groups/{id}       编辑分组关键词（AC-07）
- DELETE /api/v1/admin/shareholder-groups/{id}       删除分组（AC-10，不存在返回 404）
- GET    /api/v1/admin/shareholder-groups/preview    预览匹配股数

权限要求：normal_client 访问应被拒（401/403），未认证应返回 401。

注意（red 阶段原则）：
- 测试只通过 HTTP client 调用 API 端点，不 import 尚未实现的业务模块。
- red 阶段失败原因应为「端点尚未实现 → 404」，而非 ImportError / 测试代码错误。
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from main import app
from src.models.user import User
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


# ============== User fixtures（参照 test_fund_admin_api.py）==============


@pytest_asyncio.fixture
async def admin_user(test_session):
    """创建管理员用户"""
    user = User(
        email="admin_shareholder@example.com",
        password_hash="hash",
        role="admin",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def normal_user(test_session):
    """创建普通用户"""
    user = User(
        email="user_shareholder@example.com",
        password_hash="hash",
        role="user",
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_client(client: AsyncClient, test_session, admin_user):
    """注入管理员认证 + override get_session"""
    from src.db import database as db_module

    test_session_factory = db_module.AsyncSessionLocal

    async def _override_get_session():
        async with test_session_factory() as s:
            yield s

    async def _override_current_user():
        return admin_user

    _fastapi_app.dependency_overrides[get_session] = _override_get_session
    _fastapi_app.dependency_overrides[get_current_user] = _override_current_user
    yield client
    _fastapi_app.dependency_overrides.pop(get_session, None)
    _fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def normal_client(client: AsyncClient, test_session, normal_user):
    """注入普通用户认证 + override get_session"""
    from src.db import database as db_module

    test_session_factory = db_module.AsyncSessionLocal

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


# ============== Test: GET /api/v1/admin/shareholder-groups（列表）==============


class TestListShareholderGroups:
    """分组列表端点 — plan-01 §5「预览与列表验收」"""

    @pytest.mark.asyncio
    async def test_list_returns_predefined_groups(self, admin_client):
        """列表返回 5 个预定义分组（国家队/外资投行/社保基金/保险公司/私募基金）"""
        resp = await admin_client.get("/api/v1/admin/shareholder-groups")
        assert resp.status_code == 200

        body = resp.json()
        # 兼容 ApiResponse 包装 / 裸 list 两种返回形态
        items = body.get("data", body) if isinstance(body, dict) else body
        assert isinstance(items, list)
        assert len(items) >= 5

        names = {item["name"] for item in items}
        expected = {"国家队", "外资投行", "社保基金", "保险公司", "私募基金"}
        assert expected.issubset(names), f"缺少预定义分组: {expected - names}"

    @pytest.mark.asyncio
    async def test_list_item_camel_case_fields(self, admin_client):
        """GroupListItem 字段使用 camelCase：isSystem / ruleCount / matchedStockCount / keywords"""
        resp = await admin_client.get("/api/v1/admin/shareholder-groups")
        assert resp.status_code == 200

        body = resp.json()
        items = body.get("data", body) if isinstance(body, dict) else body
        first = items[0]

        # camelCase 字段必须存在
        assert "isSystem" in first
        assert "ruleCount" in first
        assert "matchedStockCount" in first
        assert "keywords" in first
        assert isinstance(first["keywords"], list)
        # snake_case 不应泄漏
        assert "is_system" not in first
        assert "rule_count" not in first
        assert "matched_stock_count" not in first

    @pytest.mark.asyncio
    async def test_list_requires_admin(self, normal_client):
        """普通用户访问返回 401/403"""
        resp = await normal_client.get("/api/v1/admin/shareholder-groups")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client):
        """未认证访问返回 401"""
        resp = await client.get("/api/v1/admin/shareholder-groups")
        assert resp.status_code == 401


# ============== Test: GET /api/v1/admin/shareholder-groups/{id}（单条详情）==============


class TestGetShareholderGroup:
    """单条详情端点 — 详情页 / 编辑页按 id 独立加载"""

    @pytest.mark.asyncio
    async def test_get_group_returns_detail(self, admin_client):
        """返回单个分组详情（camelCase 字段 + keywords + ruleCount）"""
        resp = await admin_client.get("/api/v1/admin/shareholder-groups/1")
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        # 国家队为预定义组（id=1）
        assert data["id"] == 1
        assert data["name"] == "国家队"
        # camelCase 字段
        assert "isSystem" in data
        assert "ruleCount" in data
        assert "matchedStockCount" in data
        assert "keywords" in data
        assert isinstance(data["keywords"], list)
        assert data["ruleCount"] == len(data["keywords"])
        # snake_case 不应泄漏
        assert "is_system" not in data
        assert "rule_count" not in data
        assert "matched_stock_count" not in data

    @pytest.mark.asyncio
    async def test_get_group_nonexistent_returns_404(self, admin_client):
        """不存在的分组 id 返回 404"""
        resp = await admin_client.get("/api/v1/admin/shareholder-groups/999999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_group_requires_admin(self, normal_client):
        """普通用户访问返回 401/403"""
        resp = await normal_client.get("/api/v1/admin/shareholder-groups/1")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_get_group_requires_auth(self, client):
        """未认证访问返回 401"""
        resp = await client.get("/api/v1/admin/shareholder-groups/1")
        assert resp.status_code == 401


# ============== Test: POST /api/v1/admin/shareholder-groups（新增，AC-06）==============


class TestCreateShareholderGroup:
    """新增分组端点 — plan-01 §5 AC-06"""

    @pytest.mark.asyncio
    async def test_create_group_success(self, admin_client):
        """管理员新增分组成功 — AC-06"""
        resp = await admin_client.post(
            "/api/v1/admin/shareholder-groups",
            json={
                "name": "QFII",
                "keywords": ["瑞士银行", "摩根大通"],
            },
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        # 新分组应能在列表中查到
        list_resp = await admin_client.get("/api/v1/admin/shareholder-groups")
        assert list_resp.status_code == 200
        list_body = list_resp.json()
        items = (
            list_body.get("data", list_body)
            if isinstance(list_body, dict)
            else list_body
        )
        names = {item["name"] for item in items}
        assert "QFII" in names

    @pytest.mark.asyncio
    async def test_create_group_duplicate_name_rejected(self, admin_client):
        """name 重复时返回 400/409 — plan-01 §5 AC-06 / §8 边界场景"""
        resp = await admin_client.post(
            "/api/v1/admin/shareholder-groups",
            json={"name": "国家队", "keywords": ["汇金"]},  # 国家队为预定义组
        )
        assert resp.status_code in (400, 409)

    @pytest.mark.asyncio
    async def test_create_group_requires_admin(self, normal_client):
        """普通用户创建返回 401/403"""
        resp = await normal_client.post(
            "/api/v1/admin/shareholder-groups",
            json={"name": "Foo", "keywords": []},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_group_requires_auth(self, client):
        """未认证创建返回 401"""
        resp = await client.post(
            "/api/v1/admin/shareholder-groups",
            json={"name": "Foo", "keywords": []},
        )
        assert resp.status_code == 401


# ============== Test: PATCH /api/v1/admin/shareholder-groups/{id}（编辑，AC-07）==============


class TestUpdateShareholderGroup:
    """编辑分组端点 — plan-01 §5 AC-07"""

    @pytest.mark.asyncio
    async def test_update_group_keywords_success(self, admin_client):
        """管理员编辑匹配关键词成功 — AC-07

        编辑 id=1（国家队）的关键词后，列表中该组 keywords 应更新。
        """
        new_keywords = ["中央汇金", "中国证券金融", "国新投资"]
        resp = await admin_client.patch(
            "/api/v1/admin/shareholder-groups/1",
            json={"keywords": new_keywords},
        )
        assert resp.status_code == 200

        # UC-010 回归：update 响应体本身应返回更新后的 keywords（非 identity map 缓存旧值）
        update_body = resp.json()
        update_data = (
            update_body.get("data", update_body)
            if isinstance(update_body, dict)
            else update_body
        )
        assert set(update_data["keywords"]) == set(new_keywords), (
            "update 响应应返回更新后的 keywords，而非缓存旧值"
        )

        # 列表中确认规则已更新
        list_resp = await admin_client.get("/api/v1/admin/shareholder-groups")
        assert list_resp.status_code == 200
        list_body = list_resp.json()
        items = (
            list_body.get("data", list_body)
            if isinstance(list_body, dict)
            else list_body
        )
        target = next((it for it in items if it["id"] == 1), None)
        assert target is not None
        assert set(target["keywords"]) == set(new_keywords)

    @pytest.mark.asyncio
    async def test_update_group_requires_admin(self, normal_client):
        """普通用户编辑返回 401/403"""
        resp = await normal_client.patch(
            "/api/v1/admin/shareholder-groups/1",
            json={"keywords": ["x"]},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_update_group_requires_auth(self, client):
        """未认证编辑返回 401"""
        resp = await client.patch(
            "/api/v1/admin/shareholder-groups/1",
            json={"keywords": ["x"]},
        )
        assert resp.status_code == 401


# ============== Test: DELETE /api/v1/admin/shareholder-groups/{id}（删除，AC-10）==============


class TestDeleteShareholderGroup:
    """删除分组端点 — plan-01 §5 AC-10"""

    @pytest.mark.asyncio
    async def test_delete_group_success(self, admin_client):
        """删除分组成功 — AC-10

        先创建一个临时分组，再删除它，列表中应不再出现。
        """
        # 创建临时分组
        create_resp = await admin_client.post(
            "/api/v1/admin/shareholder-groups",
            json={"name": "ToDelete", "keywords": ["k1"]},
        )
        assert create_resp.status_code == 200
        create_body = create_resp.json()
        created = (
            create_body.get("data", create_body)
            if isinstance(create_body, dict)
            else create_body
        )
        group_id = created["id"]

        # 删除
        del_resp = await admin_client.delete(
            f"/api/v1/admin/shareholder-groups/{group_id}"
        )
        assert del_resp.status_code == 200

        # 列表中确认不再出现
        list_resp = await admin_client.get("/api/v1/admin/shareholder-groups")
        assert list_resp.status_code == 200
        list_body = list_resp.json()
        items = (
            list_body.get("data", list_body)
            if isinstance(list_body, dict)
            else list_body
        )
        ids = {item["id"] for item in items}
        assert group_id not in ids

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, admin_client):
        """删除不存在的分组返回 404 — plan-01 §8 边界场景"""
        resp = await admin_client.delete("/api/v1/admin/shareholder-groups/999999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_group_requires_admin(self, normal_client):
        """普通用户删除返回 401/403"""
        resp = await normal_client.delete("/api/v1/admin/shareholder-groups/1")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_delete_group_requires_auth(self, client):
        """未认证删除返回 401"""
        resp = await client.delete("/api/v1/admin/shareholder-groups/1")
        assert resp.status_code == 401


# ============== Test: GET /api/v1/admin/shareholder-groups/preview（预览）==============


class TestPreviewShareholderGroups:
    """预览匹配股数端点 — plan-01 §5「预览与列表验收」"""

    @pytest.mark.asyncio
    async def test_preview_returns_matched_count(self, admin_client):
        """preview 返回 matched_stock_count（数值字段，无数据时为 0）"""
        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/preview",
            params={"keywords": "中央汇金,社保"},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        # 字段名应为 camelCase
        assert "matchedStockCount" in data
        assert isinstance(data["matchedStockCount"], int)
        assert "matched_stock_count" not in data  # snake_case 不应泄漏

    @pytest.mark.asyncio
    async def test_preview_requires_admin(self, normal_client):
        """普通用户访问预览返回 401/403"""
        resp = await normal_client.get(
            "/api/v1/admin/shareholder-groups/preview",
            params={"keywords": "中央汇金"},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_preview_requires_auth(self, client):
        """未认证访问预览返回 401"""
        resp = await client.get(
            "/api/v1/admin/shareholder-groups/preview",
            params={"keywords": "中央汇金"},
        )
        assert resp.status_code == 401


# ============== 07-plan-01 测试数据 fixture（preview-breakdown + keyword-matches）==============


@pytest_asyncio.fixture
async def sample_holders(test_session):
    """插入测试 top10_float_holders 数据：覆盖单关键词多股、同股票多股东、跨报告期。

    覆盖场景：
    - 报告期 2024-06-30（最新期）：
        600000 × 全国社保基金一一六组合
        600000 × 全国社保基金一零四组合（同股票多股东）
        600036 × 全国社保基金一零八组合
        000001 × 社保基金理事会（ stocks 表缺失 → stockName=null ）
    - 报告期 2024-03-31（旧期，验证只取最新期）：
        600000 × 全国社保基金一二三组合（旧期，应被过滤）
    """
    from datetime import date

    from src.models.stock import Stock
    from src.models.top10_float_holder import Top10FloatHolder

    rows = [
        # 报告期 2024-06-30（最新期）
        Top10FloatHolder(
            symbol="600000",
            ts_code="600000.SH",
            report_period=date(2024, 6, 30),
            holder_name="全国社保基金一一六组合",
            ann_date=date(2024, 7, 1),
        ),
        Top10FloatHolder(
            symbol="600000",
            ts_code="600000.SH",
            report_period=date(2024, 6, 30),
            holder_name="全国社保基金一零四组合",
            ann_date=date(2024, 7, 1),
        ),
        Top10FloatHolder(
            symbol="600036",
            ts_code="600036.SH",
            report_period=date(2024, 6, 30),
            holder_name="全国社保基金一零八组合",
            ann_date=date(2024, 7, 1),
        ),
        Top10FloatHolder(
            symbol="000001",
            ts_code="000001.SZ",
            report_period=date(2024, 6, 30),
            holder_name="社保基金理事会",
            ann_date=date(2024, 7, 1),
        ),
        # 旧报告期 2024-03-31（验证只取最新期）
        Top10FloatHolder(
            symbol="600000",
            ts_code="600000.SH",
            report_period=date(2024, 3, 31),
            holder_name="全国社保基金一二三组合（旧期）",
            ann_date=date(2024, 4, 1),
        ),
    ]
    test_session.add_all(rows)

    # stocks 表插入股票名称（000001 故意不插入，测试 stockName=null 兜底）
    stocks = [
        Stock(symbol="600000", name="浦发银行"),
        Stock(symbol="600036", name="招商银行"),
    ]
    test_session.add_all(stocks)
    await test_session.commit()
    return rows


@pytest_asyncio.fixture
async def sample_holders_ordered(test_session):
    """插入可验证排序的测试数据。

    使用 symbol 600001/600000/600036 三只股票 + 不同股东名，验证 ORDER BY symbol ASC。
    """
    from datetime import date

    from src.models.stock import Stock
    from src.models.top10_float_holder import Top10FloatHolder

    rows = [
        Top10FloatHolder(
            symbol="600036",
            ts_code="600036.SH",
            report_period=date(2024, 6, 30),
            holder_name="全国社保基金甲组合",
            ann_date=date(2024, 7, 1),
        ),
        Top10FloatHolder(
            symbol="600000",
            ts_code="600000.SH",
            report_period=date(2024, 6, 30),
            holder_name="全国社保基金乙组合",
            ann_date=date(2024, 7, 1),
        ),
        Top10FloatHolder(
            symbol="600001",
            ts_code="600001.SH",
            report_period=date(2024, 6, 30),
            holder_name="全国社保基金丙组合",
            ann_date=date(2024, 7, 1),
        ),
    ]
    test_session.add_all(rows)

    stocks = [
        Stock(symbol="600000", name="浦发银行"),
        Stock(symbol="600001", name="邯郸钢铁"),
        Stock(symbol="600036", name="招商银行"),
    ]
    test_session.add_all(stocks)
    await test_session.commit()
    return rows


# ============== Test: GET /preview-breakdown（逐关键词股数，AC-01/07）==============


class TestPreviewBreakdownShareholderGroups:
    """逐关键词股数细分端点 — 07 plan-01 §5 AC-01 / AC-07

    端点路径：`GET /api/v1/admin/shareholder-groups/preview-breakdown`
    """

    @pytest.mark.asyncio
    async def test_preview_breakdown_returns_per_keyword_count(
        self, admin_client, sample_holders
    ):
        """AC-01：每个非空关键词返回单独匹配的去重股票数

        全国社保 → 2 只（600000 + 600036，600000 多股东去重为 1）
        社保基金 → 3 只（600000 + 600036 + 000001）
        """
        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/preview-breakdown",
            params={"keywords": "全国社保,社保基金"},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        assert isinstance(data, dict)
        assert "items" in data
        items = data["items"]
        assert len(items) == 2

        # 每项必须含 keyword + matchedStockCount 字段（camelCase）
        for item in items:
            assert "keyword" in item
            assert "matchedStockCount" in item
            assert "matched_stock_count" not in item  # snake_case 不应泄漏
            assert isinstance(item["matchedStockCount"], int)

        count_by_kw = {item["keyword"]: item["matchedStockCount"] for item in items}
        assert count_by_kw["全国社保"] == 2, count_by_kw
        assert count_by_kw["社保基金"] == 3, count_by_kw

    @pytest.mark.asyncio
    async def test_preview_breakdown_empty_keywords_returns_empty(self, admin_client):
        """AC-01 边界：keywords 全为空 → items=[]"""
        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/preview-breakdown",
            params={"keywords": ",,,"},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_preview_breakdown_partial_failure_returns_null_for_failed_keyword(
        self, admin_client, sample_holders, monkeypatch
    ):
        """AC-07 后端语义：单个关键词查询失败 → 该 item matchedStockCount=null，其他正常

        通过 monkeypatch 让 service 在第一次调用 _count_matched_stocks_single 时抛异常，
        验证降级返回 null 且不阻塞其他关键词。

        注意：方法尚未实现时（red 阶段）跳过 monkeypatch，让端点直接 405/404 失败，
        避免因 AttributeError 干扰 red 信号。
        """
        from src.services.shareholder_group_service import ShareholderGroupService

        if hasattr(ShareholderGroupService, "_count_matched_stocks_single"):
            original = ShareholderGroupService._count_matched_stocks_single
            call_count = {"n": 0}

            async def _flaky(self, keyword, period):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise RuntimeError("mock db error for first keyword")
                return await original(self, keyword, period)

            monkeypatch.setattr(
                ShareholderGroupService, "_count_matched_stocks_single", _flaky
            )

        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/preview-breakdown",
            params={"keywords": "全国社保,社保基金"},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        items = data["items"]
        assert len(items) == 2

        # 第一个关键词应降级为 null；第二个关键词应有正常计数
        null_items = [it for it in items if it["matchedStockCount"] is None]
        valid_items = [it for it in items if it["matchedStockCount"] is not None]
        assert len(null_items) == 1, items
        assert len(valid_items) == 1, items

    @pytest.mark.asyncio
    async def test_preview_breakdown_requires_admin(
        self, normal_client, sample_holders
    ):
        """权限回归：normal_client → 401/403"""
        resp = await normal_client.get(
            "/api/v1/admin/shareholder-groups/preview-breakdown",
            params={"keywords": "全国社保"},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_preview_breakdown_requires_auth(self, client):
        """权限回归：未认证 → 401"""
        resp = await client.get(
            "/api/v1/admin/shareholder-groups/preview-breakdown",
            params={"keywords": "全国社保"},
        )
        assert resp.status_code == 401


# ============== Test: GET /keyword-matches（明细下钻，AC-03/04/05）==============


class TestKeywordMatchesShareholderGroups:
    """明细下钻端点 — 07 plan-01 §5 AC-03 / AC-04 / AC-05 / 边界 / 安全

    端点路径：`GET /api/v1/admin/shareholder-groups/keyword-matches`
    """

    @pytest.mark.asyncio
    async def test_keyword_matches_returns_three_columns(
        self, admin_client, sample_holders
    ):
        """AC-03：明细每行含 symbol + stockName + holderName 三字段；total 与列表行数一致"""
        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/keyword-matches",
            params={"keyword": "全国社保", "page": 1, "page_size": 20},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        assert isinstance(data, dict)
        for key in ("items", "total", "page", "pageSize"):
            assert key in data, f"missing field {key}: {data}"

        items = data["items"]
        assert data["total"] == len(items) == 3, items

        for item in items:
            assert "symbol" in item
            assert "stockName" in item  # camelCase
            assert "holderName" in item  # camelCase
            # snake_case 不应泄漏
            assert "stock_name" not in item
            assert "holder_name" not in item

    @pytest.mark.asyncio
    async def test_keyword_matches_same_stock_multi_holders_split_rows(
        self, admin_client, sample_holders
    ):
        """AC-04：同股票多股东 → 多行（600000 出现 2 行，holderName 不同）"""
        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/keyword-matches",
            params={"keyword": "全国社保", "page": 1, "page_size": 20},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        items = data["items"]

        rows_600000 = [it for it in items if it["symbol"] == "600000"]
        assert len(rows_600000) == 2, items
        holder_names = {it["holderName"] for it in rows_600000}
        assert holder_names == {"全国社保基金一一六组合", "全国社保基金一零四组合"}

    @pytest.mark.asyncio
    async def test_keyword_matches_ordered_by_symbol_then_holder(
        self, admin_client, sample_holders_ordered
    ):
        """AC-05：返回 items 按 symbol 升序；同 symbol 的多行相邻"""
        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/keyword-matches",
            params={"keyword": "全国社保", "page": 1, "page_size": 20},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        items = data["items"]
        symbols = [it["symbol"] for it in items]
        # 字符串升序：600000 < 600001 < 600036
        assert symbols == sorted(symbols), symbols

    @pytest.mark.asyncio
    async def test_keyword_matches_stock_name_null_when_stocks_table_missing(
        self, admin_client, sample_holders
    ):
        """AC-03 边界：stocks 表缺失某 symbol → 该行 stockName=null（兜底）"""
        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/keyword-matches",
            params={"keyword": "社保基金", "page": 1, "page_size": 20},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        items = data["items"]

        row_000001 = next((it for it in items if it["symbol"] == "000001"), None)
        assert row_000001 is not None, items
        assert row_000001["stockName"] is None

    @pytest.mark.asyncio
    async def test_keyword_matches_pagination(
        self, admin_client, sample_holders
    ):
        """AC-03 边界：分页正确

        keyword=社保基金 按 (symbol, holder_name) 粒度 DISTINCT ON 后共 4 行
        （600000 × 一一六 + 600000 × 一零四 + 600036 × 一零八 + 000001 × 理事会），
        与 AC-04 "同股票多股东按分行展示" 一致 —— total 按"明细行数"口径，
        非"去重 symbol 数"。page_size=2 时 page1 → 2 行，page2 → 2 行。
        """
        # 第 1 页（page_size=2）
        resp1 = await admin_client.get(
            "/api/v1/admin/shareholder-groups/keyword-matches",
            params={"keyword": "社保基金", "page": 1, "page_size": 2},
        )
        assert resp1.status_code == 200
        data1 = resp1.json().get("data", resp1.json())
        assert len(data1["items"]) == 2
        assert data1["total"] == 4
        assert data1["page"] == 1
        assert data1["pageSize"] == 2

        # 第 2 页
        resp2 = await admin_client.get(
            "/api/v1/admin/shareholder-groups/keyword-matches",
            params={"keyword": "社保基金", "page": 2, "page_size": 2},
        )
        assert resp2.status_code == 200
        data2 = resp2.json().get("data", resp2.json())
        assert len(data2["items"]) == 2
        assert data2["total"] == 4

    @pytest.mark.asyncio
    async def test_keyword_matches_only_latest_report_period(
        self, admin_client, sample_holders
    ):
        """隐含约束：仅查最新报告期，旧期数据（2024-03-31）不出现在结果中"""
        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/keyword-matches",
            params={"keyword": "社保基金", "page": 1, "page_size": 20},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        items = data["items"]

        # 旧期独有 holder「全国社保基金一二三组合（旧期）」不应出现
        for item in items:
            assert "（旧期）" not in item["holderName"], item

    @pytest.mark.asyncio
    async def test_keyword_matches_escapes_like_wildcards(
        self, admin_client, sample_holders
    ):
        """安全回归（架构 §8.3）：keyword=% 不会匹配全表

        % 经 _escape_like_keyword 转义后只匹配字面 %，正常测试数据中无字面 %，
        故应返回空列表 + total=0。
        """
        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/keyword-matches",
            params={"keyword": "%", "page": 1, "page_size": 20},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        assert data["total"] == 0, data
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_keyword_matches_requires_admin(
        self, normal_client, sample_holders
    ):
        """权限回归：normal_client → 401/403"""
        resp = await normal_client.get(
            "/api/v1/admin/shareholder-groups/keyword-matches",
            params={"keyword": "全国社保"},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_keyword_matches_requires_auth(self, client):
        """权限回归：未认证 → 401"""
        resp = await client.get(
            "/api/v1/admin/shareholder-groups/keyword-matches",
            params={"keyword": "全国社保"},
        )
        assert resp.status_code == 401


# ============== Test: 现有 preview 端点回归（AC-02）==============


class TestExistingPreviewRegression:
    """现有 preview 端点回归 — 07 plan-01 §5 AC-02

    现有 `GET /preview` 行为必须保持不变（合并总数）。
    """

    @pytest.mark.asyncio
    async def test_existing_preview_endpoint_still_works(
        self, admin_client, sample_holders
    ):
        """AC-02：现有 preview 端点返回合并总数，与改造前一致"""
        resp = await admin_client.get(
            "/api/v1/admin/shareholder-groups/preview",
            params={"keywords": "全国社保,社保基金"},
        )
        assert resp.status_code == 200

        body = resp.json()
        data = body.get("data", body) if isinstance(body, dict) else body
        # 字段名应为 camelCase
        assert "matchedStockCount" in data
        # 全国社保 + 社保基金 合并去重：600000 + 600036 + 000001 = 3
        assert data["matchedStockCount"] == 3, data
