"""
数据质量检查模块

监控数据质量并检测异常。
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import AsyncSessionLocal
from src.models.daily_market_data import DailyMarketData
from src.models.stock import Stock
from src.models.sector import Sector
from src.models.strength_score import StrengthScore

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """
    数据质量检查器

    检查数据完整性、异常值等问题。
    """

    async def check_data_integrity(self) -> Dict[str, Any]:
        """
        检查数据完整性

        Returns:
            检查结果
        """
        issues = []

        # 1. 检查缺失的行情数据
        missing_count = await self._check_missing_market_data()
        if missing_count > 0:
            issues.append(f"有 {missing_count} 只股票缺失最新行情数据")

        # 2. 检查异常数据
        abnormal_count = await self._check_abnormal_prices()
        if abnormal_count > 0:
            issues.append(f"发现 {abnormal_count} 条异常价格数据")

        # 3. 检查计算结果
        invalid_scores = await self._check_invalid_strength_scores()
        if invalid_scores > 0:
            issues.append(f"有 {invalid_scores} 只股票的强度得分无效")

        return {
            'has_issues': len(issues) > 0,
            'issues': issues,
            'checked_at': datetime.now().isoformat(),
        }

    async def _check_missing_market_data(self) -> int:
        """
        检查缺失的行情数据

        Returns:
            缺失数据的股票数量
        """
        session = AsyncSessionLocal()
        try:
            # 查询有股票但最近没有行情数据的
            latest_date = datetime.now().date() - timedelta(days=1)

            # TODO: 实现更复杂的缺失检测逻辑
            # 这里返回模拟结果
            return 0
        finally:
            await session.close()

    async def _check_abnormal_prices(self) -> int:
        """
        检测异常价格数据

        Returns:
            异常数据数量
        """
        session = AsyncSessionLocal()
        try:
            # 价格日涨跌幅超过 20% 视为异常
            stmt = select(DailyMarketData).where(
                DailyMarketData.change_percent > 20
            )
            result = await session.execute(stmt)
            count = len(result.all())

            return count
        finally:
            await session.close()

    async def _check_invalid_strength_scores(self) -> int:
        """
        检查无效的强度得分

        Returns:
            无效得分的实体数量
        """
        count = 0
        session = AsyncSessionLocal()
        try:
            # 检查个股的强度得分（通过 StrengthScore 关联表）
            stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == 'stock',
                    or_(
                        StrengthScore.score < 0,
                        StrengthScore.score > 100
                    )
                )
            )
            result = await session.execute(stmt)
            count += len(result.all())

            # 检查板块（直接在 Sector 表上有 strength_score 字段）
            stmt = select(Sector).where(
                or_(
                    Sector.strength_score < 0,
                    Sector.strength_score > 100
                )
            )
            result = await session.execute(stmt)
            count += len(result.all())

            return count
        finally:
            await session.close()

    async def get_data_quality_report(self) -> Dict[str, Any]:
        """
        获取数据质量报告

        Returns:
            质量报告数据
        """
        session = AsyncSessionLocal()
        try:
            # 统计各类数据数量
            stock_count_stmt = select(func.count(Stock.id))
            stock_result = await session.execute(stock_count_stmt)
            stock_count = stock_result.scalar() or 0

            sector_count_stmt = select(func.count(Sector.id))
            sector_result = await session.execute(sector_count_stmt)
            sector_count = sector_result.scalar() or 0

            market_data_stmt = select(func.count(DailyMarketData.id))
            market_result = await session.execute(market_data_stmt)
            market_data_count = market_result.scalar() or 0

            return {
                'stock_count': stock_count,
                'sector_count': sector_count,
                'market_data_count': market_data_count,
                'checked_at': datetime.now().isoformat(),
            }
        finally:
            await session.close()


class AlertManager:
    """
    告警管理器

    管理数据质量告警的发送。
    """

    def __init__(self):
        """初始化告警管理器"""
        self.enabled = True

    async def send_alert(self, message: str, level: str = "warning"):
        """
        发送告警

        Args:
            message: 告警消息
            level: 告警级别
        """
        logger.warning(f"[告警] [{level.upper()}] {message}")

        # TODO: 实现实际的告警发送（邮件/Webhook）
        # 这里暂时只记录日志

    async def send_data_quality_alert(self, issues: List[str]):
        """
        发送数据质量告警

        Args:
            issues: 问题列表
        """
        for issue in issues:
            await self.send_alert(f"数据质量问题: {issue}", level="warning")
