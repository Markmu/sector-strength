"""
RBAC 功能测试

测试基于角色的访问控制功能，包括：
- require_admin 依赖注入
- /api/admin/check 端点
- JWT 包含 role 字段
- /api/auth/me 返回 role
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestRequireAdminDependency:
    """测试 require_admin 依赖注入 - 使用 mock"""

    @pytest.mark.asyncio
    async def test_admin_access_granted(self):
        """管理员应能访问需要管理员权限的端点"""
        from src.api.deps import require_admin
        from src.models.user import User

        mock_admin = MagicMock(spec=User)
        mock_admin.role = "admin"
        mock_admin.has_role = lambda role: role == "admin"

        # 应该返回用户而不是抛出异常
        result = await require_admin(mock_admin)
        assert result == mock_admin

    @pytest.mark.asyncio
    async def test_user_access_denied(self):
        """普通用户访问管理员端点应返回 403"""
        from fastapi import HTTPException
        from src.api.deps import require_admin
        from src.models.user import User

        mock_user = MagicMock(spec=User)
        mock_user.role = "user"
        mock_user.has_role = lambda role: role == "user"

        # 应该抛出 403 异常
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_user)

        assert exc_info.value.status_code == 403
        assert "管理员权限" in exc_info.value.detail


class TestAdminCheckEndpoint:
    """测试 GET /api/admin/check 端点"""

    @pytest.mark.asyncio
    async def test_admin_check_as_admin(self):
        """管理员调用 /admin/check 应返回 is_admin=true"""
        from src.api.v1.admin import check_admin_permission, AdminCheckResponse
        from src.models.user import User

        mock_admin = MagicMock(spec=User)
        mock_admin.id = "admin-id-123"
        mock_admin.email = "admin@test.com"
        mock_admin.role = "admin"
        mock_admin.has_role = lambda role: role == "admin"

        result = await check_admin_permission(mock_admin)

        assert result.success is True
        assert result.data.is_admin is True
        assert result.data.role == "admin"

    @pytest.mark.asyncio
    async def test_admin_check_as_user(self):
        """普通用户调用 /admin/check 应返回 is_admin=false"""
        from src.api.v1.admin import check_admin_permission, AdminCheckResponse
        from src.models.user import User

        mock_user = MagicMock(spec=User)
        mock_user.id = "user-id-123"
        mock_user.email = "user@test.com"
        mock_user.role = "user"
        mock_user.has_role = lambda role: role == "user"

        result = await check_admin_permission(mock_user)

        assert result.success is True
        assert result.data.is_admin is False
        assert result.data.role == "user"


class TestUserResponseSchema:
    """测试 UserResponse schema 包含 role 字段"""

    def test_user_response_includes_role(self):
        """UserResponse schema 应包含 role 字段"""
        from src.schemas.auth import UserResponse
        from datetime import datetime

        user_data = {
            "id": "test-id",
            "email": "test@example.com",
            "username": "testuser",
            "is_active": True,
            "is_verified": True,
            "role": "user",
            "last_login": None,
            "created_at": datetime.now()
        }

        response = UserResponse(**user_data)
        assert response.role == "user"


class TestJWTTokenGeneration:
    """测试 JWT token 生成包含 role"""

    def test_create_access_token_includes_role(self):
        """创建 access token 应包含 role 字段"""
        from src.core.auth_service import AuthService

        auth_service = AuthService()
        token_data = {
            "sub": "user-id",
            "email": "test@example.com",
            "role": "admin",
            "permissions": []
        }

        token = auth_service.create_access_token(token_data)

        # 验证 token 包含 role
        from jose import jwt
        payload = jwt.decode(
            token,
            auth_service.secret_key,
            algorithms=[auth_service.algorithm]
        )

        assert "role" in payload
        assert payload["role"] == "admin"


class TestUserModelRole:
    """测试 User 模型 role 相关功能"""

    def test_user_has_role_method(self):
        """User.has_role() 方法应正确工作"""
        from src.models.user import User

        user = User()
        user.role = "admin"

        assert user.has_role("admin") is True
        assert user.has_role("user") is False

    def test_user_default_role(self):
        """新用户默认角色应为 'user'"""
        from src.models.user import User

        user = User(
            email="test@example.com",
            password_hash="hash"
        )

        assert user.role == "user"

    def test_user_custom_role(self):
        """可以设置自定义角色"""
        from src.models.user import User

        user = User(
            email="admin@example.com",
            password_hash="hash",
            role="admin"
        )

        assert user.role == "admin"
