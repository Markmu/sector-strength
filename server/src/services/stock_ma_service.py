"""
股票均线计算服务

处理股票均线数据的计算和更新。
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import date, datetime
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from src.models.stock import Stock
from src.models.daily_market_data import DailyMarketData
from src.models.moving_average_data import MovingAverageData
from src.services.calculation.moving_average_calculator import MovingAverageCalculator
from src.models.period_config import PeriodConfig

logger = logging.getLogger(__name__)


class StockMAService:
    """股票均线计算服务"""

    # 默认计算的均线周期
    DEFAULT_PERIODS = [5, 10, 20, 30, 60]

    def __init__(self, session: AsyncSession):
        """
        初始化股票均线计算服务

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

    async def calculate_stock_moving_averages(
        self,
        stock_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        periods: Optional[List[int]] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        计算股票均线

        Args:
            stock_id: 股票ID，None表示计算所有股票
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

            # 获取股票列表
            if stock_id:
                stmt = select(Stock).where(Stock.id == stock_id)
            else:
                stmt = select(Stock)

            result = await self.session.execute(stmt)
            stocks = result.scalars().all()

            if not stocks:
                return {
                    "success": False,
                    "error": "未找到股票数据"
                }

            total = len(stocks)
            created_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0

            for idx, stock in enumerate(stocks):
                try:
                    await self._report_progress(
                        idx + 1,
                        total,
                        f"计算股票均线: {stock.name} ({stock.symbol})"
                    )

                    # 计算单个股票的均线
                    result = await self._calculate_single_stock_ma(
                        stock=stock,
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
                        logger.warning(f"股票 {stock.name} 均线计算失败: {result.get('error')}")

                except Exception as e:
                    error_count += 1
                    logger.error(f"处理股票 {stock.name} 时出错: {e}")

            await self.session.commit()

            return {
                "success": True,
                "total_stocks": total,
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": error_count
            }

        except Exception as e:
            logger.error(f"股票均线计算失败: {e}")
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def _calculate_single_stock_ma(
        self,
        stock: Stock,
        start_date: Optional[date],
        end_date: Optional[date],
        periods: List[int],
        overwrite: bool
    ) -> Dict[str, Any]:
        """
        计算单个股票的均线（支持断点续传和分批保存）

        Args:
            stock: 股票对象
            start_date: 开始日期
            end_date: 结束日期
            periods: 均线周期列表
            overwrite: 是否覆盖已有数据

        Returns:
            计算结果
        """
        try:
            logger.info(f"[股票均线] 开始计算股票 {stock.name}({stock.symbol}) 的均线数据")

            # ========================================
            # 步骤1: 获取股票历史数据
            # ========================================
            stmt = select(DailyMarketData).where(
                and_(
                    DailyMarketData.entity_type == "stock",
                    DailyMarketData.entity_id == stock.id,
                    DailyMarketData.close.isnot(None)
                )
            )

            if start_date:
                stmt = stmt.where(DailyMarketData.date >= start_date)
            if end_date:
                stmt = stmt.where(DailyMarketData.date <= end_date)

            stmt = stmt.order_by(DailyMarketData.date)

            result = await self.session.execute(stmt)
            market_data_list = result.scalars().all()

            if not market_data_list:
                logger.warning(f"[股票均线] 股票 {stock.name} 没有市场数据")
                return {
                    "success": False,
                    "error": "没有找到该股票的市场数据"
                }

            # 获取数据日期范围
            data_start_date = market_data_list[0].date
            data_end_date = market_data_list[-1].date
            total_days = len(market_data_list)

            logger.info(f"[股票均线] 股票 {stock.name} 数据范围: {data_start_date} 至 {data_end_date}，共 {total_days} 个交易日")

            # ========================================
            # 步骤2: 检查断点（已有数据的最大日期）
            # ========================================
            if not overwrite:
                # 查询已有数据的最大日期
                latest_stmt = select(func.max(MovingAverageData.date)).where(
                    and_(
                        MovingAverageData.entity_type == "stock",
                        MovingAverageData.entity_id == stock.id,
                        MovingAverageData.symbol == stock.symbol
                    )
                )
                latest_result = await self.session.execute(latest_stmt)
                latest_ma_date = latest_result.scalar()

                if latest_ma_date:
                    logger.info(f"[股票均线] 股票 {stock.name} 发现已有数据，最新日期: {latest_ma_date}，将从该日期后继续计算")
                    # 过滤出需要重新计算的数据（从最新日期的下一天开始）
                    market_data_list = [
                        md for md in market_data_list
                        if md.date > latest_ma_date
                    ]

                    if not market_data_list:
                        logger.info(f"[股票均线] 股票 {stock.name} 数据已是最新，无需计算")
                        return {
                            "success": True,
                            "created": 0,
                            "updated": 0,
                            "skipped": 0,
                            "resumed": True
                        }

                    logger.info(f"[股票均线] 股票 {stock.name} 需要计算 {len(market_data_list)} 天的新数据")

            # ========================================
            # 步骤3: 转换为 pandas DataFrame
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
            # 步骤4: 按周期计算均线（每计算完一个周期就保存）
            # ========================================
            for period_idx, period in enumerate(periods, 1):
                period_str = f"{period}d"

                logger.info(f"[股票均线] 开始计算 {stock.name} 的 {period} 日均线 [{period_idx}/{len(periods)}]")

                if len(df) < period:
                    logger.warning(f"[股票均线] 股票 {stock.name} 数据不足，无法计算 {period} 日均线（需要 {period} 天，实际 {len(df)} 天）")
                    continue

                # 计算均线
                ma_series = self.ma_calculator.calculate_sma(df["close"], period)

                # 统计本周期的处理情况
                period_created = 0
                period_updated = 0
                period_skipped = 0
                batch_records = []
                batch_size = 500  # 每500条记录提交一次

                # 遍历均线数据
                for idx, ma_value in ma_series.items():
                    if pd.isna(ma_value):
                        continue

                    if idx not in df.index:
                        continue

                    current_price = df.loc[idx, "close"]

                    # 计算价格比率和趋势
                    price_ratio = self.ma_calculator.calculate_price_ratio(current_price, ma_value)
                    trend = 1 if price_ratio > 0 else (-1 if price_ratio < 0 else 0)

                    # 检查是否已存在
                    existing_stmt = select(MovingAverageData).where(
                        and_(
                            MovingAverageData.entity_type == "stock",
                            MovingAverageData.entity_id == stock.id,
                            MovingAverageData.symbol == stock.symbol,
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
                            existing_ma.symbol = stock.symbol
                            period_updated += 1
                        else:
                            period_skipped += 1
                    else:
                        # 创建新记录对象
                        ma_record = MovingAverageData(
                            entity_type="stock",
                            entity_id=stock.id,
                            symbol=stock.symbol,
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
                        logger.info(f"[股票均线] {stock.name} {period}日均线 - 已保存 {len(batch_records)} 条记录（总计创建: {period_created}）")
                        batch_records = []

                # 保存剩余记录
                if batch_records:
                    for record in batch_records:
                        self.session.add(record)
                    await self.session.commit()
                    logger.info(f"[股票均线] {stock.name} {period}日均线 - 已保存最后 {len(batch_records)} 条记录")

                total_created += period_created
                total_updated += period_updated
                total_skipped += period_skipped

                logger.info(
                    f"[股票均线] {stock.name} {period}日均线计算完成 - "
                    f"创建: {period_created}, 更新: {period_updated}, 跳过: {period_skipped}"
                )

            logger.info(
                f"[股票均线] 股票 {stock.name} 全部周期计算完成 - "
                f"总计创建: {total_created}, 更新: {total_updated}, 跳过: {total_skipped}"
            )

            return {
                "success": True,
                "created": total_created,
                "updated": total_updated,
                "skipped": total_skipped
            }

        except Exception as e:
            logger.error(f"[股票均线] 计算股票 {stock.name} 均线失败: {e}")
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def get_latest_ma_values(
        self,
        stock_id: int,
        periods: Optional[List[int]] = None
    ) -> Dict[str, Optional[float]]:
        """
        获取股票最新的均线值

        Args:
            stock_id: 股票ID
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
                    MovingAverageData.entity_type == "stock",
                    MovingAverageData.entity_id == stock_id,
                    MovingAverageData.period == period_str
                )
            ).order_by(MovingAverageData.date.desc()).limit(1)

            ma_result = await self.session.execute(stmt)
            ma_data = ma_result.scalar_one_or_none()

            result[period_str] = float(ma_data.ma_value) if ma_data else None

        return result

    async def backfill_stock_ma(
        self,
        target_date: date,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        补齐指定日期的股票均线

        Args:
            target_date: 目标日期
            overwrite: 是否覆盖已有数据

        Returns:
            补齐结果
        """
        return await self.calculate_stock_moving_averages(
            start_date=target_date,
            end_date=target_date,
            overwrite=overwrite
        )

    async def get_stock_ma_summary(
        self,
        stock_id: int
    ) -> Dict[str, Any]:
        """
        获取股票均线数据摘要

        Args:
            stock_id: 股票ID

        Returns:
            均线数据摘要
        """
        # 获取股票信息
        stmt = select(Stock).where(Stock.id == stock_id)
        result = await self.session.execute(stmt)
        stock = result.scalar_one_or_none()

        if not stock:
            return {
                "success": False,
                "error": "股票不存在"
            }

        # 获取最新收盘价
        price_stmt = select(DailyMarketData).where(
            and_(
                DailyMarketData.entity_type == "stock",
                DailyMarketData.entity_id == stock_id
            )
        ).order_by(DailyMarketData.date.desc()).limit(1)

        price_result = await self.session.execute(price_stmt)
        latest_price_data = price_result.scalar_one_or_none()

        current_price = float(latest_price_data.close) if latest_price_data else None

        # 获取最新均线值
        ma_values = await self.get_latest_ma_values(stock_id)

        # 计算价格比率
        price_ratios = {}
        for period, ma_value in ma_values.items():
            if ma_value and current_price:
                price_ratios[period] = self.ma_calculator.calculate_price_ratio(
                    current_price, ma_value
                )

        return {
            "success": True,
            "stock_id": stock_id,
            "stock_name": stock.name,
            "stock_code": stock.symbol,
            "current_price": current_price,
            "latest_date": latest_price_data.date if latest_price_data else None,
            "ma_values": ma_values,
            "price_ratios": price_ratios,
        }

    async def get_stock_date_range(
        self,
        stock_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取股票数据的日期范围

        Args:
            stock_id: 股票ID，None表示获取所有股票的日期范围

        Returns:
            日期范围信息
        """
        if stock_id:
            # 获取单个股票的日期范围
            stmt = select(
                func.min(DailyMarketData.date).label('min_date'),
                func.max(DailyMarketData.date).label('max_date'),
                func.count(DailyMarketData.id).label('data_count')
            ).where(
                and_(
                    DailyMarketData.entity_type == "stock",
                    DailyMarketData.entity_id == stock_id,
                    DailyMarketData.close.isnot(None)
                )
            )
        else:
            # 获取所有股票的日期范围
            stmt = select(
                func.min(DailyMarketData.date).label('min_date'),
                func.max(DailyMarketData.date).label('max_date'),
                func.count(DailyMarketData.id).label('data_count')
            ).where(
                and_(
                    DailyMarketData.entity_type == "stock",
                    DailyMarketData.close.isnot(None)
                )
            )

        result = await self.session.execute(stmt)
        row = result.fetchone()

        if not row or row.data_count == 0:
            return {
                "success": False,
                "error": "没有找到股票数据"
            }

        return {
            "success": True,
            "min_date": row.min_date,
            "max_date": row.max_date,
            "data_count": row.data_count
        }

    async def calculate_full_history_ma(
        self,
        stock_id: Optional[int] = None,
        periods: Optional[List[int]] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        计算股票完整历史均线（从最早数据日期到最新日期）

        Args:
            stock_id: 股票ID，None表示计算所有股票
            periods: 均线周期列表
            overwrite: 是否覆盖已有数据

        Returns:
            计算结果
        """
        try:
            # 获取周期配置
            if periods is None:
                periods = self.DEFAULT_PERIODS

            # 获取股票列表
            if stock_id:
                stmt = select(Stock).where(Stock.id == stock_id)
            else:
                stmt = select(Stock)

            result = await self.session.execute(stmt)
            stocks = result.scalars().all()

            if not stocks:
                return {
                    "success": False,
                    "error": "未找到股票数据"
                }

            total = len(stocks)
            created_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0

            for idx, stock in enumerate(stocks):
                try:
                    # 获取该股票的日期范围
                    date_range = await self.get_stock_date_range(stock.id)

                    if not date_range.get("success"):
                        logger.warning(f"股票 {stock.name} 没有市场数据")
                        error_count += 1
                        continue

                    start_date = date_range.get("min_date")
                    end_date = date_range.get("max_date")
                    data_count = date_range.get("data_count", 0)

                    await self._report_progress(
                        idx + 1,
                        total,
                        f"计算股票完整历史均线: {stock.name} ({stock.symbol}) - 共{data_count}天数据"
                    )

                    # 计算单个股票的完整历史均线
                    result = await self._calculate_single_stock_ma(
                        stock=stock,
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
                        logger.warning(f"股票 {stock.name} 均线计算失败: {result.get('error')}")

                except Exception as e:
                    error_count += 1
                    logger.error(f"处理股票 {stock.name} 时出错: {e}")

            await self.session.commit()

            return {
                "success": True,
                "total_stocks": total,
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_count,
                "errors": error_count
            }

        except Exception as e:
            logger.error(f"股票完整历史均线计算失败: {e}")
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }
