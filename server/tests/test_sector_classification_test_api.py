"""
分类算法测试 API 端点测试

测试 Story 4.2: 分类算法测试功能的 API 端点：
- POST /api/v1/admin/sector-classification/test
- 管理员权限验证
- 测试结果返回
- 审计日志记录
"""

import pytest
import pytest_asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from httpx import AsyncClient, ASGITransport

from main import app
from src.models.sector import Sector
from src.models.audit_log import AuditLog
from src.models.user import User


@pytest.fixture
def mock_admin_user():
    """模拟管理员用户"""
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "admin@example.com"
    user.username = "admin"
    user.role = "admin"
    user.is_admin = True
    user.has_role = lambda role: role == "admin"
    return user


@pytest.fixture
def mock_regular_user():
    """模拟普通用户"""
    user = MagicMock(spec=User)
    user.id = 2
    user.email = "user@example.com"
    user.username = "user"
    user.role = "user"
    user.is_admin = False
    user.has_role = lambda role: role == "user"
    return user


@pytest_asyncio.fixture
async def test_sectors(test_session: AsyncSession):
    """创建测试板块数据"""
    sectors = [
        Sector(
            name='测试板块A',
            code='TEST001',
            type='industry',
            description='测试板块A',
            strength_score=80.0,
        ),
        Sector(
            name='测试板块B',
            code='TEST002',
            type='concept',
            description='测试板块B',
            strength_score=60.0,
        ),
        Sector(
            name='测试板块C',
            code='TEST003',
            type='industry',
            description='测试板块C',
            strength_score=40.0,
        ),
    ]

    test_session.add_all(sectors)
    await test_session.commit()

    for sector in sectors:
        await test_session.refresh(sector)

    return sectors


class TestClassificationTestAPI:
    """分类算法测试 API 端点测试"""

    @pytest.mark.asyncio
    async def test_classification_test_as_admin_success(self, client: AsyncClient, mock_admin_user, test_sectors):
        """测试管理员成功执行分类测试"""
        with patch('src.api.v1.endpoints.admin_sector_classifications.get_current_user') as mock_auth:
            mock_auth.return_value = mock_admin_user

            with patch('src.api.v1.endpoints.admin_sector_classifications.SectorClassificationService') as mock_service_class:
                # Mock 服务类
                mock_service = MagicMock()
                mock_service.calculate_classification = AsyncMock()
                mock_service_class.return_value = mock_service

                with patch('src.api.v1.endpoints.admin_sector_classifications.AuditService') as mock_audit_class:
                    # Mock 审计服务
                    mock_audit_class.log_classification_test = AsyncMock()
                    mock_audit_class.return_value = MagicMock()

                    response = await client.post(
                        "/api/v1/admin/sector-classification/test"
                    )

                    assert response.status_code == 200
                    data = response.json()

                    assert data["success"] is True
                    assert "data" in data
                    assert data["data"]["total_count"] == 3
                    assert data["data"]["success_count"] == 3
                    assert data["data"]["failure_count"] == 0
                    assert "duration_ms" in data["data"]
                    assert "timestamp" in data["data"]

    @pytest.mark.asyncio
    async def test_classification_test_regular_user_denied(self, client: AsyncClient, mock_regular_user):
        """测试普通用户被拒绝访问"""
        with patch('src.api.v1.endpoints.admin_sector_classifications.get_current_user') as mock_auth:
            mock_auth.return_value = mock_regular_user

            response = await client.post(
                "/api/v1/admin/sector-classification/test"
            )

            assert response.status_code == 403
            data = response.json()
            assert "权限不足" in data["detail"]

    @pytest.mark.asyncio
    async def test_classification_test_empty_sectors(self, client: AsyncClient, mock_admin_user, test_session: AsyncSession):
        """测试空板块列表"""
        # 确保数据库中没有板块
        result = await test_session.execute(select(Sector))
        sectors = result.scalars().all()
        for sector in sectors:
            await test_session.delete(sector)
        await test_session.commit()

        with patch('src.api.v1.endpoints.admin_sector_classifications.get_current_user') as mock_auth:
            mock_auth.return_value = mock_admin_user

            with patch('src.api.v1.endpoints.admin_sector_classifications.AuditService') as mock_audit_class:
                mock_audit_class.log_classification_test = AsyncMock()
                mock_audit_class.return_value = MagicMock()

                response = await client.post(
                    "/api/v1/admin/sector-classification/test"
                )

                assert response.status_code == 200
                data = response.json()

                assert data["success"] is True
                assert data["data"]["total_count"] == 0
                assert data["data"]["success_count"] == 0
                assert data["data"]["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_classification_test_partial_failure(self, client: AsyncClient, mock_admin_user, test_sectors):
        """测试部分失败场景"""
        with patch('src.api.v1.endpoints.admin_sector_classifications.get_current_user') as mock_auth:
            mock_auth.return_value = mock_admin_user

            with patch('src.api.v1.endpoints.admin_sector_classifications.SectorClassificationService') as mock_service_class:
                # Mock 服务类，让第二个板块失败
                mock_service = MagicMock()

                async def mock_calc(sector_id):
                    if sector_id == test_sectors[1].id:
                        raise Exception("数据不足")
                    # 其他板块成功

                mock_service.calculate_classification = AsyncMock(side_effect=mock_calc)
                mock_service_class.return_value = mock_service

                with patch('src.api.v1.endpoints.admin_sector_classifications.AuditService') as mock_audit_class:
                    mock_audit_class.log_classification_test = AsyncMock()
                    mock_audit_class.return_value = MagicMock()

                    response = await client.post(
                        "/api/v1/admin/sector-classification/test"
                    )

                    assert response.status_code == 200
                    data = response.json()

                    assert data["success"] is True
                    assert data["data"]["total_count"] == 3
                    assert data["data"]["success_count"] == 2
                    assert data["data"]["failure_count"] == 1
                    assert "failures" in data["data"]
                    assert len(data["data"]["failures"]) == 1
                    assert data["data"]["failures"][0]["sector_name"] == "测试板块B"

    @pytest.mark.asyncio
    async def test_classification_test_audit_log_created(self, client: AsyncClient, mock_admin_user, test_sectors):
        """测试审计日志被创建"""
        with patch('src.api.v1.endpoints.admin_sector_classifications.get_current_user') as mock_auth:
            mock_auth.return_value = mock_admin_user

            with patch('src.api.v1.endpoints.admin_sector_classifications.SectorClassificationService') as mock_service_class:
                mock_service = MagicMock()
                mock_service.calculate_classification = AsyncMock()
                mock_service_class.return_value = mock_service

                with patch('src.api.v1.endpoints.admin_sector_classifications.AuditService') as mock_audit_class:
                    mock_log = MagicMock()
                    mock_audit_class.log_classification_test = AsyncMock(return_value=mock_log)

                    response = await client.post(
                        "/api/v1/admin/sector-classification/test",
                        headers={"User-Agent": "TestClient/1.0"}
                    )

                    # 验证审计日志被调用
                    assert mock_audit_class.log_classification_test.called

                    # 获取调用参数
                    call_args = mock_audit_class.log_classification_test.call_args
                    assert call_args is not None

                    # 验证关键参数
                    kwargs = call_args.kwargs
                    assert "user" in kwargs
                    assert kwargs["user"] == mock_admin_user
                    assert "total_count" in kwargs
                    assert kwargs["total_count"] == 3
                    assert "success_count" in kwargs
                    assert "duration_ms" in kwargs

    @pytest.mark.asyncio
    async def test_classification_test_records_client_info(self, client: AsyncClient, mock_admin_user, test_sectors):
        """测试客户端信息被记录"""
        with patch('src.api.v1.endpoints.admin_sector_classifications.get_current_user') as mock_auth:
            mock_auth.return_value = mock_admin_user

            with patch('src.api.v1.endpoints.admin_sector_classifications.SectorClassificationService') as mock_service_class:
                mock_service = MagicMock()
                mock_service.calculate_classification = AsyncMock()
                mock_service_class.return_value = mock_service

                with patch('src.api.v1.endpoints.admin_sector_classifications.AuditService') as mock_audit_class:
                    mock_audit_class.log_classification_test = AsyncMock(return_value=MagicMock())

                    response = await client.post(
                        "/api/v1/admin/sector-classification/test",
                        headers={
                            "User-Agent": "Mozilla/5.0 TestBrowser",
                            "X-Forwarded-For": "192.168.1.100"
                        }
                    )

                    # 验证审计日志包含客户端信息
                    call_args = mock_audit_class.log_classification_test.call_args
                    kwargs = call_args.kwargs

                    # IP 和 User-Agent 应该被传递（虽然可能为 None）
                    assert "ip_address" in kwargs
                    assert "user_agent" in kwargs


class TestAuditServiceIntegration:
    """审计服务集成测试"""

    @pytest.mark.asyncio
    async def test_audit_service_log_classification_test_success(self, test_session: AsyncSession, mock_admin_user):
        """测试审计服务记录成功的分类测试"""
        from src.services.audit_service import AuditService

        log_entry = await AuditService.log_classification_test(
            db=test_session,
            user=mock_admin_user,
            total_count=50,
            success_count=50,
            failure_count=0,
            duration_ms=1234,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )

        await test_session.commit()
        await test_session.refresh(log_entry)

        assert log_entry.action == "test_classification"
        assert log_entry.resource_type == "sector_classification"
        assert log_entry.status == "success"
        assert log_entry.user_id == mock_admin_user.id
        assert log_entry.ip_address == "192.168.1.1"
        assert log_entry.user_agent == "Mozilla/5.0"
        assert "全部计算完成" in log_entry.result

    @pytest.mark.asyncio
    async def test_audit_service_log_classification_test_partial_failure(self, test_session: AsyncSession, mock_admin_user):
        """测试审计服务记录部分失败"""
        from src.services.audit_service import AuditService

        failures = [
            {"sector_id": "1", "sector_name": "板块A", "error": "数据不足"},
            {"sector_id": "2", "sector_name": "板块B", "error": "计算错误"},
        ]

        log_entry = await AuditService.log_classification_test(
            db=test_session,
            user=mock_admin_user,
            total_count=50,
            success_count=48,
            failure_count=2,
            duration_ms=2345,
            failures=failures,
        )

        await test_session.commit()
        await test_session.refresh(log_entry)

        assert log_entry.status == "partial"
        assert log_entry.details["failure_count"] == 2
        assert log_entry.details["failures"] == failures

    @pytest.mark.asyncio
    async def test_audit_service_log_classification_test_total_failure(self, test_session: AsyncSession, mock_admin_user):
        """测试审计服务记录完全失败"""
        from src.services.audit_service import AuditService

        log_entry = await AuditService.log_classification_test(
            db=test_session,
            user=mock_admin_user,
            total_count=10,
            success_count=0,
            failure_count=10,
            duration_ms=500,
        )

        await test_session.commit()
        await test_session.refresh(log_entry)

        assert log_entry.status == "failed"
        assert "全部计算失败" in log_entry.result

    @pytest.mark.asyncio
    async def test_audit_service_query_logs(self, test_session: AsyncSession, mock_admin_user):
        """测试审计服务查询日志"""
        from src.services.audit_service import AuditService
        from datetime import datetime

        # 创建几条日志
        await AuditService.log_classification_test(
            db=test_session,
            user=mock_admin_user,
            total_count=10,
            success_count=10,
            failure_count=0,
            duration_ms=100,
        )

        await AuditService.log_classification_test(
            db=test_session,
            user=mock_admin_user,
            total_count=20,
            success_count=18,
            failure_count=2,
            duration_ms=200,
        )

        await test_session.commit()

        # 查询所有日志
        logs, total = await AuditService.query_logs(test_session)

        assert total >= 2
        assert len(logs) >= 2

        # 查询特定操作类型的日志
        logs, total = await AuditService.query_logs(
            test_session,
            action="test_classification"
        )

        assert total >= 2
        for log in logs:
            assert log.action == "test_classification"
