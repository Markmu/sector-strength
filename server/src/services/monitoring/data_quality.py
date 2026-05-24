"""
数据质量检查模块

监控数据质量并检测异常，支持自动补齐缺失交易日数据。
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import AsyncSessionLocal
from src.models.daily_market_data import DailyMarketData
from src.models.stock import Stock
from src.models.sector import Sector
from src.models.strength_score import StrengthScore
from src.services.trading_calendar import TradingCalendar
from src.services.data_acquisition.akshare_client import AkShareDataSource

logger = logging.getLogger(__name__)


class DataQualityChecker:

    def __init__(self):
        self._trading_calendar = TradingCalendar()
        self._data_source = AkShareDataSource()

    async def run_full_check(self) -> Dict[str, Any]:
        """执行完整质检：检测缺失 → 检测日期缺口 → 自动补齐 → 返回报告"""
        check_time = datetime.now()

        # 1. 检测缺失数据
        missing_info = await self._check_missing_market_data()

        # 2. 检测日期缺口
        latest_date = missing_info.get('latest_date')
        gap_trading_days: List[date] = []
        if latest_date is not None:
            gap_trading_days = await self._detect_date_gaps(latest_date)

        # 3. 自动补齐
        backfill_result = {"filled_successfully": 0, "filled_failed": 0}
        if gap_trading_days:
            backfill_result = await self._backfill_missing_dates(gap_trading_days)

        # 4. 汇总数据概览
        data_overview = await self._get_data_overview()

        # 5. 判断健康状态
        missing_count = missing_info.get('missing_count', 0)
        is_healthy = missing_count == 0 and len(gap_trading_days) == 0

        # 确定缺口范围
        gap_start = gap_trading_days[0].isoformat() if gap_trading_days else None
        gap_end = gap_trading_days[-1].isoformat() if gap_trading_days else None

        return {
            'check_time': check_time.isoformat(),
            'is_healthy': is_healthy,
            'latest_trading_date': latest_date.isoformat() if latest_date else None,
            'checks': {
                'missing_data': {
                    'affected_count': missing_count,
                    'severity': 'high' if missing_count > 0 else 'none',
                },
            },
            'backfill': {
                'gap_start': gap_start,
                'gap_end': gap_end,
                'trading_days_to_fill': len(gap_trading_days),
                'filled_successfully': backfill_result['filled_successfully'],
                'filled_failed': backfill_result['filled_failed'],
            },
            'data_overview': data_overview,
        }

    async def _check_missing_market_data(self) -> Dict[str, Any]:
        """检查最新交易日股票行情缺失"""
        session = AsyncSessionLocal()
        try:
            latest_date_result = await session.execute(
                select(func.max(DailyMarketData.date))
            )
            latest_date = latest_date_result.scalar()

            total_stocks_result = await session.execute(
                select(func.count(Stock.id))
            )
            total_stocks = total_stocks_result.scalar() or 0

            stocks_with_data = 0
            if latest_date is not None:
                stocks_data_result = await session.execute(
                    select(func.count(func.distinct(DailyMarketData.entity_id)))
                    .where(
                        DailyMarketData.entity_type == 'stock',
                        DailyMarketData.date == latest_date,
                    )
                )
                stocks_with_data = stocks_data_result.scalar() or 0

            missing_count = total_stocks - stocks_with_data
            if latest_date is None:
                missing_count = total_stocks

            return {
                'latest_date': latest_date,
                'total_stocks': total_stocks,
                'stocks_with_data': stocks_with_data,
                'missing_count': missing_count,
            }
        finally:
            await session.close()

    async def _detect_date_gaps(self, latest_date: date) -> List[date]:
        """查询 latest_date+1 至当日之间的交易日列表"""
        if latest_date is None:
            return []

        today = datetime.now().date()
        start = latest_date + timedelta(days=1)
        if start > today:
            return []

        return await self._trading_calendar.get_trading_days_between(start, today)

    async def _backfill_missing_dates(self, trading_days: List[date]) -> Dict[str, int]:
        """对每个缺失交易日补齐板块和个股行情数据"""
        filled_successfully = 0
        filled_failed = 0

        for td in trading_days:
            try:
                await self._backfill_single_date(td)
                filled_successfully += 1
                logger.info(f"[数据补齐] 交易日 {td} 补齐成功")
            except Exception as e:
                filled_failed += 1
                logger.error(f"[数据补齐] 交易日 {td} 补齐失败: {e}")

        return {
            'filled_successfully': filled_successfully,
            'filled_failed': filled_failed,
        }

    async def _backfill_single_date(self, target_date: date) -> None:
        """补齐单个交易日的板块和个股行情"""
        session = AsyncSessionLocal()
        try:
            # 获取板块映射
            sector_result = await session.execute(select(Sector))
            sector_map = {s.code: (s.id, s.name, s.type) for s in sector_result.scalars().all()}

            # 补齐板块行情
            for code, (entity_id, name, stype) in sector_map.items():
                try:
                    quotes = self._data_source.get_sector_daily_data(
                        sector_name=name,
                        sector_type=stype,
                        start_date=target_date,
                        end_date=target_date,
                    )
                    for q in quotes:
                        stmt = pg_insert(DailyMarketData).values(
                            entity_type='sector',
                            entity_id=entity_id,
                            symbol=code,
                            date=q.trade_date,
                            open=q.open,
                            high=q.high,
                            low=q.low,
                            close=q.close,
                            volume=q.volume,
                            turnover=q.turnover,
                        )
                        stmt = stmt.on_conflict_do_nothing(
                            constraint='uq_daily_market_data_entity_date'
                        )
                        await session.execute(stmt)
                except Exception as e:
                    logger.warning(f"[数据补齐] 板块 {name} 行情获取失败: {e}")

            await session.commit()

            # 获取股票映射
            stock_result = await session.execute(select(Stock))
            stock_map = {s.symbol: s.id for s in stock_result.scalars().all()}

            # 补齐个股行情
            batch_size = 50
            symbols = list(stock_map.items())
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                for symbol, entity_id in batch:
                    try:
                        quotes = self._data_source.get_daily_data(
                            symbol=symbol,
                            start_date=target_date,
                            end_date=target_date,
                        )
                        for q in quotes:
                            change_val = None
                            change_pct = None
                            if q.close and q.open:
                                change_val = q.close - q.open
                                if q.open != 0:
                                    change_pct = change_val / q.open * 100

                            stmt = pg_insert(DailyMarketData).values(
                                entity_type='stock',
                                entity_id=entity_id,
                                symbol=symbol,
                                date=q.trade_date,
                                open=q.open,
                                high=q.high,
                                low=q.low,
                                close=q.close,
                                volume=q.volume,
                                turnover=q.turnover,
                                change=change_val,
                                change_percent=change_pct,
                            )
                            stmt = stmt.on_conflict_do_nothing(
                                constraint='uq_daily_market_data_entity_date'
                            )
                            await session.execute(stmt)
                    except Exception as e:
                        logger.warning(f"[数据补齐] 股票 {symbol} 行情获取失败: {e}")

                await session.commit()

        finally:
            await session.close()

    async def _get_data_overview(self) -> Dict[str, int]:
        """获取数据概览统计"""
        session = AsyncSessionLocal()
        try:
            stock_count = (await session.execute(select(func.count(Stock.id)))).scalar() or 0
            sector_count = (await session.execute(select(func.count(Sector.id)))).scalar() or 0
            market_data_count = (await session.execute(select(func.count(DailyMarketData.id)))).scalar() or 0

            return {
                'total_stocks': stock_count,
                'total_sectors': sector_count,
                'total_market_data': market_data_count,
            }
        finally:
            await session.close()

    async def check_data_integrity(self) -> Dict[str, Any]:
        """检查数据完整性（兼容旧接口）"""
        issues = []

        missing_count = await self._check_missing_market_data()
        if missing_count.get('missing_count', 0) > 0:
            issues.append(f"有 {missing_count['missing_count']} 只股票缺失最新行情数据")

        abnormal_count = await self._check_abnormal_prices()
        if abnormal_count > 0:
            issues.append(f"发现 {abnormal_count} 条异常价格数据")

        invalid_scores = await self._check_invalid_strength_scores()
        if invalid_scores > 0:
            issues.append(f"有 {invalid_scores} 只股票的强度得分无效")

        return {
            'has_issues': len(issues) > 0,
            'issues': issues,
            'checked_at': datetime.now().isoformat(),
        }

    async def _check_abnormal_prices(self) -> int:
        """检测异常价格数据"""
        session = AsyncSessionLocal()
        try:
            stmt = select(DailyMarketData).where(
                DailyMarketData.change_percent > 20
            )
            result = await session.execute(stmt)
            return len(result.all())
        finally:
            await session.close()

    async def _check_invalid_strength_scores(self) -> int:
        """检查无效的强度得分"""
        count = 0
        session = AsyncSessionLocal()
        try:
            stmt = select(StrengthScore).where(
                StrengthScore.entity_type == 'stock',
                (StrengthScore.score < 0) | (StrengthScore.score > 100)
            )
            result = await session.execute(stmt)
            count += len(result.all())

            stmt = select(Sector).where(
                (Sector.strength_score < 0) | (Sector.strength_score > 100)
            )
            result = await session.execute(stmt)
            count += len(result.all())

            return count
        finally:
            await session.close()

    async def get_data_quality_report(self) -> Dict[str, Any]:
        """获取数据质量报告"""
        session = AsyncSessionLocal()
        try:
            stock_count = (await session.execute(select(func.count(Stock.id)))).scalar() or 0
            sector_count = (await session.execute(select(func.count(Sector.id)))).scalar() or 0
            market_data_count = (await session.execute(select(func.count(DailyMarketData.id)))).scalar() or 0

            return {
                'stock_count': stock_count,
                'sector_count': sector_count,
                'market_data_count': market_data_count,
                'checked_at': datetime.now().isoformat(),
            }
        finally:
            await session.close()


class AlertManager:

    def __init__(self):
        self.enabled = True

    async def send_alert(self, message: str, level: str = "warning"):
        logger.warning(f"[告警] [{level.upper()}] {message}")

    async def send_data_quality_alert(self, issues: List[str]):
        for issue in issues:
            await self.send_alert(f"数据质量问题: {issue}", level="warning")
