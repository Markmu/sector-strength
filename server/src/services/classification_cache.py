"""
板块分类应用级缓存服务

提供针对板块分类数据的内存缓存功能，支持 TTL 过期机制和线程安全。

缓存设计说明:
    - 缓存键包含分页参数: "classification:all:{skip}:{limit}"
    - 原因: 避免缓存整个数据集造成内存浪费
    - 影响: 不同分页参数会创建独立缓存条目
    - 建议: 在数据更新后调用清除缓存接口

使用限制:
    - 单进程内存缓存，不支持多 worker 共享
    - 缓存的是 Pydantic 响应模型，结构变化需清空缓存
    - 24 小时 TTL 自动过期
    - LRU 淘汰机制，默认最大 1000 条目
"""

import logging
import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 缓存 TTL 配置（24 小时）
CLASSIFICATION_CACHE_TTL_HOURS = 24

# 内存缓存配置
IN_MEMORY_CACHE_SIZE = 1000  # 最大缓存条目数

# 哨兵值：用于区分缓存未命中和缓存的 None 值
_CACHE_MISSING = object()

# 缓存结果类型： Tuple[是否命中, 缓存值]
CacheResult = Tuple[bool, Any]


class ClassificationCache:
    """
    板块分类应用级缓存服务

    使用内存字典存储缓存数据，支持 TTL 过期机制。
    线程安全，适用于 FastAPI 异步环境。
    """

    def __init__(self, ttl_hours: int = CLASSIFICATION_CACHE_TTL_HOURS, max_size: int = IN_MEMORY_CACHE_SIZE):
        """
        初始化缓存

        参数:
            ttl_hours: 缓存过期时间（小时），默认 24 小时
            max_size: 最大缓存条目数
        """
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._cache_time: Dict[str, datetime] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._max_size = max_size
        self._lock = threading.RLock()  # 可重入锁，支持线程安全

        # 缓存统计
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> CacheResult:
        """
        获取缓存值

        参数:
            key: 缓存键

        返回:
            Tuple[是否命中, 缓存值]
            - 如果缓存命中: (True, value) - value 可能是 None
            - 如果缓存未命中或过期: (False, None)
        """
        with self._lock:
            # 检查键是否存在
            if key not in self._cache:
                self._misses += 1
                logger.debug(f"缓存未命中: {key}")
                return (False, None)

            # 检查是否过期
            cache_time = self._cache_time[key]
            time_since_cache = datetime.now() - cache_time
            # 处理 TTL=0 的特殊情况（立即过期）
            if self._ttl.total_seconds() == 0 or time_since_cache > self._ttl:
                # 缓存已过期，删除并返回未命中
                del self._cache[key]
                del self._cache_time[key]
                self._misses += 1
                logger.debug(f"缓存过期: {key}")
                return (False, None)

            # 缓存命中，移到末尾（LRU 更新）
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug(f"缓存命中: {key}")
            return (True, self._cache[key])

    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值

        参数:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            # 如果键已存在，先删除再添加（更新位置和值）
            if key in self._cache:
                del self._cache[key]
                del self._cache_time[key]

            # 检查容量
            while len(self._cache) >= self._max_size:
                # LRU：移除最旧的
                oldest_key, _ = self._cache.popitem(last=False)
                # 清理对应的时间戳
                if oldest_key in self._cache_time:
                    del self._cache_time[oldest_key]

            # 添加到末尾
            self._cache[key] = value
            self._cache_time[key] = datetime.now()
            logger.debug(f"缓存设置: {key}")

    def clear(self, key: Optional[str] = None) -> int:
        """
        清除缓存

        参数:
            key: 缓存键，如果为 None 则清除所有缓存

        返回:
            清除的缓存条目数量
        """
        with self._lock:
            if key is None:
                # 清除所有缓存
                count = len(self._cache)
                self._cache.clear()
                self._cache_time.clear()
                logger.info(f"清除所有缓存: {count} 条")
                return count
            else:
                # 清除指定缓存
                if key in self._cache:
                    del self._cache[key]
                    del self._cache_time[key]
                    logger.debug(f"清除缓存: {key}")
                    return 1
                return 0

    def clear_pattern(self, pattern: str) -> int:
        """
        按模式清除缓存

        参数:
            pattern: 键模式（支持前缀匹配）

        返回:
            删除的缓存条目数量
        """
        with self._lock:
            keys_to_delete = [
                key for key in list(self._cache.keys())
                if key.startswith(pattern)
            ]
            for key in keys_to_delete:
                del self._cache[key]
                del self._cache_time[key]
            logger.info(f"按模式清除缓存: {pattern}, 删除 {len(keys_to_delete)} 条")
            return len(keys_to_delete)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        返回:
            包含缓存统计的字典
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0

            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "size": len(self._cache),
                "ttl_hours": self._ttl.total_seconds() / 3600,
                "max_size": self._max_size
            }

    def reset_stats(self) -> None:
        """重置缓存统计"""
        with self._lock:
            self._hits = 0
            self._misses = 0


# 全局缓存实例
classification_cache = ClassificationCache(ttl_hours=CLASSIFICATION_CACHE_TTL_HOURS)
