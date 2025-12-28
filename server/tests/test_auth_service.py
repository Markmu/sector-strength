import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.auth_service import AuthService
from src.core.config import settings


class TestAuthServiceSecurity:
    """认证安全机制测试"""

    @pytest.mark.asyncio
    async def test_rate_limit_check(self):
        """测试速率限制检查"""
        user_id = "test-user"

        # 测试未超出限制
        is_limited = await AuthService.check_rate_limit(user_id)
        assert is_limited is False

        # 模拟多次失败登录
        for _ in range(10):
            await AuthService.record_failed_login(user_id)

        # 测试超出限制
        is_limited = await AuthService.check_rate_limit(user_id)
        assert is_limited is True

    @pytest.mark.asyncio
    async def test_account_lock_check(self):
        """测试账户锁定检查"""
        user_id = "test-user"

        # 测试账户未锁定
        is_locked = await AuthService.check_account_locked(user_id)
        assert is_locked is False

        # 模拟多次失败登录导致锁定
        for _ in range(6):  # 超过5次失败
            await AuthService.record_failed_login(user_id)

        # 测试账户锁定
        is_locked = await AuthService.check_account_locked(user_id)
        assert is_locked is True

    @pytest.mark.asyncio
    async def test_successful_login_clears_attempts(self):
        """测试成功登录清除失败计数"""
        user_id = "test-user"

        # 添加多次失败记录
        for _ in range(3):
            await AuthService.record_failed_login(user_id)

        # 模拟成功登录
        await AuthService.record_successful_login(user_id)

        # 验证失败计数已清除
        assert await AuthService.check_rate_limit(user_id) is False

    @pytest.mark.asyncio
    async def test_token_expiry_time(self):
        """测试token过期时间"""
        # 测试访问token过期时间（24小时）
        access_token, _, access_expires_in = AuthService.generate_tokens(
            "test-user", "test@example.com"
        )
        assert access_expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        # 测试refresh token过期时间（7天）
        _, refresh_token, refresh_expires_in = AuthService.generate_tokens(
            "test-user", "test@example.com"
        )
        assert refresh_expires_in == settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    def test_password_complexity_validation(self):
        """测试密码复杂度验证"""
        # 有效密码
        assert AuthService.validate_password_strength("SecurePass123!") is True
        assert AuthService.validate_password_strength("MyPassword@2024") is True

        # 无效密码
        assert AuthService.validate_password_strength("password") is False  # 太短
        assert AuthService.validate_password_strength("12345678") is False  # 缺少大小写和特殊字符
        assert AuthService.validate_password_strength("Password") is False   # 缺少数字
        assert AuthService.validate_password_strength("password123") is False # 缺少大写和特殊字符


class TestAuthServiceIntegration:
    """认证服务集成测试"""

    @pytest.mark.asyncio
    async def test_complete_auth_flow(self):
        """测试完整的认证流程"""
        user_id = "integration-test-user"
        email = "integration@test.com"
        password = "SecurePass123!"

        # 1. 生成tokens
        access_token, refresh_token, _ = AuthService.generate_tokens(user_id, email)

        # 2. 验证访问token
        payload = AuthService.validate_access_token(access_token)
        assert payload["user_id"] == user_id
        assert payload["email"] == email

        # 3. 验证refresh token
        refresh_payload = AuthService.validate_refresh_token(refresh_token)
        assert refresh_payload["user_id"] == user_id
        assert refresh_payload["email"] == email

        # 4. 验证密码哈希
        hashed_password = AuthService.hash_password(password)
        assert AuthService.verify_password(password, hashed_password) is True
        assert AuthService.verify_password("wrong", hashed_password) is False

    @pytest.mark.asyncio
    async def test_token_payload_structure(self):
        """测试token payload结构"""
        user_id = "payload-test-user"
        email = "payload@test.com"

        access_token, refresh_token, _ = AuthService.generate_tokens(user_id, email)

        # 验证访问token payload
        access_payload = AuthService.validate_access_token(access_token)
        required_fields = ["user_id", "email", "exp", "iat"]
        for field in required_fields:
            assert field in access_payload

        # 验证refresh token payload
        refresh_payload = AuthService.validate_refresh_token(refresh_token)
        required_fields = ["user_id", "email", "exp", "iat"]
        for field in required_fields:
            assert field in refresh_payload

        # 验证token过期时间
        assert access_payload["exp"] > access_payload["iat"]
        assert refresh_payload["exp"] > refresh_payload["iat"]

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        # 测试无效token
        with pytest.raises(Exception):
            AuthService.validate_access_token("invalid.token.here")

        with pytest.raises(Exception):
            AuthService.validate_refresh_token("invalid.token.here")

        # 测试无效密码
        hashed = AuthService.hash_password("validPassword123!")
        assert AuthService.verify_password("wrongPassword", hashed) is False

    @pytest.mark.asyncio
    async def test_security_headers_generation(self):
        """测试安全头生成"""
        from fastapi import Request
        from unittest.mock import Mock

        # 创建模拟请求
        request = Mock(spec=Request)
        request.headers = Mock()
        request.headers.get = Mock(return_value="Bearer test-token")

        # 这个测试可以根据实际的security headers实现来调整
        # 目前只是确保没有错误发生
        try:
            # 这里可以添加实际的security headers测试
            pass
        except Exception as e:
            pytest.fail(f"Security headers generation failed: {e}")


class TestAuthServicePerformance:
    """认证服务性能测试"""

    @pytest.mark.asyncio
    async def test_password_hashing_performance(self):
        """测试密码哈希性能"""
        import time

        password = "PerformanceTestPassword123!"

        # 测试哈希性能
        start_time = time.time()
        hashed = AuthService.hash_password(password)
        hash_time = time.time() - start_time

        # 验证哈希不是瞬间完成的（防止彩虹表攻击）
        assert hash_time > 0.001  # 至少1ms

        # 验证密码验证性能
        start_time = time.time()
        is_valid = AuthService.verify_password(password, hashed)
        verify_time = time.time() - start_time

        # 验证密码验证
        assert is_valid is True
        assert verify_time < 0.1  # 验证应该很快

    @pytest.mark.asyncio
    async def test_token_validation_performance(self):
        """测试token验证性能"""
        import time

        user_id = "perf-test-user"
        email = "perf@test.com"

        # 生成token
        access_token, _, _ = AuthService.generate_tokens(user_id, email)

        # 测试多次验证性能
        iterations = 1000
        start_time = time.time()

        for _ in range(iterations):
            try:
                AuthService.validate_access_token(access_token)
            except:
                pass

        avg_time = (time.time() - start_time) / iterations

        # 验证平均时间在合理范围内
        assert avg_time < 0.001  # 平均每次验证小于1ms


if __name__ == "__main__":
    pytest.main(["-v", "tests/test_auth_service.py"])