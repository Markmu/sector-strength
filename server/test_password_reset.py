"""密码重置功能测试"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from datetime import datetime, timedelta

from src.api.auth.password_reset import router
from src.db.database import get_db
from src.models.user import User, PasswordResetToken
from src.core.security import hash_password
from src.core.email_queue import send_password_reset_email_queue
import uuid


@pytest.fixture
def client():
    """创建测试客户端"""
    from main import app
    return TestClient(app)


@pytest.mark.asyncio
async def test_request_password_reset():
    """测试请求密码重置"""
    # 模拟数据库查询
    with patch('src.api.auth.password_reset.get_db') as mock_get_db:
        mock_session = AsyncMock()

        # 模拟用户查询
        mock_user = AsyncMock()
        mock_user.is_active = True
        mock_user.email = "test@example.com"
        mock_user.username = "testuser"

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_session.execute.return_value = mock_result
        mock_get_db.return_value = mock_session

        # 模拟密码哈希
        with patch('src.api.auth.password_reset.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"

            # 模拟令牌创建和保存
            mock_token = AsyncMock()
            mock_session.add.return_value = mock_token
            mock_session.commit.return_value = None

            # 模拟邮件队列发送
            with patch('src.api.auth.password_reset.send_password_reset_email_queue') as mock_send:
                mock_send.return_value = "task_id_123"

                # 创建测试客户端请求
                from fastapi import FastAPI
                from fastapi.testclient import TestClient
                app = FastAPI()
                app.include_router(router, prefix="/auth")
                client = TestClient(app)

                # 发送请求
                response = client.post("/forgot-password", json={"email": "test@example.com"})

                # 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "密码重置链接已发送到您的邮箱"

                # 验证邮件队列被调用
                mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_confirm_password_reset():
    """测试确认密码重置"""
    # 模拟数据库查询
    with patch('src.api.auth.password_reset.get_db') as mock_get_db:
        mock_session = AsyncMock()

        # 模拟重置令牌查询
        mock_token = AsyncMock()
        mock_token.expires_at = datetime.utcnow() + timedelta(hours=1)
        mock_token.is_used = False
        mock_token.user_id = uuid.uuid4()

        mock_token_result = AsyncMock()
        mock_token_result.scalar_one_or_none.return_value = mock_token

        # 模拟用户查询
        mock_user = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_session.execute.side_effect = [mock_token_result, mock_result]
        mock_session.commit.return_value = None

        mock_get_db.return_value = mock_session

        # 创建测试客户端请求
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        app.include_router(router, prefix="/auth")
        client = TestClient(app)

        # 发送请求
        response = client.post("/reset-password", json={
            "token": "test_token_123",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        })

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "密码重置成功，请使用新密码登录"

        # 验证用户密码被更新
        assert mock_session.commit.called

        # 验证令牌被标记为已使用
        assert mock_token.is_used == True


@pytest.mark.asyncio
async def test_request_password_reset_user_not_found():
    """测试请求密码重置 - 用户不存在"""
    with patch('src.api.auth.password_reset.get_db') as mock_get_db:
        mock_session = AsyncMock()

        # 模拟用户不存在
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        mock_get_db.return_value = mock_session

        # 创建测试客户端
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        app.include_router(router, prefix="/auth")
        client = TestClient(app)

        # 发送请求
        response = client.post("/forgot-password", json={"email": "nonexistent@example.com"})

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "如果您的邮箱存在，我们将向您发送重置链接"


@pytest.mark.asyncio
async def test_confirm_password_reset_invalid_token():
    """测试确认密码重置 - 无效令牌"""
    with patch('src.api.auth.password_reset.get_db') as mock_get_db:
        mock_session = AsyncMock()

        # 模令令牌不存在
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        mock_get_db.return_value = mock_session

        # 创建测试客户端
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        app.include_router(router, prefix="/auth")
        client = TestClient(app)

        # 发送请求
        response = client.post("/reset-password", json={
            "token": "invalid_token",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        })

        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "重置令牌无效或已使用" in data["detail"]


@pytest.mark.asyncio
async def test_confirm_password_reset_expired_token():
    """测试确认密码重置 - 令牌过期"""
    with patch('src.api.auth.password_reset.get_db') as mock_get_db:
        mock_session = AsyncMock()

        # 模拟过期令牌
        mock_token = AsyncMock()
        mock_token.expires_at = datetime.utcnow() - timedelta(hours=1)  # 已过期
        mock_token.is_used = False
        mock_token.user_id = uuid.uuid4()

        mock_token_result = AsyncMock()
        mock_token_result.scalar_one_or_none.return_value = mock_token

        mock_session.execute.return_value = mock_token_result
        mock_get_db.return_value = mock_session

        # 创建测试客户端
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        app.include_router(router, prefix="/auth")
        client = TestClient(app)

        # 发送请求
        response = client.post("/reset-password", json={
            "token": "expired_token",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        })

        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "重置令牌已过期" in data["detail"]