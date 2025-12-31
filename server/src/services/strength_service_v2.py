"""
均线系统强度计算服务 (V2)

提供个股和板块的强度计算服务，使用新的均线系统算法。
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Callable

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.strength_score import StrengthScore
from src.models.stock import Stock
from src.models.sector import Sector
from src.services.calculation.ma_system.ma_data_loader import MADataLoader
from src.services.calculation.ma_system.strength_calculator_v2 import StrengthCalculatorV2
from src.config.ma_system import MA_PERIODS, get_available_periods, MIN_DATA_DAYS, FULL_DATA_DAYS

logger = logging.getLogger(__name__)


class StrengthServiceV2:
    """
    均线系统强度计算服务 (V2)

    使用基于均线系统的两维度算法计算强度。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化强度计算服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.calculator = StrengthCalculatorV2()
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

    async def calculate_stock_strength(
        self,
        stock_id: int,
        calc_date: Optional[date] = None
    ) -> Dict:
        """
        计算个股强度

        Args:
            stock_id: 股票ID
            calc_date: 计算日期，None 表示使用最新日期

        Returns:
            计算结果字典
        """
        if calc_date is None:
            calc_date = date.today()

        try:
            # 创建数据加载器
            loader = MADataLoader(self.session)

            # 加载数据
            data = await loader.load_data_for_calculation("stock", stock_id, calc_date)

            if not data["has_data"]:
                return {
                    "success": False,
                    "error": "数据不足或无效",
                    "stock_id": stock_id
                }

            current_price = data["current_price"]
            ma_values = data["ma_values"]
            available_days = data["available_days"]

            # 渐近式计算：检查数据是否足够
            if available_days < MIN_DATA_DAYS:
                return {
                    "success": False,
                    "error": f"数据不足（{available_days}天），至少需要{MIN_DATA_DAYS}天",
                    "stock_id": stock_id
                }

            # 计算强度
            result = self.calculator.calculate_composite_strength(current_price, ma_values)

            # 如果数据不足，使用渐近式计算
            if available_days < FULL_DATA_DAYS:
                result = self.calculator.calculate_with_insufficient_data(
                    current_price, ma_values, available_days
                )

            # 保存到数据库
            await self._save_strength_score(
                entity_type="stock",
                entity_id=stock_id,
                calc_date=calc_date,
                result=result
            )

            # 自动计算并更新变化率
            await self.calculate_and_update_change_rate("stock", stock_id, calc_date)

            return {
                "success": True,
                "stock_id": stock_id,
                "calc_date": calc_date,
                "result": result
            }

        except Exception as e:
            logger.error(f"计算个股强度失败 (stock_id={stock_id}): {e}")
            return {
                "success": False,
                "error": str(e),
                "stock_id": stock_id
            }

    async def calculate_sector_strength(
        self,
        sector_id: int,
        calc_date: Optional[date] = None
    ) -> Dict:
        """
        计算板块强度

        Args:
            sector_id: 板块ID
            calc_date: 计算日期，None 表示使用最新日期

        Returns:
            计算结果字典
        """
        if calc_date is None:
            calc_date = date.today()

        logger.info(f"开始计算板块强度: sector_id={sector_id}, date={calc_date}")

        try:
            # 创建数据加载器
            loader = MADataLoader(self.session)

            # 加载数据
            logger.debug(f"正在加载板块数据: sector_id={sector_id}")
            data = await loader.load_data_for_calculation("sector", sector_id, calc_date)

            if not data["has_data"]:
                logger.warning(f"板块数据不足或无效: sector_id={sector_id}, date={calc_date}")
                return {
                    "success": False,
                    "error": "数据不足或无效",
                    "sector_id": sector_id
                }

            current_price = data["current_price"]
            ma_values = data["ma_values"]
            available_days = data["available_days"]

            # 渐近式计算：检查数据是否足够
            if available_days < MIN_DATA_DAYS:
                logger.warning(
                    f"板块数据天数不足: sector_id={sector_id}, "
                    f"available={available_days}天, required={MIN_DATA_DAYS}天"
                )
                return {
                    "success": False,
                    "error": f"数据不足（{available_days}天），至少需要{MIN_DATA_DAYS}天",
                    "sector_id": sector_id
                }

            # 计算强度
            logger.debug(f"正在计算板块综合强度: sector_id={sector_id}, available_days={available_days}")
            result = self.calculator.calculate_composite_strength(current_price, ma_values)

            # 如果数据不足，使用渐近式计算
            if available_days < FULL_DATA_DAYS:
                logger.debug(f"使用渐近式计算: sector_id={sector_id}, available_days={available_days}")
                result = self.calculator.calculate_with_insufficient_data(
                    current_price, ma_values, available_days
                )

            # 保存到数据库
            logger.debug(f"正在保存板块强度数据: sector_id={sector_id}, score={result.get('composite_score', 0):.2f}")
            await self._save_strength_score(
                entity_type="sector",
                entity_id=sector_id,
                calc_date=calc_date,
                result=result
            )

            # 自动计算并更新变化率
            logger.debug(f"正在计算板块变化率: sector_id={sector_id}")
            await self.calculate_and_update_change_rate("sector", sector_id, calc_date)

            logger.info(
                f"板块强度计算完成: sector_id={sector_id}, "
                f"score={result.get('composite_score', 0):.2f}, "
                f"grade={result.get('strength_grade', 'N/A')}"
            )

            return {
                "success": True,
                "sector_id": sector_id,
                "calc_date": calc_date,
                "result": result
            }

        except Exception as e:
            logger.error(f"计算板块强度失败 (sector_id={sector_id}): {e}")
            return {
                "success": False,
                "error": str(e),
                "sector_id": sector_id
            }

    async def batch_calculate(
        self,
        entity_type: str,
        entity_ids: List[int],
        calc_date: Optional[date] = None
    ) -> Dict:
        """
        批量计算强度

        Args:
            entity_type: 实体类型 ('stock' 或 'sector')
            entity_ids: 实体ID列表
            calc_date: 计算日期

        Returns:
            批量计算结果
        """
        if calc_date is None:
            calc_date = date.today()

        total = len(entity_ids)
        success_count = 0
        error_count = 0
        results = []

        for idx, entity_id in enumerate(entity_ids):
            try:
                await self._report_progress(
                    idx + 1,
                    total,
                    f"计算 {entity_type} ID: {entity_id}"
                )

                if entity_type == "stock":
                    result = await self.calculate_stock_strength(entity_id, calc_date)
                else:
                    result = await self.calculate_sector_strength(entity_id, calc_date)

                results.append(result)

                if result.get("success"):
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                logger.error(f"批量计算失败 (entity_type={entity_type}, entity_id={entity_id}): {e}")
                error_count += 1

        return {
            "success": True,
            "total": total,
            "success_count": success_count,
            "error_count": error_count,
            "results": results
        }

    async def _save_strength_score(
        self,
        entity_type: str,
        entity_id: int,
        calc_date: date,
        result: Dict
    ):
        """
        保存强度得分到数据库

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            calc_date: 计算日期
            result: 计算结果
        """
        try:
            # 获取 symbol
            symbol = await self._get_symbol(entity_type, entity_id)

            # 检查是否已存在记录
            stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == entity_type,
                    StrengthScore.entity_id == entity_id,
                    StrengthScore.date == calc_date,
                    StrengthScore.period == "all"
                )
            )

            existing_result = await self.session.execute(stmt)
            existing_score = existing_result.scalar_one_or_none()

            if existing_score:
                # 更新现有记录
                existing_score.score = result.get('composite_score', 0)
                existing_score.price_position_score = result.get('price_position_score')
                existing_score.ma_alignment_score = result.get('ma_alignment_score')
                existing_score.ma_alignment_state = result.get('ma_alignment_state')
                existing_score.short_term_score = result.get('short_term_score')
                existing_score.medium_term_score = result.get('medium_term_score')
                existing_score.long_term_score = result.get('long_term_score')
                existing_score.strength_grade = result.get('strength_grade')
                existing_score.current_price = result.get('current_price')

                # 更新均线值
                ma_values = result.get('ma_values', {})
                existing_score.ma5 = ma_values.get(5)
                existing_score.ma10 = ma_values.get(10)
                existing_score.ma20 = ma_values.get(20)
                existing_score.ma30 = ma_values.get(30)
                existing_score.ma60 = ma_values.get(60)
                existing_score.ma90 = ma_values.get(90)
                existing_score.ma120 = ma_values.get(120)
                existing_score.ma240 = ma_values.get(240)

                # 更新价格是否高于均线标记
                price_above_flags = result.get('price_above_flags', {})
                existing_score.price_above_ma5 = price_above_flags.get('above_ma5')
                existing_score.price_above_ma10 = price_above_flags.get('above_ma10')
                existing_score.price_above_ma20 = price_above_flags.get('above_ma20')
                existing_score.price_above_ma30 = price_above_flags.get('above_ma30')
                existing_score.price_above_ma60 = price_above_flags.get('above_ma60')
                existing_score.price_above_ma90 = price_above_flags.get('above_ma90')
                existing_score.price_above_ma120 = price_above_flags.get('above_ma120')
                existing_score.price_above_ma240 = price_above_flags.get('above_ma240')

            else:
                # 创建新记录
                new_score = StrengthScore(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    symbol=symbol,
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
                )

                # 设置均线值
                ma_values = result.get('ma_values', {})
                new_score.ma5 = ma_values.get(5)
                new_score.ma10 = ma_values.get(10)
                new_score.ma20 = ma_values.get(20)
                new_score.ma30 = ma_values.get(30)
                new_score.ma60 = ma_values.get(60)
                new_score.ma90 = ma_values.get(90)
                new_score.ma120 = ma_values.get(120)
                new_score.ma240 = ma_values.get(240)

                # 设置价格是否高于均线标记
                price_above_flags = result.get('price_above_flags', {})
                new_score.price_above_ma5 = price_above_flags.get('above_ma5')
                new_score.price_above_ma10 = price_above_flags.get('above_ma10')
                new_score.price_above_ma20 = price_above_flags.get('above_ma20')
                new_score.price_above_ma30 = price_above_flags.get('above_ma30')
                new_score.price_above_ma60 = price_above_flags.get('above_ma60')
                new_score.price_above_ma90 = price_above_flags.get('above_ma90')
                new_score.price_above_ma120 = price_above_flags.get('above_ma120')
                new_score.price_above_ma240 = price_above_flags.get('above_ma240')

                self.session.add(new_score)

            await self.session.commit()

        except Exception as e:
            logger.error(f"保存强度得分失败: {e}")
            await self.session.rollback()
            raise

    async def _get_symbol(self, entity_type: str, entity_id: int) -> str:
        """
        获取实体代码

        Args:
            entity_type: 实体类型
            entity_id: 实体ID

        Returns:
            代码
        """
        try:
            if entity_type == "stock":
                stmt = select(Stock).where(Stock.id == entity_id)
            else:
                stmt = select(Sector).where(Sector.id == entity_id)

            result = await self.session.execute(stmt)
            entity = result.scalar_one_or_none()

            if entity:
                return entity.symbol if entity_type == "stock" else entity.code

            return ""

        except Exception as e:
            logger.error(f"获取实体代码失败: {e}")
            return ""

    # ========== 变化率计算方法 ==========

    @staticmethod
    def calculate_change_rate_1d(
        current_score: Optional[float],
        previous_score: Optional[float]
    ) -> Optional[float]:
        """
        计算1日变化率

        Args:
            current_score: 当前得分
            previous_score: 前一日得分

        Returns:
            变化率百分比，None 表示无法计算
        """
        if current_score is None or previous_score is None:
            return None
        if previous_score == 0:
            return None
        return round(((current_score - previous_score) / previous_score) * 100, 2)

    @staticmethod
    def calculate_change_rate_5d(
        current_score: Optional[float],
        scores_5d: List[Optional[float]]
    ) -> Optional[float]:
        """
        计算5日变化率

        Args:
            current_score: 当前得分
            scores_5d: 最近5天得分列表（不含今天）

        Returns:
            变化率百分比，None 表示无法计算
        """
        if current_score is None:
            return None
        if not scores_5d:
            return None

        # 过滤空值
        valid_scores = [s for s in scores_5d if s is not None]
        if not valid_scores:
            return None

        avg_5d = sum(valid_scores) / len(valid_scores)
        if avg_5d == 0:
            return None

        return round(((current_score - avg_5d) / avg_5d) * 100, 2)

    async def calculate_and_update_change_rate(
        self,
        entity_type: str,
        entity_id: int,
        calc_date: Optional[date] = None
    ) -> Optional[Dict]:
        """
        计算并更新变化率

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            calc_date: 计算日期

        Returns:
            变化率数据字典
        """
        if calc_date is None:
            calc_date = date.today()

        try:
            # 获取当前得分
            current_stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == entity_type,
                    StrengthScore.entity_id == entity_id,
                    StrengthScore.date == calc_date,
                    StrengthScore.period == 'all'
                )
            )
            current_result = await self.session.execute(current_stmt)
            current_score = current_result.scalar_one_or_none()

            if not current_score:
                return None

            # 获取前一日得分
            prev_date = calc_date - timedelta(days=1)
            prev_stmt = select(StrengthScore).where(
                and_(
                    StrengthScore.entity_type == entity_type,
                    StrengthScore.entity_id == entity_id,
                    StrengthScore.date == prev_date,
                    StrengthScore.period == 'all'
                )
            )
            prev_result = await self.session.execute(prev_stmt)
            prev_score = prev_result.scalar_one_or_none()

            # 计算1日变化率
            change_rate_1d = self.calculate_change_rate_1d(
                current_score.score,
                prev_score.score if prev_score else None
            )

            # 获取前5天得分（不含今天）- 使用单个查询避免N+1问题
            start_date_5d = calc_date - timedelta(days=5)
            end_date_5d = calc_date - timedelta(days=1)

            stmt_5d = select(StrengthScore.score).where(
                and_(
                    StrengthScore.entity_type == entity_type,
                    StrengthScore.entity_id == entity_id,
                    StrengthScore.date >= start_date_5d,
                    StrengthScore.date <= end_date_5d,
                    StrengthScore.period == 'all'
                )
            ).order_by(StrengthScore.date.asc())

            result_5d = await self.session.execute(stmt_5d)
            scores_5d = [s for s in result_5d.scalars().all() if s is not None]

            # 计算5日变化率
            change_rate_5d = self.calculate_change_rate_5d(
                current_score.score,
                scores_5d
            )

            # 更新数据库
            current_score.change_rate_1d = change_rate_1d
            current_score.change_rate_5d = change_rate_5d

            await self.session.commit()

            return {
                'entity_type': entity_type,
                'entity_id': entity_id,
                'calc_date': calc_date,
                'current_score': current_score.score,
                'change_rate_1d': change_rate_1d,
                'change_rate_5d': change_rate_5d,
            }

        except Exception as e:
            logger.error(f"计算变化率失败 (entity_type={entity_type}, entity_id={entity_id}): {e}")
            await self.session.rollback()
            return None
