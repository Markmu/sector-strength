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
        """测试注册定时任务"""
        job_manager._register_jobs()

        jobs = job_manager.scheduler.get_jobs()
        job_ids = [job.id for job in jobs]

        assert 'daily_data_update' in job_ids
        assert 'data_quality_check' in job_ids
        assert 'cache_cleanup' in job_ids

    def test_daily_data_update_job(self, job_manager):
        """测试每日数据更新任务配置"""
        job_manager._register_jobs()

        job = job_manager.scheduler.get_job('daily_data_update')
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)

    def test_data_quality_check_job(self, job_manager):
        """测试数据质量检查任务配置"""
        job_manager._register_jobs()

        job = job_manager.scheduler.get_job('data_quality_check')
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)

    def test_cache_cleanup_job(self, job_manager):
        """测试缓存清理任务配置"""
        job_manager._register_jobs()

        job = job_manager.scheduler.get_job('cache_cleanup')
        assert job is not None
        assert isinstance(job.trigger, IntervalTrigger)

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
        """测试获取所有任务"""
        job_manager._register_jobs()
        jobs = job_manager.get_jobs()

        assert isinstance(jobs, dict)
        assert 'daily_data_update' in jobs
        assert 'data_quality_check' in jobs
        assert 'cache_cleanup' in jobs

    @pytest.mark.asyncio
    async def test_trigger_job_success(self, job_manager):
        """测试触发指定任务 - 成功"""
        job_manager._register_jobs()

        # Mock the job function
        with patch.object(job_manager, '_daily_data_update', new_callable=AsyncMock) as mock_task:
            result = await job_manager.trigger_job('daily_data_update')
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
            mock_checker.check_data_integrity.return_value = {
                'has_issues': False,
                'issues': []
            }
            mock_checker_class.return_value = mock_checker

            await job_manager._check_data_quality()

            mock_checker.check_data_integrity.assert_called_once()

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
