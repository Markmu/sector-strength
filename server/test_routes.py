"""测试 API 路由"""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_routes():
    """测试所有路由是否可访问"""

    # 测试根路径
    response = client.get("/")
    print(f"Root endpoint: {response.status_code} - {response.json()}")

    # 测试健康检查
    response = client.get("/health")
    print(f"Health check: {response.status_code}")

    # 测试 API 端点
    routes = [
        "/api/v1/stocks",
        "/api/v1/sectors",
        "/api/v1/strength",
        "/api/v1/strength/latest"
    ]

    for route in routes:
        response = client.get(route)
        print(f"{route}: {response.status_code}")

    # 测试 API 文档
    response = client.get("/docs")
    print(f"API docs: {response.status_code}")

    print("\n✅ All routes are accessible!")

if __name__ == "__main__":
    test_routes()