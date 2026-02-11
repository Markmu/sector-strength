"""主应用测试"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "version" in response.json()
    assert "environment" in response.json()

def test_health_check():
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data

def test_database_health_check():
    """测试数据库健康检查端点"""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data

def test_api_docs():
    """测试 API 文档可访问"""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_openapi_schema():
    """测试 OpenAPI 模式"""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()

def test_stocks_endpoint():
    """测试股票端点"""
    response = client.get("/api/v1/stocks")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert body.get("success") is True
    assert "data" in body

def test_sectors_endpoint():
    """测试板块端点"""
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert body.get("success") is True
    assert "data" in body

def test_strength_endpoint():
    """测试强度端点"""
    response = client.get("/api/v1/strength")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert body.get("success") is True
    assert "data" in body

def test_cors_headers():
    """测试 CORS 头"""
    response = client.options(
        "/api/v1/stocks",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" in response.headers

def test_process_time_header():
    """测试请求处理时间头"""
    response = client.get("/health")
    assert "x-process-time" in response.headers
