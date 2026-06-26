"""
FundCrowdCache 单元测试

验证：L1/L2 命中跳过 compute、single-flight 并发只算一次、invalidate_all 清
命名空间、空结果缓存防穿透。不依赖真实 DB（mock CacheManager 的 get/set/
clear_pattern）。
"""

import asyncio
from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.services.cache.fund_crowd_cache import FundCrowdCache


@pytest.mark.asyncio
async def test_agg_l2_hit_skips_compute():
    """L2 命中时 compute 不被调用"""
    cache = FundCrowdCache()
    cache._cache_manager.get = AsyncMock(
        return_value={"000001": {"fund_count": 5, "name": "平安银行"}}
    )
    compute = AsyncMock()
    result = await cache.get_or_compute_agg(date(2024, 12, 31), "active", compute)
    assert result["000001"]["fund_count"] == 5
    compute.assert_not_awaited()


@pytest.mark.asyncio
async def test_agg_miss_then_l1_hit_computes_once():
    """miss 时 compute 并写缓存，二次命中 L1（compute 只算一次）"""
    cache = FundCrowdCache()
    cache._cache_manager.get = AsyncMock(return_value=None)
    cache._cache_manager.set = AsyncMock(return_value=True)
    counter = 0

    async def compute():
        nonlocal counter
        counter += 1
        return {"000001": {"fund_count": 3, "name": None}}

    r1 = await cache.get_or_compute_agg(date(2024, 12, 31), "active", compute)
    r2 = await cache.get_or_compute_agg(date(2024, 12, 31), "active", compute)  # 命中 L1
    assert r1 == r2
    assert counter == 1


@pytest.mark.asyncio
async def test_single_flight_concurrent_computes_once():
    """并发同 key 只 compute 一次（per-key Lock single-flight）"""
    cache = FundCrowdCache()
    cache._cache_manager.get = AsyncMock(return_value=None)
    cache._cache_manager.set = AsyncMock(return_value=True)
    counter = 0

    async def compute():
        nonlocal counter
        counter += 1
        await asyncio.sleep(0.02)  # 放大并发窗口
        return {}

    await asyncio.gather(
        *[
            cache.get_or_compute_agg(date(2024, 12, 31), "active", compute)
            for _ in range(5)
        ]
    )
    assert counter == 1


@pytest.mark.asyncio
async def test_invalidate_all_clears_namespace_and_l1():
    """invalidate_all 清 L2 命名空间 + L1 内存"""
    cache = FundCrowdCache()
    cache._cache_manager.clear_pattern = AsyncMock(return_value=3)
    cache._set_memory_cache("fund_crowd:agg:x:active", {"foo": 1})
    count = await cache.invalidate_all()
    assert count == 3
    cache._cache_manager.clear_pattern.assert_awaited_with("fund_crowd:%")
    assert cache.get_memory_cache_size() == 0


@pytest.mark.asyncio
async def test_empty_agg_cached_prevents_penetration():
    """空 {} 也缓存，避免缓存穿透"""
    cache = FundCrowdCache()
    cache._cache_manager.get = AsyncMock(return_value=None)
    cache._cache_manager.set = AsyncMock(return_value=True)

    async def compute():
        return {}

    result = await cache.get_or_compute_agg(date(2024, 12, 31), "active", compute)
    assert result == {}
    cache._cache_manager.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_empty_periods_list_cached():
    """空报告期列表 [] 也缓存"""
    cache = FundCrowdCache()
    cache._cache_manager.get = AsyncMock(return_value=None)
    cache._cache_manager.set = AsyncMock(return_value=True)

    async def compute():
        return []

    result = await cache.get_or_compute_periods(compute)
    assert result == []
    cache._cache_manager.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_industry_key_isolated_by_sector_type():
    """不同 sector_type 走独立 key，互不污染"""
    cache = FundCrowdCache()
    cache._cache_manager.get = AsyncMock(return_value=None)
    cache._cache_manager.set = AsyncMock(return_value=True)
    seen_scopes = []

    async def make_compute(sector_type):
        async def _compute():
            seen_scopes.append(sector_type)
            return {"000001": [sector_type]}

        return _compute

    await cache.get_or_compute_industry(
        date(2024, 12, 31), "active", "industry", await make_compute("industry")
    )
    await cache.get_or_compute_industry(
        date(2024, 12, 31), "active", "concept", await make_compute("concept")
    )
    assert seen_scopes == ["industry", "concept"]  # 两次都 miss，各自计算
