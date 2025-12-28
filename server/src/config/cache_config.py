"""
缓存配置

定义缓存相关的常量和配置。
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.cache.cache_manager import CacheManager


class CacheKeys:
    """
    缓存键命名规范

    遵循一致的命名约定，便于管理和清除缓存。
    """

    # 板块相关
    SECTOR_LIST = "sectors:list:{type}"  # sectors:list:industry
    SECTOR_DETAIL = "sectors:detail:{id}"  # sectors:detail:001
    SECTOR_RANKING = "sectors:ranking:{order}:{n}"  # sectors:ranking:desc:20
    SECTOR_STOCKS = "sectors:{id}:stocks:page:{page}:size:{size}"

    # 股票相关
    STOCK_LIST = "stocks:list:{filters}:page:{page}:size:{size}"
    STOCK_DETAIL = "stocks:detail:{id}"
    STOCK_RANKING = "stocks:ranking:{order}:{n}"
    STOCK_BY_SECTOR = "stocks:sector:{sector_id}:page:{page}:size:{size}"

    # 强度数据
    STRENGTH_DATA = "strength:{entity_type}:{entity_id}:{date}"
    STRENGTH_LIST = "strength:list:{entity_type}:page:{page}:size:{size}"
    HEATMAP_DATA = "heatmap:sectors:{type}"

    # 行情数据
    MARKET_DATA = "market:{symbol}:{date}"
    MARKET_DATA_LATEST = "market:{symbol}:latest"

    # 统计数据
    STATS_OVERVIEW = "stats:overview"

    @classmethod
    def build_key(cls, template: str, **kwargs) -> str:
        """
        构建缓存键

        Args:
            template: 键模板
            **kwargs: 模板参数

        Returns:
            完整的缓存键

        Examples:
            >>> CacheKeys.build_key(CacheKeys.SECTOR_DETAIL, id="001")
            'sectors:detail:001'
        """
        return template.format(**kwargs)


class CacheTTL:
    """
    缓存 TTL 配置（秒）

    根据数据更新频率和业务需求设置不同的过期时间。
    """

    TTL_MINUTE = 60         # 1 分钟
    TTL_5_MINUTES = 300     # 5 分钟
    TTL_15_MINUTES = 900    # 15 分钟
    TTL_30_MINUTES = 1800   # 30 分钟
    TTL_1_HOUR = 3600       # 1 小时
    TTL_6_HOURS = 21600     # 6 小时
    TTL_12_HOURS = 43200    # 12 小时
    TTL_1_DAY = 86400       # 1 天

    # 各类型数据的默认 TTL
    SECTOR_LIST_TTL = TTL_30_MINUTES
    SECTOR_DETAIL_TTL = TTL_5_MINUTES
    STOCK_LIST_TTL = TTL_5_MINUTES
    STOCK_DETAIL_TTL = TTL_1_HOUR
    STRENGTH_DATA_TTL = TTL_15_MINUTES
    RANKING_TTL = TTL_5_MINUTES
    HEATMAP_TTL = TTL_30_MINUTES
    MARKET_DATA_TTL = TTL_MINUTE


class CacheConfig:
    """
    缓存系统配置
    """

    # 是否启用缓存
    ENABLE_CACHE: bool = True

    # 缓存后端: 'database' | 'redis'
    CACHE_BACKEND: str = "database"

    # Redis 配置（如果使用 Redis）
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 10

    # 缓存前缀
    CACHE_PREFIX: str = "sector_strength:"

    # 默认 TTL
    DEFAULT_TTL: int = CacheTTL.TTL_30_MINUTES

    # 清理配置
    CLEANUP_INTERVAL: int = 3600  # 每小时清理一次过期缓存
    CLEANUP_ON_STARTUP: bool = True  # 启动时清理过期缓存

    # 缓存预热配置
    WARMUP_ON_STARTUP: bool = False  # 启动时预热常用缓存

    @classmethod
    def get_ttl_for_key_type(cls, key_type: str) -> int:
        """
        根据键类型获取对应的 TTL

        Args:
            key_type: 键类型（如 'sector_list', 'stock_detail'）

        Returns:
            TTL（秒）
        """
        ttl_map = {
            "sector_list": CacheTTL.SECTOR_LIST_TTL,
            "sector_detail": CacheTTL.SECTOR_DETAIL_TTL,
            "stock_list": CacheTTL.STOCK_LIST_TTL,
            "stock_detail": CacheTTL.STOCK_DETAIL_TTL,
            "strength_data": CacheTTL.STRENGTH_DATA_TTL,
            "ranking": CacheTTL.RANKING_TTL,
            "heatmap": CacheTTL.HEATMAP_TTL,
            "market_data": CacheTTL.MARKET_DATA_TTL,
        }
        return ttl_map.get(key_type, cls.DEFAULT_TTL)


# 缓存装饰器
def cached(ttl: int = 300, key_prefix: str = ""):
    """
    缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀

    Examples:
        ```python
        @cached(ttl=600, key_prefix="sectors")
        async def get_sectors():
            return await fetch_sectors()
        ```
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 延迟导入避免循环引用
            from src.services.cache.cache_manager import get_cache_manager

            # 构建缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"

            # 尝试从缓存获取
            cache = get_cache_manager()
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
