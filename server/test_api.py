"""简单的 API 测试脚本"""

import asyncio
import sys
import os
from httpx import AsyncClient
from datetime import datetime

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import app


async def test_registration():
    """测试注册 API"""
    print("Testing registration API...")

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 测试数据
        test_email = f"test{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        user_data = {
            "email": test_email,
            "password": "Test123!@#",
            "username": "testuser"
        }

        # 发送注册请求
        response = await client.post("/api/auth/register", json=user_data)

        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")

        if response.status_code == 201:
            print("✓ Registration API test passed")
            return True
        else:
            print("✗ Registration API test failed")
            return False


async def test_invalid_registration():
    """测试无效注册"""
    print("\nTesting invalid registration...")

    async with AsyncClient(app=app, base_url="http://test") as client:
        # 测试无效邮箱
        invalid_data = {
            "email": "invalid-email",
            "password": "Test123!@#",
            "username": "testuser"
        }

        response = await client.post("/api/auth/register", json=invalid_data)

        print(f"Status code (invalid email): {response.status_code}")

        if response.status_code == 422:
            print("✓ Invalid email test passed")
        else:
            print("✗ Invalid email test failed")

        # 测试弱密码
        weak_data = {
            "email": "test2@example.com",
            "password": "123",
            "username": "testuser"
        }

        response = await client.post("/api/auth/register", json=weak_data)

        print(f"Status code (weak password): {response.status_code}")

        if response.status_code == 400:
            print("✓ Weak password test passed")
        else:
            print("✗ Weak password test failed")


if __name__ == "__main__":
    print("Running API tests...\n")

    # 运行测试
    success = asyncio.run(test_registration())
    asyncio.run(test_invalid_registration())

    if success:
        print("\n✅ Core API functionality working!")
    else:
        print("\n❌ API tests failed!")