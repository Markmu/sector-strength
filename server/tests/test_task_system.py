"""
异步任务系统测试

测试任务管理器和任务执行器的基本功能。
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.task_manager import TaskManager
from src.services.task_executor import TaskRegistry, init_task_executor
from src.services.task_handlers import (
    init_sectors_task,
    init_stocks_task,
    init_historical_data_task,
    backfill_by_date_task,
    backfill_by_range_task,
)
from src.db.database import AsyncSessionLocal


@pytest_asyncio.fixture
async def db_session():
    """创建测试数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session
        # 清理：回滚测试创建的数据
        try:
            await session.rollback()
        except RuntimeError as exc:
            if "Event loop is closed" not in str(exc):
                raise


@pytest.mark.asyncio
async def test_task_registry():
    """测试任务注册表"""
    registered_tasks = TaskRegistry.list_registered_tasks()

    expected_tasks = [
        'init_sectors',
        'init_stocks',
        'init_historical_data',
        'backfill_by_date',
        'backfill_by_range',
    ]

    for task in expected_tasks:
        assert task in registered_tasks, f"Task {task} not registered"

    # 验证每个任务都有对应的处理器
    for task_type in registered_tasks:
        handler = TaskRegistry.get_handler(task_type)
        assert handler is not None, f"No handler for task type: {task_type}"
        assert callable(handler), f"Handler for {task_type} is not callable"


@pytest.mark.asyncio
async def test_task_manager_create_and_get(db_session):
    """测试任务管理器的创建和获取功能"""
    manager = TaskManager(db_session)

    # 创建任务
    task = await manager.create_task(
        task_type="init_stocks",
        params={},
        max_retries=3,
        timeout_seconds=3600,
    )

    assert task is not None
    assert task.task_id is not None
    assert task.task_type == "init_stocks"
    assert task.status == "pending"
    assert task.retry_count == 0
    assert task.max_retries == 3

    # 获取任务
    fetched_task = await manager.get_task(task.task_id)
    assert fetched_task is not None
    assert fetched_task.task_id == task.task_id

    # 获取任务参数
    params = await manager.get_task_params(task.task_id)
    assert params == {}


@pytest.mark.asyncio
async def test_task_manager_progress_update(db_session):
    """测试任务进度更新"""
    manager = TaskManager(db_session)

    task = await manager.create_task(
        task_type="test_task",
        params={"test": "value"},
    )

    # 更新进度
    success = await manager.update_progress(task.task_id, 50, 100)
    assert success is True

    # 验证进度
    updated_task = await manager.get_task(task.task_id)
    assert updated_task.progress == 50
    assert updated_task.total == 100
    assert updated_task.percent == 50


@pytest.mark.asyncio
async def test_task_manager_cancel(db_session):
    """测试任务取消"""
    manager = TaskManager(db_session)

    task = await manager.create_task(
        task_type="test_task",
        params={},
    )

    # 取消任务
    success = await manager.cancel_task(task.task_id)
    assert success is True

    # 验证状态
    cancelled_task = await manager.get_task(task.task_id)
    assert cancelled_task.status == "cancelled"
    assert cancelled_task.cancelled_at is not None


@pytest.mark.asyncio
async def test_task_manager_log_message(db_session):
    """测试日志记录"""
    manager = TaskManager(db_session)

    task = await manager.create_task(
        task_type="test_task",
        params={},
    )

    # 记录日志
    await manager.log_message(task.task_id, "INFO", "Test log message")

    # 获取日志
    logs = await manager.get_task_logs(task.task_id)
    assert len(logs) > 0
    assert logs[0].level == "INFO"
    assert logs[0].message == "Test log message"


@pytest.mark.asyncio
async def test_task_manager_list_and_count(db_session):
    """测试任务列表和计数"""
    manager = TaskManager(db_session)

    # 创建多个任务
    task1 = await manager.create_task(task_type="test_task", params={})
    task2 = await manager.create_task(task_type="test_task", params={})

    # 列出任务
    tasks = await manager.list_tasks(limit=10)
    assert len(tasks) >= 2

    # 计数
    count = await manager.count_tasks()
    assert count >= 2


@pytest.mark.asyncio
async def test_task_status_transitions(db_session):
    """测试任务状态转换"""
    manager = TaskManager(db_session)

    task = await manager.create_task(
        task_type="test_task",
        params={},
    )

    # pending -> running
    success = await manager.start_task(task.task_id)
    assert success is True

    running_task = await manager.get_task(task.task_id)
    assert running_task.status == "running"
    assert running_task.started_at is not None

    # running -> completed
    success = await manager.complete_task(task.task_id, success=True)
    assert success is True

    completed_task = await manager.get_task(task.task_id)
    assert completed_task.status == "completed"
    assert completed_task.completed_at is not None


@pytest.mark.asyncio
async def test_task_retry_mechanism(db_session):
    """测试任务重试机制"""
    manager = TaskManager(db_session)

    task = await manager.create_task(
        task_type="test_task",
        params={},
        max_retries=3,
    )

    # 增加重试计数
    success = await manager.increment_retry(task.task_id)
    assert success is True

    task_with_retry = await manager.get_task(task.task_id)
    assert task_with_retry.retry_count == 1

    # 重置为重试
    success = await manager.reset_for_retry(task.task_id)
    assert success is True

    retry_task = await manager.get_task(task.task_id)
    assert retry_task.status == "pending"


@pytest.mark.asyncio
async def test_task_timeout_check(db_session):
    """测试任务超时检查"""
    manager = TaskManager(db_session)

    # 创建一个短超时的任务
    task = await manager.create_task(
        task_type="test_task",
        params={},
        timeout_seconds=1,  # 1秒超时
    )

    # 标记为运行中
    await manager.start_task(task.task_id)

    # 等待超过超时时间
    await asyncio.sleep(2)

    # 检查是否超时
    is_timeout = await manager.check_task_timeout(task.task_id)
    assert is_timeout is True


# 任务处理器测试（不实际执行，只验证存在性）
@pytest.mark.asyncio
async def test_task_handlers_exist():
    """验证所有任务处理器都已正确注册"""
    expected_handlers = {
        'init_sectors': init_sectors_task,
        'init_stocks': init_stocks_task,
        'init_historical_data': init_historical_data_task,
        'backfill_by_date': backfill_by_date_task,
        'backfill_by_range': backfill_by_range_task,
    }

    for task_type, expected_handler in expected_handlers.items():
        actual_handler = TaskRegistry.get_handler(task_type)
        assert actual_handler is not None, f"No handler for {task_type}"
        assert actual_handler == expected_handler, f"Handler mismatch for {task_type}"


@pytest.mark.asyncio
async def test_admin_tasks_api_rejects_migration_without_truncate_confirmation():
    """验证板块迁移任务缺少清空确认时会被拒绝"""
    from src.api.admin.tasks import CreateTaskRequest, create_task

    request = CreateTaskRequest(task_type="init_sectors", params={"sector_type": "industry"})

    with patch("src.api.admin.tasks.TaskRegistry.list_registered_tasks", return_value=["init_sectors"]):
        response = await create_task(
            request=request,
            session=AsyncMock(),
            _admin=SimpleNamespace(id="admin-1"),
        )

    assert response.success is False
    assert "confirm_truncate_executed" in response.message


@pytest.mark.asyncio
async def test_admin_tasks_api_create_task_fields():
    """验证 API 创建任务时 task_type/params/status 字段语义一致"""
    from src.api.admin.tasks import CreateTaskRequest, create_task

    request = CreateTaskRequest(
        task_type="init_sectors",
        params={"sector_type": "industry", "confirm_truncate_executed": True},
    )
    fake_task = SimpleNamespace(
        task_id="task_123",
        task_type="init_sectors",
        to_dict=lambda: {
            "taskId": "task_123",
            "taskType": "init_sectors",
            "status": "pending",
            "progress": 0,
            "total": 0,
            "percent": 0,
            "errorMessage": None,
            "retryCount": 0,
            "maxRetries": 3,
            "timeoutSeconds": 14400,
            "createdBy": "admin-1",
            "createdAt": None,
            "startedAt": None,
            "completedAt": None,
            "cancelledAt": None,
        },
    )

    with patch("src.api.admin.tasks.TaskRegistry.list_registered_tasks", return_value=["init_sectors"]), \
         patch("src.api.admin.tasks.TaskManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.create_task = AsyncMock(return_value=fake_task)

        response = await create_task(
            request=request,
            session=AsyncMock(),
            _admin=SimpleNamespace(id="admin-1"),
        )

    assert response.success is True
    assert response.data["taskType"] == "init_sectors"
    assert response.data["status"] == "pending"
    create_call = mock_manager.create_task.call_args.kwargs
    assert create_call["params"]["sector_type"] == "industry"
    assert create_call["params"]["confirm_truncate_executed"] is True


@pytest.mark.asyncio
async def test_admin_tasks_api_rejects_invalid_sector_type():
    """验证 init_sectors 仅允许 industry/concept。"""
    from src.api.admin.tasks import CreateTaskRequest, create_task

    request = CreateTaskRequest(
        task_type="init_sectors",
        params={"sector_type": "invalid", "confirm_truncate_executed": True},
    )

    with patch("src.api.admin.tasks.TaskRegistry.list_registered_tasks", return_value=["init_sectors"]):
        response = await create_task(
            request=request,
            session=AsyncMock(),
            _admin=SimpleNamespace(id="admin-1"),
        )

    assert response.success is False
    assert "sector_type" in response.message


@pytest.mark.asyncio
async def test_admin_tasks_api_rejects_invalid_init_sector_historical_data_days():
    """验证 init_sector_historical_data 的 days 参数范围校验。"""
    from src.api.admin.tasks import CreateTaskRequest, create_task

    request = CreateTaskRequest(
        task_type="init_sector_historical_data",
        params={"days": 0, "confirm_truncate_executed": True},
    )

    with patch(
        "src.api.admin.tasks.TaskRegistry.list_registered_tasks",
        return_value=["init_sector_historical_data"],
    ):
        response = await create_task(
            request=request,
            session=AsyncMock(),
            _admin=SimpleNamespace(id="admin-1"),
        )

    assert response.success is False
    assert "days" in response.message


@pytest.mark.asyncio
async def test_admin_tasks_api_rejects_invalid_init_sector_historical_data_date_range():
    """验证 init_sector_historical_data 的日期范围校验。"""
    from src.api.admin.tasks import CreateTaskRequest, create_task

    request = CreateTaskRequest(
        task_type="init_sector_historical_data",
        params={
            "start_date": "2026-01-10",
            "end_date": "2026-01-01",
            "confirm_truncate_executed": True,
        },
    )

    with patch(
        "src.api.admin.tasks.TaskRegistry.list_registered_tasks",
        return_value=["init_sector_historical_data"],
    ):
        response = await create_task(
            request=request,
            session=AsyncMock(),
            _admin=SimpleNamespace(id="admin-1"),
        )

    assert response.success is False
    assert "start_date" in response.message


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
