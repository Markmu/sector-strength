"""测试认证中间件"""

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI, HTTPException
from httpx import AsyncClient, ASGITransport
from jose import jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.core.auth import AuthService
from src.core.auth_middleware import (
    get_current_user,
    require_authenticated,
    require_role,
    require_permission,
    get_current_user_optional
)
from src.core.settings import settings


auth_service = AuthService()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """创建测试用户"""
    user = User(
        email="test@example.com",
        password_hash=auth_service.get_password_hash("testpassword"),
        role="user",
        permissions=["read", "write"],
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """创建管理员测试用户"""
    admin = User(
        email="admin@example.com",
        password_hash=auth_service.get_password_hash("adminpassword"),
        role="admin",
        permissions=["read", "write", "delete", "manage_users"],
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


def _make_app(db_session: AsyncSession) -> FastAPI:
    """创建测试 FastAPI 应用，覆盖 get_db 依赖"""
    from src.core.database import get_db
    from src.db.database import AsyncSessionLocal

    app = FastAPI()

    async def override_get_db():
        # 使用 conftest 已 patch 的 AsyncSessionLocal 创建新 session（同一 engine/schema，当前 event loop）
        session = AsyncSessionLocal()
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/protected")
    async def protected_route(user: User = Depends(require_authenticated())):
        return {"message": f"Hello, {user.email}!"}

    @app.get("/admin-only")
    async def admin_only(user: User = Depends(require_role("admin"))):
        return {"message": f"Admin access granted to {user.email}"}

    @app.get("/user-only")
    async def user_only(user: User = Depends(require_role("user"))):
        return {"message": f"User access granted to {user.email}"}

    @app.get("/delete-permission")
    async def delete_permission(user: User = Depends(require_permission("delete"))):
        return {"message": f"Delete permission granted to {user.email}"}

    @app.get("/optional-auth")
    async def optional_auth(user: User = Depends(get_current_user_optional)):
        if user:
            return {"message": f"Hello, {user.email}!"}
        return {"message": "Hello, anonymous user!"}

    return app


def _make_token(user: User) -> str:
    """创建访问令牌"""
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "permissions": user.permissions
    }
    return auth_service.create_access_token(token_data)


def _make_expired_token(user: User) -> str:
    """创建过期令牌"""
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "permissions": user.permissions
    }
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    to_encode = token_data.copy()
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


class TestGetCurrentUser:
    """测试get_current_user函数"""

    @pytest.mark.asyncio
    async def test_valid_token(self, db_session, test_user):
        """使用有效令牌应成功"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = _make_token(test_user)
            response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert "test@example.com" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_no_token(self, db_session):
        """没有令牌应返回403"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/protected")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_token(self, db_session):
        """无效令牌应返回401"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/protected", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    @pytest.mark.asyncio
    async def test_expired_token(self, db_session, test_user):
        """过期令牌应返回401"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = _make_expired_token(test_user)
            response = await client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_type(self, db_session, test_user):
        """使用刷新令牌类型应返回401"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_data = {
                "sub": str(test_user.id),
                "email": test_user.email,
                "role": test_user.role,
                "permissions": test_user.permissions
            }
            refresh_token = auth_service.create_refresh_token(token_data)
            response = await client.get("/protected", headers={"Authorization": f"Bearer {refresh_token}"})
        assert response.status_code == 401
        assert "Invalid token type" in response.json()["detail"]


class TestRequireRole:
    """测试require_role装饰器"""

    @pytest.mark.asyncio
    async def test_admin_role_success(self, db_session, admin_user):
        """管理员访问admin-only端点应成功"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = _make_token(admin_user)
            response = await client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert "admin" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_user_role_failure(self, db_session, test_user):
        """普通用户访问admin-only端点应失败"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = _make_token(test_user)
            response = await client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        assert "Insufficient privileges" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_user_role_success(self, db_session, test_user):
        """普通用户访问user-only端点应成功"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = _make_token(test_user)
            response = await client.get("/user-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert "User access granted" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_admin_role_failure_for_user_endpoint(self, db_session, admin_user):
        """管理员访问user-only端点应失败（角色精确匹配，admin != user）"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = _make_token(admin_user)
            response = await client.get("/user-only", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403


class TestRequirePermission:
    """测试require_permission装饰器"""

    @pytest.mark.asyncio
    async def test_has_permission(self, db_session, admin_user):
        """具有权限的用户应成功"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = _make_token(admin_user)
            response = await client.get("/delete-permission", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert "Delete permission granted" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_no_permission(self, db_session, test_user):
        """没有权限的用户应失败"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = _make_token(test_user)
            response = await client.get("/delete-permission", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        assert "Insufficient privileges" in response.json()["detail"]
        assert "delete" in response.json()["detail"]


class TestGetCurrentUserOptional:
    """测试get_current_user_optional函数"""

    @pytest.mark.asyncio
    async def test_with_valid_token(self, db_session, test_user):
        """提供有效令牌应返回用户信息"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = _make_token(test_user)
            response = await client.get("/optional-auth", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert "test@example.com" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_without_token(self, db_session):
        """不提供令牌应返回匿名用户信息"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/optional-auth")
        assert response.status_code == 200
        assert "anonymous user" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_with_invalid_token(self, db_session):
        """提供无效令牌应返回匿名用户信息"""
        app = _make_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/optional-auth", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 200
        assert "anonymous user" in response.json()["message"]
