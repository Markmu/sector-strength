"""测试注册 API 端点"""

import pytest
import pytest_asyncio
import time
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from main import app


@pytest_asyncio.fixture
async def client(test_session):
    """创建测试客户端（使用隔离 schema）"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


class TestRegistrationAPI:
    """测试注册 API"""

    @pytest.mark.asyncio
    async def test_register_success(self, client):
        """测试成功注册"""
        user_data = {
            "email": f"test_{int(time.time() * 1000)}@example.com",
            "password": "Test123!@#",
            "username": "testuser"
        }

        with patch('src.api.auth.registration.send_verification_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            response = await client.post("/api/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "注册成功，请查看邮箱进行验证"
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client):
        """测试重复邮箱注册"""
        user_data = {
            "email": f"duplicate_{int(time.time() * 1000)}@example.com",
            "password": "Test123!@#",
            "username": "testuser"
        }

        # 第一次注册
        with patch('src.api.auth.registration.send_verification_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            response1 = await client.post("/api/auth/register", json=user_data)
            assert response1.status_code == 201

        # 第二次注册同一邮箱
        response2 = await client.post("/api/auth/register", json=user_data)
        assert response2.status_code == 400
        assert "邮箱已被注册" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        """测试无效邮箱格式"""
        user_data = {
            "email": "invalid-email",
            "password": "Test123!@#",
            "username": "testuser"
        }

        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client):
        """测试弱密码"""
        user_data = {
            "email": "test@example.com",
            "password": "123",  # 太简单
            "username": "testuser"
        }

        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "密码强度不够" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client):
        """测试缺少必填字段"""
        # 缺少密码
        user_data = {
            "email": "test@example.com",
            "username": "testuser"
        }

        response = await client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_email_verification_flow(self, client):
        """测试邮箱验证流程"""
        user_data = {
            "email": f"verify_{int(time.time() * 1000)}@example.com",
            "password": "Test123!@#",
            "username": "testuser"
        }

        with patch('src.api.auth.registration.send_verification_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            response = await client.post("/api/auth/register", json=user_data)
            user_id = response.json()["user_id"]

        # 未使用真实令牌时，接口应返回无效令牌
        response = await client.get("/api/auth/verify/mock_verification_token")
        assert response.status_code == 404
