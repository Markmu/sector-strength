"""
缠论板块分类算法服务

实现缠论理论中的板块强弱分类算法，根据均线数据计算板块分类级别和状态。
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import date, timedelta
from dataclasses import dataclass
from functools import wraps
import time
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.daily_market_data import DailyMarketData
from src.models.moving_average_data import MovingAverageData
from src.models.sector_classification import SectorClassification

# 导入自定义异常类
from src.exceptions.classification import (
    ClassificationError,
    MissingMADataError,
    ClassificationFailedError,
    InvalidPriceError
)

logger = logging.getLogger(__name__)


# ===============================
# 数据类定义
# ===============================

@dataclass
class ClassificationResult:
    """分类计算结果

    Attributes:
        sector_id: 板块ID
        sector_name: 板块名称
        symbol: 板块代码
        classification_level: 分类级别 (1-9)
        state: 状态 ('反弹' or '调整')
        current_price: 当前价格
        ma_values: 均线值字典
        price_5_days_ago: 5天前价格
        classification_date: 分类日期
    """
    sector_id: int
    sector_name: str
    symbol: str
    classification_level: int
    state: str
    current_price: float
    ma_values: Dict[str, float]
    price_5_days_ago: float
    classification_date: date


# ===============================
# 性能计时装饰器
# ===============================

def timing_decorator(func: Callable) -> Callable:
    """性能计时装饰器

    用于测量函数执行时间。

    Args:
        func: 被装饰的函数

    Returns:
        包装后的函数
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_ms = (end_time - start_time) * 1000

        # 将执行时间附加到结果中（如果是字典）
        if isinstance(result, dict):
            result['_elapsed_ms'] = elapsed_ms

        logger.debug(f"{func.__name__} 执行耗时: {elapsed_ms:.2f}ms")
        return result

    return wrapper


# ===============================
# 核心分类算法函数
# ===============================

def calculate_classification_level(current_price: float, ma_values: Dict[str, float]) -> int:
    """根据当前价格相对于8条均线的位置计算分类级别

    缠论分类规则：
    - 第 9 类: 当前价格 > 所有8条均线
    - 第 8 类: 当前价格 <= ma_5 但 > ma_240（攻克240日线）
    - 第 7 类: 当前价格 <= ma_240 但 > ma_120（攻克120日线）
    - 第 6 类: 当前价格 <= ma_120 但 > ma_90（攻克90日线）
    - 第 5 类: 当前价格 <= ma_90 但 > ma_60（攻克60日线）
    - 第 4 类: 当前价格 <= ma_60 但 > ma_30（攻克30日线）
    - 第 3 类: 当前价格 <= ma_30 但 > ma_20（攻克20日线）
    - 第 2 类: 当前价格 <= ma_20 但 > ma_10（攻克10日线）
    - 第 1 类: 当前价格 <= 所有8条均线

    Args:
        current_price: 当前价格
        ma_values: 包含8条均线的字典，键为 'ma_5', 'ma_10', ..., 'ma_240'

    Returns:
        分类级别 (1-9)

    Raises:
        MissingMADataError: 当缺少必需的均线数据时
    """
    # 验证输入数据
    required_ma_keys = ['ma_5', 'ma_10', 'ma_20', 'ma_30', 'ma_60', 'ma_90', 'ma_120', 'ma_240']
    for key in required_ma_keys:
        if key not in ma_values or ma_values[key] is None:
            raise MissingMADataError(f"缺少必需的均线数据: {key}")

    ma_5 = ma_values['ma_5']
    ma_10 = ma_values['ma_10']
    ma_20 = ma_values['ma_20']
    ma_30 = ma_values['ma_30']
    ma_60 = ma_values['ma_60']
    ma_90 = ma_values['ma_90']
    ma_120 = ma_values['ma_120']
    ma_240 = ma_values['ma_240']

    # 按照从长到短的顺序判断（避免边界条件问题）
    if current_price > ma_5 and current_price > ma_10 and current_price > ma_20 and \
       current_price > ma_30 and current_price > ma_60 and current_price > ma_90 and \
       current_price > ma_120 and current_price > ma_240:
        return 9  # 价格在所有均线上方
    elif current_price <= ma_5 and current_price > ma_240:
        return 8  # 攻克240日线
    elif current_price <= ma_240 and current_price > ma_120:
        return 7  # 攻克120日线
    elif current_price <= ma_120 and current_price > ma_90:
        return 6  # 攻克90日线
    elif current_price <= ma_90 and current_price > ma_60:
        return 5  # 攻克60日线
    elif current_price <= ma_60 and current_price > ma_30:
        return 4  # 攻克30日线
    elif current_price <= ma_30 and current_price > ma_20:
        return 3  # 攻克20日线
    elif current_price <= ma_20 and current_price > ma_10:
        return 2  # 攻克10日线
    else:
        return 1  # 价格在所有均线下方


def calculate_state(current_price: float, price_5_days_ago: float) -> str:
    """根据当前价格与5天前价格判断反弹/调整状态

    Args:
        current_price: 当前价格
        price_5_days_ago: 5天前价格

    Returns:
        '反弹' 或 '调整'
    """
    if current_price > price_5_days_ago:
        return '反弹'
    else:
        return '调整'


# ===============================
# 服务类
# ===============================

class SectorClassificationService:
    """板块分类服务

    提供板块强弱分类计算功能，基于缠论均线理论。
    """

    # 所需的均线周期
    MA_PERIODS = [5, 10, 20, 30, 60, 90, 120, 240]

    def __init__(self, session: AsyncSession):
        """初始化板块分类服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self._progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """设置进度回调函数

        Args:
            callback: 回调函数 (current: int, total: int, message: str) -> None
        """
        self._progress_callback = callback

    async def _report_progress(self, current: int, total: int, message: str):
        """报告进度"""
        if self._progress_callback:
            await self._progress_callback(current, total, message)

    async def get_ma_data(
        self,
        sector_id: int,
        target_date: date
    ) -> Dict[str, float]:
        """获取指定板块在指定日期的均线数据

        Args:
            sector_id: 板块ID
            target_date: 目标日期

        Returns:
            包含8条均线值的字典

        Raises:
            MissingMADataError: 当均线数据缺失时
        """
        ma_values = {}

        for period in self.MA_PERIODS:
            period_str = f"{period}d"

            # 查询该周期的最新均线数据（<= target_date）
            stmt = select(MovingAverageData).where(
                and_(
                    MovingAverageData.entity_type == "sector",
                    MovingAverageData.entity_id == sector_id,
                    MovingAverageData.period == period_str,
                    MovingAverageData.date <= target_date
                )
            ).order_by(MovingAverageData.date.desc()).limit(1)

            result = await self.session.execute(stmt)
            ma_data = result.scalar_one_or_none()

            if ma_data is None or ma_data.ma_value is None:
                raise MissingMADataError(
                    sector_id=sector_id,
                    missing_fields=[f"ma_{period}"]
                )

            ma_values[f'ma_{period}'] = float(ma_data.ma_value)

        return ma_values

    async def get_price_data(
        self,
        sector_id: int,
        target_date: date
    ) -> tuple[float, float]:
        """获取当前价格和5天前价格

        Args:
            sector_id: 板块ID
            target_date: 目标日期

        Returns:
            (当前价格, 5天前价格) 元组

        Raises:
            InvalidPriceError: 当价格数据缺失或无效时
        """
        # 获取最近6天的数据（用于确定当前价格和5天前价格）
        stmt = select(DailyMarketData).where(
            and_(
                DailyMarketData.entity_type == "sector",
                DailyMarketData.entity_id == sector_id,
                DailyMarketData.date <= target_date,
                DailyMarketData.close.isnot(None)
            )
        ).order_by(DailyMarketData.date.desc()).limit(6)

        result = await self.session.execute(stmt)
        price_data_list = result.scalars().all()

        if len(price_data_list) < 6:
            raise InvalidPriceError(
                sector_id=sector_id,
                reason=f"在 {target_date} 附近的价格数据不足（需要至少6天数据，当前{len(price_data_list)}天）"
            )

        # 最新一天的数据是当前价格
        current_price = float(price_data_list[0].close)

        # 第6天的数据是5天前的价格
        price_5_days_ago = float(price_data_list[5].close)

        return current_price, price_5_days_ago

    async def calculate_classification(
        self,
        sector_id: int,
        classification_date: date
    ) -> ClassificationResult:
        """计算单个板块的分类

        Args:
            sector_id: 板块ID
            classification_date: 分类日期

        Returns:
            分类结果对象

        Raises:
            MissingMADataError: 当均线数据缺失时
            InvalidPriceError: 当价格数据无效时
            ClassificationFailedError: 当分类计算失败时
        """
        # 获取板块信息
        stmt = select(Sector).where(Sector.id == sector_id)
        result = await self.session.execute(stmt)
        sector = result.scalar_one_or_none()

        if sector is None:
            raise InvalidPriceError(
                sector_id=sector_id,
                reason="板块不存在"
            )

        try:
            # 获取均线数据
            ma_values = await self.get_ma_data(sector_id, classification_date)

            # 获取价格数据
            current_price, price_5_days_ago = await self.get_price_data(sector_id, classification_date)

            # 计算分类级别
            classification_level = calculate_classification_level(current_price, ma_values)

            # 计算状态
            state = calculate_state(current_price, price_5_days_ago)

            return ClassificationResult(
                sector_id=sector_id,
                sector_name=sector.name,
                symbol=sector.code,
                classification_level=classification_level,
                state=state,
                current_price=current_price,
                ma_values=ma_values,
                price_5_days_ago=price_5_days_ago,
                classification_date=classification_date
            )
        except (MissingMADataError, InvalidPriceError):
            # 重新抛出已知异常，添加板块名称
            raise
        except Exception as e:
            # 捕获其他异常并转换为 ClassificationFailedError
            raise ClassificationFailedError(
                sector_id=sector_id,
                sector_name=sector.name,
                reason=str(e)
            ) from e

    @timing_decorator
    async def batch_calculate_all_sectors(
        self,
        classification_date: Optional[date] = None
    ) -> List[ClassificationResult]:
        """批量计算所有板块的分类

        Args:
            classification_date: 分类日期，None 表示使用最新日期

        Returns:
            分类结果列表

        Raises:
            InvalidPriceError: 当价格数据无效时
        """
        if classification_date is None:
            classification_date = date.today()

        # 获取所有板块
        stmt = select(Sector).order_by(Sector.id)
        result = await self.session.execute(stmt)
        sectors = result.scalars().all()

        if not sectors:
            raise InvalidPriceError("没有找到任何板块")

        total = len(sectors)
        results = []
        errors = []

        for idx, sector in enumerate(sectors):
            try:
                await self._report_progress(
                    idx + 1,
                    total,
                    f"计算板块分类: {sector.name} ({sector.code})"
                )

                classification_result = await self.calculate_classification(
                    sector.id,
                    classification_date
                )
                results.append(classification_result)

            except (MissingMADataError, InvalidPriceError) as e:
                # 已知异常，数据不足是预期情况
                logger.info(f"板块 {sector.name} 数据不足，跳过: {e}")
                errors.append({
                    'sector_id': sector.id,
                    'sector_name': sector.name,
                    'error': str(e)
                })
            except Exception as e:
                # 非预期异常使用 error 级别
                logger.error(f"处理板块 {sector.name} 时出错: {e}", exc_info=True)
                errors.append({
                    'sector_id': sector.id,
                    'sector_name': sector.name,
                    'error': str(e)
                })

        if errors:
            logger.info(f"批量计算完成，{len(errors)} 个板块失败")

        return results

    # ===============================
    # 数据持久化方法
    # ===============================

    def _update_ma_fields(self, target: Any, ma_values: Dict[str, float], change_percent: Optional[float]) -> None:
        """更新均线字段到目标对象

        Args:
            target: 目标对象（SectorClassification 实例）
            ma_values: 均线值字典
            change_percent: 涨跌幅
        """
        target.ma_5 = ma_values.get('ma_5')
        target.ma_10 = ma_values.get('ma_10')
        target.ma_20 = ma_values.get('ma_20')
        target.ma_30 = ma_values.get('ma_30')
        target.ma_60 = ma_values.get('ma_60')
        target.ma_90 = ma_values.get('ma_90')
        target.ma_120 = ma_values.get('ma_120')
        target.ma_240 = ma_values.get('ma_240')

    async def _save_classification_result(
        self,
        result: ClassificationResult,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """保存单个分类结果到数据库

        Args:
            result: 分类计算结果
            overwrite: 是否覆盖已有数据

        Returns:
            操作结果字典 {"action": "created" | "skipped" | "updated", "record": SectorClassification}
        """
        # 检查是否已存在
        stmt = select(SectorClassification).where(
            and_(
                SectorClassification.sector_id == result.sector_id,
                SectorClassification.classification_date == result.classification_date
            )
        )
        db_result = await self.session.execute(stmt)
        existing = db_result.scalar_one_or_none()

        if existing and not overwrite:
            return {"action": "skipped", "record": existing}

        # 计算涨跌幅
        change_percent = None
        if result.price_5_days_ago and result.price_5_days_ago > 0:
            change_percent = ((result.current_price - result.price_5_days_ago) / result.price_5_days_ago) * 100

        if existing:
            # 更新现有记录
            existing.symbol = result.symbol
            existing.classification_level = result.classification_level
            existing.state = result.state
            existing.current_price = result.current_price
            existing.change_percent = change_percent
            existing.price_5_days_ago = result.price_5_days_ago
            self._update_ma_fields(existing, result.ma_values, change_percent)
            return {"action": "updated", "record": existing}
        else:
            # 创建新记录
            new_classification = SectorClassification(
                sector_id=result.sector_id,
                symbol=result.symbol,
                classification_date=result.classification_date,
                classification_level=result.classification_level,
                state=result.state,
                current_price=result.current_price,
                change_percent=change_percent,
                price_5_days_ago=result.price_5_days_ago
            )
            self._update_ma_fields(new_classification, result.ma_values, change_percent)
            self.session.add(new_classification)
            return {"action": "created", "record": new_classification}

    async def initialize_classifications(
        self,
        start_date: Optional[date] = None,
        overwrite: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """初始化所有板块的分类数据

        Args:
            start_date: 起始日期，None 表示从每个板块最早日期开始
            overwrite: 是否覆盖已有数据
            progress_callback: 进度回调函数

        Returns:
            初始化结果字典
        """
        if progress_callback:
            self.set_progress_callback(progress_callback)

        logger.info(
            f"开始初始化板块分类数据: start_date={start_date}, overwrite={overwrite}"
        )

        # 获取所有板块
        stmt = select(Sector).order_by(Sector.id)
        result = await self.session.execute(stmt)
        sectors = result.scalars().all()

        if not sectors:
            return {"success": False, "error": "未找到板块数据"}

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
                    f"初始化板块分类: {sector.name} ({sector.code})"
                )

                # 获取该板块的日期范围
                if start_date:
                    # 使用指定起始日期
                    date_stmt = select(func.min(DailyMarketData.date)).where(
                        and_(
                            DailyMarketData.entity_type == "sector",
                            DailyMarketData.entity_id == sector.id,
                            DailyMarketData.date >= start_date
                        )
                    )
                else:
                    # 从最早日期开始
                    date_stmt = select(func.min(DailyMarketData.date)).where(
                        and_(
                            DailyMarketData.entity_type == "sector",
                            DailyMarketData.entity_id == sector.id
                        )
                    )

                date_result = await self.session.execute(date_stmt)
                min_date = date_result.scalar()

                if min_date is None:
                    logger.warning(f"板块 {sector.name} 无市场数据，跳过")
                    skipped_count += 1
                    continue

                # 获取最大日期
                max_date_stmt = select(func.max(DailyMarketData.date)).where(
                    and_(
                        DailyMarketData.entity_type == "sector",
                        DailyMarketData.entity_id == sector.id
                    )
                )
                max_date_result = await self.session.execute(max_date_stmt)
                max_date = max_date_result.scalar()

                # 生成日期列表
                current = min_date
                date_count = 0

                # 批量预加载已存在的分类数据（性能优化）
                if not overwrite:
                    existing_stmt = select(SectorClassification).where(
                        and_(
                            SectorClassification.sector_id == sector.id,
                            SectorClassification.classification_date >= min_date,
                            SectorClassification.classification_date <= max_date
                        )
                    )
                    existing_result = await self.session.execute(existing_stmt)
                    existing_records = existing_result.scalars().all()
                    existing_dates = {record.classification_date for record in existing_records}
                else:
                    existing_dates = set()

                while current <= max_date:
                    try:
                        # 检查数据是否已存在（使用预加载的数据）
                        if current in existing_dates and not overwrite:
                            date_count += 1
                            skipped_count += 1
                            current += timedelta(days=1)
                            continue

                        # 计算分类
                        classification_result = await self.calculate_classification(
                            sector.id, current
                        )
                        save_result = await self._save_classification_result(
                            classification_result, overwrite
                        )

                        if save_result["action"] == "created":
                            created_count += 1
                        elif save_result["action"] == "updated":
                            updated_count += 1
                        else:
                            skipped_count += 1

                        date_count += 1

                        # 每处理 10 个日期 flush 一次
                        if date_count % 10 == 0:
                            await self.session.flush()

                    except (MissingMADataError, InvalidPriceError) as e:
                        # 数据不足是预期情况，使用 debug 级别
                        logger.debug(f"日期 {current} 数据不足，跳过: {e}")
                    except Exception as e:
                        # 非预期异常使用 warning 级别
                        logger.warning(f"处理日期 {current} 失败: {e}", exc_info=True)

                    current += timedelta(days=1)

                # 完成一个板块后 flush
                await self.session.flush()

            except Exception as e:
                error_count += 1
                logger.error(f"处理板块 {sector.name} 时出错: {e}")

        return {
            "success": True,
            "total_sectors": total,
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": error_count
        }

    async def update_daily_classification(
        self,
        target_date: Optional[date] = None,
        overwrite: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """每日增量更新板块分类

        Args:
            target_date: 目标日期，None 表示使用今天
            overwrite: 是否覆盖已有数据
            progress_callback: 进度回调函数

        Returns:
            更新结果字典
        """
        if target_date is None:
            target_date = date.today()

        if progress_callback:
            self.set_progress_callback(progress_callback)

        logger.info(f"开始每日板块分类更新: target_date={target_date}, overwrite={overwrite}")

        # 数据新鲜度检查：验证是否有当日市场数据
        data_check_stmt = select(func.count(DailyMarketData.id)).where(
            and_(
                DailyMarketData.entity_type == "sector",
                DailyMarketData.date == target_date
            )
        )
        data_check_result = await self.session.execute(data_check_stmt)
        data_count = data_check_result.scalar()

        if data_count == 0:
            return {
                "success": False,
                "error": f"市场数据未就绪: {target_date} 无板块市场数据"
            }

        # 批量计算当天所有板块分类
        results = await self.batch_calculate_all_sectors(target_date)

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for result in results:
            save_result = await self._save_classification_result(result, overwrite)
            if save_result["action"] == "created":
                created_count += 1
            elif save_result["action"] == "updated":
                updated_count += 1
            else:
                skipped_count += 1

        # 完成后清除缓存
        try:
            from src.services.classification_cache import classification_cache
            cache_cleared = classification_cache.clear_pattern("classification:")
            logger.info(f"已清除 {cache_cleared} 条分类缓存")
        except Exception as e:
            logger.warning(f"清除缓存失败: {e}")

        return {
            "success": True,
            "target_date": target_date.isoformat(),
            "total_sectors": len(results),
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count
        }

    async def get_classification_status(self) -> Dict[str, Any]:
        """获取分类数据状态统计

        Returns:
            状态统计字典
        """
        # 获取最新日期
        latest_date_stmt = select(func.max(SectorClassification.classification_date))
        latest_date_result = await self.session.execute(latest_date_stmt)
        latest_date = latest_date_result.scalar()

        # 获取板块总数
        total_sectors_stmt = select(func.count(func.distinct(SectorClassification.sector_id)))
        total_sectors_result = await self.session.execute(total_sectors_stmt)
        total_sectors = total_sectors_result.scalar() or 0

        # 按级别统计
        by_level_stmt = select(
            SectorClassification.classification_level,
            func.count(SectorClassification.id)
        ).where(
            SectorClassification.classification_date == latest_date
        ).group_by(SectorClassification.classification_level)

        by_level_result = await self.session.execute(by_level_stmt)
        by_level = {level: count for level, count in by_level_result.all()}

        # 按状态统计
        by_state_stmt = select(
            SectorClassification.state,
            func.count(SectorClassification.id)
        ).where(
            SectorClassification.classification_date == latest_date
        ).group_by(SectorClassification.state)

        by_state_result = await self.session.execute(by_state_stmt)
        by_state = {state: count for state, count in by_state_result.all()}

        return {
            "latest_date": latest_date.isoformat() if latest_date else None,
            "total_sectors": total_sectors,
            "by_level": by_level,
            "by_state": by_state
        }
