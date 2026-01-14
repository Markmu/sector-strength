"""
板块均线计算服务

处理板块均线数据的计算和更新。
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import date, datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from src.models.sector import Sector
from src.models.daily_market_data import DailyMarketData
from src.models.moving_average_data import MovingAverageData
from src.services.calculation.moving_average_calculator import MovingAverageCalculator
from src.models.period_config import PeriodConfig

logger = logging.getLogger(__name__)


class SectorMAService:
    """板块均线计算服务"""

    # 默认计算的均线周期
    DEFAULT_PERIODS = [5, 10, 20, 30, 60, 90, 120, 240]

    def __init__(self, session: AsyncSession):
        """
        初始化板块均线计算服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.ma_calculator = MovingAverageCalculator()
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """
        设置进度回调函数

        Args:
            callback: 回调函数 (current: int, total: int, message: str) -> None
        """
        self._progress_callback = callback

    async def _report_progress(self, current: int, total: int, message: str):
        """报告进度"""
        if self._progress_callback:
            await self._progress_callback(current, total, message)

    async def calculate_sector_moving_averages(
        self,
        sector_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        periods: Optional[List[int]] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        计算板块均线

        Args:
            sector_id: 板块ID，None表示计算所有板块
            start_date: 计算开始日期
            end_date: 计算结束日期
            periods: 均线周期列表
            overwrite: 是否覆盖已有数据

        Returns:
            计算结果
        """
        try:
            # 获取周期配置
            if periods is None:
                periods = self.DEFAULT_PERIODS

            # 获取板块列表
            if sector_id:
                stmt = select(Sector).where(Sector.id == sector_id)
            else:
                stmt = select(Sector)

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
                try:
                    await self._report_progress(
                        idx + 1,
                        total,
                        f"计算板块均线: {sector.name} ({sector.code})"
                    )

                    # 计算单个板块的均线
                    result = await self._calculate_single_sector_ma(
                        sector=sector,
                        start_date=start_date,
                        end_date=end_date,
                        periods=periods,
                        overwrite=overwrite
                    )

                    if result.get("success"):
                        created_count += result.get("created", 0)
                        updated_count += result.get("updated", 0)
                        skipped_count += result.get("skipped", 0)
                    else:
                        error_count += 1
                        logger.warning(f"板块 {sector.name} 均线计算失败: {result.get('error')}")

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

        except Exception as e:
            logger.error(f"板块均线计算失败: {e}")
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def _calculate_single_sector_ma(
        self,
        sector: Sector,
        start_date: Optional[date],
        end_date: Optional[date],
        periods: List[int],
        overwrite: bool
    ) -> Dict[str, Any]:
        """
        计算单个板块的均线（支持断点续传和分批保存）

        Args:
            sector: 板块对象
            start_date: 开始日期
            end_date: 结束日期
            periods: 均线周期列表
            overwrite: 是否覆盖已有数据

        Returns:
            计算结果
        """
        try:
            logger.info(f"[板块均线] 开始计算板块 {sector.name}({sector.code}) 的均线数据")

            # ========================================
            # 步骤1: 确定需要查询的数据范围
            # ========================================
            # 根据最长的均线周期，智能确定需要查询的历史数据范围
            # 使用 LIMIT 查询提高效率：只需要查询 max_period 条数据即可
            max_period = max(periods)
            logger.info(f"[板块均线] 最长均线周期: {max_period}日")

            # 构建查询语句：使用 LIMIT 和日期过滤来高效获取数据
            stmt = select(DailyMarketData).where(
                and_(
                    DailyMarketData.entity_type == "sector",
                    DailyMarketData.entity_id == sector.id,
                    DailyMarketData.close.isnot(None)
                )
            )

            # 确定查询的结束日期
            if end_date:
                query_end_date = end_date
            else:
                # 查询最新的数据日期
                temp_result = await self.session.execute(
                    select(func.max(DailyMarketData.date)).where(
                        and_(
                            DailyMarketData.entity_type == "sector",
                            DailyMarketData.entity_id == sector.id,
                            DailyMarketData.close.isnot(None)
                        )
                    )
                )
                query_end_date = temp_result.scalar()
                if not query_end_date:
                    logger.warning(f"[板块均线] 板块 {sector.name} 没有市场数据")
                    return {
                        "success": False,
                        "error": "没有找到该板块的市场数据"
                    }

            # 应用日期过滤：查询 end_date 之前的 max_period 条数据
            # 这样可以确保有足够的历史数据来计算均线，同时不会查询过多数据
            stmt = stmt.where(DailyMarketData.date <= query_end_date)

            # 如果指定了 start_date，需要查询更多数据以确保能正确计算均线
            # 需要计算从 start_date 到 query_end_date 的天数，加上 max_period 用于计算均线
            if start_date:
                days_span = (query_end_date - start_date).days + 1
                limit_count = max(days_span + max_period, max_period)
                logger.info(f"[板块均线] 指定开始日期 {start_date}，将查询 {limit_count} 条数据（跨度 {days_span} 天 + 均线周期 {max_period} 天）")
            else:
                limit_count = max_period
                logger.info(f"[板块均线] 将查询 {limit_count} 条数据用于计算均线")

            stmt = stmt.order_by(DailyMarketData.date.desc())
            stmt = stmt.limit(limit_count)

            result = await self.session.execute(stmt)
            market_data_list = result.scalars().all()

            if not market_data_list:
                logger.warning(f"[板块均线] 板块 {sector.name} 在指定范围内没有市场数据")
                return {
                    "success": False,
                    "error": "没有找到该板块的市场数据"
                }

            # 反转列表，使数据按日期升序排列
            market_data_list = list(reversed(market_data_list))

            # 获取数据日期范围
            data_start_date = market_data_list[0].date
            data_end_date = market_data_list[-1].date
            total_days = len(market_data_list)

            logger.info(
                f"[板块均线] 板块 {sector.name} 查询到 {total_days} 个交易日数据 "
                f"({data_start_date} 至 {data_end_date})"
            )

            # 记录保存范围
            save_start_date = start_date if start_date else data_start_date
            save_end_date = end_date if end_date else data_end_date
            if save_start_date != data_start_date or save_end_date != data_end_date:
                logger.info(
                    f"[板块均线] 将保存时间范围 {save_start_date} 至 {save_end_date} 内的均线数据"
                )

            # ========================================
            # 步骤2: 转换为 pandas DataFrame
            # ========================================
            data = {
                "date": [md.date for md in market_data_list],
                "close": [float(md.close) for md in market_data_list]
            }
            df = pd.DataFrame(data)
            df.set_index("date", inplace=True)
            df = df.sort_index()

            total_created = 0
            total_updated = 0
            total_skipped = 0

            # ========================================
            # 步骤3: 按周期计算均线（每计算完一个周期就保存）
            # ========================================
            for period_idx, period in enumerate(periods, 1):
                period_str = f"{period}d"

                logger.info(f"[板块均线] 开始计算 {sector.name} 的 {period} 日均线 [{period_idx}/{len(periods)}]")

                if len(df) < period:
                    logger.warning(f"[板块均线] 板块 {sector.name} 数据不足，无法计算 {period} 日均线（需要 {period} 天，实际 {len(df)} 天）")
                    continue

                # ========================================
                # 步骤3.1: 检查该周期的断点（已有数据的最大日期）
                # ========================================
                # 用于计算均线的数据集：始终使用完整数据，确保均线计算正确
                calc_df = df

                # 用于保存的数据集：根据断点续传逻辑确定
                save_df = df
                save_start_date_limit = None

                if not overwrite:
                    # 查询该周期已有数据的最大日期
                    latest_period_stmt = select(func.max(MovingAverageData.date)).where(
                        and_(
                            MovingAverageData.entity_type == "sector",
                            MovingAverageData.entity_id == sector.id,
                            MovingAverageData.symbol == sector.code,
                            MovingAverageData.period == period_str
                        )
                    )
                    latest_period_result = await self.session.execute(latest_period_stmt)
                    latest_period_date = latest_period_result.scalar()

                    if latest_period_date:
                        logger.info(f"[板块均线] {sector.name} {period}日均线已有数据，最新日期: {latest_period_date}，将从该日期后继续保存")
                        # 过滤出需要保存的数据（从最新日期的下一天开始）
                        save_df = df[df.index > latest_period_date]
                        save_start_date_limit = latest_period_date

                        if len(save_df) == 0:
                            logger.info(f"[板块均线] {sector.name} {period}日均线数据已是最新，跳过该周期")
                            total_skipped += 0  # 本周期没有处理任何数据
                            continue

                        logger.info(f"[板块均线] {sector.name} {period}日均线需要保存 {len(save_df)} 天的新数据（使用全部 {len(df)} 天数据计算均线）")
                    else:
                        logger.info(f"[板块均线] {sector.name} {period}日均线无历史数据，将计算并保存全部数据")

                # 计算均线：使用完整数据集计算
                ma_series = self.ma_calculator.calculate_sma(calc_df["close"], period)

                # 统计本周期的处理情况
                period_created = 0
                period_updated = 0
                period_skipped = 0
                batch_records = []
                batch_size = 500  # 每500条记录提交一次

                # 遍历均线数据，只保存 save_df 中的数据
                for idx, ma_value in ma_series.items():
                    if pd.isna(ma_value):
                        continue

                    # 只保存 save_df 中的数据（断点之后的数据）
                    if idx not in save_df.index:
                        continue

                    # 应用日期过滤：只保存指定时间范围内的均线数据
                    if start_date and idx < start_date:
                        continue
                    if end_date and idx > end_date:
                        continue

                    current_price = save_df.loc[idx, "close"]

                    # 计算价格比率和趋势
                    price_ratio = self.ma_calculator.calculate_price_ratio(current_price, ma_value)
                    trend = 1 if price_ratio > 0 else (-1 if price_ratio < 0 else 0)

                    # 检查是否已存在
                    existing_stmt = select(MovingAverageData).where(
                        and_(
                            MovingAverageData.entity_type == "sector",
                            MovingAverageData.entity_id == sector.id,
                            MovingAverageData.symbol == sector.code,
                            MovingAverageData.date == idx,
                            MovingAverageData.period == period_str
                        )
                    )
                    existing_result = await self.session.execute(existing_stmt)
                    existing_ma = existing_result.scalar_one_or_none()

                    if existing_ma:
                        if overwrite:
                            # 更新已有数据
                            existing_ma.ma_value = ma_value
                            existing_ma.price_ratio = price_ratio
                            existing_ma.trend = trend
                            existing_ma.symbol = sector.code
                            period_updated += 1
                        else:
                            period_skipped += 1
                    else:
                        # 创建新记录对象
                        ma_record = MovingAverageData(
                            entity_type="sector",
                            entity_id=sector.id,
                            symbol=sector.code,
                            date=idx,
                            period=period_str,
                            ma_value=ma_value,
                            price_ratio=price_ratio,
                            trend=trend
                        )
                        batch_records.append(ma_record)
                        period_created += 1

                    # 分批保存
                    if len(batch_records) >= batch_size:
                        for record in batch_records:
                            self.session.add(record)
                        await self.session.commit()
                        logger.info(f"[板块均线] {sector.name} {period}日均线 - 已保存 {len(batch_records)} 条记录（总计创建: {period_created}）")
                        batch_records = []

                # 保存剩余记录
                if batch_records:
                    for record in batch_records:
                        self.session.add(record)
                    await self.session.commit()
                    logger.info(f"[板块均线] {sector.name} {period}日均线 - 已保存最后 {len(batch_records)} 条记录")

                total_created += period_created
                total_updated += period_updated
                total_skipped += period_skipped

                logger.info(
                    f"[板块均线] {sector.name} {period}日均线计算完成 - "
                    f"创建: {period_created}, 更新: {period_updated}, 跳过: {period_skipped}"
                )

            logger.info(
                f"[板块均线] 板块 {sector.name} 全部周期计算完成 - "
                f"总计创建: {total_created}, 更新: {total_updated}, 跳过: {total_skipped}"
            )

            return {
                "success": True,
                "created": total_created,
                "updated": total_updated,
                "skipped": total_skipped
            }

        except Exception as e:
            logger.error(f"[板块均线] 计算板块 {sector.name} 均线失败: {e}")
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def get_latest_ma_values(
        self,
        sector_id: int,
        periods: Optional[List[int]] = None
    ) -> Dict[str, Optional[float]]:
        """
        获取板块最新的均线值

        Args:
            sector_id: 板块ID
            periods: 均线周期列表

        Returns:
            最新均线值字典 {period: ma_value}
        """
        if periods is None:
            periods = self.DEFAULT_PERIODS

        result = {}

        for period in periods:
            period_str = f"{period}d"

            # 获取该周期最新的均线数据
            stmt = select(MovingAverageData).where(
                and_(
                    MovingAverageData.entity_type == "sector",
                    MovingAverageData.entity_id == sector_id,
                    MovingAverageData.period == period_str
                )
            ).order_by(MovingAverageData.date.desc()).limit(1)

            ma_result = await self.session.execute(stmt)
            ma_data = ma_result.scalar_one_or_none()

            result[period_str] = float(ma_data.ma_value) if ma_data else None

        return result

    async def backfill_sector_ma(
        self,
        target_date: date,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        补齐指定日期的板块均线

        Args:
            target_date: 目标日期
            overwrite: 是否覆盖已有数据

        Returns:
            补齐结果
        """
        return await self.calculate_sector_moving_averages(
            start_date=target_date,
            end_date=target_date,
            overwrite=overwrite
        )

    async def get_sector_ma_summary(
        self,
        sector_id: int
    ) -> Dict[str, Any]:
        """
        获取板块均线数据摘要

        Args:
            sector_id: 板块ID

        Returns:
            均线数据摘要
        """
        # 获取板块信息
        stmt = select(Sector).where(Sector.id == sector_id)
        result = await self.session.execute(stmt)
        sector = result.scalar_one_or_none()

        if not sector:
            return {
                "success": False,
                "error": "板块不存在"
            }

        # 获取最新收盘价
        price_stmt = select(DailyMarketData).where(
            and_(
                DailyMarketData.entity_type == "sector",
                DailyMarketData.entity_id == sector_id
            )
        ).order_by(DailyMarketData.date.desc()).limit(1)

        price_result = await self.session.execute(price_stmt)
        latest_price_data = price_result.scalar_one_or_none()

        current_price = float(latest_price_data.close) if latest_price_data else None

        # 获取最新均线值
        ma_values = await self.get_latest_ma_values(sector_id)

        # 计算价格比率
        price_ratios = {}
        for period, ma_value in ma_values.items():
            if ma_value and current_price:
                price_ratios[period] = self.ma_calculator.calculate_price_ratio(
                    current_price, ma_value
                )

        return {
            "success": True,
            "sector_id": sector_id,
            "sector_name": sector.name,
            "sector_code": sector.code,
            "current_price": current_price,
            "latest_date": latest_price_data.date if latest_price_data else None,
            "ma_values": ma_values,
            "price_ratios": price_ratios,
        }

    async def get_sector_date_range(
        self,
        sector_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取板块数据的日期范围

        Args:
            sector_id: 板块ID，None表示获取所有板块的日期范围

        Returns:
            日期范围信息
        """
        if sector_id:
            # 获取单个板块的日期范围
            stmt = select(
                func.min(DailyMarketData.date).label('min_date'),
                func.max(DailyMarketData.date).label('max_date'),
                func.count(DailyMarketData.id).label('data_count')
            ).where(
                and_(
                    DailyMarketData.entity_type == "sector",
                    DailyMarketData.entity_id == sector_id,
                    DailyMarketData.close.isnot(None)
                )
            )
        else:
            # 获取所有板块的日期范围
            stmt = select(
                func.min(DailyMarketData.date).label('min_date'),
                func.max(DailyMarketData.date).label('max_date'),
                func.count(DailyMarketData.id).label('data_count')
            ).where(
                and_(
                    DailyMarketData.entity_type == "sector",
                    DailyMarketData.close.isnot(None)
                )
            )

        result = await self.session.execute(stmt)
        row = result.fetchone()

        if not row or row.data_count == 0:
            return {
                "success": False,
                "error": "没有找到板块数据"
            }

        return {
            "success": True,
            "min_date": row.min_date,
            "max_date": row.max_date,
            "data_count": row.data_count
        }

    async def calculate_full_history_ma(
        self,
        sector_id: Optional[int] = None,
        periods: Optional[List[int]] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        计算板块完整历史均线（从最早数据日期到最新日期）

        Args:
            sector_id: 板块ID，None表示计算所有板块
            periods: 均线周期列表
            overwrite: 是否覆盖已有数据

        Returns:
            计算结果
        """
        try:
            # 获取周期配置
            if periods is None:
                periods = self.DEFAULT_PERIODS

            # 获取板块列表
            if sector_id:
                stmt = select(Sector).where(Sector.id == sector_id)
            else:
                stmt = select(Sector)

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
                try:
                    # 获取该板块的日期范围
                    date_range = await self.get_sector_date_range(sector.id)

                    if not date_range.get("success"):
                        logger.warning(f"板块 {sector.name} 没有市场数据")
                        error_count += 1
                        continue

                    start_date = date_range.get("min_date")
                    end_date = date_range.get("max_date")
                    data_count = date_range.get("data_count", 0)

                    await self._report_progress(
                        idx + 1,
                        total,
                        f"计算板块完整历史均线: {sector.name} ({sector.code}) - 共{data_count}天数据"
                    )

                    # 计算单个板块的完整历史均线
                    result = await self._calculate_single_sector_ma(
                        sector=sector,
                        start_date=start_date,
                        end_date=end_date,
                        periods=periods,
                        overwrite=overwrite
                    )

                    if result.get("success"):
                        created_count += result.get("created", 0)
                        updated_count += result.get("updated", 0)
                        skipped_count += result.get("skipped", 0)
                    else:
                        error_count += 1
                        logger.warning(f"板块 {sector.name} 均线计算失败: {result.get('error')}")

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

        except Exception as e:
            logger.error(f"板块完整历史均线计算失败: {e}")
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }
