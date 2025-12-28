"""测试注册 API 端点"""

import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.main import app


client = TestClient(app)


class TestRegistrationAPI:
    """测试注册 API"""

    def test_register_success(self):
        """测试成功注册"""
        # 准备测试数据
        user_data = {
            "email": "test@example.com",
            "password": "Test123!@#",
            "username": "testuser"
        }

        # 发送注册请求
        with patch('src.api.auth.registration.send_verification_email') as mock_send:
            mock_send.return_value = True
            response = client.post("/api/auth/register", json=user_data)

        # 验证响应
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "注册成功，请查看邮箱进行验证"
        assert "user_id" in data

    def test_register_duplicate_email(self):
        """测试重复邮箱注册"""
        # 先注册一个用户
        user_data = {
            "email": "duplicate@example.com",
            "password": "Test123!@#",
            "username": "testuser"
        }

        # 第一次注册
        with patch('src.api.auth.registration.send_verification_email') as mock_send:
            mock_send.return_value = True
            response1 = client.post("/api/auth/register", json=user_data)
            assert response1.status_code == 201

        # 第二次注册同一邮箱
        response2 = client.post("/api/auth/register", json=user_data)
        assert response2.status_code == 400
        assert "邮箱已被注册" in response2.json()["detail"]

    def test_register_invalid_email(self):
        """测试无效邮箱格式"""
        user_data = {
            "email": "invalid-email",
            "password": "Test123!@#",
            "username": "testuser"
        }

        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422
        assert "邮箱格式无效" in str(response.json())

    def test_register_weak_password(self):
        """测试弱密码"""
        user_data = {
            "email": "test@example.com",
            "password": "123",  # 太简单
            "username": "testuser"
        }

        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 400
        assert "密码强度不够" in response.json()["detail"]

    def test_register_missing_fields(self):
        """测试缺少必填字段"""
        # 缺少密码
        user_data = {
            "email": "test@example.com",
            "username": "testuser"
        }

        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 422

    def test_register_email_verification_flow(self):
        """测试邮箱验证流程"""
        # 注册用户
        user_data = {
            "email": "verify@example.com",
            "password": "Test123!@#",
            "username": "testuser"
        }

        with patch('src.api.auth.registration.send_verification_email') as mock_send:
            mock_send.return_value = True
            response = client.post("/api/auth/register", json=user_data)
            user_id = response.json()["user_id"]

        # 模拟获取验证令牌
        with patch('src.api.auth.auth.get_verification_token') as mock_get:
            mock_get.return_value = user_id
            # 使用模拟的令牌进行验证
            token = "mock_verification_token"
            response = client.get(f"/api/auth/verify/{token}")

        assert response.status_code == 200
        assert "邮箱验证成功" in response.json()["message"]