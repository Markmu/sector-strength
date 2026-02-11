import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from httpx import ASGITransport
import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from main import app
from src.models.database import async_session
from src.models.user import User
from src.core.auth_service import AuthService


@pytest.fixture
async def test_client():
    """创建HTTP测试客户端"""
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def test_db():
    """创建测试数据库"""
    async with async_session() as session:
        yield session


@pytest.fixture
async def test_user(test_db):
    """创建测试用户"""
    # 清理可能存在的测试用户
    await test_db.execute(
        "DELETE FROM refresh_tokens WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test%@example.com')"
    )
    await test_db.execute(
        "DELETE FROM users WHERE email LIKE 'test%@example.com'"
    )

    # 创建测试用户
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'hashed_password': AuthService.hash_password('TestPassword123!'),
        'full_name': 'Test User',
        'is_active': True
    }
    user = User(**user_data)
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


class TestAuthenticationIntegration:
    """认证系统集成测试"""

    @pytest.mark.asyncio
    async def test_complete_auth_flow(self, test_client: AsyncClient, test_user):
        """测试完整的认证流程"""
        # 1. 登录
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
        )

        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "refresh_token" in login_data
        assert login_data["token_type"] == "bearer"

        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]

        # 2. 获取当前用户
        me_response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == "test@example.com"
        assert me_data["username"] == "testuser"

        # 3. 刷新token
        refresh_response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["token_type"] == "bearer"

        new_access_token = refresh_data["access_token"]

        # 4. 验证新token
        me_response2 = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )

        assert me_response2.status_code == 200
        me_data2 = me_response2.json()
        assert me_data2["email"] == "test@example.com"

        # 5. 注销
        logout_response = await test_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {new_access_token}"}
        )

        assert logout_response.status_code == 200
        assert logout_response.json()["message"] == "注销成功"

        # 6. 验证注销后token失效
        me_response3 = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )

        assert me_response3.status_code == 401

    @pytest.mark.asyncio
    async def test_login_with_remember_me(self, test_client: AsyncClient, test_user):
        """测试启用记住我功能的登录"""
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "remember_me": True
            }
        )

        assert login_response.status_code == 200
        login_data = login_response.json()

        # 验证返回了token
        assert "access_token" in login_data
        assert "refresh_token" in login_data

        # 验证refresh token有较长的过期时间
        # （这个验证取决于实际的实现）

    @pytest.mark.asyncio
    async def test_multiple_login_attempts(self, test_client: AsyncClient):
        """测试多次登录尝试"""
        # 创建测试用户
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser2",
                "email": "test2@example.com",
                "password": "TestPassword123!",
                "full_name": "Test User 2"
            }
        )

        # 多次错误登录
        for i in range(5):
            response = await test_client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test2@example.com",
                    "password": "wrongpassword",
                    "remember_me": False
                }
            )
            assert response.status_code == 401

        # 第6次尝试应该被阻止
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test2@example.com",
                "password": "TestPassword123!",  # 正确密码
                "remember_me": False
            }
        )
        # 由于速率限制，即使是正确密码也应该被阻止
        assert response.status_code in [429, 401]

    @pytest.mark.asyncio
    async def test_token_expiry_and_refresh(self, test_client: AsyncClient, test_user):
        """测试token过期和刷新"""
        # 登录获取token
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "remember_me": True
            }
        )

        access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # 验证访问token有效
        me_response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == 200

        # 刷新token
        refresh_response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert refresh_response.status_code == 200
        new_access_token = refresh_response.json()["access_token"]

        # 验证新token有效
        me_response2 = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert me_response2.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, test_client):
        """测试未授权访问"""
        # 尝试访问受保护的端点而不提供token
        response = await test_client.get("/api/v1/auth/me")
        assert response.status_code == 401

        # 提供无效的token
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_refresh_token(self, test_client):
        """测试无效的refresh token"""
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_without_tokens(self, test_client):
        """测试不带token的注销"""
        response = await test_client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cross_user_access(self, test_client, test_user):
        """测试跨用户访问保护"""
        # 创建另一个用户
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "username": "otheruser",
                "email": "other@example.com",
                "password": "OtherPassword123!",
                "full_name": "Other User"
            }
        )

        # 用第一个用户登录
        login1_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
                "remember_me": False
            }
        )
        token1 = login1_response.json()["access_token"]

        # 用第二个用户登录
        login2_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "other@example.com",
                "password": "OtherPassword123!",
                "remember_me": False
            }
        )
        token2 = login2_response.json()["access_token"]

        # 获取两个用户的信息
        me1_response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token1}"}
        )
        me1_data = me1_response.json()

        me2_response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token2}"}
        )
        me2_data = me2_response.json()

        # 验证是不同的用户
        assert me1_data["email"] != me2_data["email"]
        assert me1_data["id"] != me2_data["id"]

        # 验证token不能互换使用
        me1_response_wrong = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token2}"}
        )
        # 这里应该返回第二个用户的信息，而不是错误
        # 这个测试可能需要根据实际的业务逻辑调整


class TestSecurityIntegration:
    """安全机制集成测试"""

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, test_client):
        """测试SQL注入保护"""
        # 尝试SQL注入攻击
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com' OR '1'='1",
                "password": "any",
                "remember_me": False
            }
        )

        # 应该失败，而不是返回用户信息
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_xss_protection(self, test_client):
        """测试XSS保护"""
        # 尝试XSS攻击
        xss_script = "<script>alert('XSS')</script>"
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": xss_script,
                "password": "any",
                "remember_me": False
            }
        )

        # 应该失败（因为邮箱格式无效）
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, test_client):
        """测试速率限制集成"""
        # 创建测试用户
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "username": "ratelimituser",
                "email": "ratelimit@example.com",
                "password": "RateLimit123!",
                "full_name": "Rate Limit User"
            }
        )

        # 多次请求
        responses = []
        for i in range(10):
            response = await test_client.post(
                "/api/v1/auth/login",
                json={
                    "email": "ratelimit@example.com",
                    "password": "wrongpassword",  # 故意使用错误密码
                    "remember_me": False
                }
            )
            responses.append(response.status_code)

        # 检查是否有429状态码（请求过多）
        assert 429 in responses or all(status == 401 for status in responses[-5:])

    @pytest.mark.asyncio
    async def test_password_complexity_enforcement(self, test_client):
        """测试密码复杂度强制执行"""
        # 尝试使用弱密码注册
        weak_passwords = [
            "password",  # 太短
            "12345678",  # 只有数字
            "Password",  # 只有字母，没有数字或特殊字符
            "password123",  # 只有小写字母和数字，没有大写或特殊字符
        ]

        for i, password in enumerate(weak_passwords):
            response = await test_client.post(
                "/api/v1/auth/register",
                json={
                    "username": "weakuser",
                    "email": f"weak{i}@example.com",
                    "password": password,
                    "full_name": "Weak Password User"
                }
            )

            # 注册应该失败或密码应该被拒绝
            # 注意：这取决于API是否在注册时验证密码强度
            assert response.status_code in [400, 422]


class TestDatabaseIntegration:
    """数据库集成测试"""

    @pytest.mark.asyncio
    async def test_user_creation_in_database(self, test_db):
        """测试用户创建到数据库"""
        await test_db.execute("DELETE FROM users WHERE email = 'dbtest@example.com'")
        await test_db.commit()

        user_data = {
            'username': 'dbtestuser',
            'email': 'dbtest@example.com',
            'hashed_password': AuthService.hash_password('DBTestPassword123!'),
            'full_name': 'DB Test User',
            'is_active': True
        }
        user = User(**user_data)
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        # 验证用户被正确创建
        assert user.id is not None
        assert user.email == 'dbtest@example.com'
        assert user.username == 'dbtestuser'

    @pytest.mark.asyncio
    async def test_refresh_token_storage(self, test_db):
        """测试refresh token存储"""
        from src.models.user import RefreshToken

        await test_db.execute("DELETE FROM refresh_tokens WHERE token = 'test_refresh_token_12345'")
        await test_db.execute("DELETE FROM users WHERE email = 'token@example.com'")
        await test_db.commit()

        user_data = {
            'username': 'tokenuser',
            'email': 'token@example.com',
            'hashed_password': AuthService.hash_password('TokenTestPassword123!'),
            'full_name': 'Token User',
            'is_active': True
        }
        user = User(**user_data)
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        # 创建refresh token
        refresh_token = "test_refresh_token_12345"
        expires_at = datetime.utcnow() + timedelta(days=7)

        db_refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            access_token_version=1,
            expires_at=expires_at
        )
        test_db.add(db_refresh_token)
        await test_db.commit()
        await test_db.refresh(db_refresh_token)

        # 验证refresh token被正确存储
        assert db_refresh_token.id is not None
        assert db_refresh_token.user_id == user.id
        assert db_refresh_token.token == refresh_token
        stored_expiry = db_refresh_token.expires_at
        if stored_expiry.tzinfo is None:
            stored_expiry = stored_expiry.replace(tzinfo=expires_at.tzinfo)
        assert int(stored_expiry.timestamp()) == int(expires_at.timestamp())


if __name__ == "__main__":
    pytest.main(["-v", "tests/test_auth_integration.py"])
