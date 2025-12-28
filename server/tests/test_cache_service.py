"""
缓存服务测试

测试数据库缓存后端和缓存管理器的功能。
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.cache.backends.db_cache import DatabaseCache
from src.services.cache.cache_manager import CacheManager, get_cache_manager
from src.models.cache import CacheEntry


@pytest.fixture
def db_cache():
    """创建数据库缓存实例"""
    return DatabaseCache()


@pytest.fixture
def cache_manager():
    """创建缓存管理器实例"""
    return CacheManager(backend="database")


class TestDatabaseCache:
    """数据库缓存测试"""

    @pytest.mark.asyncio
    async def test_set_and_get(self, db_cache):
        """测试设置和获取缓存"""
        key = "test:key"
        value = {"data": "test_value"}

        with patch('src.services.cache.backends.db_cache.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            # Mock execute -> scalar_one_or_none chain
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=MagicMock(
                key=key,
                expires_at=datetime.now() + timedelta(seconds=300),
                value=b'{"data": "test_value"}'  # bytes for pickle
            ))
            mock_session.execute.return_value = mock_result

            # Mock set operations
            result_set = select = await db_cache.set(key, value, ttl=300)

            # Mock get - return cached entry
            import pickle
            mock_entry = MagicMock()
            mock_entry.key = key
            mock_entry.expires_at = datetime.now() + timedelta(seconds=300)
            mock_entry.value = pickle.dumps(value)
            mock_result.scalar_one_or_none.return_value = mock_entry

            result = await db_cache.get(key)

            assert result == value

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, db_cache):
        """测试获取不存在的缓存"""
        key = "test:nonexistent"

        with patch('src.services.cache.backends.db_cache.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            # Mock execute -> scalar_one_or_none chain returning None
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=None)
            mock_session.execute.return_value = mock_result

            result = await db_cache.get(key)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_expired(self, db_cache):
        """测试获取过期缓存 - 由查询条件过滤"""
        key = "test:expired"

        with patch('src.services.cache.backends.db_cache.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            # 模拟查询返回 None（已过期的被 SQL 条件过滤）
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = AsyncMock(return_value=None)
            mock_session.execute.return_value = mock_result

            result = await db_cache.get(key)

            assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, db_cache):
        """测试删除缓存"""
        key = "test:delete"

        with patch('src.services.cache.backends.db_cache.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            # Mock execute result
            mock_result = MagicMock()
            mock_result.rowcount = 1
            mock_session.execute.return_value = mock_result

            result = await db_cache.delete(key)

            assert result is True

    @pytest.mark.asyncio
    async def test_clear_pattern(self, db_cache):
        """测试按模式清除缓存"""
        pattern = "%test:%"

        with patch('src.services.cache.backends.db_cache.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            # Mock execute result
            mock_result = MagicMock()
            mock_result.rowcount = 5
            mock_session.execute.return_value = mock_result

            count = await db_cache.clear_pattern(pattern)

            assert count == 5

    @pytest.mark.asyncio
    async def test_clear_all(self, db_cache):
        """测试清除所有缓存"""
        with patch('src.services.cache.backends.db_cache.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            # Mock execute result
            mock_result = MagicMock()
            mock_result.rowcount = 10
            mock_session.execute.return_value = mock_result

            count = await db_cache.clear_all()

            assert count == 10

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, db_cache):
        """测试清理过期缓存"""
        with patch('src.services.cache.backends.db_cache.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            # Mock execute result
            mock_result = MagicMock()
            mock_result.rowcount = 3
            mock_session.execute.return_value = mock_result

            count = await db_cache.cleanup_expired()

            assert count == 3


class TestCacheManager:
    """缓存管理器测试"""

    def test_init_database_backend(self):
        """测试初始化数据库后端"""
        manager = CacheManager(backend="database")
        assert isinstance(manager._backend, DatabaseCache)

    def test_singleton(self):
        """测试单例模式"""
        # Reset singleton
        import src.services.cache.cache_manager as cm
        cm._cache_manager = None

        manager1 = get_cache_manager()
        manager2 = get_cache_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_get(self, cache_manager):
        """测试获取缓存"""
        with patch.object(cache_manager._backend, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"data": "test"}

            result = await cache_manager.get("test:key")

            assert result == {"data": "test"}
            mock_get.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_set(self, cache_manager):
        """测试设置缓存"""
        with patch.object(cache_manager._backend, 'set', new_callable=AsyncMock):
            await cache_manager.set("test:key", {"data": "test"}, ttl=300)

    @pytest.mark.asyncio
    async def test_delete(self, cache_manager):
        """测试删除缓存"""
        with patch.object(cache_manager._backend, 'delete', new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True

            result = await cache_manager.delete("test:key")

            assert result is True

    @pytest.mark.asyncio
    async def test_clear_pattern(self, cache_manager):
        """测试按模式清除缓存"""
        with patch.object(cache_manager._backend, 'clear_pattern', new_callable=AsyncMock) as mock_clear:
            mock_clear.return_value = 5

            count = await cache_manager.clear_pattern("%test:%")

            assert count == 5

    @pytest.mark.asyncio
    async def test_clear_all(self, cache_manager):
        """测试清除所有缓存"""
        with patch.object(cache_manager._backend, 'clear_all', new_callable=AsyncMock) as mock_clear:
            mock_clear.return_value = 10

            count = await cache_manager.clear_all()

            assert count == 10


class TestCacheConfig:
    """缓存配置测试"""

    def test_cache_keys_build_key(self):
        """测试缓存键命名"""
        from src.config.cache_config import CacheKeys

        # 测试板块详情键
        sector_detail_key = CacheKeys.build_key(CacheKeys.SECTOR_DETAIL, id="001")
        assert sector_detail_key == "sectors:detail:001"

        # 测试板块列表键
        sector_list_key = CacheKeys.build_key(CacheKeys.SECTOR_LIST, type="concept")
        assert sector_list_key == "sectors:list:concept"

        # 测试股票列表键
        stock_list_key = CacheKeys.build_key(
            CacheKeys.STOCK_LIST,
            filters="sector:123",
            page=1,
            size=20
        )
        assert "stocks:list" in stock_list_key
        assert "sector:123" in stock_list_key
        assert "page:1" in stock_list_key
        assert "size:20" in stock_list_key

    def test_cache_ttl(self):
        """测试缓存 TTL 配置"""
        from src.config.cache_config import CacheTTL

        assert CacheTTL.TTL_MINUTE == 60
        assert CacheTTL.TTL_5_MINUTES == 300
        assert CacheTTL.TTL_30_MINUTES == 1800
        assert CacheTTL.TTL_1_HOUR == 3600
        assert CacheTTL.TTL_1_DAY == 86400

    def test_cache_config_get_ttl(self):
        """测试根据类型获取 TTL"""
        from src.config.cache_config import CacheConfig, CacheTTL

        assert CacheConfig.get_ttl_for_key_type("sector_list") == CacheTTL.TTL_30_MINUTES
        assert CacheConfig.get_ttl_for_key_type("stock_detail") == CacheTTL.TTL_1_HOUR
        assert CacheConfig.get_ttl_for_key_type("unknown") == CacheConfig.DEFAULT_TTL
