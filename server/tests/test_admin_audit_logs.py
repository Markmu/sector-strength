"""
测试管理员审计日志 API 端点
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.main import app
from src.db.database import get_db
from src.models.user import User
from src.models.audit_log import AuditLog
from src.api.v1.endpoints.auth import get_current_user


class MockAdminUser:
    """模拟管理员用户"""
    id = 1
    username = "admin"
    email = "admin@example.com"
    is_admin = True


class MockNormalUser:
    """模拟普通用户"""
    id = 2
    username = "user"
    email = "user@example.com"
    is_admin = False


@pytest.mark.asyncio
async def test_get_audit_logs_success(db: AsyncSession, client: TestClient):
    """测试成功获取审计日志"""

    def mock_get_current_user():
        return MockAdminUser()

    # 正确覆盖依赖注入
    app.dependency_overrides[get_current_user] = mock_get_current_user

    # 创建测试数据
    log1 = AuditLog(
        user_id=1,
        username="admin",
        action="test_classification",
        resource_type="sector",
        details='{"test": "data"}',
        ip_address="192.168.1.100",
        status="success",
        result="测试成功",
        created_at=datetime.now() - timedelta(hours=1)
    )
    log2 = AuditLog(
        user_id=1,
        username="admin",
        action="view_config",
        resource_type=None,
        details=None,
        ip_address="192.168.1.100",
        status="success",
        result="查看配置",
        created_at=datetime.now() - timedelta(hours=2)
    )
    db.add(log1)
    db.add(log2)
    await db.commit()

    response = client.get("/api/v1/admin/audit-logs")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "items" in data["data"]
    assert "total" in data["data"]
    assert "page" in data["data"]
    assert "total_pages" in data["data"]

    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_audit_logs_with_filters(db: AsyncSession, client: TestClient):
    """测试带筛选条件的审计日志查询"""

    def mock_get_current_user():
        return MockAdminUser()

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # 创建测试数据
    log1 = AuditLog(
        user_id=1,
        username="admin",
        action="test_classification",
        resource_type=None,
        details=None,
        ip_address="192.168.1.100",
        status="success",
        result="测试成功",
        created_at=datetime.now()
    )
    db.add(log1)
    await db.commit()

    # 使用正确的参数名 action_type
    response = client.get("/api/v1/admin/audit-logs?action_type=test_classification&page=1&page_size=10")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 10

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_audit_logs_non_admin(db: AsyncSession, client: TestClient):
    """测试非管理员用户无法访问"""

    def mock_get_current_user():
        return MockNormalUser()

    app.dependency_overrides[get_current_user] = mock_get_current_user

    response = client.get("/api/v1/admin/audit-logs")

    assert response.status_code == 403
    data = response.json()
    assert "权限不足" in data["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cleanup_old_audit_logs(db: AsyncSession, client: TestClient):
    """测试清理过期审计日志"""

    def mock_get_current_user():
        return MockAdminUser()

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # 创建 7 个月前的过期日志
    old_log = AuditLog(
        user_id=1,
        username="admin",
        action="test_classification",
        resource_type=None,
        details=None,
        ip_address="192.168.1.100",
        status="success",
        result="过期日志",
        created_at=datetime.now() - timedelta(days=210)  # 7 个月前
    )
    db.add(old_log)
    await db.commit()

    response = client.post("/api/v1/admin/audit-logs/cleanup")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "deleted_count" in data["data"]
    assert data["data"]["deleted_count"] >= 0

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_audit_logs_date_filter(db: AsyncSession, client: TestClient):
    """测试日期范围筛选"""

    def mock_get_current_user():
        return MockAdminUser()

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # 创建不同日期的日志
    now = datetime.now()
    log1 = AuditLog(
        user_id=1,
        username="admin",
        action="test_classification",
        resource_type=None,
        details=None,
        ip_address="192.168.1.100",
        status="success",
        result="最近日志",
        created_at=now
    )
    db.add(log1)
    await db.commit()

    # 测试开始日期筛选
    start_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    response = client.get(f"/api/v1/admin/audit-logs?start_date={start_date}")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_audit_logs_invalid_date_format(db: AsyncSession, client: TestClient):
    """测试无效日期格式"""

    def mock_get_current_user():
        return MockAdminUser()

    app.dependency_overrides[get_current_user] = mock_get_current_user

    response = client.get("/api/v1/admin/audit-logs?start_date=invalid-date")

    assert response.status_code == 400
    data = response.json()
    assert "格式无效" in data["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_audit_logs_pagination(db: AsyncSession, client: TestClient):
    """测试分页功能"""

    def mock_get_current_user():
        return MockAdminUser()

    app.dependency_overrides[get_current_user] = mock_get_current_user

    # 创建多条日志
    for i in range(25):
        log = AuditLog(
            user_id=1,
            username="admin",
            action="test_action",
            resource_type=None,
            details=None,
            ip_address="192.168.1.100",
            status="success",
            result=f"测试日志 {i}",
            created_at=datetime.now() - timedelta(hours=i)
        )
        db.add(log)
    await db.commit()

    # 测试第一页
    response = client.get("/api/v1/admin/audit-logs?page=1&page_size=20")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["page"] == 1
    assert data["data"]["page_size"] == 20
    assert len(data["data"]["items"]) <= 20

    # 测试第二页
    response = client.get("/api/v1/admin/audit-logs?page=2&page_size=20")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["page"] == 2

    app.dependency_overrides.clear()

