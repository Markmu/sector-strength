"""
板块强度计算服务

处理板块强度得分的计算和更新，使用新的MA系统算法并保存到StrengthScore表。
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import date, datetime
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.daily_market_data import DailyMarketData
from src.models.strength_score import StrengthScore
from src.services.calculation.ma_system.strength_calculator_v2 import StrengthCalculatorV2
from src.services.calculation.ma_system.ma_data_loader import MADataLoader
from src.config.ma_system import MIN_DATA_DAYS, FULL_DATA_DAYS

logger = logging.getLogger(__name__)


class SectorStrengthService:
    """板块强度计算服务（使用MA系统V2算法）"""

    def __init__(self, session: AsyncSession):
        """
        初始化板块强度计算服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.calculator = StrengthCalculatorV2()
        self.data_loader = MADataLoader(session)
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
        logger.info(
            f"开始按日期范围计算板块强度: sector_id={sector_id or 'all'}, "
            f"start_date={start_date}, end_date={end_date}, overwrite={overwrite}"
        )

        try:
            # 获取板块列表
            if sector_id:
                stmt = select(Sector).where(Sector.id == sector_id)
                logger.info(f"查询单个板块: sector_id={sector_id}")
            else:
                stmt = select(Sector).order_by(Sector.id)
                logger.info("查询所有板块")

            result = await self.session.execute(stmt)
            sectors = result.scalars().all()

            if not sectors:
                logger.error("未找到板块数据")
                return {
                    "success": False,
                    "error": "未找到板块数据"
                }

            total = len(sectors)
            created_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0

            logger.info(f"找到 {total} 个板块需要计算强度 (日期范围: {start_date} 至 {end_date})")

            for idx, sector in enumerate(sectors):
                self._check_cancelled()

                try:
                    logger.debug(
                        f"[{idx + 1}/{total}] 处理板块: {sector.name} ({sector.code})"
                    )

                    await self._report_progress(
                        idx + 1,
                        total,
                        f"计算板块强度: {sector.name} ({sector.code})"
                    )

                    # 计算单个板块的强度
                    result = await self._calculate_single_sector_strength_by_range(
                        sector=sector,
                        start_date=start_date,
                        end_date=end_date,
                        overwrite=overwrite
                    )

                    if result.get("success"):
                        created = result.get("created", 0)
                        updated = result.get("updated", 0)
                        skipped = result.get("skipped", 0)

                        created_count += created
                        updated_count += updated
                        skipped_count += skipped

                        logger.debug(
                            f"板块 {sector.name} 完成: 新增={created}, 更新={updated}, 跳过={skipped}"
                        )
                    else:
                        error_count += 1
                        logger.warning(f"板块 {sector.name} 强度计算失败: {result.get('error')}")

                except InterruptedError:
                    raise
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理板块 {sector.name} 时出错: {e}")

            await self.session.commit()

            logger.info(
                f"板块强度按范围计算完成: "
                f"总数={total}, 新增={created_count}, 更新={updated_count}, "
                f"跳过={skipped_count}, 错误={error_count}"
            )

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
            logger.warning("按范围计算任务被取消")
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
        logger.info(f"开始计算板块完整历史强度: sector_id={sector_id or 'all'}, overwrite={overwrite}")

        try:
            # 获取板块列表
            if sector_id:
                stmt = select(Sector).where(Sector.id == sector_id)
                logger.info(f"查询单个板块: sector_id={sector_id}")
            else:
                stmt = select(Sector).order_by(Sector.id)
                logger.info("查询所有板块")

            result = await self.session.execute(stmt)
            sectors = result.scalars().all()

            if not sectors:
                logger.error("未找到板块数据")
                return {
                    "success": False,
                    "error": "未找到板块数据"
                }

            total = len(sectors)
            created_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0

            logger.info(f"找到 {total} 个板块需要计算历史强度")

            for idx, sector in enumerate(sectors):
                self._check_cancelled()

                try:
                    # 获取该板块的日期范围
                    date_range = await self._get_sector_date_range(sector.id)
                    if not date_range:
                        logger.warning(f"板块 {sector.name} (ID: {sector.id}) 没有历史数据")
                        skipped_count += 1
                        continue

                    sector_start, sector_end = date_range
                    days_count = (sector_end - sector_start).days + 1

                    logger.info(
                        f"[{idx + 1}/{total}] 处理板块: {sector.name} ({sector.code}), "
                        f"日期范围: {sector_start} 至 {sector_end} (共{days_count}天)"
                    )

                    await self._report_progress(
                        idx + 1,
                        total,
                        f"计算板块强度历史: {sector.name} ({sector.code}) - {sector_start} 至 {sector_end}"
                    )

                    # 计算该板块的完整历史强度
                    result = await self._calculate_single_sector_strength_by_range(
                        sector=sector,
                        start_date=sector_start,
                        end_date=sector_end,
                        overwrite=overwrite
                    )

                    if result.get("success"):
                        created = result.get("created", 0)
                        updated = result.get("updated", 0)
                        skipped = result.get("skipped", 0)

                        created_count += created
                        updated_count += updated
                        skipped_count += skipped

                        logger.info(
                            f"板块 {sector.name} 完成: 新增={created}, 更新={updated}, 跳过={skipped}"
                        )
                    else:
                        error_count += 1
                        logger.warning(f"板块 {sector.name} 强度计算失败: {result.get('error')}")

                except InterruptedError:
                    raise
                except Exception as e:
                    error_count += 1
                    logger.error(f"处理板块 {sector.name} (ID: {sector.id}) 时出错: {e}")

            await self.session.commit()

            logger.info(
                f"板块完整历史强度计算完成: "
                f"总数={total}, 新增={created_count}, 更新={updated_count}, "
                f"跳过={skipped_count}, 错误={error_count}"
            )

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
            logger.warning("完整历史计算任务被取消")
            raise
        except Exception as e:
            logger.error(f"板块强度计算失败: {e}")
            await self.session.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def _calculate_single_sector_strength_by_range(
        self,
        sector: Sector,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        计算单个板块在指定日期范围内的强度

        Args:
            sector: 板块对象
            start_date: 开始日期
            end_date: 结束日期
            overwrite: 是否覆盖已有数据

        Returns:
            计算结果
        """
        logger.debug(
            f"开始计算板块 {sector.name} 强度: "
            f"{start_date} 至 {end_date}, overwrite={overwrite}"
        )

        try:
            # 获取该板块的日期范围
            sector_date_range = await self._get_sector_date_range(sector.id)
            if not sector_date_range:
                return {
                    "success": False,
                    "error": "该板块没有市场数据"
                }

            sector_start, sector_end = sector_date_range

            # 如果没有指定日期范围，使用板块的完整日期范围
            if start_date is None:
                start_date = sector_start
            if end_date is None:
                end_date = sector_end

            # 确保日期范围在板块数据范围内
            start_date = max(start_date, sector_start)
            end_date = min(end_date, sector_end)

            # 获取所有需要计算的日期
            dates_to_calc = await self._get_dates_to_calculate(sector.id, start_date, end_date)

            total_dates = len(dates_to_calc)
            if total_dates == 0:
                logger.warning(f"板块 {sector.name} 在指定日期范围内没有可用数据")
                return {
                    "success": True,
                    "created": 0,
                    "updated": 0,
                    "skipped": 0
                }

            logger.debug(f"板块 {sector.name} 需要计算 {total_dates} 个日期的强度数据")

            created = 0
            updated = 0
            skipped = 0
            errored = 0

            # 每批次保存后 flush 的日期数量（阶段保存）
            BATCH_FLUSH_SIZE = 10

            # 按日期计算强度
            for date_idx, calc_date in enumerate(dates_to_calc):
                self._check_cancelled()

                # 每处理 100 个日期输出一次进度
                if date_idx > 0 and date_idx % 100 == 0:
                    logger.debug(
                        f"板块 {sector.name} 进度: {date_idx}/{total_dates} "
                        f"(新增={created}, 更新={updated}, 跳过={skipped})"
                    )

                # 记录本次循环是否有数据变更
                has_change = False

                # 检查是否已有数据
                existing = await self._get_existing_strength_score(sector.id, calc_date)

                if existing and not overwrite:
                    # 每跳过100条输出一次警告
                    if skipped == 0 or (skipped + 1) % 100 == 0:
                        logger.warning(
                            f"板块 {sector.name} 日期 {calc_date} 已有数据，跳过 (overwrite=False)。"
                            f"如需覆盖，请设置 overwrite=True"
                        )
                    skipped += 1
                    continue

                # 加载计算所需的数据
                data = await self.data_loader.load_data_for_calculation(
                    entity_type="sector",
                    entity_id=sector.id,
                    calc_date=calc_date
                )

                if not data["has_data"]:
                    # 只在第一次输出详细信息
                    if skipped == 0:
                        logger.warning(
                            f"板块 {sector.name} 日期 {calc_date} 无有效数据，跳过。"
                            f"可能原因：1) 市场数据缺失 2) 均线数据缺失"
                        )
                    skipped += 1
                    continue

                current_price = data["current_price"]
                ma_values = data["ma_values"]
                available_days = data["available_days"]

                # 检查数据是否足够
                if available_days < MIN_DATA_DAYS:
                    # 只在第一次输出详细信息
                    if skipped == 0:
                        logger.warning(
                            f"板块 {sector.name} 日期 {calc_date} 数据天数不足，跳过。"
                            f"可用天数: {available_days}，要求: {MIN_DATA_DAYS}"
                        )
                    skipped += 1
                    continue

                # 计算强度
                if available_days < FULL_DATA_DAYS:
                    result = self.calculator.calculate_with_insufficient_data(
                        current_price, ma_values, available_days
                    )
                else:
                    result = self.calculator.calculate_composite_strength(
                        current_price, ma_values
                    )

                # 保存到数据库
                if result.get('error'):
                    errored += 1
                    logger.debug(
                        f"板块 {sector.name} 日期 {calc_date} 计算失败: {result.get('error')}"
                    )
                    continue

                if existing:
                    # 更新现有记录
                    await self._update_strength_score(existing, result)
                    updated += 1
                    has_change = True
                else:
                    # 创建新记录
                    await self._create_strength_score(sector, calc_date, result)
                    created += 1
                    has_change = True

                # 每处理 BATCH_FLUSH_SIZE 个日期或有数据变更时，阶段性保存到数据库
                if has_change and (date_idx + 1) % BATCH_FLUSH_SIZE == 0:
                    try:
                        await self.session.flush()
                        logger.debug(
                            f"板块 {sector.name} 阶段保存完成: {date_idx + 1}/{total_dates} "
                            f"已保存 {created + updated} 条记录"
                        )
                    except Exception as flush_error:
                        logger.error(
                            f"板块 {sector.name} 阶段保存失败 (第 {date_idx + 1} 个日期): {flush_error}"
                        )
                        # flush 失败不影响继续计算，但最终 commit 可能会失败

            logger.debug(
                f"板块 {sector.name} 强度计算完成: "
                f"总日期={total_dates}, 新增={created}, 更新={updated}, "
                f"跳过={skipped}, 错误={errored}"
            )

            # 最终 flush：确保所有剩余数据都写入数据库
            if created + updated > 0:
                try:
                    await self.session.flush()
                    logger.debug(
                        f"板块 {sector.name} 最终保存完成: "
                        f"新增={created}, 更新={updated}"
                    )
                except Exception as flush_error:
                    logger.error(
                        f"板块 {sector.name} 最终保存失败: {flush_error}"
                    )
                    raise  # 最终保存失败应该抛出异常

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

    async def _get_dates_to_calculate(
        self,
        sector_id: int,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """
        获取需要计算的日期列表

        Args:
            sector_id: 板块ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            日期列表
        """
        try:
            # 获取该日期范围内有数据的所有日期
            stmt = select(DailyMarketData.date).where(
                and_(
                    DailyMarketData.entity_type == "sector",
                    DailyMarketData.entity_id == sector_id,
                    DailyMarketData.date >= start_date,
                    DailyMarketData.date <= end_date,
                    DailyMarketData.close.isnot(None)
                )
            ).order_by(DailyMarketData.date).distinct()

            result = await self.session.execute(stmt)
            # 获取所有行
            rows = result.all()

            # 处理结果：检查是否是 SQLAlchemy Row 对象
            # 如果是 Row 对象（有 _fields 属性），提取第一列
            # 如果是直接的值列表（mock 情况），直接转换为列表
            if rows and hasattr(rows[0], '_fields'):
                # SQLAlchemy Row 对象
                dates = [row[0] for row in rows]
            else:
                # 直接是值列表（测试 mock 的情况）
                dates = list(rows) if rows else []

            return dates

        except Exception as e:
            logger.error(f"获取日期列表失败: {e}")
            return []

    async def _get_existing_strength_score(
        self,
        sector_id: int,
        calc_date: date
    ) -> Optional[StrengthScore]:
        """
        获取已有的强度记录

        Args:
            sector_id: 板块ID
            calc_date: 计算日期

        Returns:
            已有的强度记录或None
        """
        try:
            stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == "sector",
                    StrengthScore.entity_id == sector_id,
                    StrengthScore.date == calc_date,
                    StrengthScore.period == "all"
                )
            )

            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"查询已有强度记录失败: {e}")
            return None

    async def _create_strength_score(
        self,
        sector: Sector,
        calc_date: date,
        result: Dict
    ):
        """
        创建新的强度记录

        Args:
            sector: 板块对象
            calc_date: 计算日期
            result: 计算结果
        """
        try:
            ma_values = result.get('ma_values', {})
            price_above_flags = result.get('price_above_flags', {})

            new_score = StrengthScore(
                entity_type="sector",
                entity_id=sector.id,
                symbol=sector.code,
                date=calc_date,
                period="all",
                score=result.get('composite_score', 0),
                price_position_score=result.get('price_position_score'),
                ma_alignment_score=result.get('ma_alignment_score'),
                ma_alignment_state=result.get('ma_alignment_state'),
                short_term_score=result.get('short_term_score'),
                medium_term_score=result.get('medium_term_score'),
                long_term_score=result.get('long_term_score'),
                strength_grade=result.get('strength_grade'),
                current_price=result.get('current_price'),
                # 均线值
                ma5=ma_values.get(5),
                ma10=ma_values.get(10),
                ma20=ma_values.get(20),
                ma30=ma_values.get(30),
                ma60=ma_values.get(60),
                ma90=ma_values.get(90),
                ma120=ma_values.get(120),
                ma240=ma_values.get(240),
                # 价格是否高于均线
                price_above_ma5=price_above_flags.get('above_ma5'),
                price_above_ma10=price_above_flags.get('above_ma10'),
                price_above_ma20=price_above_flags.get('above_ma20'),
                price_above_ma30=price_above_flags.get('above_ma30'),
                price_above_ma60=price_above_flags.get('above_ma60'),
                price_above_ma90=price_above_flags.get('above_ma90'),
                price_above_ma120=price_above_flags.get('above_ma120'),
                price_above_ma240=price_above_flags.get('above_ma240'),
            )

            self.session.add(new_score)

        except Exception as e:
            logger.error(f"创建强度记录失败: {e}")
            raise

    async def _update_strength_score(
        self,
        existing: StrengthScore,
        result: Dict
    ):
        """
        更新已有强度记录

        Args:
            existing: 已有强度记录
            result: 计算结果
        """
        try:
            ma_values = result.get('ma_values', {})
            price_above_flags = result.get('price_above_flags', {})

            # 更新基础字段
            existing.score = result.get('composite_score', 0)
            existing.price_position_score = result.get('price_position_score')
            existing.ma_alignment_score = result.get('ma_alignment_score')
            existing.ma_alignment_state = result.get('ma_alignment_state')
            existing.short_term_score = result.get('short_term_score')
            existing.medium_term_score = result.get('medium_term_score')
            existing.long_term_score = result.get('long_term_score')
            existing.strength_grade = result.get('strength_grade')
            existing.current_price = result.get('current_price')

            # 更新均线值
            existing.ma5 = ma_values.get(5)
            existing.ma10 = ma_values.get(10)
            existing.ma20 = ma_values.get(20)
            existing.ma30 = ma_values.get(30)
            existing.ma60 = ma_values.get(60)
            existing.ma90 = ma_values.get(90)
            existing.ma120 = ma_values.get(120)
            existing.ma240 = ma_values.get(240)

            # 更新价格是否高于均线
            existing.price_above_ma5 = price_above_flags.get('above_ma5')
            existing.price_above_ma10 = price_above_flags.get('above_ma10')
            existing.price_above_ma20 = price_above_flags.get('above_ma20')
            existing.price_above_ma30 = price_above_flags.get('above_ma30')
            existing.price_above_ma60 = price_above_flags.get('above_ma60')
            existing.price_above_ma90 = price_above_flags.get('above_ma90')
            existing.price_above_ma120 = price_above_flags.get('above_ma120')
            existing.price_above_ma240 = price_above_flags.get('above_ma240')

        except Exception as e:
            logger.error(f"更新强度记录失败: {e}")
            raise

    async def _get_sector_date_range(self, sector_id: int) -> Optional[tuple]:
        """
        获取板块的日期范围

        Args:
            sector_id: 板块ID

        Returns:
            (start_date, end_date) 或 None
        """
        try:
            stmt = select(
                func.min(DailyMarketData.date),
                func.max(DailyMarketData.date)
            ).where(
                and_(
                    DailyMarketData.entity_type == "sector",
                    DailyMarketData.entity_id == sector_id,
                    DailyMarketData.close.isnot(None)
                )
            )

            result = await self.session.execute(stmt)
            row = result.one()

            if row[0] is None or row[1] is None:
                return None

            return (row[0], row[1])

        except Exception as e:
            logger.error(f"获取板块日期范围失败: {e}")
            return None
