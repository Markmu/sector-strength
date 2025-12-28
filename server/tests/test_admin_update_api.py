"""
数据更新 API 端点测试

测试 /api/admin/update 端点的错误处理和边界条件。
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app


@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_admin_user():
    """模拟管理员用户"""
    return {
        "id": "admin-id",
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True
    }


@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
class TestAdminUpdateAPI:
    """数据更新 API 测试"""

    async def test_update_by_date_success(self, client, mock_admin_user):
        """测试成功按日期补齐"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            mock_auth.return_value = mock_admin_user

            response = client.post(
                "/v1/admin/update/by-date",
                json={
                    "date": "2025-12-20",
                    "overwrite": False
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该返回任务创建成功
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "task_id" in data["data"]

    async def test_update_by_date_future_date_rejected(self, client, mock_admin_user):
        """测试未来日期被拒绝"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            mock_auth.return_value = mock_admin_user

            future_date = (date.today() + timedelta(days=1)).isoformat()

            response = client.post(
                "/v1/admin/update/by-date",
                json={
                    "date": future_date,
                    "overwrite": False
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该拒绝未来日期
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "未来" in data["message"]

    async def test_update_by_date_invalid_target_type(self, client, mock_admin_user):
        """测试无效的 target_type"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            mock_auth.return_value = mock_admin_user

            response = client.post(
                "/v1/admin/update/by-date",
                json={
                    "date": "2025-12-20",
                    "overwrite": False,
                    "target_type": "invalid"  # 无效值
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该返回验证错误
            assert response.status_code == 422  # Unprocessable Entity

    async def test_update_by_date_stock_without_target_id(self, client, mock_admin_user):
        """测试 target_type=stock 但未提供 target_id"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            mock_auth.return_value = mock_admin_user

            response = client.post(
                "/v1/admin/update/by-date",
                json={
                    "date": "2025-12-20",
                    "overwrite": False,
                    "target_type": "stock"
                    # 缺少 target_id
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该返回验证错误
            assert response.status_code == 422

    async def test_update_by_range_invalid_date_order(self, client, mock_admin_user):
        """测试开始日期晚于结束日期"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            mock_auth.return_value = mock_admin_user

            response = client.post(
                "/v1/admin/update/by-range",
                json={
                    "start_date": "2025-12-25",
                    "end_date": "2025-12-20",  # 早于开始日期
                    "overwrite": False
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该返回验证错误
            assert response.status_code == 422

    async def test_update_by_range_too_many_days(self, client, mock_admin_user):
        """测试日期范围超过 365 天"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            mock_auth.return_value = mock_admin_user

            start = (date.today() - timedelta(days=400)).isoformat()
            end = date.today().isoformat()

            response = client.post(
                "/v1/admin/update/by-range",
                json={
                    "start_date": start,
                    "end_date": end,
                    "overwrite": False
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该返回验证错误
            assert response.status_code == 422

    async def test_update_by_range_future_end_date_rejected(self, client, mock_admin_user):
        """测试未来结束日期被拒绝"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            mock_auth.return_value = mock_admin_user

            future_end = (date.today() + timedelta(days=1)).isoformat()

            response = client.post(
                "/v1/admin/update/by-range",
                json={
                    "start_date": "2025-12-20",
                    "end_date": future_end,
                    "overwrite": False
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该拒绝未来日期
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "未来" in data["message"]

    async def test_get_missing_dates_success(self, client, mock_admin_user, mock_session):
        """测试成功查询缺失日期"""
        with patch('src.api.admin.update.require_admin') as mock_auth, \
             patch('src.api.admin.update.get_session') as mock_get_session:

            mock_auth.return_value = mock_admin_user
            mock_get_session.return_value = mock_session

            # 模拟返回数据
            mock_session.execute.return_value.all.return_value = []

            response = client.get(
                "/v1/admin/update/missing-dates",
                params={
                    "stock_symbol": "000001",
                    "start_date": "2025-12-01",
                    "end_date": "2025-12-20"
                },
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该返回成功
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    async def test_get_status_nonexistent_task(self, client, mock_admin_user):
        """测试查询不存在的任务"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            mock_auth.return_value = mock_admin_user

            response = client.get(
                "/v1/admin/update/status/nonexistent-task-id",
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该返回任务不存在
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "不存在" in data["message"]

    async def test_cancel_completed_task_fails(self, client, mock_admin_user):
        """测试取消已完成的任务应该失败"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            mock_auth.return_value = mock_admin_user

            # 首先需要模拟一个已存在的任务
            from src.api.admin import update
            task_id = "completed-task"
            update._init_tasks[task_id] = {
                "task_id": task_id,
                "status": "completed",
                "current": 100,
                "total": 100,
                "message": "已完成",
                "result": None
            }

            response = client.post(
                f"/v1/admin/update/cancel/{task_id}",
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该返回无法取消
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    async def test_cancel_nonexistent_task_fails(self, client, mock_admin_user):
        """测试取消不存在的任务应该失败"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            mock_auth.return_value = mock_admin_user

            response = client.post(
                "/v1/admin/update/cancel/nonexistent-task",
                headers={"Authorization": "Bearer fake-token"}
            )

            # 应该返回任务不存在
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "不存在" in data["message"]

    async def test_unauthorized_access_rejected(self, client):
        """测试未授权访问被拒绝"""
        with patch('src.api.admin.update.require_admin') as mock_auth:
            # 模拟未授权
            from fastapi import HTTPException
            mock_auth.side_effect = HTTPException(status_code=403, detail="Forbidden")

            response = client.post(
                "/v1/admin/update/by-date",
                json={
                    "date": "2025-12-20",
                    "overwrite": False
                },
                headers={"Authorization": "Bearer invalid-token"}
            )

            # 应该返回 403
            assert response.status_code == 403
