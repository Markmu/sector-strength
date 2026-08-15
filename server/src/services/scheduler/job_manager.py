"""
任务管理器

管理定时任务的调度和执行。
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

from src.core.settings import settings

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
        # 除板块资金流快照外，其余日级/小时级 job 默认停用，避免开发期间
        # 后台任务自动执行。各 job 的启用方式见下方注释：
        #   - daily_data_update：由 settings.enable_daily_update_job
        #     （env: ENABLE_DAILY_UPDATE_JOB）控制，生产置 true。
        #   - margin_daily_sync：由 settings.enable_margin_daily_job
        #     （env: ENABLE_MARGIN_DAILY_JOB）控制，生产置 true。
        #   - data_quality_check / cache_cleanup / etf / index：仍按惯例
        #     注释停用，需要时取消注释即可。
        # ============================================================

        # 每日数据更新：架构 §6.3 要求生产恢复每日 job 时统一安排 18:00 北京时间。
        # 由 ENABLE_DAILY_UPDATE_JOB 控制，开发期默认停用（false），生产置 true。
        # 休市判定不依赖 cron 工作日表达式——采集侧守卫由 collector.run_daily_update
        # 内 refresh_range(today,today) + 本地交易日历完成（架构 §6.3 / AC-09）。
        if settings.enable_daily_update_job:
            self.scheduler.add_job(
                self._daily_data_update,
                trigger=CronTrigger(
                    hour=18,
                    minute=0,
                    timezone='Asia/Shanghai',
                ),
                id='daily_data_update',
                name='每日数据更新',
                replace_existing=True,
                max_instances=1,  # 防止并发执行，避免风控
            )

        # 融资融券早间增量同步：Tushare margin 为 T+1 接口——次一交易日早晨
        # 8:30 左右发布上一交易日数据、接口最晚 9:05 更新完（官方 doc_id=58；
        # 2026-08-15 周六实测镜像确认非交易日不发布，周五数据周一早晨补）。
        # 09:30 触发留 25 分钟缓冲；休市守卫在回调内用本地日历完成
        # （margin_daily_sync），近 14 自然日缺口自愈，更早走管理面板手动同步。
        if settings.enable_margin_daily_job:
            self.scheduler.add_job(
                self._margin_daily_sync,
                trigger=CronTrigger(
                    hour=9,
                    minute=30,
                    timezone='Asia/Shanghai',
                ),
                id='margin_daily_sync',
                name='融资融券早间增量同步（每日 09:30，休市自动跳过）',
                replace_existing=True,
                max_instances=1,  # 防止并发执行，避免风控
            )

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

        # 历史停用的 job（质量检查/缓存清理/ETF/指数/量价指标）已删除注册代码；
        # 需要恢复时参照上方 enable_daily_update_job / enable_margin_daily_job 的
        # settings 开关模式新增（源码历史见 git）。

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

    async def _margin_daily_sync(self):
        """融资融券早间增量同步任务

        每日 09:30 Asia/Shanghai 触发。margin 为 T+1 接口（次一交易日早晨
        ~9:05 发布上一交易日数据），与 18:00 盘后 job 分离、单独早间执行。
        交易日守卫、近 14 自然日缺口计算与互斥建任务见
        ``margin_daily_sync.run_margin_daily_sync``；实际逐日拉取由
        TaskExecutor 拾取 ``sync_market_margin`` 任务完成（与手动面板互斥）。
        """
        from src.db.database import AsyncSessionLocal
        from src.services.margin_daily_sync import run_margin_daily_sync

        logger.info(f"[定时任务] 开始执行融资融券早间同步: {datetime.now()}")

        try:
            async with AsyncSessionLocal() as session:
                result = await run_margin_daily_sync(session)
                logger.info(f"[定时任务] 融资融券早间同步完成: {result}")
        except Exception as e:
            logger.error(f"[定时任务] 融资融券早间同步失败: {e}")
            # 不 raise：失败不影响下一次调度（次日缺口自愈）

    async def _sector_fund_flow_snapshot(self):
        """板块资金流即时快照任务

        每分钟触发，直接调用 collector。盘中时段 + 交易日守卫已下沉到
        collector._update_sector_fund_flow（北京时区，同时覆盖手动触发路径），
        非盘中/非交易日时 collector 内部直接返回 0，不调用同花顺接口。
        """
        try:
            from src.services.data_updater.collector import DataCollector

            collector = DataCollector()
            count = await collector._update_sector_fund_flow()
            logger.info(f"[定时任务] 板块资金流采集完成: {count} 条记录")
        except Exception as e:
            logger.error(f"[定时任务] 板块资金流采集失败: {e}")
            # 不 raise：采集失败只记日志，不影响下一次调度

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
            next_run = job.next_run_time
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
                # APScheduler 3.x 无显式 trigger API，把 next_run_time 提前到现在即可立即执行
                job.modify(next_run_time=datetime.now(timezone.utc))
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
