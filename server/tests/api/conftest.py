import pytest

from main import app
from src.api.deps import get_current_user
from src.models.user import User


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


@pytest.fixture(autouse=True)
def api_auth_override():
    """Keep API auth dependencies unchanged; override only for tests/api."""
    fastapi_app = _unwrap_fastapi(app)

    async def _mock_current_user():
        return User(
            email="api-test@example.com",
            password_hash="test-hash",
            username="api_test_user",
            is_active=True,
            is_verified=True,
            role="admin",
            permissions=["read", "write", "admin"],
        )

    fastapi_app.dependency_overrides[get_current_user] = _mock_current_user
    yield
    fastapi_app.dependency_overrides.pop(get_current_user, None)
