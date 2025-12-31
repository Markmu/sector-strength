"""
板块强度计算服务

处理板块强度得分的计算和更新。
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import date, datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from src.models.sector import Sector
from src.models.daily_market_data import DailyMarketData
from src.models.moving_average_data import MovingAverageData
from src.services.calculation.strength_calculator import StrengthCalculator
from src.services.calculation.trend_analyzer import TrendAnalyzer
from src.models.period_config import PeriodConfig

logger = logging.getLogger(__name__)


class SectorStrengthService:
    """板块强度计算服务"""

    def __init__(self, session: AsyncSession):
        """
        初始化板块强度计算服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.strength_calculator = StrengthCalculator()
        self.trend_analyzer = TrendAnalyzer()
        self._progress_callback: Optional[Callable] = None
        self._cancelled: bool = False

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """
        设置进度回调函数

        Args:
            callback: 回调函数 (current: int, total: int, message: str) -> None
        """
        self._progress_callback = callback

    def _check_cancelled(self):
        """检查是否已取消"""
        if self._cancelled:
            raise InterruptedError("任务已取消")

    async def _report_progress(self, current: int, total: int, message: str):
        """报告进度"""
        if self._progress_callback:
            await self._progress_callback(current, total, message)

    async def calculate_sector_strength_by_range(
        self,
        sector_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        按日期范围计算板块强度

        Args:
            sector_id: 板块ID，None表示计算所有板块
            start_date: 计算开始日期
            end_date: 计算结束日期
            overwrite: 是否覆盖已有数据

        Returns:
            计算结果
        """
        try:
            # 获取周期配置
            period_configs = await self._get_period_configs()

            # 获取板块列表
            if sector_id:
                stmt = select(Sector).where(Sector.id == sector_id)
            else:
                stmt = select(Sector).order_by(Sector.id)

            result = await self.session.execute(stmt)
            sectors = result.scalars().all()

            if not sectors:
                return {
                    "success": False,
                    "error": "未找到板块数据"
                }

            total = len(sectors)
            created_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0

            for idx, sector in enumerate(sectors):
                self._check_cancelled()

                try:
                    await self._report_progress(
                        idx + 1,
                        total,
                        f"计算板块强度: {sector.name} ({sector.code})"
                    )

                    # 计算单个板块的强度
                    result = await self._calculate_single_sector_strength(
                        sector=sector,
                        start_date=start_date,
                        end_date=end_date,
                        period_configs=period_configs,
                        overwrite=overwrite
                    )

                    if result.get("success"):
                        created_count += result.get("created", 0)
                        updated_count += result.get("updated", 0)
                        skipped_count += result.get("skipped", 0)
                    else:
                        error_count += 1
                        logger.warning(f"板块 {sector.name} 强度计算失败: {result.get('error')}")

                except InterruptedError:
                    raise
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理板块 {sector.name} 时出错: {e}")

            await self.session.commit()

            return {
                "success": True,
                "total_sectors": total,
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": error_count
            }

        except InterruptedError:
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"板块强度计算失败: {e}")
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def calculate_sector_strength_by_date(
        self,
        target_date: date,
        sector_id: Optional[int] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        按指定日期计算板块强度

        Args:
            target_date: 目标日期
            sector_id: 板块ID，None表示计算所有板块
            overwrite: 是否覆盖已有数据

        Returns:
            计算结果
        """
        return await self.calculate_sector_strength_by_range(
            sector_id=sector_id,
            start_date=target_date,
            end_date=target_date,
            overwrite=overwrite
        )

    async def calculate_sector_strength_full_history(
        self,
        sector_id: Optional[int] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        计算板块完整历史强度

        从每个板块的最早数据日期开始，计算到最新日期的所有强度数据。

        Args:
            sector_id: 板块ID，None表示计算所有板块
            overwrite: 是否覆盖已有数据

        Returns:
            计算结果
        """
        try:
            # 获取周期配置
            period_configs = await self._get_period_configs()

            # 获取板块列表
            if sector_id:
                stmt = select(Sector).where(Sector.id == sector_id)
            else:
                stmt = select(Sector).order_by(Sector.id)

            result = await self.session.execute(stmt)
            sectors = result.scalars().all()

            if not sectors:
                return {
                    "success": False,
                    "error": "未找到板块数据"
                }

            total = len(sectors)
            created_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0

            for idx, sector in enumerate(sectors):
                self._check_cancelled()

                try:
                    # 获取该板块的日期范围
                    date_range = await self._get_sector_date_range(sector.id)
                    if not date_range:
                        logger.warning(f"板块 {sector.name} 没有历史数据")
                        skipped_count += 1
                        continue

                    sector_start, sector_end = date_range

                    await self._report_progress(
                        idx + 1,
                        total,
                        f"计算板块强度历史: {sector.name} ({sector.code}) - {sector_start} 至 {sector_end}"
                    )

                    # 计算该板块的完整历史强度
                    result = await self._calculate_single_sector_strength(
                        sector=sector,
                        start_date=sector_start,
                        end_date=sector_end,
                        period_configs=period_configs,
                        overwrite=overwrite
                    )

                    if result.get("success"):
                        created_count += result.get("created", 0)
                        updated_count += result.get("updated", 0)
                        skipped_count += result.get("skipped", 0)
                    else:
                        error_count += 1
                        logger.warning(f"板块 {sector.name} 强度计算失败: {result.get('error')}")

                except InterruptedError:
                    raise
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理板块 {sector.name} 时出错: {e}")

            await self.session.commit()

            return {
                "success": True,
                "total_sectors": total,
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": error_count
            }

        except InterruptedError:
            await self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"板块强度计算失败: {e}")
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def _calculate_single_sector_strength(
        self,
        sector: Sector,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        period_configs: Optional[List[Dict]] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        计算单个板块的强度

        Args:
            sector: 板块对象
            start_date: 开始日期
            end_date: 结束日期
            period_configs: 周期配置
            overwrite: 是否覆盖已有数据

        Returns:
            计算结果
        """
        try:
            # 获取周期配置
            if period_configs is None:
                period_configs = await self._get_period_configs()

            # 获取板块历史价格数据
            stmt = select(DailyMarketData).where(
                and_(
                    DailyMarketData.sector_id == sector.id,
                    DailyMarketData.close_price.isnot(None)
                )
            )

            if start_date:
                stmt = stmt.where(DailyMarketData.trade_date >= start_date)
            if end_date:
                stmt = stmt.where(DailyMarketData.trade_date <= end_date)

            stmt = stmt.order_by(DailyMarketData.trade_date)

            result = await self.session.execute(stmt)
            market_data_list = result.scalars().all()

            if not market_data_list:
                return {
                    "success": False,
                    "error": "该板块没有市场数据"
                }

            # 转换为 pandas Series
            dates = [md.trade_date for md in market_data_list]
            prices = [float(md.close_price) for md in market_data_list]
            price_series = pd.Series(prices, index=pd.to_datetime(dates))

            created = 0
            updated = 0
            skipped = 0

            # 按日期计算强度
            for i in range(len(market_data_list)):
                self._check_cancelled()

                current_date = dates[i]
                current_price = prices[i]

                # 检查是否已有数据
                has_existing = sector.strength_score is not None and sector.strength_score_date == current_date

                if has_existing and not overwrite:
                    skipped += 1
                    continue

                # 获取历史价格用于计算（至少需要足够的数据）
                if i < 60:  # 至少需要60天数据
                    skipped += 1
                    continue

                hist_prices = price_series.iloc[:i+1]

                # 计算强度得分
                calc_result = self.strength_calculator.calculate_entity_strength(
                    prices=hist_prices,
                    current_price=current_price,
                    period_configs=period_configs
                )

                if not calc_result.get("success"):
                    skipped += 1
                    continue

                strength_score = calc_result.get("strength_score")

                # 判定趋势
                trend = self.trend_analyzer.determine_trend(
                    current_price=current_price,
                    ma_values=calc_result.get("ma_values", {})
                )

                # 更新板块强度
                sector.strength_score = strength_score
                sector.strength_score_date = current_date
                sector.trend_direction = int(trend)

                if has_existing:
                    updated += 1
                else:
                    created += 1

            return {
                "success": True,
                "created": created,
                "updated": updated,
                "skipped": skipped
            }

        except Exception as e:
            logger.error(f"计算板块 {sector.name} 强度失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_period_configs(self) -> List[Dict]:
        """获取周期配置"""
        stmt = select(PeriodConfig).where(PeriodConfig.is_active == True)
        result = await self.session.execute(stmt)
        configs = result.scalars().all()

        if not configs:
            # 使用默认配置
            return [
                {'period': 5, 'days': 5, 'weight': 0.15},
                {'period': 10, 'days': 10, 'weight': 0.20},
                {'period': 20, 'days': 20, 'weight': 0.25},
                {'period': 30, 'days': 30, 'weight': 0.20},
                {'period': 60, 'days': 60, 'weight': 0.20},
            ]

        return [
            {
                'period': c.period,
                'days': c.days,
                'weight': c.weight,
            }
            for c in configs
        ]

    async def _get_sector_date_range(self, sector_id: int) -> Optional[tuple]:
        """
        获取板块的日期范围

        Args:
            sector_id: 板块ID

        Returns:
            (start_date, end_date) 或 None
        """
        from sqlalchemy import func

        stmt = select(
            func.min(DailyMarketData.trade_date),
            func.max(DailyMarketData.trade_date)
        ).where(
            and_(
                DailyMarketData.sector_id == sector_id,
                DailyMarketData.close_price.isnot(None)
            )
        )

        result = await self.session.execute(stmt)
        row = result.one()

        if row[0] is None or row[1] is None:
            return None

        return (row[0], row[1])
