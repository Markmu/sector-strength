"""
管理接口测试

测试管理 API 端点的功能。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def admin_headers():
    """管理员请求头"""
    return {"api_key": "admin-secret-key-change-in-production"}


class TestAdminAPI:
    """管理接口测试"""

    def test_trigger_update_success(self, client, admin_headers):
        """测试手动触发数据更新"""
        with patch('src.api.v1.admin.DataCollector') as mock_collector_class:
            mock_collector = MagicMock()
            mock_collector.get_latest_update_status = AsyncMock(return_value=None)
            mock_collector_class.return_value = mock_collector

            response = client.post("/v1/admin/data/update", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['success'] is True
            assert 'task_id' in data['data']

    def test_trigger_update_invalid_api_key(self, client):
        """测试手动触发数据更新 - 无效 API Key"""
        response = client.post(
            "/v1/admin/data/update",
            headers={"api_key": "invalid-key"}
        )

        assert response.status_code == 401

    def test_get_update_status(self, client, admin_headers):
        """测试获取更新状态"""
        with patch('src.api.v1.admin.DataCollector') as mock_collector_class:
            mock_collector = MagicMock()
            mock_collector.get_latest_update_status = AsyncMock(return_value={
                'success': True,
                'sectors_updated': 10
            })
            mock_collector_class.return_value = mock_collector

            response = client.get("/v1/admin/data/update-status", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True

    def test_get_update_status_no_records(self, client, admin_headers):
        """测试获取更新状态 - 无记录"""
        with patch('src.api.v1.admin.DataCollector') as mock_collector_class:
            mock_collector = MagicMock()
            mock_collector.get_latest_update_status = AsyncMock(return_value=None)
            mock_collector_class.return_value = mock_collector

            response = client.get("/v1/admin/data/update-status", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data'] is None

    def test_get_update_history(self, client, admin_headers):
        """测试获取更新历史"""
        with patch('src.api.v1.admin.DataCollector') as mock_collector_class:
            mock_collector = MagicMock()
            mock_collector.get_update_history = AsyncMock(return_value={
                'items': [],
                'total': 0
            })
            mock_collector_class.return_value = mock_collector

            response = client.get("/v1/admin/data/update-history", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True

    def test_cancel_running_update(self, client, admin_headers):
        """测试取消正在运行的更新"""
        response = client.post("/v1/admin/data/update/cancel", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert '待实现' in data['message']


class TestSchedulerAdminAPI:
    """调度器管理接口测试"""

    def test_get_scheduler_status(self, client, admin_headers):
        """测试获取调度器状态"""
        with patch('src.api.v1.admin.get_job_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running = False
            mock_manager.get_jobs.return_value = {
                'daily_data_update': {'next_run_time': '2024-01-10 15:30:00'}
            }
            mock_get_manager.return_value = mock_manager

            response = client.get("/v1/admin/data/scheduler/status", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['is_running'] is False

    def test_start_scheduler(self, client, admin_headers):
        """测试启动调度器"""
        with patch('src.api.v1.admin.get_job_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager

            response = client.post("/v1/admin/data/scheduler/start", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            mock_manager.start.assert_called_once()

    def test_stop_scheduler(self, client, admin_headers):
        """测试停止调度器"""
        with patch('src.api.v1.admin.get_job_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager

            response = client.post("/v1/admin/data/scheduler/stop", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            mock_manager.shutdown.assert_called_once()

    def test_trigger_scheduler_job_success(self, client, admin_headers):
        """测试手动触发调度任务 - 成功"""
        with patch('src.api.v1.admin.get_job_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.trigger_job = AsyncMock(return_value=True)
            mock_get_manager.return_value = mock_manager

            response = client.post("/v1/admin/data/scheduler/trigger/daily_data_update", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True

    def test_trigger_scheduler_job_not_found(self, client, admin_headers):
        """测试手动触发调度任务 - 任务不存在"""
        with patch('src.api.v1.admin.get_job_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.trigger_job = AsyncMock(return_value=False)
            mock_get_manager.return_value = mock_manager

            response = client.post("/v1/admin/data/scheduler/trigger/nonexistent", headers=admin_headers)

            assert response.status_code == 404


class TestDataQualityAdminAPI:
    """数据质量管理接口测试"""

    def test_check_data_quality(self, client, admin_headers):
        """测试数据质量检查"""
        with patch('src.api.v1.admin.DataQualityChecker') as mock_checker_class:
            mock_checker = MagicMock()
            mock_checker.check_data_integrity = AsyncMock(return_value={
                'has_issues': False,
                'issues': []
            })
            mock_checker.get_data_quality_report = AsyncMock(return_value={
                'stock_count': 100
            })
            mock_checker_class.return_value = mock_checker

            response = client.get("/v1/admin/data/quality/check", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'integrity' in data['data']


class TestCacheAdminAPI:
    """缓存管理接口测试"""

    def test_get_cache_stats(self, client, admin_headers):
        """测试获取缓存统计"""
        with patch('src.api.v1.admin.get_cache_manager') as mock_get_cache:
            mock_cache = MagicMock()
            mock_get_cache.return_value = mock_cache

            response = client.get("/v1/admin/data/cache/stats", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True

    def test_clear_cache_all(self, client, admin_headers):
        """测试清除所有缓存"""
        with patch('src.api.v1.admin.get_cache_manager') as mock_get_cache:
            mock_cache = MagicMock()
            mock_cache.clear_all = AsyncMock(return_value=50)
            mock_get_cache.return_value = mock_cache

            response = client.post("/v1/admin/data/cache/clear", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['cleared_count'] == 50

    def test_clear_cache_with_pattern(self, client, admin_headers):
        """测试按模式清除缓存"""
        with patch('src.api.v1.admin.get_cache_manager') as mock_get_cache:
            mock_cache = MagicMock()
            mock_cache.clear_pattern = AsyncMock(return_value=10)
            mock_get_cache.return_value = mock_cache

            response = client.post(
                "/v1/admin/data/cache/clear?pattern=sectors",
                headers=admin_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['cleared_count'] == 10


class TestSystemHealthAdminAPI:
    """系统健康检查接口测试"""

    def test_get_system_health(self, client, admin_headers):
        """测试获取系统健康状态"""
        with patch('src.api.v1.admin.get_job_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.is_running = True
            mock_get_manager.return_value = mock_manager

            response = client.get("/v1/admin/data/health", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['status'] == 'healthy'
            assert data['data']['scheduler'] == 'running'
