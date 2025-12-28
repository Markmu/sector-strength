"""测试User模型的角色和权限功能"""

import pytest
from src.models.user import User
from sqlalchemy.orm import Session


def test_user_default_role():
    """测试新用户默认角色为'user'"""
    user = User(
        email="test@example.com",
        password_hash="hashed_password"
    )

    assert user.role == "user"
    assert user.has_role("user") is True
    assert user.has_role("admin") is False


def test_user_has_role():
    """测试has_role方法"""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        role="admin"
    )

    assert user.has_role("admin") is True
    assert user.has_role("user") is False


def test_user_default_permissions():
    """测试新用户默认权限为空列表"""
    user = User(
        email="test@example.com",
        password_hash="hashed_password"
    )

    assert user.permissions == []
    assert user.has_permission("any_permission") is False


def test_user_has_permission():
    """测试has_permission方法"""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        permissions=["read", "write"]
    )

    assert user.has_permission("read") is True
    assert user.has_permission("write") is True
    assert user.has_permission("delete") is False


def test_user_add_permission():
    """测试add_permission方法"""
    user = User(
        email="test@example.com",
        password_hash="hashed_password"
    )

    # 初始为空
    assert user.permissions == []

    # 添加权限
    user.add_permission("read")
    assert user.permissions == ["read"]
    assert user.has_permission("read") is True

    # 添加重复权限（不应重复）
    user.add_permission("read")
    assert user.permissions == ["read"]

    # 添加新权限
    user.add_permission("write")
    assert "read" in user.permissions
    assert "write" in user.permissions


def test_user_remove_permission():
    """测试remove_permission方法"""
    user = User(
        email="test@example.com",
        password_hash="hashed_password",
        permissions=["read", "write", "delete"]
    )

    # 移除一个权限
    user.remove_permission("write")
    assert "read" in user.permissions
    assert "write" not in user.permissions
    assert "delete" in user.permissions

    # 移除不存在的权限（应无错误）
    user.remove_permission("execute")
    assert len(user.permissions) == 2
