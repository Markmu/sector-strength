"""
强度数据专用缓存服务

提供针对强度数据的缓存封装，包括键格式化和 TTL 管理。
"""

import logging
from collections import OrderedDict
from datetime import date
from typing import Dict, List, Optional, Any, Tuple

from src.services.cache.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

# 缓存 TTL 配置
STRENGTH_CACHE_TTL = 300  # 5分钟 - 实时强度数据
RANKING_CACHE_TTL = 300   # 5分钟 - 排名数据
HISTORY_CACHE_TTL = 600   # 10分钟 - 历史数据

# 内存缓存配置
IN_MEMORY_CACHE_SIZE = 1000  # 最大缓存条目数


class StrengthCache:
    """
    强度数据专用缓存服务

    提供两层缓存：
    1. 内存缓存（L1）：最快访问，FIFO淘汰
    2. 数据库缓存（L2）：持久化，支持TTL
    """

    def __init__(self):
        """初始化缓存服务"""
        self._cache_manager = get_cache_manager()
        self._memory_cache: OrderedDict[str, Any] = OrderedDict()
        self._memory_cache_max = IN_MEMORY_CACHE_SIZE

    def _generate_key(self, entity_type: str, entity_id: int, calc_date: date) -> str:
        """
        生成缓存键

        Args:
            entity_type: 实体类型 ('stock' 或 'sector')
            entity_id: 实体ID
            calc_date: 计算日期

        Returns:
            缓存键
        """
        return f"strength:{entity_type}:{entity_id}:{calc_date}"

    def _generate_ranking_key(self, entity_type: str, calc_date: date) -> str:
        """
        生成排名缓存键

        Args:
            entity_type: 实体类型
            calc_date: 计算日期

        Returns:
            排名缓存键
        """
        return f"ranking:{entity_type}:{calc_date}"

    def _generate_history_key(
        self,
        entity_type: str,
        entity_id: int,
        days: int,
        end_date: date
    ) -> str:
        """
        生成历史数据缓存键

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            days: 查询天数
            end_date: 结束日期

        Returns:
            历史数据缓存键
        """
        return f"history:{entity_type}:{entity_id}:{days}:{end_date}"

    def _set_memory_cache(self, key: str, value: Any) -> None:
        """
        设置内存缓存（FIFO淘汰）

        Args:
            key: 缓存键
            value: 缓存值
        """
        # 如果已存在，先删除再添加（更新位置）
        if key in self._memory_cache:
            del self._memory_cache[key]

        # 检查容量
        if len(self._memory_cache) >= self._memory_cache_max:
            # FIFO：移除最旧的
            self._memory_cache.popitem(last=False)

        # 添加到末尾
        self._memory_cache[key] = value

    def _get_memory_cache(self, key: str) -> Optional[Any]:
        """
        获取内存缓存

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回 None
        """
        return self._memory_cache.get(key)

    def _clear_memory_cache(self, key: Optional[str] = None) -> None:
        """
        清除内存缓存

        Args:
            key: 缓存键，None 表示清除全部
        """
        if key is None:
            self._memory_cache.clear()
        elif key in self._memory_cache:
            del self._memory_cache[key]

    # ========== 强度数据缓存 ==========

    async def get_strength(
        self,
        entity_type: str,
        entity_id: int,
        calc_date: date
    ) -> Optional[Dict]:
        """
        获取强度数据缓存

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            calc_date: 计算日期

        Returns:
            强度数据字典，不存在返回 None
        """
        key = self._generate_key(entity_type, entity_id, calc_date)

        # L1: 内存缓存
        value = self._get_memory_cache(key)
        if value is not None:
            return value

        # L2: 数据库缓存
        value = await self._cache_manager.get(key)
        if value is not None:
            # 回填内存缓存
            self._set_memory_cache(key, value)
            return value

        return None

    async def set_strength(
        self,
        entity_type: str,
        entity_id: int,
        calc_date: date,
        data: Dict
    ) -> bool:
        """
        设置强度数据缓存

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            calc_date: 计算日期
            data: 强度数据

        Returns:
            是否成功
        """
        key = self._generate_key(entity_type, entity_id, calc_date)

        # L1: 内存缓存
        self._set_memory_cache(key, data)

        # L2: 数据库缓存
        return await self._cache_manager.set(key, data, STRENGTH_CACHE_TTL)

    async def delete_strength(
        self,
        entity_type: str,
        entity_id: int,
        calc_date: date
    ) -> bool:
        """
        删除强度数据缓存

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            calc_date: 计算日期

        Returns:
            是否成功
        """
        key = self._generate_key(entity_type, entity_id, calc_date)

        # 清除两层缓存
        self._clear_memory_cache(key)
        return await self._cache_manager.delete(key)

    async def clear_strength_by_entity(
        self,
        entity_type: str,
        entity_id: int
    ) -> int:
        """
        清除指定实体的所有强度缓存

        Args:
            entity_type: 实体类型
            entity_id: 实体ID

        Returns:
            清除的缓存数量
        """
        pattern = f"strength:{entity_type}:{entity_id}:%"

        # 清除内存缓存中的匹配项
        keys_to_remove = [
            k for k in self._memory_cache.keys()
            if k.startswith(f"strength:{entity_type}:{entity_id}:")
        ]
        for key in keys_to_remove:
            del self._memory_cache[key]

        return await self._cache_manager.clear_pattern(pattern)

    # ========== 排名数据缓存 ==========

    async def get_ranking(
        self,
        entity_type: str,
        calc_date: date
    ) -> Optional[Dict]:
        """
        获取排名数据缓存

        Args:
            entity_type: 实体类型
            calc_date: 计算日期

        Returns:
            排名数据字典，不存在返回 None
        """
        key = self._generate_ranking_key(entity_type, calc_date)

        # L1: 内存缓存
        value = self._get_memory_cache(key)
        if value is not None:
            return value

        # L2: 数据库缓存
        value = await self._cache_manager.get(key)
        if value is not None:
            self._set_memory_cache(key, value)
            return value

        return None

    async def set_ranking(
        self,
        entity_type: str,
        calc_date: date,
        data: Dict
    ) -> bool:
        """
        设置排名数据缓存

        Args:
            entity_type: 实体类型
            calc_date: 计算日期
            data: 排名数据

        Returns:
            是否成功
        """
        key = self._generate_ranking_key(entity_type, calc_date)

        # L1: 内存缓存
        self._set_memory_cache(key, data)

        # L2: 数据库缓存
        return await self._cache_manager.set(key, data, RANKING_CACHE_TTL)

    async def delete_ranking(
        self,
        entity_type: str,
        calc_date: date
    ) -> bool:
        """
        删除排名数据缓存

        Args:
            entity_type: 实体类型
            calc_date: 计算日期

        Returns:
            是否成功
        """
        key = self._generate_ranking_key(entity_type, calc_date)

        # 清除两层缓存
        self._clear_memory_cache(key)
        return await self._cache_manager.delete(key)

    # ========== 历史数据缓存 ==========

    async def get_history(
        self,
        entity_type: str,
        entity_id: int,
        days: int,
        end_date: date
    ) -> Optional[List]:
        """
        获取历史数据缓存

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            days: 查询天数
            end_date: 结束日期

        Returns:
            历史数据列表，不存在返回 None
        """
        key = self._generate_history_key(entity_type, entity_id, days, end_date)

        # L1: 内存缓存
        value = self._get_memory_cache(key)
        if value is not None:
            return value

        # L2: 数据库缓存
        value = await self._cache_manager.get(key)
        if value is not None:
            self._set_memory_cache(key, value)
            return value

        return None

    async def set_history(
        self,
        entity_type: str,
        entity_id: int,
        days: int,
        end_date: date,
        data: List
    ) -> bool:
        """
        设置历史数据缓存

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            days: 查询天数
            end_date: 结束日期
            data: 历史数据列表

        Returns:
            是否成功
        """
        key = self._generate_history_key(entity_type, entity_id, days, end_date)

        # L1: 内存缓存
        self._set_memory_cache(key, data)

        # L2: 数据库缓存
        return await self._cache_manager.set(key, data, HISTORY_CACHE_TTL)

    async def delete_history(
        self,
        entity_type: str,
        entity_id: int,
        days: int,
        end_date: date
    ) -> bool:
        """
        删除历史数据缓存

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            days: 查询天数
            end_date: 结束日期

        Returns:
            是否成功
        """
        key = self._generate_history_key(entity_type, entity_id, days, end_date)

        # 清除两层缓存
        self._clear_memory_cache(key)
        return await self._cache_manager.delete(key)

    # ========== 批量操作 ==========

    async def get_many_strength(
        self,
        items: List[Tuple[str, int, date]]
    ) -> Dict[str, Dict]:
        """
        批量获取强度数据缓存

        Args:
            items: (entity_type, entity_id, calc_date) 元组列表

        Returns:
            键到数据的映射字典
        """
        keys = [self._generate_key(*item) for item in items]
        result = {}

        # 先从内存缓存获取
        for key in keys:
            value = self._get_memory_cache(key)
            if value is not None:
                result[key] = value

        # 从数据库获取剩余的
        remaining_keys = [k for k in keys if k not in result]
        if remaining_keys:
            db_result = await self._cache_manager.get_many(remaining_keys)
            result.update(db_result)
            # 回填内存缓存
            for k, v in db_result.items():
                self._set_memory_cache(k, v)

        return result

    # ========== 缓存管理 ==========

    async def clear_all_strength_cache(self) -> int:
        """
        清除所有强度相关缓存

        Returns:
            清除的缓存数量
        """
        # 清除内存缓存
        self._clear_memory_cache(None)

        # 清除数据库缓存
        count = await self._cache_manager.clear_pattern("strength:%")
        count += await self._cache_manager.clear_pattern("ranking:%")
        count += await self._cache_manager.clear_pattern("history:%")

        return count

    async def cleanup_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的缓存数量
        """
        return await self._cache_manager.cleanup_expired()

    def clear_memory_cache(self) -> None:
        """清除所有内存缓存"""
        self._memory_cache.clear()

    def get_memory_cache_size(self) -> int:
        """获取内存缓存当前大小"""
        return len(self._memory_cache)

    def get_memory_cache_max_size(self) -> int:
        """获取内存缓存最大容量"""
        return self._memory_cache_max
