"""测试JWT令牌包含角色和权限信息"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.auth_service import AuthService
from src.models.user import User


@pytest.mark.asyncio
async def test_jwt_includes_role_and_permissions(db_session: AsyncSession):
    """测试JWT令牌包含角色和权限信息"""
    auth_service = AuthService()

    # 创建测试用户
    user = User(
        email="test@example.com",
        password_hash=auth_service.get_password_hash("testpassword"),
        role="admin",
        permissions=["read", "write", "delete"]
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 创建访问令牌
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "permissions": user.permissions
    }
    access_token = auth_service.create_access_token(token_data)

    # 解码令牌（不验证签名）
    decoded = auth_service.decode_token(access_token)

    # 验证令牌包含角色和权限
    assert decoded["sub"] == str(user.id)
    assert decoded["email"] == user.email
    assert decoded["role"] == "admin"
    assert decoded["permissions"] == ["read", "write", "delete"]
    assert decoded["type"] == "access"
    assert "exp" in decoded

    # 测试普通用户
    user2 = User(
        email="user2@example.com",
        password_hash=auth_service.get_password_hash("user2password"),
        role="user",  # 默认角色
        permissions=[]  # 无特殊权限
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)

    token_data2 = {
        "sub": str(user2.id),
        "email": user2.email,
        "role": user2.role,
        "permissions": user2.permissions
    }
    access_token2 = auth_service.create_access_token(token_data2)
    decoded2 = auth_service.decode_token(access_token2)

    assert decoded2["role"] == "user"
    assert decoded2["permissions"] == []


@pytest.mark.asyncio
async def test_registration_sets_default_role(db_session: AsyncSession):
    """测试注册时自动设置默认角色"""
    auth_service = AuthService()

    # 创建用户（不指定角色）
    user = User(
        email="newuser@example.com",
        password_hash=auth_service.get_password_hash("newpassword")
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 验证默认角色为user
    assert user.role == "user"
    assert user.permissions == []
    assert user.has_role("user")
    assert not user.has_role("admin")
