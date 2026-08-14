"""
基金管理 API 集成测试

覆盖端点：
- POST /api/v1/admin/init/funds — 触发基金基本信息同步
- POST /api/v1/admin/init/fund-portfolio — 触发持仓同步
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
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


# ============== User fixtures ==============


@pytest_asyncio.fixture
async def admin_user(test_session):
    """创建管理员用户"""
    user = User(
        email="admin_fund@example.com",
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
        email="user_fund@example.com",
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


# ============== Mock fixture for TaskManager ==============


@pytest_asyncio.fixture
def mock_task_manager():
    """Mock TaskManager 类，避免真正触发同步。

    init_funds.py 中 TaskManager 是延迟导入（函数内部 import），
    所以 patch src.services.task_manager.TaskManager 类本身，
    让 TaskManager(session) 返回 mock 实例。
    """
    mock_task = MagicMock()
    mock_task.task_id = "task_test12345678"

    mock_instance = MagicMock()
    mock_instance.create_task = AsyncMock(return_value=mock_task)

    with patch("src.services.task_manager.TaskManager", return_value=mock_instance):
        yield mock_instance


# ============== Concurrent task fixtures ==============


@pytest_asyncio.fixture
async def running_fund_basic_task(test_session):
    """预置一个 pending 状态的 SYNC_FUND_BASIC 任务"""
    from src.models.async_task import AsyncTask
    from src.services.task_handlers import TaskType

    task = AsyncTask(
        task_id="task_existing001",
        task_type=TaskType.SYNC_FUND_BASIC.value,
        status="pending",
    )
    test_session.add(task)
    await test_session.commit()
    yield task


@pytest_asyncio.fixture
async def running_fund_portfolio_task(test_session):
    """预置一个 running 状态的 SYNC_FUND_PORTFOLIO 任务"""
    from src.models.async_task import AsyncTask
    from src.services.task_handlers import TaskType

    task = AsyncTask(
        task_id="task_existing002",
        task_type=TaskType.SYNC_FUND_PORTFOLIO.value,
        status="running",
    )
    test_session.add(task)
    await test_session.commit()
    yield task


# ============== Test: POST /api/v1/admin/init/funds ==============


class TestInitFundBasic:
    """基金基本信息同步端点测试"""

    @pytest.mark.asyncio
    async def test_init_fund_basic_success(
        self, admin_client, admin_user, mock_task_manager
    ):
        """管理员触发基金基本信息同步 — 返回 task_id"""
        resp = await admin_client.post("/api/v1/admin/init/funds")
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        assert body["data"]["task_id"] == "task_test12345678"

        # 验证 create_task 被调用
        mock_task_manager.create_task.assert_called_once()
        call_kwargs = mock_task_manager.create_task.call_args[1]
        assert call_kwargs["task_type"] == "sync_fund_basic"
        assert call_kwargs["created_by"] == admin_user.id

    @pytest.mark.asyncio
    async def test_init_fund_basic_requires_admin(self, normal_client):
        """非管理员返回 403"""
        resp = await normal_client.post("/api/v1/admin/init/funds")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_init_fund_basic_requires_auth(self, client):
        """未认证返回 401"""
        resp = await client.post("/api/v1/admin/init/funds")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_init_fund_basic_concurrent_protection(
        self, admin_client, admin_user, running_fund_basic_task
    ):
        """已有 running 任务时返回友好提示"""
        resp = await admin_client.post("/api/v1/admin/init/funds")
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is False
        assert "已有" in body["message"] or "正在运行" in body["message"]


# ============== Test: POST /api/v1/admin/init/fund-portfolio ==============


class TestInitFundPortfolio:
    """基金持仓同步端点测试"""

    @pytest.mark.asyncio
    async def test_init_fund_portfolio_success(
        self, admin_client, admin_user, mock_task_manager
    ):
        """管理员触发持仓同步 — 返回 task_id"""
        resp = await admin_client.post(
            "/api/v1/admin/init/fund-portfolio",
            json={"period": "20241231"},
        )
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is True
        assert body["data"]["task_id"] == "task_test12345678"

        # 验证 create_task 被调用
        mock_task_manager.create_task.assert_called_once()
        call_kwargs = mock_task_manager.create_task.call_args[1]
        assert call_kwargs["task_type"] == "sync_fund_portfolio"
        assert call_kwargs["params"] == {"period": "20241231"}
        assert call_kwargs["created_by"] == admin_user.id

    @pytest.mark.asyncio
    async def test_init_fund_portfolio_period_validation(
        self, admin_client
    ):
        """period 格式校验 — 非 8 位数字返回 422"""
        invalid_periods = [
            "2024123",    # 7 位
            "202412311",  # 9 位
            "2024ABCD",   # 含字母
            "2024-12-31", # 含横线
            "",           # 空字符串
        ]
        for period in invalid_periods:
            resp = await admin_client.post(
                "/api/v1/admin/init/fund-portfolio",
                json={"period": period},
            )
            assert resp.status_code == 422, f"Expected 422 for period={period!r}"

    @pytest.mark.asyncio
    async def test_init_fund_portfolio_valid_periods(
        self, admin_client, admin_user, mock_task_manager
    ):
        """合法 period 格式通过校验"""
        valid_periods = ["20241231", "20240930", "20230630"]
        for period in valid_periods:
            resp = await admin_client.post(
                "/api/v1/admin/init/fund-portfolio",
                json={"period": period},
            )
            assert resp.status_code == 200, f"Expected 200 for period={period!r}"

    @pytest.mark.asyncio
    async def test_init_fund_portfolio_requires_admin(
        self, normal_client
    ):
        """非管理员返回 403"""
        resp = await normal_client.post(
            "/api/v1/admin/init/fund-portfolio",
            json={"period": "20241231"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_init_fund_portfolio_requires_auth(self, client):
        """未认证返回 401"""
        resp = await client.post(
            "/api/v1/admin/init/fund-portfolio",
            json={"period": "20241231"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_init_fund_portfolio_concurrent_protection(
        self, admin_client, admin_user, running_fund_portfolio_task
    ):
        """已有 running 任务时返回友好提示"""
        resp = await admin_client.post(
            "/api/v1/admin/init/fund-portfolio",
            json={"period": "20241231"},
        )
        assert resp.status_code == 200

        body = resp.json()
        assert body["success"] is False
        assert "已有" in body["message"] or "正在运行" in body["message"]

    @pytest.mark.asyncio
    async def test_init_fund_portfolio_missing_body(
        self, admin_client
    ):
        """缺少 body 返回 422"""
        resp = await admin_client.post("/api/v1/admin/init/fund-portfolio")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_init_fund_portfolio_missing_period_field(
        self, admin_client
    ):
        """body 中缺少 period 字段返回 422"""
        resp = await admin_client.post(
            "/api/v1/admin/init/fund-portfolio",
            json={},
        )
        assert resp.status_code == 422
