"""测试用户模型和密码功能"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models.user import User, EmailVerificationToken
from src.core.security import hash_password, verify_password, create_access_token


class TestUserModel:
    """测试用户模型"""

    def test_user_model_creation(self):
        """测试用户模型创建"""
        # 创建用户实例
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            username="testuser"
        )

        # 验证字段
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.username == "testuser"
        assert user.is_active is False  # 默认值
        assert user.is_verified is False  # 默认值
        assert user.id is not None  # UUID 应该自动生成

    def test_password_hashing(self):
        """测试密码哈希功能"""
        password = "test123!@#"
        hashed = hash_password(password)

        # 验证哈希不等于原密码
        assert hashed != password
        assert len(hashed) > 50  # sha256_crypt 哈希长度

        # 验证密码验证功能
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_jwt_token_creation(self):
        """测试 JWT 令牌创建"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        token = create_access_token(user_id)

        # 验证令牌不为空
        assert token is not None
        assert len(token) > 100  # JWT 令牌长度

        # 验证令牌包含三部分（header.payload.signature）
        parts = token.split('.')
        assert len(parts) == 3

    def test_email_verification_token_creation(self):
        """测试邮箱验证令牌模型创建"""
        # 创建验证令牌实例
        token = EmailVerificationToken(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            token="verification_token_123",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )

        # 验证字段
        assert token.user_id == "123e4567-e89b-12d3-a456-426614174000"
        assert token.token == "verification_token_123"
        assert token.is_used is False  # 默认值
        assert token.expires_at > datetime.utcnow()  # 未过期
        assert token.id is not None  # UUID 应该自动生成