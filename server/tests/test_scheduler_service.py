"""
调度器服务测试

测试定时任务调度器和作业管理的功能。
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, MagicMock
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.services.scheduler.job_manager import JobManager, get_job_manager


@pytest.fixture
def job_manager():
    """创建作业管理器实例（简化版，不启动实际调度器）"""
    # Reset singleton
    import src.services.scheduler.job_manager as jm
    jm._job_manager = None

    # Create a mock scheduler for testing
    mock_scheduler = MagicMock(spec=AsyncIOScheduler)
    mock_scheduler.running = False

    # Track jobs added to the scheduler
    jobs_dict = {}

    def mock_add_job(func, trigger, **kwargs):
        job_id = kwargs.get('id', str(id(func)))
        # Create a mock job object
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.name = kwargs.get('name', job_id)
        mock_job.trigger = trigger
        # Capture scheduling options (max_instances etc.) for assertion
        mock_job.max_instances = kwargs.get('max_instances')
        mock_job.kwargs = kwargs
        jobs_dict[job_id] = mock_job
        return mock_job

    def mock_get_job(job_id):
        return jobs_dict.get(job_id)

    def mock_get_jobs():
        return list(jobs_dict.values())

    mock_scheduler.add_job = mock_add_job
    mock_scheduler.get_job = mock_get_job
    mock_scheduler.get_jobs = mock_get_jobs
    mock_scheduler.running = False

    manager = JobManager.__new__(JobManager)
    manager.scheduler = mock_scheduler

    yield manager

    # Cleanup
    if manager.scheduler.running:
        manager.scheduler.shutdown(wait=False)


@pytest.fixture
def real_job_manager():
    """创建真实的作业管理器实例（用于测试启动/关闭）"""
    # Reset singleton
    import src.services.scheduler.job_manager as jm
    jm._job_manager = None

    manager = JobManager()

    yield manager

    # Cleanup
    if manager.is_running:
        manager.shutdown(wait=False)


class TestJobManager:
    """作业管理器测试"""

    def test_init(self):
        """测试初始化"""
        # Reset singleton
        import src.services.scheduler.job_manager as jm
        jm._job_manager = None

        manager = JobManager()
        assert isinstance(manager.scheduler, AsyncIOScheduler)
        assert manager.is_running is False

    def test_singleton(self):
        """测试单例模式"""
        # Reset singleton
        import src.services.scheduler.job_manager as jm
        jm._job_manager = None

        manager1 = get_job_manager()
        manager2 = get_job_manager()

        assert manager1 is manager2

    def test_register_jobs(self, job_manager):
        """默认（开关 false）只注册 sector_fund_flow_snapshot，日级 job 不注册"""
        job_manager._register_jobs()

        jobs = job_manager.scheduler.get_jobs()
        job_ids = [job.id for job in jobs]

        # 板块资金流快照始终注册
        assert 'sector_fund_flow_snapshot' in job_ids
        # 开发期默认停用的 job 不应注册
        assert 'daily_data_update' not in job_ids
        assert 'data_quality_check' not in job_ids
        assert 'cache_cleanup' not in job_ids

    def test_daily_data_update_job_disabled_by_default(self, job_manager):
        """ENABLE_DAILY_UPDATE_JOB 默认 false 时 daily_data_update 不注册"""
        from src.core.settings import settings
        assert settings.enable_daily_update_job is False

        job_manager._register_jobs()

        job = job_manager.scheduler.get_job('daily_data_update')
        assert job is None

    def test_daily_data_update_job_when_enabled(self, job_manager, monkeypatch):
        """ENABLE_DAILY_UPDATE_JOB=True 时 daily_data_update 按 18:00 Asia/Shanghai 注册"""
        from src.core.settings import settings
        monkeypatch.setattr(settings, 'enable_daily_update_job', True)

        job_manager._register_jobs()

        job = job_manager.scheduler.get_job('daily_data_update')
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)
        # trigger 字段：hour=18, minute=0
        field_map = {f.name: str(f) for f in job.trigger.fields}
        assert field_map['hour'] == '18'
        assert field_map['minute'] == '0'
        # 不使用 day_of_week 工作日表达式（守卫由 collector 内本地日历完成）
        assert field_map['day_of_week'] == '*'
        # 时区 Asia/Shanghai
        assert str(job.trigger.timezone) == 'Asia/Shanghai'
        # 防止并发执行
        assert job.max_instances == 1

    def test_data_quality_check_job_disabled(self, job_manager):
        """数据质量检查 job 当前停用（保留覆盖语义，不删测试）"""
        job_manager._register_jobs()

        job = job_manager.scheduler.get_job('data_quality_check')
        # 仍按惯例注释停用，恢复时此处改为断言 IntervalTrigger
        assert job is None

    def test_cache_cleanup_job_disabled(self, job_manager):
        """缓存清理 job 当前停用（保留覆盖语义，不删测试）"""
        job_manager._register_jobs()

        job = job_manager.scheduler.get_job('cache_cleanup')
        # 仍按惯例注释停用，恢复时此处改为断言 IntervalTrigger
        assert job is None

    @pytest.mark.asyncio
    async def test_start(self, real_job_manager):
        """测试启动调度器"""
        # Check if scheduler is not running initially
        assert real_job_manager.is_running is False

        # Start the scheduler (needs event loop)
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        real_job_manager.start()

        # Verify it's now running
        assert real_job_manager.scheduler.running is True

        # Shutdown to clean up
        real_job_manager.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_shutdown(self, real_job_manager):
        """测试关闭调度器"""
        # Start the scheduler first
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        real_job_manager.start()
        assert real_job_manager.scheduler.running is True

        # Shutdown the scheduler - wait for completion
        real_job_manager.shutdown(wait=True)

        # APScheduler's running state may not immediately reflect shutdown
        # The important thing is shutdown() was called and scheduler is stopped
        # Verify is_running property reflects the stopped state
        assert real_job_manager.is_running is False

    def test_get_jobs(self, job_manager):
        """测试获取所有任务（默认态：sector_fund_flow_snapshot 在，日级 job 不在）"""
        job_manager._register_jobs()
        jobs = job_manager.get_jobs()

        assert isinstance(jobs, dict)
        assert 'sector_fund_flow_snapshot' in jobs
        assert 'daily_data_update' not in jobs
        assert 'data_quality_check' not in jobs
        assert 'cache_cleanup' not in jobs

    @pytest.mark.asyncio
    async def test_trigger_job_success(self, job_manager):
        """测试触发指定任务 - 成功（用默认注册的 sector_fund_flow_snapshot）"""
        job_manager._register_jobs()

        # Mock the job function
        with patch.object(job_manager, '_sector_fund_flow_snapshot', new_callable=AsyncMock) as mock_task:
            result = await job_manager.trigger_job('sector_fund_flow_snapshot')
            assert result is True

    @pytest.mark.asyncio
    async def test_trigger_job_not_found(self, job_manager):
        """测试触发指定任务 - 不存在"""
        job_manager._register_jobs()

        result = await job_manager.trigger_job('nonexistent_job')
        assert result is False

    @pytest.mark.asyncio
    async def test_daily_data_update_task(self, job_manager):
        """测试每日数据更新任务执行"""
        with patch('src.services.data_updater.collector.DataCollector') as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector.run_daily_update.return_value = {
                'sectors_updated': 10,
                'stocks_updated': 100
            }
            mock_collector_class.return_value = mock_collector

            await job_manager._daily_data_update()

            mock_collector.run_daily_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_data_quality_check_task(self, job_manager):
        """测试数据质量检查任务执行"""
        with patch('src.services.monitoring.data_quality.DataQualityChecker') as mock_checker_class:
            mock_checker = AsyncMock()
            mock_checker.run_full_check.return_value = {
                'check_time': '2024-01-10T10:00:00',
                'is_healthy': True,
                'latest_trading_date': '2024-01-09',
                'checks': {'missing_data': {'affected_count': 0, 'severity': 'none'}},
                'backfill': {
                    'gap_start': None,
                    'gap_end': None,
                    'trading_days_to_fill': 0,
                    'filled_successfully': 0,
                    'filled_failed': 0,
                },
                'data_overview': {
                    'total_stocks': 100,
                    'total_sectors': 50,
                    'total_market_data': 5000,
                },
            }
            mock_checker_class.return_value = mock_checker

            await job_manager._check_data_quality()

            mock_checker.run_full_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_cleanup_task(self, job_manager):
        """测试缓存清理任务执行"""
        # Import the module to patch its namespace
        import src.services.scheduler.job_manager as jm

        # Create a fresh JobManager for testing
        import asyncio
        if job_manager.scheduler.running:
            job_manager.shutdown()

        with patch('src.services.cache.cache_manager.get_cache_manager') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.cleanup_expired.return_value = 5
            mock_get_cache.return_value = mock_cache

            # Create a new job manager instance
            test_manager = jm.JobManager()

            await test_manager._cleanup_cache()

            mock_cache.cleanup_expired.assert_called_once()

        # Clean up
        if test_manager.scheduler.running:
            test_manager.shutdown()


class TestMarginDailySyncJob:
    """融资融券早间增量 job（第 17 期后续运维增强）注册与回调测试"""

    def test_disabled_by_default(self, job_manager):
        """ENABLE_MARGIN_DAILY_JOB 默认 false 时 margin_daily_sync 不注册"""
        from src.core.settings import settings
        assert settings.enable_margin_daily_job is False

        job_manager._register_jobs()

        assert job_manager.scheduler.get_job('margin_daily_sync') is None

    def test_registered_when_enabled(self, job_manager, monkeypatch):
        """ENABLE_MARGIN_DAILY_JOB=True 时按 09:30 Asia/Shanghai 注册"""
        from src.core.settings import settings
        monkeypatch.setattr(settings, 'enable_margin_daily_job', True)

        job_manager._register_jobs()

        job = job_manager.scheduler.get_job('margin_daily_sync')
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)
        field_map = {f.name: str(f) for f in job.trigger.fields}
        assert field_map['hour'] == '9'
        assert field_map['minute'] == '30'
        # 不使用 day_of_week 工作日表达式（守卫由回调内本地日历完成）
        assert field_map['day_of_week'] == '*'
        assert str(job.trigger.timezone) == 'Asia/Shanghai'
        assert job.max_instances == 1

    @pytest.mark.asyncio
    async def test_callback_delegates_to_margin_daily_sync(self):
        """回调获取会话并委托 run_margin_daily_sync"""
        manager = JobManager.__new__(JobManager)
        fake_session = MagicMock()

        class _SessionCtx:
            async def __aenter__(self):
                return fake_session

            async def __aexit__(self, *exc):
                return False

        with patch(
            'src.db.database.AsyncSessionLocal', return_value=_SessionCtx()
        ), patch(
            'src.services.margin_daily_sync.run_margin_daily_sync',
            new_callable=AsyncMock,
            return_value={'status': 'noop'},
        ) as mock_run:
            await manager._margin_daily_sync()

        mock_run.assert_awaited_once_with(fake_session)

    @pytest.mark.asyncio
    async def test_callback_swallows_errors(self):
        """回调内异常只记日志不抛出（不影响下一次调度）"""
        manager = JobManager.__new__(JobManager)

        class _SessionCtx:
            async def __aenter__(self):
                return MagicMock()

            async def __aexit__(self, *exc):
                return False

        with patch(
            'src.db.database.AsyncSessionLocal', return_value=_SessionCtx()
        ), patch(
            'src.services.margin_daily_sync.run_margin_daily_sync',
            new_callable=AsyncMock,
            side_effect=ValueError('日历响应不完整'),
        ):
            # 不应抛出
            await manager._margin_daily_sync()
