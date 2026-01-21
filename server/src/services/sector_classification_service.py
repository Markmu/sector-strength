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
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.daily_market_data import DailyMarketData
from src.models.moving_average_data import MovingAverageData

logger = logging.getLogger(__name__)


# ===============================
# 自定义异常类
# ===============================

class ClassificationError(Exception):
    """分类计算基础异常"""
    pass


class MissingMADataError(ClassificationError):
    """均线数据缺失异常

    当所需的均线数据缺失时抛出。

    Attributes:
        message: 错误消息
        sector_id: 板块ID
        date: 查询日期
    """

    def __init__(self, message: str, sector_id: int = None, date: date = None):
        self.sector_id = sector_id
        self.date = date
        super().__init__(message)


class InvalidPriceError(ClassificationError):
    """价格数据无效异常

    当价格数据无效或缺失时抛出。

    Attributes:
        message: 错误消息
        sector_id: 板块ID
    """

    def __init__(self, message: str, sector_id: int = None):
        self.sector_id = sector_id
        super().__init__(message)


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
                    f"板块 {sector_id} 在 {target_date} 缺少 {period} 日均线数据",
                    sector_id=sector_id,
                    date=target_date
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
                f"板块 {sector_id} 在 {target_date} 附近的价格数据不足（需要至少6天数据）",
                sector_id=sector_id
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
        """
        # 获取板块信息
        stmt = select(Sector).where(Sector.id == sector_id)
        result = await self.session.execute(stmt)
        sector = result.scalar_one_or_none()

        if sector is None:
            raise InvalidPriceError(f"板块 {sector_id} 不存在", sector_id=sector_id)

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
                logger.warning(f"板块 {sector.name} 分类计算失败: {e}")
                errors.append({
                    'sector_id': sector.id,
                    'sector_name': sector.name,
                    'error': str(e)
                })
            except Exception as e:
                logger.error(f"处理板块 {sector.name} 时出错: {e}")
                errors.append({
                    'sector_id': sector.id,
                    'sector_name': sector.name,
                    'error': str(e)
                })

        if errors:
            logger.warning(f"批量计算完成，{len(errors)} 个板块失败")

        return results
