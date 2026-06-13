"""
股东监控组管理 Admin API 集成测试（plan-01）

对应 plan-01 §5 验收标准与 §3 实现规格，覆盖 5 个端点：
- GET    /api/v1/admin/shareholder-groups            列表（含预定义 5 组 + camelCase 字段）
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

# app 被 ProcessTimeMiddleware 包装，需要获取底层 FastAPI 实例
_fastapi_app = app.app if hasattr(app, "app") else app


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
