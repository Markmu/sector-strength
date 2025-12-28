"""测试认证中间件"""

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from src.models.user import User
from src.core.auth import AuthService
from src.core.auth_middleware import (
    get_current_user,
    require_authenticated,
    require_role,
    require_permission,
    get_current_user_optional
)
from src.core.database import get_db
from src.core.settings import settings


# 创建测试FastAPI应用
app = FastAPI()
auth_service = AuthService()


@app.get("/protected")
async def protected_route(user: User = Depends(require_authenticated())):
    """需要认证的端点"""
    return {"message": f"Hello, {user.email}!"}


@app.get("/admin-only")
async def admin_only(user: User = Depends(require_role("admin"))):
    """需要管理员角色的端点"""
    return {"message": f"Admin access granted to {user.email}"}


@app.get("/user-only")
async def user_only(user: User = Depends(require_role("user"))):
    """需要普通用户角色的端点"""
    return {"message": f"User access granted to {user.email}"}


@app.get("/delete-permission")
async def delete_permission(user: User = Depends(require_permission("delete"))):
    """需要delete权限的端点"""
    return {"message": f"Delete permission granted to {user.email}"}


@app.get("/optional-auth")
async def optional_auth(user: User = Depends(get_current_user_optional)):
    """可选认证的端点"""
    if user:
        return {"message": f"Hello, {user.email}!"}
    return {"message": "Hello, anonymous user!"}


client = TestClient(app)


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """创建测试用户"""
    user = User(
        email="test@example.com",
        password_hash=auth_service.get_password_hash("testpassword"),
        role="user",
        permissions=["read", "write"]
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """创建管理员测试用户"""
    admin = User(
        email="admin@example.com",
        password_hash=auth_service.get_password_hash("adminpassword"),
        role="admin",
        permissions=["read", "write", "delete", "manage_users"]
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def valid_token(test_user):
    """创建有效的访问令牌"""
    token_data = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "role": test_user.role,
        "permissions": test_user.permissions
    }
    return auth_service.create_access_token(token_data)


@pytest.fixture
def admin_token(admin_user):
    """创建管理员访问令牌"""
    token_data = {
        "sub": str(admin_user.id),
        "email": admin_user.email,
        "role": admin_user.role,
        "permissions": admin_user.permissions
    }
    return auth_service.create_access_token(token_data)


@pytest.fixture
def expired_token(test_user):
    """创建过期的访问令牌"""
    token_data = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "role": test_user.role,
        "permissions": test_user.permissions
    }
    # 创建已过期的令牌
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    to_encode = token_data.copy()
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


class TestGetCurrentUser:
    """测试get_current_user函数"""

    def test_valid_token(self, client, valid_token):
        """使用有效令牌应成功"""
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        assert "test@example.com" in response.json()["message"]

    def test_no_token(self, client):
        """没有令牌应返回401"""
        response = client.get("/protected")
        assert response.status_code == 403  # FastAPI HTTPBearer返回403而不是401

    def test_invalid_token(self, client):
        """无效令牌应返回401"""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    def test_expired_token(self, client, expired_token):
        """过期令牌应返回401"""
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

    def test_refresh_token_type(self, client, test_user):
        """使用刷新令牌类型应返回401"""
        # 创建刷新令牌而非访问令牌
        token_data = {
            "sub": str(test_user.id),
            "email": test_user.email,
            "role": test_user.role,
            "permissions": test_user.permissions
        }
        refresh_token = auth_service.create_refresh_token(token_data)

        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )
        assert response.status_code == 401
        assert "Invalid token type" in response.json()["detail"]


class TestRequireRole:
    """测试require_role装饰器"""

    def test_admin_role_success(self, client, admin_token):
        """管理员访问admin-only端点应成功"""
        response = client.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert "admin" in response.json()["message"]

    def test_user_role_failure(self, client, valid_token):
        """普通用户访问admin-only端点应失败"""
        response = client.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 403
        assert "Insufficient privileges" in response.json()["detail"]

    def test_user_role_success(self, client, valid_token):
        """普通用户访问user-only端点应成功"""
        response = client.get(
            "/user-only",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        assert "User access granted" in response.json()["message"]

    def test_admin_role_success_for_user_endpoint(self, client, admin_token):
        """管理员访问user-only端点也应成功（admin > user）"""
        response = client.get(
            "/user-only",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert "User access granted" in response.json()["message"]


class TestRequirePermission:
    """测试require_permission装饰器"""

    def test_has_permission(self, client, admin_token):
        """具有权限的用户应成功"""
        response = client.get(
            "/delete-permission",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert "Delete permission granted" in response.json()["message"]

    def test_no_permission(self, client, valid_token):
        """没有权限的用户应失败"""
        response = client.get(
            "/delete-permission",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 403
        assert "Insufficient privileges" in response.json()["detail"]
        assert "delete" in response.json()["detail"]


class TestGetCurrentUserOptional:
    """测试get_current_user_optional函数"""

    def test_with_valid_token(self, client, valid_token):
        """提供有效令牌应返回用户信息"""
        response = client.get(
            "/optional-auth",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        assert "test@example.com" in response.json()["message"]

    def test_without_token(self, client):
        """不提供令牌应返回匿名用户信息"""
        response = client.get("/optional-auth")
        assert response.status_code == 200
        assert "anonymous user" in response.json()["message"]

    def test_with_invalid_token(self, client):
        """提供无效令牌应返回匿名用户信息"""
        response = client.get(
            "/optional-auth",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 200
        assert "anonymous user" in response.json()["message"]
