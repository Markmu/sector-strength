"""tests/api/admin 子目录 autouse 鉴权覆盖（plan-05）。

父目录 ``tests/api/conftest.py`` 的同名 autouse fixture 假设 ``main.app`` 仅被一层
中间件包裹；当前 ``main.app`` 为 ``ResponseLoggingMiddleware`` → ``ProcessTimeMiddleware``
→ FastAPI app（双层），其 ``app.app if hasattr(app, "app") else app`` 取到
``ProcessTimeMiddleware``（无 ``dependency_overrides``）导致 setup 报错。本子目录以
同名 fixture ``api_auth_override`` 覆盖（pytest 取最近 conftest），按 ``.app`` 链
解包到真正持 ``dependency_overrides`` 的 FastAPI 实例后再注入 admin。
"""

import pytest

from main import app
from src.api.deps import get_current_user
from src.models.user import User


def _unwrap_fastapi(app_obj):
    """沿 ``.app`` 链解包到持 ``dependency_overrides`` 的 FastAPI 实例。"""
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
    """覆盖父目录同名 fixture：注入 admin 用户使 require_admin 通过。"""
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
