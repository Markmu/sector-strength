"""
缓存管理器

统一的缓存接口，支持多种后端。
"""

from typing import Optional, Any, Dict
import logging

from .backends.db_cache import DatabaseCache

logger = logging.getLogger(__name__)


class CacheManager:
    """
    缓存管理器

    提供统一的缓存接口，支持多种后端实现。
    """

    def __init__(self, backend: str = "database"):
        """
        初始化缓存管理器

        Args:
            backend: 缓存后端类型 ('database' | 'redis')
        """
        self.backend_type = backend
        self._backend = None

        if backend == "database":
            self._backend = DatabaseCache()
        # elif backend == "redis":
        #     from .backends.redis_cache import RedisCache
        #     self._backend = RedisCache()
        else:
            raise ValueError(f"不支持的缓存后端: {backend}")

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        return await self._backend.get(key)

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存"""
        return await self._backend.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        return await self._backend.delete(key)

    async def clear_pattern(self, pattern: str) -> int:
        """按模式清除缓存"""
        return await self._backend.clear_pattern(pattern)

    async def clear_all(self) -> int:
        """清除所有缓存"""
        return await self._backend.clear_all()

    async def cleanup_expired(self) -> int:
        """清理过期缓存"""
        return await self._backend.cleanup_expired()

    async def get_many(self, keys: list[str]) -> Dict[str, Any]:
        """批量获取缓存"""
        return await self._backend.get_many(keys)

    async def set_many(self, mapping: Dict[str, Any], ttl: int = 3600) -> int:
        """批量设置缓存"""
        return await self._backend.set_many(mapping, ttl)

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return await self._backend.exists(key)

    async def ttl(self, key: str) -> Optional[int]:
        """获取缓存剩余 TTL"""
        return await self._backend.ttl(key)


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    获取全局缓存管理器实例

    Returns:
        CacheManager: 缓存管理器单例
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(backend="database")
    return _cache_manager


def reset_cache_manager():
    """重置缓存管理器（主要用于测试）"""
    global _cache_manager
    _cache_manager = None
