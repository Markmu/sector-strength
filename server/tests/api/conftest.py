import pytest

from main import app
from src.api.deps import get_current_user
from src.models.user import User


@pytest.fixture(autouse=True)
def api_auth_override():
    """Keep API auth dependencies unchanged; override only for tests/api."""
    fastapi_app = app.app if hasattr(app, "app") else app

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
