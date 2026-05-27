"""数据状态服务 — 聚合三类板块数据的时效性状态与补齐范围计算"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Literal, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.async_task import AsyncTask
from src.models.daily_market_data import DailyMarketData
from src.models.moving_average_data import MovingAverageData
from src.models.strength_score import StrengthScore
from src.services.trading_calendar import TradingCalendar

logger = logging.getLogger(__name__)


class DataStatusService:
    """聚合三类板块数据（历史、均线、强度）的状态查询和补齐范围计算"""

    DATA_TYPES: List[Dict] = [
        {
            "type": "history",
            "label": "板块历史数据",
            "model": DailyMarketData,
            "task_types": ["backfill_history"],
        },
        {
            "type": "ma",
            "label": "板块均线数据",
            "model": MovingAverageData,
            "task_types": ["backfill_ma"],
        },
        {
            "type": "strength",
            "label": "板块强度数据",
            "model": StrengthScore,
            "task_types": ["backfill_strength"],
        },
    ]

    MARKET_CLOSE_HOUR = 16

    def __init__(self, db: AsyncSession):
        self.db = db
        self.trading_calendar = TradingCalendar()

    @staticmethod
    def _effective_end_date() -> date:
        """根据当前时间返回有效的数据截止日期

        A股 15:00 收盘，数据通常 16:00 前后入库。
        16:00 之前当天数据不完整，截止日期用前一天。
        """
        now = datetime.now()
        if now.hour < DataStatusService.MARKET_CLOSE_HOUR:
            return now.date() - timedelta(days=1)
        return now.date()

    # ------------------------------------------------------------------
    # 公共方法
    # ------------------------------------------------------------------

    async def get_status(self) -> Dict:
        """返回三类数据的完整状态快照

        返回结构:
        {
            "items": [
                {
                    "type": "history" | "ma" | "strength",
                    "label": "...",
                    "latest_date": "YYYY-MM-DD" | None,
                    "status": "normal" | "missing" | "no_data",
                    "missing_range": {"start": "...", "end": "..."} | None,
                    "active_task": {
                        "task_id": "...",
                        "status": "pending" | "running" | "completed" | "failed",
                        "progress": 10,
                        "total": 100,
                        "error_message": "..." | None,
                    } | None,
                },
                ...
            ]
        }
        """
        items = []
        effective_end = self._effective_end_date()

        for cfg in self.DATA_TYPES:
            item = await self._build_item_status(cfg, effective_end)
            items.append(item)

        return {"items": items}

    async def get_backfill_range(
        self, data_type: Literal["history", "ma", "strength"]
    ) -> Optional[Tuple[date, date]]:
        """计算指定数据类型的补齐日期范围

        Returns:
            (start, end) 日期元组，无数据或无需补齐时返回 None
        """
        cfg = self._get_cfg(data_type)
        if cfg is None:
            return None

        latest_date = await self._get_latest_date(cfg["model"])
        if latest_date is None:
            return None

        today = date.today()
        start = latest_date + timedelta(days=1)
        end = self._effective_end_date()

        if start > end:
            return None

        # 使用交易日历确认区间内确实有交易日
        try:
            trading_days = await self.trading_calendar.get_trading_days_between(start, end)
            if not trading_days:
                return None
        except Exception:
            logger.warning("TradingCalendar 不可用，降级返回日历范围")
            # 无法判断，返回计算的范围
            pass

        return (start, end)

    async def has_active_task(
        self, data_type: Literal["history", "ma", "strength"]
    ) -> bool:
        """判断指定数据类型是否有活跃任务（pending / running）"""
        cfg = self._get_cfg(data_type)
        if cfg is None:
            return False

        stmt = (
            select(AsyncTask)
            .where(
                AsyncTask.task_type.in_(cfg["task_types"]),
                AsyncTask.status.in_(["pending", "running"]),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _build_item_status(self, cfg: Dict, effective_end: date) -> Dict:
        """构建单个数据类型的状态项"""
        latest_date = await self._get_latest_date(cfg["model"])
        active_task = await self._get_active_task(cfg["task_types"])

        # 状态判定
        if latest_date is None:
            status = "no_data"
            missing_range = None
        elif latest_date >= effective_end:
            status = "normal"
            missing_range = None
        else:
            # latest_date < effective_end，检查缺失
            status, missing_range = await self._detect_gap(latest_date, effective_end)

        # 数据已正常时，清除旧的失败任务信息，避免显示已过时的错误
        if status == "normal" and active_task and active_task.get("status") == "failed":
            active_task = None

        return {
            "type": cfg["type"],
            "label": cfg["label"],
            "latest_date": str(latest_date) if latest_date else None,
            "status": status,
            "missing_range": missing_range,
            "active_task": active_task,
        }

    async def _detect_gap(
        self, latest_date: date, effective_end: date
    ) -> Tuple[str, Optional[Dict]]:
        """检测最新日期和有效截止日期之间是否有交易日缺失

        Returns:
            (status, missing_range)
        """
        start = latest_date + timedelta(days=1)
        end = effective_end

        try:
            trading_days = await self.trading_calendar.get_trading_days_between(start, end)
        except Exception as exc:
            logger.warning(f"TradingCalendar 调用失败，降级为 normal: {exc}")
            return ("normal", None)

        if trading_days:
            return (
                "missing",
                {
                    "start": str(trading_days[0]),
                    "end": str(trading_days[-1]),
                },
            )

        return ("normal", None)

    async def _get_latest_date(self, model) -> Optional[date]:
        """查询指定模型中 sector 类型数据的最新日期"""
        stmt = select(func.max(model.date)).where(model.entity_type == "sector")
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_active_task(self, task_types: List[str]) -> Optional[Dict]:
        """查询指定任务类型中最新的活跃或失败任务

        包含 failed 状态，以便前端展示最近一次失败的任务信息和重新补齐按钮。
        """
        stmt = (
            select(AsyncTask)
            .where(
                AsyncTask.task_type.in_(task_types),
                AsyncTask.status.in_(["pending", "running", "failed"]),
            )
            .order_by(AsyncTask.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()

        if task is None:
            return None

        return {
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress or 0,
            "total": task.total or 0,
            "error_message": task.error_message,
        }

    def _get_cfg(
        self, data_type: Literal["history", "ma", "strength"]
    ) -> Optional[Dict]:
        """根据 data_type 查找配置"""
        for cfg in self.DATA_TYPES:
            if cfg["type"] == data_type:
                return cfg
        return None
