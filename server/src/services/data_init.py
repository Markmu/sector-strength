"""
数据初始化服务

提供系统首次数据初始化功能，包括板块、股票和历史数据获取。
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.stock import Stock
from src.models.sector_stock import SectorStock
from src.models.daily_market_data import DailyMarketData
from src.services.data_acquisition.akshare_client import AkShareDataSource
from src.services.data_acquisition.models import StockInfo, SectorInfo, DailyQuote, SectorConstituent

logger = logging.getLogger(__name__)


class DataInitService:
    """
    数据初始化服务

    负责从 AkShare 获取初始数据并填充数据库。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化数据初始化服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.ak_source = AkShareDataSource()
        self._progress_callback: Optional[callable] = None
        self._cancelled = False

    def set_progress_callback(self, callback: callable):
        """
        设置进度回调函数

        Args:
            callback: 回调函数，签名为 (current: int, total: int, message: str) -> None
        """
        self._progress_callback = callback

    async def _update_progress(self, current: int, total: int, message: str):
        """
        更新进度

        Args:
            current: 当前进度
            total: 总数
            message: 进度消息
        """
        if self._progress_callback:
            try:
                # 直接 await 回调，不使用 create_task
                if asyncio.iscoroutinefunction(self._progress_callback):
                    await self._progress_callback(current, total, message)
                else:
                    self._progress_callback(current, total, message)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

    def cancel(self):
        """取消当前初始化任务"""
        self._cancelled = True
        logger.warning("数据初始化任务已请求取消")

    def _check_cancelled(self):
        """检查是否已取消"""
        if self._cancelled:
            raise InterruptedError("数据初始化任务已被取消")

    async def init_sectors(self, sector_type: Optional[str] = None) -> dict:
        """
        初始化板块数据及其成分股关联

        此方法会：
        1. 从 AkShare 获取板块列表
        2. 创建板块记录
        3. 获取每个板块的成分股并建立关联关系

        Args:
            sector_type: 板块类型过滤 (industry/concept)，None 表示获取所有

        Returns:
            初始化结果字典: {"success": bool, "created": int, "skipped": int, "relations_created": int, "errors": list}
        """
        self._cancelled = False
        logger.info(f"开始初始化板块数据 (类型: {sector_type or '全部'})")

        try:
            # 从 AkShare 获取板块列表
            sectors = self.ak_source.get_sector_list(sector_type)
            self._check_cancelled()

            created = 0
            skipped = 0
            relations_created = 0
            errors = []

            for i, sector_info in enumerate(sectors, 1):
                self._check_cancelled()
                await self._update_progress(i, len(sectors), f"正在处理板块: {sector_info.name}")

                try:
                    # 使用 savepoint 隔离每个板块的操作，防止单个失败影响整个事务
                    async with self.session.begin_nested():
                        # 检查板块是否已存在
                        result = await self.session.execute(
                            select(Sector).where(Sector.code == sector_info.code)
                        )
                        existing = result.scalar_one_or_none()

                        if existing:
                            skipped += 1
                            logger.debug(f"板块已存在，跳过: {sector_info.code} - {sector_info.name}")
                        else:
                            # 创建新板块
                            sector = Sector(
                                code=sector_info.code,
                                name=sector_info.name,
                                type=sector_info.type,
                                description=f"{sector_info.type} sector from AkShare"
                            )
                            self.session.add(sector)
                            created += 1
                            logger.debug(f"创建板块: {sector_info.code} - {sector_info.name}")

                        # 获取板块成分股并建立关联（无论板块是新建还是已存在）
                        try:
                            constituents = self.ak_source.get_sector_stocks(sector_info.code)

                            for constituent in constituents:
                                # 检查关联是否已存在
                                result = await self.session.execute(
                                    select(SectorStock).where(
                                        SectorStock.sector_code == sector_info.code,
                                        SectorStock.stock_code == constituent.symbol
                                    )
                                )
                                existing_relation = result.scalar_one_or_none()

                                if not existing_relation:
                                    # 创建板块-股票关联
                                    sector_stock = SectorStock(
                                        sector_code=sector_info.code,
                                        stock_code=constituent.symbol
                                    )
                                    self.session.add(sector_stock)
                                    relations_created += 1

                            logger.debug(f"板块 {sector_info.code} 建立了 {len(constituents)} 个成分股关联")

                        except Exception as e:
                            # 成分股获取失败不影响板块创建
                            logger.warning(f"获取板块 {sector_info.code} 成分股失败: {e}")
                            errors.append(f"板块 {sector_info.code} 成分股获取失败: {e}")

                except Exception as e:
                    error_msg = f"处理板块失败 {sector_info.code}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # 提交事务
            await self.session.commit()

            result = {
                "success": True,
                "created": created,
                "skipped": skipped,
                "relations_created": relations_created,
                "errors": errors,
                "total": len(sectors)
            }

            logger.info(f"板块初始化完成: 创建 {created}, 跳过 {skipped}, 关联创建 {relations_created}, 错误 {len(errors)}")
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("板块初始化已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"板块初始化失败: {e}")
            return {"success": False, "error": str(e)}

    async def init_stocks(self) -> dict:
        """
        初始化股票数据

        Returns:
            初始化结果字典
        """
        self._cancelled = False
        logger.info("开始初始化股票数据")

        try:
            # 从 AkShare 获取股票列表
            stocks = self.ak_source.get_stock_list()
            self._check_cancelled()

            created = 0
            skipped = 0
            errors = []

            for i, stock_info in enumerate(stocks, 1):
                self._check_cancelled()
                await self._update_progress(i, len(stocks), f"正在处理股票: {stock_info.symbol} - {stock_info.name}")

                try:
                    # 使用 savepoint 隔离每个股票的操作
                    async with self.session.begin_nested():
                        # 检查股票是否已存在
                        result = await self.session.execute(
                            select(Stock).where(Stock.symbol == stock_info.symbol)
                        )
                        existing = result.scalar_one_or_none()

                        if existing:
                            skipped += 1
                            logger.debug(f"股票已存在，跳过: {stock_info.symbol}")
                        else:
                            # 创建新股票
                            stock = Stock(
                                symbol=stock_info.symbol,
                                name=stock_info.name,
                                current_price=None,
                                market_cap=None
                            )
                            self.session.add(stock)
                            created += 1
                            logger.debug(f"创建股票: {stock_info.symbol} - {stock_info.name}")

                except Exception as e:
                    error_msg = f"处理股票失败 {stock_info.symbol}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # 提交事务
            await self.session.commit()

            result = {
                "success": True,
                "created": created,
                "skipped": skipped,
                "errors": errors,
                "total": len(stocks)
            }

            logger.info(f"股票初始化完成: 创建 {created}, 跳过 {skipped}, 错误 {len(errors)}")
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("股票初始化已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"股票初始化失败: {e}")
            return {"success": False, "error": str(e)}

    async def init_historical_data(
        self,
        days: int = 60,
        symbol_filter: Optional[list[str]] = None
    ) -> dict:
        """
        初始化历史行情数据

        Args:
            days: 回溯天数（1-365）
            symbol_filter: 股票代码过滤列表，None 表示全部

        Returns:
            初始化结果字典
        """
        self._cancelled = False

        # 验证参数
        days = max(1, min(365, days))
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        logger.info(f"开始初始化历史数据: {start_date} 至 {end_date} ({days} 天)")

        try:
            # 获取需要处理的股票列表
            if symbol_filter:
                # 使用过滤列表
                symbols = symbol_filter
            else:
                # 获取所有股票
                result = await self.session.execute(select(Stock.symbol))
                symbols = [row[0] for row in result.all()]

            self._check_cancelled()

            created = 0
            skipped = 0
            errors = []

            for i, symbol in enumerate(symbols, 1):
                self._check_cancelled()
                await self._update_progress(i, len(symbols), f"正在获取历史数据: {symbol}")

                try:
                    # 使用 savepoint 隔离每个股票的操作
                    async with self.session.begin_nested():
                        # 获取股票ID
                        result = await self.session.execute(
                            select(Stock).where(Stock.symbol == symbol)
                        )
                        stock = result.scalar_one_or_none()

                        if not stock:
                            logger.warning(f"股票不存在，跳过: {symbol}")
                            skipped += 1
                            continue

                        # 从 AkShare 获取历史数据
                        quotes = self.ak_source.get_daily_data(symbol, start_date, end_date)

                        for quote in quotes:
                            # 检查数据是否已存在
                            result = await self.session.execute(
                                select(DailyMarketData).where(
                                    DailyMarketData.entity_type == "stock",
                                    DailyMarketData.entity_id == stock.id,
                                    DailyMarketData.date == quote.trade_date
                                )
                            )
                            existing = result.scalar_one_or_none()

                            if existing:
                                continue

                            # 创建新记录
                            market_data = DailyMarketData(
                                entity_type="stock",
                                entity_id=stock.id,
                                symbol=stock.symbol,
                                date=quote.trade_date,
                                open=quote.open,
                                high=quote.high,
                                low=quote.low,
                                close=quote.close,
                                volume=quote.volume,
                                turnover=quote.turnover,
                                change=None,
                                change_percent=None
                            )
                            self.session.add(market_data)
                            created += 1

                except Exception as e:
                    error_msg = f"获取历史数据失败 {symbol}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # 最终提交
            await self.session.commit()

            result = {
                "success": True,
                "created": created,
                "skipped": skipped,
                "errors": errors,
                "total_symbols": len(symbols)
            }

            logger.info(f"历史数据初始化完成: 创建 {created}, 跳过 {skipped}, 错误 {len(errors)}")
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("历史数据初始化已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"历史数据初始化失败: {e}")
            return {"success": False, "error": str(e)}

    async def init_historical_data_by_date_range(
        self,
        start_date: date,
        end_date: date,
        symbol_filter: Optional[list[str]] = None
    ) -> dict:
        """
        根据日期范围初始化历史行情数据

        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbol_filter: 股票代码过滤列表，None 表示全部

        Returns:
            初始化结果字典
        """
        self._cancelled = False

        # 验证日期范围
        if start_date > end_date:
            return {"success": False, "error": "开始日期不能晚于结束日期"}

        # 计算年份差
        years_diff = (end_date.year - start_date.year)
        if end_date.month < start_date.month or (end_date.month == start_date.month and end_date.day < start_date.day):
            years_diff -= 1

        if years_diff > 10:
            return {"success": False, "error": "日期范围不能超过 10 年"}

        days = (end_date - start_date).days + 1
        logger.info(f"开始初始化历史数据: {start_date} 至 {end_date} ({days} 天，约 {years_diff + 1} 年)")

        try:
            # 获取需要处理的股票列表
            if symbol_filter:
                # 使用过滤列表
                symbols = symbol_filter
            else:
                # 获取所有股票
                result = await self.session.execute(select(Stock.symbol))
                symbols = [row[0] for row in result.all()]

            self._check_cancelled()

            created = 0
            skipped = 0
            errors = []
            processed_symbols = []  # 记录已处理的股票

            for i, symbol in enumerate(symbols, 1):
                self._check_cancelled()
                await self._update_progress(i, len(symbols), f"正在获取历史数据: {symbol} ({start_date} - {end_date})")

                try:
                    # 获取股票ID
                    result = await self.session.execute(
                        select(Stock).where(Stock.symbol == symbol)
                    )
                    stock = result.scalar_one_or_none()

                    if not stock:
                        logger.warning(f"股票不存在，跳过: {symbol}")
                        skipped += 1
                        continue

                    # 检查这只股票是否已有数据（断点续传支持）
                    result = await self.session.execute(
                        select(DailyMarketData).where(
                            DailyMarketData.entity_type == "stock",
                            DailyMarketData.entity_id == stock.id,
                            DailyMarketData.date.between(start_date, end_date)
                        ).limit(1)
                    )
                    has_existing_data = result.scalar_one_or_none() is not None

                    if has_existing_data:
                        logger.info(f"股票 {symbol} 在日期范围内已有数据，跳过")
                        skipped += 1
                        processed_symbols.append(symbol)
                        continue

                    # 从 AkShare 获取历史数据
                    quotes = self.ak_source.get_daily_data(symbol, start_date, end_date)

                    symbol_created = 0
                    for quote in quotes:
                        # 检查数据是否已存在
                        result = await self.session.execute(
                            select(DailyMarketData).where(
                                DailyMarketData.entity_type == "stock",
                                DailyMarketData.entity_id == stock.id,
                                DailyMarketData.date == quote.trade_date
                            )
                        )
                        existing = result.scalar_one_or_none()

                        if existing:
                            continue

                        # 创建新记录
                        market_data = DailyMarketData(
                            entity_type="stock",
                            entity_id=stock.id,
                            symbol=stock.symbol,
                            date=quote.trade_date,
                            open=quote.open,
                            high=quote.high,
                            low=quote.low,
                            close=quote.close,
                            volume=quote.volume,
                            turnover=quote.turnover,
                            change=None,
                            change_percent=None
                        )
                        self.session.add(market_data)
                        created += 1
                        symbol_created += 1

                    # 每只股票处理完后立即提交
                    await self.session.commit()
                    processed_symbols.append(symbol)
                    logger.debug(f"股票 {symbol} 数据已保存: {symbol_created} 条记录")

                except Exception as e:
                    error_msg = f"获取历史数据失败 {symbol}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    # 发生错误时回滚当前股票的更改
                    await self.session.rollback()
            # 不需要最终提交，因为每只股票都已提交

            result = {
                "success": True,
                "created": created,
                "skipped": skipped,
                "errors": errors,
                "total_symbols": len(symbols),
                "processed_symbols": len(processed_symbols),
                "date_range": f"{start_date} to {end_date}"
            }

            logger.info(f"历史数据初始化完成: 创建 {created}, 跳过 {skipped}, 已处理 {len(processed_symbols)}/{len(symbols)} 只股票, 错误 {len(errors)}")
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("历史数据初始化已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"历史数据初始化失败: {e}")
            return {"success": False, "error": str(e)}

    async def init_sector_historical_data(
        self,
        days: Optional[int] = None,
        sector_filter: Optional[list[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """
        初始化板块历史行情数据

        使用 AkShare 的 stock_board_industry_hist_em 接口直接获取板块历史数据。

        Args:
            days: 回溯天数（1-365），如果提供 start_date/end_date 则忽略此参数
            sector_filter: 板块代码过滤列表，None 表示全部
            start_date: 开始日期，如果提供则优先使用
            end_date: 结束日期，如果提供则优先使用

        Returns:
            初始化结果字典
        """
        self._cancelled = False

        # 确定日期范围
        if start_date and end_date:
            # 使用传入的日期范围
            pass
        elif days is not None:
            # 使用天数计算
            days = max(1, min(365, days))
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
        else:
            # 默认 60 天
            end_date = date.today()
            start_date = end_date - timedelta(days=60)

        logger.info(f"开始初始化板块历史数据: {start_date} 至 {end_date}")

        try:
            # 获取需要处理的板块列表
            if sector_filter:
                # 使用过滤列表
                result = await self.session.execute(
                    select(Sector).where(Sector.code.in_(sector_filter))
                )
                sectors = result.scalars().all()
            else:
                # 获取所有板块
                result = await self.session.execute(select(Sector))
                sectors = result.scalars().all()

            self._check_cancelled()

            created = 0
            skipped = 0
            errors = []

            for i, sector in enumerate(sectors, 1):
                self._check_cancelled()
                await self._update_progress(i, len(sectors), f"正在获取板块历史数据: {sector.name}")

                try:
                    # 使用 savepoint 隔离每个板块的操作
                    async with self.session.begin_nested():
                        # 从 AkShare 直接获取板块历史数据
                        quotes = self.ak_source.get_sector_daily_data(
                            sector.code, start_date, end_date
                        )

                        if not quotes:
                            logger.warning(f"板块 {sector.code} 没有获取到历史数据，跳过")
                            skipped += 1
                            continue

                        sector_created = 0
                        for quote in quotes:
                            # 检查数据是否已存在
                            result = await self.session.execute(
                                select(DailyMarketData).where(
                                    DailyMarketData.entity_type == "sector",
                                    DailyMarketData.entity_id == sector.id,
                                    DailyMarketData.date == quote.trade_date
                                )
                            )
                            existing = result.scalar_one_or_none()

                            if existing:
                                continue

                            # 创建新记录
                            market_data = DailyMarketData(
                                entity_type="sector",
                                entity_id=sector.id,
                                symbol=sector.code,
                                date=quote.trade_date,
                                open=quote.open,
                                high=quote.high,
                                low=quote.low,
                                close=quote.close,
                                volume=quote.volume,
                                turnover=quote.turnover,
                                change=None,
                                change_percent=None
                            )
                            self.session.add(market_data)
                            created += 1
                            sector_created += 1

                        logger.debug(f"板块 {sector.code} 数据已保存: {sector_created} 条记录")

                except Exception as e:
                    error_msg = f"获取板块历史数据失败 {sector.code}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # 最终提交
            await self.session.commit()

            result = {
                "success": True,
                "created": created,
                "skipped": skipped,
                "errors": errors,
                "total_sectors": len(sectors)
            }

            logger.info(f"板块历史数据初始化完成: 创建 {created}, 跳过 {skipped}, 错误 {len(errors)}")
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("板块历史数据初始化已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"板块历史数据初始化失败: {e}")
            return {"success": False, "error": str(e)}

    async def init_sector_stocks(self) -> dict:
        """
        初始化板块成分股关联

        Returns:
            初始化结果字典
        """
        self._cancelled = False
        logger.info("开始初始化板块成分股关联")

        try:
            # 获取所有板块
            result = await self.session.execute(select(Sector))
            sectors = result.scalars().all()

            if not sectors:
                return {"success": False, "error": "没有找到板块数据，请先初始化板块"}

            created = 0
            errors = []

            total = len(sectors)
            for i, sector in enumerate(sectors, 1):
                self._check_cancelled()
                await self._update_progress(i, total, f"正在获取板块成分股: {sector.name}")

                try:
                    # 使用 savepoint 隔离每个板块的操作
                    async with self.session.begin_nested():
                        # 获取板块成分股
                        constituents = self.ak_source.get_sector_stocks(sector.code)

                        for constituent in constituents:
                            # 查找股票记录
                            result = await self.session.execute(
                                select(Stock).where(Stock.symbol == constituent.symbol)
                            )
                            stock = result.scalar_one_or_none()

                            if not stock:
                                continue

                            # 检查关联是否已存在
                            result = await self.session.execute(
                                select(SectorStock).where(
                                    SectorStock.sector_code == sector.code,
                                    SectorStock.stock_code == stock.symbol
                                )
                            )
                            existing = result.scalar_one_or_none()

                            if not existing:
                                # 创建关联
                                sector_stock = SectorStock(
                                    sector_code=sector.code,
                                    stock_code=stock.symbol
                                )
                                self.session.add(sector_stock)
                                created += 1

                except Exception as e:
                    error_msg = f"获取板块成分股失败 {sector.code}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)

            # 提交事务
            await self.session.commit()

            result = {
                "success": True,
                "created": created,
                "errors": errors,
                "total_sectors": total
            }

            logger.info(f"板块成分股关联完成: 创建 {created}, 错误 {len(errors)}")
            return result

        except InterruptedError:
            await self.session.rollback()
            logger.warning("板块成分股关联已取消")
            return {"success": False, "cancelled": True, "message": "任务已取消"}
        except Exception as e:
            await self.session.rollback()
            logger.error(f"板块成分股关联失败: {e}")
            return {"success": False, "error": str(e)}
