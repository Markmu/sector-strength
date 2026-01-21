"""
板块分类缓存服务测试

测试板块分类应用级内存缓存的功能。
"""

import pytest
import threading
import time
from datetime import timedelta

from src.services.classification_cache import ClassificationCache, classification_cache


@pytest.fixture
def cache():
    """创建新的缓存实例用于测试"""
    # 使用较短的 TTL 用于测试
    return ClassificationCache(ttl_hours=1)


class TestClassificationCache:
    """板块分类缓存测试"""

    def test_cache_set_and_get(self, cache):
        """测试缓存设置和获取"""
        cache.set("test_key", {"data": "test_value"})

        hit, result = cache.get("test_key")
        assert hit is True
        assert result == {"data": "test_value"}

    def test_cache_get_nonexistent(self, cache):
        """测试获取不存在的缓存"""
        hit, result = cache.get("non_existent_key")
        assert hit is False
        assert result is None

    def test_cache_set_update(self, cache):
        """测试更新已存在的缓存"""
        cache.set("key1", {"value": "first"})
        hit, result = cache.get("key1")
        assert hit is True
        assert result == {"value": "first"}

        cache.set("key1", {"value": "updated"})
        hit, result = cache.get("key1")
        assert hit is True
        assert result == {"value": "updated"}

        # 验证大小仍然为 1
        stats = cache.get_stats()
        assert stats["size"] == 1

    def test_cache_expiration(self):
        """测试缓存过期"""
        # 创建立即过期的缓存
        cache = ClassificationCache(ttl_hours=0)

        cache.set("test_key", {"data": "test_value"})

        # 立即获取应该返回未命中（已过期）
        hit, result = cache.get("test_key")
        assert hit is False
        assert result is None

    def test_cache_clear_single_key(self, cache):
        """测试清除单个缓存键"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        # 清除 key1
        count = cache.clear("key1")

        assert count == 1
        hit, _ = cache.get("key1")
        assert hit is False
        hit, result = cache.get("key2")
        assert hit is True
        assert result == "value2"

    def test_cache_clear_all(self, cache):
        """测试清除所有缓存"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # 清除所有
        count = cache.clear(None)

        assert count == 3
        hit, _ = cache.get("key1")
        assert hit is False
        hit, _ = cache.get("key2")
        assert hit is False
        hit, _ = cache.get("key3")
        assert hit is False

    def test_cache_clear_pattern(self, cache):
        """测试按模式清除缓存"""
        cache.set("classification:1", "value1")
        cache.set("classification:2", "value2")
        cache.set("classification:all:0:100", "value3")
        cache.set("other:key", "value4")

        # 按模式清除
        count = cache.clear_pattern("classification:")

        assert count == 3
        hit, _ = cache.get("classification:1")
        assert hit is False
        hit, _ = cache.get("classification:2")
        assert hit is False
        hit, _ = cache.get("classification:all:0:100")
        assert hit is False
        hit, result = cache.get("other:key")
        assert hit is True
        assert result == "value4"

    def test_cache_stats(self, cache):
        """测试缓存统计"""
        cache.set("key1", "value1")
        cache.get("key1")  # 命中
        cache.get("key2")  # 未命中

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        assert stats["size"] == 1
        assert stats["ttl_hours"] == 1

    def test_cache_stats_empty(self, cache):
        """测试空缓存统计"""
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0
        assert stats["size"] == 0

    def test_cache_reset_stats(self, cache):
        """测试重置缓存统计"""
        cache.set("key1", "value1")
        cache.get("key1")

        cache.reset_stats()

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_cache_lru_eviction(self):
        """测试 LRU 淘汰机制"""
        # 创建小容量缓存
        cache = ClassificationCache(ttl_hours=1, max_size=3)

        # 添加 4 个项目
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # 应该淘汰 key1

        # 验证 key1 被淘汰
        hit, _ = cache.get("key1")
        assert hit is False
        hit, result = cache.get("key2")
        assert hit is True
        assert result == "value2"
        hit, result = cache.get("key3")
        assert hit is True
        assert result == "value3"
        hit, result = cache.get("key4")
        assert hit is True
        assert result == "value4"

    def test_cache_lru_update_on_access(self):
        """测试访问时更新 LRU 顺序"""
        cache = ClassificationCache(ttl_hours=1, max_size=3)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # 访问 key1 使其变为最新
        cache.get("key1")

        # 添加 key4，应该淘汰 key2（最旧的）
        cache.set("key4", "value4")

        hit, result = cache.get("key1")
        assert hit is True
        assert result == "value1"  # 仍在缓存
        hit, _ = cache.get("key2")
        assert hit is False  # 被淘汰
        hit, result = cache.get("key3")
        assert hit is True
        assert result == "value3"
        hit, result = cache.get("key4")
        assert hit is True
        assert result == "value4"

    def test_cache_thread_safety(self):
        """测试线程安全"""
        cache = ClassificationCache(ttl_hours=1)
        errors = []

        def worker():
            try:
                for i in range(100):
                    cache.set(f"key_{i}", f"value_{i}")
                    cache.get(f"key_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证没有异常
        assert len(errors) == 0

        # 验证数据一致性
        stats = cache.get_stats()
        assert stats["size"] <= 100  # 最多 100 个键

    def test_cache_concurrent_writes(self):
        """测试并发写入"""
        cache = ClassificationCache(ttl_hours=1)
        results = {}

        def worker(worker_id):
            for i in range(50):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                cache.set(key, value)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证所有数据都被写入
        stats = cache.get_stats()
        assert stats["size"] == 250  # 5 个 worker * 50 个键


class TestGlobalCacheInstance:
    """全局缓存实例测试"""

    def test_global_cache_exists(self):
        """测试全局缓存实例存在"""
        assert classification_cache is not None
        assert isinstance(classification_cache, ClassificationCache)

    def test_global_cache_ttl(self):
        """测试全局缓存 TTL 为 24 小时"""
        stats = classification_cache.get_stats()
        assert stats["ttl_hours"] == 24


class TestCachePerformance:
    """缓存性能测试"""

    @pytest.mark.performance
    def test_cache_get_performance(self):
        """测试缓存获取性能"""
        cache = ClassificationCache(ttl_hours=1)

        # 预热缓存
        cache.set("test_key", {"data": "x" * 1000})

        # 测试缓存命中性能
        start = time.perf_counter()
        for _ in range(10000):
            cache.get("test_key")
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 10000 次查询应该在 50ms 内完成
        assert elapsed_ms < 50, f"缓存性能不达标: {elapsed_ms:.2f}ms"

    @pytest.mark.performance
    def test_cache_set_performance(self):
        """测试缓存设置性能"""
        cache = ClassificationCache(ttl_hours=1)

        # 测试缓存设置性能
        start = time.perf_counter()
        for i in range(1000):
            cache.set(f"key_{i}", {"data": f"value_{i}"})
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 1000 次设置应该在 100ms 内完成
        assert elapsed_ms < 100, f"缓存设置性能不达标: {elapsed_ms:.2f}ms"


class TestCacheEdgeCases:
    """缓存边界情况测试"""

    def test_cache_empty_key(self, cache):
        """测试空字符串键"""
        cache.set("", "value")
        hit, result = cache.get("")
        assert hit is True
        assert result == "value"

    def test_cache_large_value(self, cache):
        """测试大值缓存"""
        large_value = {"data": "x" * 100000}  # 100KB 数据
        cache.set("large_key", large_value)
        hit, result = cache.get("large_key")
        assert hit is True
        assert result == large_value

    def test_cache_none_value(self, cache):
        """测试 None 值可以与缓存未命中区分"""
        cache.set("none_key", None)
        # None 值应该可以存储，并且可以与缓存未命中区分
        hit, result = cache.get("none_key")
        assert hit is True  # 缓存命中
        assert result is None  # 值确实是 None

        # 对比：不存在的键
        hit2, result2 = cache.get("non_existent_key")
        assert hit2 is False  # 缓存未命中
        assert result2 is None

    def test_cache_complex_value(self, cache):
        """测试复杂嵌套值"""
        complex_value = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "tuple": (1, 2, 3),
            "set": {1, 2, 3},
        }
        cache.set("complex_key", complex_value)
        hit, result = cache.get("complex_key")
        assert hit is True
        assert result["list"] == [1, 2, 3]
        assert result["dict"]["nested"] == "value"
