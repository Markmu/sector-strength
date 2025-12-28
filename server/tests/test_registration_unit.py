"""注册功能的单元测试"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models.user import User, EmailVerificationToken
from src.core.security import hash_password, verify_password
from src.core.rate_limiter import RateLimiter, check_rate_limit
from src.core.sanitizer import (
    sanitize_string,
    sanitize_email,
    validate_password_strength,
    validate_username,
    InputValidator
)
from src.core.csrf import CSRFProtection
from fastapi import Request, HTTPException


class TestPasswordSecurity:
    """测试密码安全性"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "Test123!@#"
        hashed = hash_password(password)

        # 验证哈希不等于原密码
        assert hashed != password
        # 验证哈希长度
        assert len(hashed) > 50
        # 验证 sha256_crypt 标识
        assert hashed.startswith('$2b$')

    def test_verify_password(self):
        """测试密码验证"""
        password = "Test123!@#"
        hashed = hash_password(password)

        # 正确密码
        assert verify_password(password, hashed) is True
        # 错误密码
        assert verify_password("WrongPassword", hashed) is False
        # 空密码
        assert verify_password("", hashed) is False

    def test_sha256_crypt_cost(self):
        """测试 sha256_crypt 成本因子"""
        password = "Test123!@#"
        hashed = hash_password(password)

        # 提取成本因子（$2b$12$ 中的 12）
        cost = int(hashed.split('$')[2])
        assert cost >= 12  # 成本因子应该 >= 12


class TestRateLimiter:
    """测试速率限制"""

    @pytest.fixture
    def limiter(self):
        """创建速率限制器实例"""
        return RateLimiter()

    def test_rate_limit_within_limit(self, limiter):
        """测试在限制内的请求"""
        key = "test_ip"

        # 发送 3 个请求（限制为 5）
        for _ in range(3):
            assert limiter.is_allowed(key, limit=5, window=60) is True

    def test_rate_limit_exceeded(self, limiter):
        """测试超过限制的请求"""
        key = "test_ip"

        # 发送 5 个请求（达到限制）
        for _ in range(5):
            assert limiter.is_allowed(key, limit=5, window=60) is True

        # 第 6 个请求应该被拒绝
        assert limiter.is_allowed(key, limit=5, window=60) is False

    def test_rate_limit_window_reset(self, limiter):
        """测试时间窗口重置"""
        key = "test_ip"

        # 发送请求直到达到限制
        for _ in range(5):
            assert limiter.is_allowed(key, limit=5, window=1) is True

        # 请求被拒绝
        assert limiter.is_allowed(key, limit=5, window=1) is False

        # 模拟时间流逝（在测试中手动删除旧记录）
        limiter.requests[key].popleft()

        # 现在应该可以再次请求
        assert limiter.is_allowed(key, limit=5, window=1) is True


class TestInputSanitization:
    """测试输入清理"""

    def test_sanitize_string(self):
        """测试字符串清理"""
        # HTML 转义
        assert sanitize_string("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

        # 长度限制
        long_string = "a" * 1000 + "b"
        assert len(sanitize_string(long_string, max_length=1000)) == 1000

        # 移除脚本标签
        assert "<script>" not in sanitize_string("<script>malicious</script>content")

    def test_sanitize_email(self):
        """测试邮箱清理"""
        # 有效邮箱
        assert sanitize_email("Test@EXAMPLE.COM") == "test@example.com"

        # 包含危险字符
        assert sanitize_email("test<script>@example.com") == "testscript@example.com"

        # 无效邮箱
        assert sanitize_email("invalid-email") == ""

    def test_validate_password_strength(self):
        """测试密码强度验证"""
        # 有效密码
        assert validate_password_strength("Test123!@#")[0] is True

        # 太短
        assert validate_password_strength("Test12!")[1] == "密码长度至少8位"

        # 缺少大写字母
        assert validate_password_strength("test123!@#")[1] == "密码必须包含大写字母"

        # 缺少小写字母
        assert validate_password_strength("TEST123!@#")[1] == "密码必须包含小写字母"

        # 缺少数字
        assert validate_password_strength("TestABC!@#")[1] == "密码必须包含数字"

        # 缺少特殊字符
        assert validate_password_strength("Test123abc")[1] == "密码必须包含特殊字符"

        # 常见弱密码
        assert validate_password_strength("Password123!")[1] == "密码过于简单，请使用更复杂的密码"

    def test_validate_username(self):
        """测试用户名验证"""
        # 有效用户名
        assert validate_username("test_user")[0] is True
        assert validate_username("用户名")[0] is True
        assert validate_username("test-123")[0] is True

        # 太短
        assert validate_username("t")[1] == "用户名长度至少2个字符"

        # 太长
        long_name = "a" * 51
        assert validate_username(long_name)[1] == "用户名长度不能超过50个字符"

        # 无效字符
        assert validate_username("test@user")[1] == "用户名只能包含字母、数字、中文、下划线和连字符"

        # 特殊字符开头
        assert validate_username("_test")[1] == "用户名不能以下划线或连字符开头或结尾"

    def test_input_validator_register_data(self):
        """测试注册数据验证器"""
        # 有效数据
        is_valid, cleaned, errors = InputValidator.validate_and_sanitize_register_data({
            'email': 'Test@EXAMPLE.COM',
            'password': 'Test123!@#',
            'username': 'Test_User'
        })
        assert is_valid is True
        assert cleaned['email'] == 'test@example.com'
        assert len(errors) == 0

        # 无效邮箱
        is_valid, _, errors = InputValidator.validate_and_sanitize_register_data({
            'email': 'invalid-email',
            'password': 'Test123!@#'
        })
        assert is_valid is False
        assert "邮箱格式无效" in errors

        # 弱密码
        is_valid, _, errors = InputValidator.validate_and_sanitize_register_data({
            'email': 'test@example.com',
            'password': 'weak'
        })
        assert is_valid is False
        assert any("密码" in error for error in errors)


class TestCSRFProtection:
    """测试 CSRF 保护"""

    @pytest.fixture
    def csrf(self):
        """创建 CSRF 保护实例"""
        return CSRFProtection()

    def test_generate_token(self, csrf):
        """测试生成令牌"""
        token = csrf.generate_token()
        assert len(token) > 30
        assert isinstance(token, str)

    def test_validate_token_valid(self, csrf):
        """测试有效令牌验证"""
        # 模拟请求对象
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"

        # 生成并存储令牌
        token = csrf.generate_token()
        csrf.store_token(request, token)

        # 验证令牌
        assert csrf.validate_token(request, token) is True

    def test_validate_token_invalid(self, csrf):
        """测试无效令牌验证"""
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"

        # 没有存储令牌
        assert csrf.validate_token(request, "invalid_token") is False

        # 令牌不匹配
        csrf.store_token(request, "token1")
        assert csrf.validate_token(request, "token2") is False


class TestUserModel:
    """测试用户模型"""

    def test_user_creation(self):
        """测试用户创建"""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            username="testuser"
        )

        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.username == "testuser"
        assert user.is_active is False  # 默认值
        assert user.is_verified is False  # 默认值
        assert user.id is not None  # UUID 应该自动生成

    def test_verification_token_creation(self):
        """测试验证令牌创建"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        token = EmailVerificationToken(
            user_id=user_id,
            token="verification_token",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )

        assert token.user_id == user_id
        assert token.token == "verification_token"
        assert token.is_used is False  # 默认值
        assert token.expires_at > datetime.utcnow()  # 未过期
        assert token.id is not None  # UUID 应该自动生成


@pytest.mark.asyncio
class TestRegistrationIntegration:
    """注册功能集成测试（异步）"""

    async def test_check_rate_limit_async(self):
        """测试异步速率限制检查"""
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}

        # 模拟成功的情况
        with patch('src.core.rate_limiter.rate_limiter.is_allowed', return_value=True):
            # 不应该抛出异常
            await check_rate_limit(request, limit=5, window=60)

        # 模拟速率限制触发
        with patch('src.core.rate_limiter.rate_limiter.is_allowed', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await check_rate_limit(request, limit=5, window=60)
            assert exc_info.value.status_code == 429
            assert "请求过于频繁" in str(exc_info.value.detail)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])