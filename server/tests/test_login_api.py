"""登录API测试"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.core.security import hash_password

@pytest.fixture
async def test_user(db: AsyncSession):
    """创建测试用户"""
    # 创建用户
    user = User(
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@pytest.mark.asyncio
async def test_login_success(client, test_user):
    """测试登录成功"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )

    assert response.status_code == 200
    data = response.json()

    # 验证返回数据结构
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert "user" in data

    # 验证用户信息
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["is_active"] is True

@pytest.mark.asyncio
async def test_login_invalid_email(client):
    """测试无效邮箱"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrong@example.com",
            "password": "testpassword123"
        }
    )

    assert response.status_code == 401
    assert "邮箱或密码错误" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_invalid_password(client, test_user):
    """测试无效密码"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    assert "邮箱或密码错误" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_inactive_user(db: AsyncSession, client):
    """测试非活跃用户"""
    # 创建非活跃用户
    user = User(
        email="inactive@example.com",
        password_hash=hash_password("testpassword123"),
        is_active=False,
        is_verified=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "testpassword123"
        }
    )

    assert response.status_code == 401
    assert "账户已被禁用" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_invalid_data(client):
    """测试无效数据格式"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "invalid-email",
            "password": ""
        }
    )

    assert response.status_code == 422

@pytest.mark.asyncio
async def test_remember_me(client, test_user):
    """测试记住我功能"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "remember_me": True
        }
    )

    assert response.status_code == 200
    data = response.json()

    # 验证expires_in是7天（604800秒）
    assert data["expires_in"] == 604800

@pytest.mark.asyncio
async def test_refresh_token_success(client, test_user):
    """测试刷新令牌成功"""
    # 先登录获取刷新令牌
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )

    refresh_token = login_response.json()["refresh_token"]

    # 使用刷新令牌获取新访问令牌
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_refresh_token_invalid(client):
    """测试无效刷新令牌"""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"}
    )

    assert response.status_code == 401
    assert "无效的刷新令牌" in response.json()["detail"]

@pytest.mark.asyncio
async def test_logout(client, test_user):
    """测试注销功能"""
    # 先登录
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )

    token = login_response.json()["access_token"]

    # 注销
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == "注销成功"
