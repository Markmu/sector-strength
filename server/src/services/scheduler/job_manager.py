"""
任务管理器

管理定时任务的调度和执行。
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job

logger = logging.getLogger(__name__)


class JobManager:
    """
    任务管理器

    使用 APScheduler 管理所有定时任务。
    """

    def __init__(self):
        """初始化任务管理器"""
        self.scheduler = AsyncIOScheduler()
        self._is_running = False  # 内部运行状态标志
        self._register_jobs()

    def _register_jobs(self):
        """注册所有定时任务"""
        # ============================================================
        # ⏸ 暂停注册：所有定时任务暂时停用，调度器仍会启动但不绑定任何 job。
        # 需要恢复时，把下方对应 add_job 块的注释去掉即可。
        # （2026-06-15 暂停，原因：开发期间避免后台任务自动执行）
        # ============================================================

        # # 每个工作日 15:30 执行数据更新
        # self.scheduler.add_job(
        #     self._daily_data_update,
        #     trigger=CronTrigger(
        #         day_of_week='mon-fri',
        #         hour=15,
        #         minute=30
        #     ),
        #     id='daily_data_update',
        #     name='每日数据更新',
        #     replace_existing=True
        # )

        # # 每小时检查数据质量
        # self.scheduler.add_job(
        #     self._check_data_quality,
        #     trigger=IntervalTrigger(hours=1),
        #     id='data_quality_check',
        #     name='数据质量检查',
        #     replace_existing=True
        # )

        # # 每小时清理过期缓存
        # self.scheduler.add_job(
        #     self._cleanup_cache,
        #     trigger=IntervalTrigger(hours=1),
        #     id='cache_cleanup',
        #     name='缓存清理',
        #     replace_existing=True
        # )

        # # 每日 16:00 执行板块分类更新
        # self.scheduler.add_job(
        #     self._daily_sector_classification_update,
        #     trigger=CronTrigger(hour=16, minute=0),
        #     id='daily_sector_classification',
        #     name='板块分类每日更新',
        #     replace_existing=True,
        #     max_instances=1,  # 防止并发执行
        #     misfire_grace_time=3600  # 错过执行时间后1小时内仍可执行
        # )

        # 板块资金流即时快照：每分钟触发，任务内部按交易日 + 盘中时段过滤
        # 仅在交易日连续竞价时段（9:30-11:30、13:00-15:00）真正采集；
        # 非交易时段/节假日只做一次轻量时间判断即跳过，不调用同花顺接口。
        self.scheduler.add_job(
            self._sector_fund_flow_snapshot,
            trigger=IntervalTrigger(minutes=1),
            id='sector_fund_flow_snapshot',
            name='板块资金流即时快照（仅交易日盘中）',
            replace_existing=True,
            max_instances=1,  # 防止并发执行，避免风控
        )

    async def _daily_data_update(self):
        """每日数据更新任务"""
        from src.services.data_updater.collector import DataCollector

        logger.info(f"[定时任务] 开始执行每日数据更新: {datetime.now()}")

        try:
            collector = DataCollector()
            result = await collector.run_daily_update()
            logger.info(f"[定时任务] 数据更新完成: {result}")
        except Exception as e:
            logger.error(f"[定时任务] 数据更新失败: {e}")
            raise

    async def _sector_fund_flow_snapshot(self):
        """板块资金流即时快照任务

        每分钟触发，但仅在交易日连续竞价时段真正采集：
        - 交易日判断：周末/节假日跳过（复用 TradingCalendar）
        - 盘中时段：9:30-11:30（上午）、13:00-15:00（下午）A 股连续竞价时段
        非交易时段只做轻量判断即返回，不调用同花顺接口，避免无效请求与风控。
        采集后 on_conflict_do_update 保证同分钟重采覆盖最新值。
        """
        now = datetime.now()

        # 盘中时段判断（A 股连续竞价：9:30-11:30、13:00-15:00）
        hm = now.hour * 60 + now.minute
        in_morning = 9 * 60 + 30 <= hm <= 11 * 60 + 30
        in_afternoon = 13 * 60 <= hm <= 15 * 60
        if not (in_morning or in_afternoon):
            return  # 非盘中时段，跳过（不打日志，避免每分钟刷屏）

        # 交易日判断（节假日跳过）
        from src.services.trading_calendar import TradingCalendar

        calendar = TradingCalendar()
        try:
            is_trading, _ = await calendar.is_trading_day(now.date())
        except Exception as e:
            logger.warning(f"[定时任务] 交易日判断失败，保守跳过本次: {e}")
            return
        if not is_trading:
            return  # 非交易日，跳过

        logger.info(f"[定时任务] 开始采集板块资金流即时快照: {now}")

        try:
            from src.services.data_updater.collector import DataCollector

            collector = DataCollector()
            count = await collector._update_sector_fund_flow()
            logger.info(f"[定时任务] 板块资金流采集完成: {count} 条记录")
        except Exception as e:
            logger.error(f"[定时任务] 板块资金流采集失败: {e}")
            # 不 raise：采集失败不影响下一次调度（APScheduler 默认会移除抛异常的 job）


    async def _check_data_quality(self):
        """数据质量检查任务"""
        from src.services.monitoring.data_quality import DataQualityChecker

        logger.info("[定时任务] 执行数据质量检查")

        try:
            checker = DataQualityChecker()
            report = await checker.run_full_check()

            if not report.get('is_healthy'):
                logger.warning(
                    f"[定时任务] 发现数据质量问题: 缺失 {report['checks']['missing_data']['affected_count']} 条"
                )
                backfill = report.get('backfill', {})
                logger.info(
                    f"[定时任务] 补齐结果: 成功 {backfill.get('filled_successfully', 0)} 日, "
                    f"失败 {backfill.get('filled_failed', 0)} 日"
                )
            else:
                logger.info("[定时任务] 数据质量检查通过")
        except Exception as e:
            logger.error(f"[定时任务] 数据质量检查失败: {e}")

    async def _cleanup_cache(self):
        """缓存清理任务"""
        from src.services.cache.cache_manager import get_cache_manager

        logger.debug("[定时任务] 清理过期缓存")

        try:
            cache = get_cache_manager()
            count = await cache.cleanup_expired()
            logger.info(f"[定时任务] 清理了 {count} 条过期缓存")
        except Exception as e:
            logger.error(f"[定时任务] 缓存清理失败: {e}")

    async def _daily_sector_classification_update(self):
        """每日板块分类更新任务

        注意：数据新鲜度检查已在服务层 update_daily_classification() 中统一处理
        """
        from src.services.sector_classification_service import SectorClassificationService
        from src.db.database import AsyncSessionLocal

        logger.info("[定时任务] 开始执行板块分类更新")

        try:
            async with AsyncSessionLocal() as session:
                service = SectorClassificationService(session)
                result = await service.update_daily_classification()

                if result.get("success"):
                    logger.info(f"[定时任务] 板块分类更新完成: {result}")
                else:
                    # 服务层返回失败（如数据未就绪），不抛出异常
                    logger.warning(f"[定时任务] 板块分类更新跳过: {result.get('error')}")
        except Exception as e:
            logger.error(f"[定时任务] 板块分类更新失败: {e}")
            raise  # 其他异常继续抛出，触发任务重试

    def start(self):
        """启动调度器"""
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("[调度器] 已启动")
        else:
            logger.warning("[调度器] 已经在运行中")

    def shutdown(self, wait: bool = True):
        """
        关闭调度器

        Args:
            wait: 是否等待正在执行的任务完成
        """
        if self._is_running:
            self.scheduler.shutdown(wait=wait)
            self._is_running = False
            logger.info("[调度器] 已关闭")

    def get_jobs(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有任务信息

        Returns:
            任务信息字典
        """
        jobs = {}
        for job in self.scheduler.get_jobs():
            # 在 APScheduler 3.x 中，next_run_time 可能是私有属性
            # 使用 getattr 安全获取
            next_run = getattr(job, 'next_run_time', None)
            jobs[job.id] = {
                'id': job.id,
                'name': job.name,
                'next_run_time': next_run.isoformat() if next_run else None,
                'trigger': str(job.trigger),
            }
        return jobs

    async def trigger_job(self, job_id: str) -> bool:
        """
        手动触发任务执行

        Args:
            job_id: 任务 ID

        Returns:
            是否成功触发
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify()
                logger.info(f"[调度器] 手动触发任务: {job_id}")
                return True
            else:
                logger.warning(f"[调度器] 任务不存在: {job_id}")
                return False
        except Exception as e:
            logger.error(f"[调度器] 触发任务失败: {e}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """暂停任务"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.pause()
                logger.info(f"[调度器] 暂停任务: {job_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"[调度器] 暂停任务失败: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """恢复任务"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.resume()
                logger.info(f"[调度器] 恢复任务: {job_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"[调度器] 恢复任务失败: {e}")
            return False

    @property
    def is_running(self) -> bool:
        """调度器是否正在运行"""
        return self._is_running


# 全局任务管理器实例
_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """
    获取全局任务管理器实例

    Returns:
        JobManager: 任务管理器单例
    """
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager


def reset_job_manager():
    """重置任务管理器（主要用于测试）"""
    global _job_manager
    if _job_manager is not None and _job_manager.is_running:
        _job_manager.shutdown()
    _job_manager = None
