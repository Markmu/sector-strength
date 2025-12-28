import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import app
from src.models.database import async_session
from src.models.user import User
from src.core.auth_service import AuthService
from src.core.config import settings


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
async def db_session():
    """创建测试数据库会话"""
    async with async_session() as session:
        yield session


@pytest.fixture
async def test_user(db_session):
    """创建测试用户"""
    # 清理可能存在的测试用户
    existing_user = await db_session.execute(
        "SELECT id FROM users WHERE email = 'test@example.com'"
    )
    if existing_user.fetchone():
        await db_session.execute(
            "DELETE FROM refresh_tokens WHERE user_id = (SELECT id FROM users WHERE email = 'test@example.com')"
        )
        await db_session.execute(
            "DELETE FROM users WHERE email = 'test@example.com'"
        )

    # 创建新用户
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'hashed_password': AuthService.hash_password('TestPassword123!'),
        'full_name': 'Test User',
        'is_active': True
    }
    user = User(**user_data)

    # 添加到数据库
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def locked_test_user(db_session):
    """创建被锁定的测试用户"""
    # 清理可能存在的测试用户
    existing_user = await db_session.execute(
        "SELECT id FROM users WHERE email = 'locked@example.com'"
    )
    if existing_user.fetchone():
        await db_session.execute(
            "DELETE FROM refresh_tokens WHERE user_id = (SELECT id FROM users WHERE email = 'locked@example.com')"
        )
        await db_session.execute(
            "DELETE FROM users WHERE email = 'locked@example.com'"
        )

    # 创建新用户并锁定
    user_data = {
        'username': 'lockeduser',
        'email': 'locked@example.com',
        'hashed_password': AuthService.hash_password('TestPassword123!'),
        'full_name': 'Locked User',
        'is_active': False  # 账户被锁定
    }
    user = User(**user_data)

    # 添加到数据库
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


class TestAuthAPI:
    """认证API测试"""

    def test_login_success(self, client, test_user):
        """测试成功登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "test@example.com"

    def test_login_wrong_password(self, client, test_user):
        """测试密码错误"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword",
                "remember_me": False
            }
        )

        assert response.status_code == 401
        assert "邮箱或密码错误" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """测试不存在的用户"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "AnyPassword123!",
                "remember_me": False
            }
        )

        assert response.status_code == 401
        assert "邮箱或密码错误" in response.json()["detail"]

    def test_login_locked_account(self, client, locked_test_user):
        """测试被锁定的账户"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "locked@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
        )

        assert response.status_code == 403
        assert "账户已被锁定，请联系管理员" in response.json()["detail"]

    def test_login_invalid_email(self, client):
        """测试无效的邮箱格式"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "invalid-email",
                "password": "TestPassword123!",
                "remember_me": False
            }
        )

        assert response.status_code == 422

    def test_login_missing_fields(self, client):
        """测试缺少必填字段"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com"
                # 缺少 password 字段
            }
        )

        assert response.status_code == 422

    def test_get_current_user(self, client, test_user):
        """测试获取当前用户信息"""
        # 先登录获取token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
        )
        token = login_response.json()["access_token"]

        # 使用token获取当前用户
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"

    def test_get_current_user_unauthorized(self, client):
        """测试未授权获取当前用户"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """测试无效token获取当前用户"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_refresh_token_success(self, client, test_user):
        """测试成功刷新token"""
        # 先登录获取refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "remember_me": True  # 启用remember_me以获得更长的refresh token
            }
        )
        refresh_token = login_response.json()["refresh_token"]

        # 使用refresh token获取新token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_invalid(self, client):
        """测试无效的refresh token"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )
        assert response.status_code == 401

    def test_logout(self, client, test_user):
        """测试注销"""
        # 先登录获取token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
        )
        access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # 注销
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        assert response.json()["message"] == "注销成功"

        # 验证token已失效
        user_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert user_response.status_code == 401

    def test_logout_without_refresh_token(self, client, test_user):
        """测试不带refresh token注销"""
        # 先登录获取token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
        )
        access_token = login_response.json()["access_token"]

        # 不带refresh token注销
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 422  # 缺少refresh_token字段

    def test_logout_invalid_token(self, client):
        """测试无效token注销"""
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "invalid_token"},
            headers={"Authorization": "Bearer invalid_access_token"}
        )
        assert response.status_code == 401


class TestAuthService:
    """认证服务测试"""

    @pytest.mark.asyncio
    async def test_hash_password(self):
        """测试密码哈希"""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        # 哈希后的密码应该与原密码不同
        assert hashed != password
        assert hashed.startswith('$5$')  # sha256_crypt格式

    @pytest.mark.asyncio
    async def test_verify_password(self):
        """测试密码验证"""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        # 正确密码
        assert AuthService.verify_password(password, hashed) is True

        # 错误密码
        assert AuthService.verify_password("WrongPassword", hashed) is False

    @pytest.mark.asyncio
    async def test_generate_tokens(self):
        """测试生成token"""
        user_id = "test-user-id"
        email = "test@example.com"

        access_token, refresh_token, expires_in = AuthService.generate_tokens(user_id, email)

        # 验证token格式
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert isinstance(expires_in, int)
        assert len(access_token) > 0
        assert len(refresh_token) > 0
        assert expires_in > 0

        # 访问token应该较短（因为不包含payload）
        assert len(access_token) < len(refresh_token)

    @pytest.mark.asyncio
    async def test_validate_access_token(self):
        """验证访问token"""
        user_id = "test-user-id"
        email = "test@example.com"

        access_token, _, _ = AuthService.generate_tokens(user_id, email)
        payload = AuthService.validate_access_token(access_token)

        assert payload["user_id"] == user_id
        assert payload["email"] == email
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_validate_invalid_access_token(self):
        """验证无效访问token"""
        with pytest.raises(Exception):
            AuthService.validate_access_token("invalid_token")

    @pytest.mark.asyncio
    async def test_validate_refresh_token(self):
        """验证refresh token"""
        user_id = "test-user-id"
        email = "test@example.com"

        _, refresh_token, _ = AuthService.generate_tokens(user_id, email)
        payload = AuthService.validate_refresh_token(refresh_token)

        assert payload["user_id"] == user_id
        assert payload["email"] == email
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_validate_invalid_refresh_token(self):
        """验证无效refresh token"""
        with pytest.raises(Exception):
            AuthService.validate_refresh_token("invalid_token")


if __name__ == "__main__":
    pytest.main(["-v", "tests/test_auth.py"])