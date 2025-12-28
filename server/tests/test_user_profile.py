"""用户资料管理测试"""

import pytest
from unittest.mock import Mock, patch
from src.models.user import User, UserPreferences, ActiveSession
from src.core.auth_service import AuthService
from src.core.security import verify_password, hash_password
import uuid
from datetime import datetime, timezone


class TestUserProfile:
    """测试用户资料管理功能"""

    def test_user_model_has_profile_fields(self, db_session):
        """测试用户模型包含个人资料字段"""
        user = User(
            email="test@example.com",
            password_hash=hash_password("password123"),
            display_name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            timezone="Asia/Shanghai",
            language="zh-CN"
        )
        db_session.add(user)
        db_session.commit()

        # 重新查询验证字段保存
        saved_user = db_session.query(User).filter_by(email="test@example.com").first()
        assert saved_user.display_name == "Test User"
        assert saved_user.avatar_url == "https://example.com/avatar.jpg"
        assert saved_user.timezone == "Asia/Shanghai"
        assert saved_user.language == "zh-CN"

    def test_user_preferences_model(self, db_session):
        """测试用户偏好设置模型"""
        user = User(
            email="test@example.com",
            password_hash=hash_password("password123")
        )
        db_session.add(user)
        db_session.commit()

        preferences = UserPreferences(
            user_id=user.id,
            email_notifications=True,
            push_notifications=False,
            marketing_emails=True
        )
        db_session.add(preferences)
        db_session.commit()

        # 验证关联关系
        saved_user = db_session.query(User).filter_by(email="test@example.com").first()
        assert saved_user.preferences is not None
        assert saved_user.preferences.email_notifications is True
        assert saved_user.preferences.push_notifications is False

    def test_active_session_model(self, db_session):
        """测试活跃会话模型"""
        user = User(
            email="test@example.com",
            password_hash=hash_password("password123")
        )
        db_session.add(user)
        db_session.commit()

        session = ActiveSession(
            user_id=user.id,
            session_id="test-session-123",
            device_info='{"browser": "Chrome", "os": "Windows 10"}',
            ip_address="192.168.1.1",
            expires_at=datetime.now(timezone.utc)
        )
        db_session.add(session)
        db_session.commit()

        # 验证关联关系
        saved_user = db_session.query(User).filter_by(email="test@example.com").first()
        assert len(saved_user.active_sessions) == 1
        assert saved_user.active_sessions[0].session_id == "test-session-123"


class TestProfileAPI:
    """测试用户资料管理API"""

    @pytest.fixture
    def auth_headers(self, test_user, auth_token):
        """创建认证头"""
        return {"Authorization": f"Bearer {auth_token}"}

    def test_get_user_profile_success(self, client, auth_headers):
        """测试获取用户资料成功"""
        response = client.get("/api/user/profile", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "display_name" in data
        assert "created_at" in data
        assert "is_active" in data

    def test_get_user_profile_unauthorized(self, client):
        """测试获取用户资料未授权"""
        response = client.get("/api/user/profile")

        assert response.status_code == 401

    def test_update_user_profile_success(self, client, auth_headers):
        """测试更新用户资料成功"""
        update_data = {
            "display_name": "Updated Name",
            "timezone": "America/New_York",
            "language": "en-US"
        }

        response = client.put("/api/user/profile", json=update_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Name"
        assert data["timezone"] == "America/New_York"
        assert data["language"] == "en-US"

    def test_update_user_profile_partial(self, client, auth_headers):
        """测试部分更新用户资料"""
        update_data = {
            "display_name": "Partial Update"
        }

        response = client.put("/api/user/profile", json=update_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Partial Update"


class TestPasswordChange:
    """测试密码更改功能"""

    @pytest.fixture
    def auth_headers(self, test_user, auth_token):
        """创建认证头"""
        return {"Authorization": f"Bearer {auth_token}"}

    def test_change_password_success(self, client, auth_headers, db_session):
        """测试密码更改成功"""
        change_data = {
            "current_password": "testpassword",
            "new_password": "newpassword123"
        }

        response = client.post("/api/user/change-password", json=change_data, headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["message"] == "密码更改成功"

    def test_change_password_wrong_current(self, client, auth_headers):
        """测试使用错误的当前密码"""
        change_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123"
        }

        response = client.post("/api/user/change-password", json=change_data, headers=auth_headers)

        assert response.status_code == 401
        assert "当前密码不正确" in response.json()["detail"]

    def test_change_password_same_as_current(self, client, auth_headers):
        """测试新密码与当前密码相同"""
        change_data = {
            "current_password": "testpassword",
            "new_password": "testpassword"
        }

        response = client.post("/api/user/change-password", json=change_data, headers=auth_headers)

        assert response.status_code == 400
        assert "新密码不能与当前密码相同" in response.json()["detail"]


class TestUserPreferencesAPI:
    """测试用户偏好设置API"""

    @pytest.fixture
    def auth_headers(self, test_user, auth_token):
        """创建认证头"""
        return {"Authorization": f"Bearer {auth_token}"}

    def test_get_user_preferences(self, client, auth_headers):
        """测试获取用户偏好设置"""
        response = client.get("/api/user/preferences", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "email_notifications" in data
        assert "push_notifications" in data
        assert "marketing_emails" in data

    def test_update_user_preferences(self, client, auth_headers):
        """测试更新用户偏好设置"""
        preference_data = {
            "email_notifications": False,
            "push_notifications": True,
            "marketing_emails": False
        }

        response = client.put("/api/user/preferences", json=preference_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email_notifications"] is False
        assert data["push_notifications"] is True
        assert data["marketing_emails"] is False


class TestSessionManagement:
    """测试会话管理API"""

    @pytest.fixture
    def auth_headers(self, test_user, auth_token):
        """创建认证头"""
        return {"Authorization": f"Bearer {auth_token}"}

    def test_get_active_sessions(self, client, auth_headers):
        """测试获取活跃会话"""
        response = client.get("/api/user/sessions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_terminate_session(self, client, auth_headers, db_session):
        """测试终止特定会话"""
        # 先创建测试会话
        from src.models.user import ActiveSession
        from datetime import datetime, timezone, timedelta

        session = ActiveSession(
            user_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),  # 测试用户ID
            session_id="test-session-to-delete",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.add(session)
        db_session.commit()

        response = client.delete("/api/user/sessions/test-session-to-delete", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["message"] == "会话已终止"

    def test_terminate_all_other_sessions(self, client, auth_headers):
        """测试终止所有其他会话"""
        response = client.delete("/api/user/sessions/all", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["message"] == "已终止所有其他会话"


class TestAccountManagement:
    """测试账户管理功能"""

    @pytest.fixture
    def auth_headers(self, test_user, auth_token):
        """创建认证头"""
        return {"Authorization": f"Bearer {auth_token}"}

    def test_deactivate_account(self, client, auth_headers):
        """测试停用账户"""
        response = client.post("/api/user/deactivate", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["message"] == "账户已停用"

    def test_delete_account_request(self, client, auth_headers):
        """测试请求删除账户"""
        response = client.delete("/api/user/account", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deletion_date" in data
