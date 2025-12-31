"""
均线数据加载器

从数据库加载均线数据和当前价格。
"""

import logging
from datetime import date
from typing import Dict, Optional, List, Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.moving_average_data import MovingAverageData
from src.models.daily_market_data import DailyMarketData
from src.config.ma_system import MA_PERIODS, get_available_periods

logger = logging.getLogger(__name__)


class MADataLoader:
    """
    均线数据加载器

    从数据库加载均线数据和当前价格，支持数据缓存。
    """

    # 缓存配置
    MAX_CACHE_SIZE = 1000  # 最大缓存条目数

    def __init__(self, session: AsyncSession, enable_cache: bool = True):
        """
        初始化均线数据加载器

        Args:
            session: 数据库会话
            enable_cache: 是否启用缓存
        """
        self.session = session
        self.enable_cache = enable_cache
        self._cache: Dict[str, Dict] = {}

    def _make_cache_key(self, entity_type: str, entity_id: int, calc_date: date) -> str:
        """
        生成缓存键

        Args:
            entity_type: 实体类型 ('stock' 或 'sector')
            entity_id: 实体ID
            calc_date: 计算日期

        Returns:
            缓存键
        """
        return f"{entity_type}:{entity_id}:{calc_date}"

    async def load_ma_values(
        self,
        entity_type: str,
        entity_id: int,
        calc_date: date,
        periods: Optional[List[int]] = None
    ) -> Dict[int, float]:
        """
        加载均线数据

        直接从均线表（MovingAverageData）加载已计算好的均线值，不重新计算。

        Args:
            entity_type: 实体类型 ('stock' 或 'sector')
            entity_id: 实体ID
            calc_date: 计算日期
            periods: 要加载的周期列表，None 表示加载全部

        Returns:
            均线值字典 {周期: 均线值}
        """
        if periods is None:
            periods = MA_PERIODS

        # 检查缓存
        cache_key = self._make_cache_key(entity_type, entity_id, calc_date)
        if self.enable_cache and cache_key in self._cache:
            cached_data = self._cache[cache_key]
            # 返回请求的周期
            return {p: cached_data.get(p) for p in periods if p in cached_data}

        try:
            # 将周期列表转换为字符串列表（如 '5d', '10d'）
            period_strs = [f"{period}d" for period in periods]

            # 使用 DISTINCT ON 为每个周期获取最新的记录（PostgreSQL 语法）
            # 对于不支持的数据库，需要使用窗口函数或子查询
            from sqlalchemy import distinct, literal_column
            from sqlalchemy.dialects.postgresql import aggregate_order_by

            # 构建子查询：先找出每个周期的最新日期
            latest_dates_subq = select(
                MovingAverageData.period,
                func.max(MovingAverageData.date).label('max_date')
            ).where(
                and_(
                    MovingAverageData.entity_type == entity_type,
                    MovingAverageData.entity_id == entity_id,
                    MovingAverageData.period.in_(period_strs),
                    MovingAverageData.date <= calc_date,
                    MovingAverageData.ma_value.isnot(None)
                )
            ).group_by(MovingAverageData.period).subquery()

            # 主查询：通过子查询连接获取每个周期的最新数据
            stmt = select(
                MovingAverageData.period,
                MovingAverageData.ma_value
            ).join(
                latest_dates_subq,
                and_(
                    MovingAverageData.period == latest_dates_subq.c.period,
                    MovingAverageData.date == latest_dates_subq.c.max_date
                )
            ).where(
                and_(
                    MovingAverageData.entity_type == entity_type,
                    MovingAverageData.entity_id == entity_id,
                    MovingAverageData.period.in_(period_strs),
                    MovingAverageData.ma_value.isnot(None)
                )
            )

            # 执行查询
            result = await self.session.execute(stmt)
            ma_rows = result.all()

            # 构建结果字典
            ma_values = {}
            for row in ma_rows:
                period = int(row[0].rstrip('d'))  # 从 '5d' 转换为 5
                ma_value = float(row[1])
                ma_values[period] = ma_value

            # 更新缓存（带大小限制）
            if self.enable_cache:
                # 如果缓存已满，清空最旧的10%
                if len(self._cache) >= self.MAX_CACHE_SIZE:
                    cache_keys = list(self._cache.keys())
                    # 移除最旧的条目（简单的FIFO策略）
                    for key in cache_keys[:self.MAX_CACHE_SIZE // 10]:
                        del self._cache[key]
                self._cache[cache_key] = ma_values

            logger.debug(
                f"从均线表加载数据: {entity_type}={entity_id}, "
                f"calc_date={calc_date}, 加载周期数={len(ma_values)}/{len(periods)}"
            )

            return ma_values

        except Exception as e:
            logger.error(
                f"加载均线数据失败 (entity_type={entity_type}, entity_id={entity_id}, calc_date={calc_date}): {e}"
            )
            return {}

    async def load_current_price(
        self,
        entity_type: str,
        entity_id: int,
        calc_date: date
    ) -> Optional[float]:
        """
        加载当前价格

        Args:
            entity_type: 实体类型 ('stock' 或 'sector')
            entity_id: 实体ID
            calc_date: 计算日期

        Returns:
            当前价格，失败返回 None
        """
        try:
            # 查询该日期或最近日期的收盘价
            stmt = select(DailyMarketData).where(
                and_(
                    DailyMarketData.entity_type == entity_type,
                    DailyMarketData.entity_id == entity_id,
                    DailyMarketData.date <= calc_date,
                    DailyMarketData.close.isnot(None)
                )
            ).order_by(DailyMarketData.date.desc()).limit(1)

            result = await self.session.execute(stmt)
            market_data = result.scalar_one_or_none()

            if market_data and market_data.close is not None:
                return float(market_data.close)

            return None

        except Exception as e:
            logger.error(f"加载当前价格失败 (entity_type={entity_type}, entity_id={entity_id}): {e}")
            return None

    async def load_data_for_calculation(
        self,
        entity_type: str,
        entity_id: int,
        calc_date: date,
        periods: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        加载计算所需的全部数据

        Args:
            entity_type: 实体类型 ('stock' 或 'sector')
            entity_id: 实体ID
            calc_date: 计算日期
            periods: 要加载的周期列表

        Returns:
            包含价格和均线数据的字典
        """
        # 加载均线数据
        ma_values = await self.load_ma_values(entity_type, entity_id, calc_date, periods)

        # 加载当前价格
        current_price = await self.load_current_price(entity_type, entity_id, calc_date)

        # 检查可用数据天数（用于渐近式计算）
        available_days = await self._get_available_days(entity_type, entity_id, calc_date)

        return {
            "current_price": current_price,
            "ma_values": ma_values,
            "available_days": available_days,
            "has_data": current_price is not None and len(ma_values) > 0
        }

    async def _get_available_days(
        self,
        entity_type: str,
        entity_id: int,
        calc_date: date
    ) -> int:
        """
        获取可用数据天数

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            calc_date: 计算日期

        Returns:
            可用天数
        """
        try:
            # 使用聚合函数计数，避免加载所有数据到内存
            stmt = select(func.count(DailyMarketData.id)).where(
                and_(
                    DailyMarketData.entity_type == entity_type,
                    DailyMarketData.entity_id == entity_id,
                    DailyMarketData.date <= calc_date,
                    DailyMarketData.close.isnot(None)
                )
            )

            result = await self.session.execute(stmt)
            count = result.scalar()

            return count if count is not None else 0

        except Exception as e:
            logger.error(f"获取可用数据天数失败: {e}")
            return 0

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()

    def remove_from_cache(self, entity_type: str, entity_id: int, calc_date: date):
        """
        从缓存中移除特定数据

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            calc_date: 计算日期
        """
        cache_key = self._make_cache_key(entity_type, entity_id, calc_date)
        if cache_key in self._cache:
            del self._cache[cache_key]
