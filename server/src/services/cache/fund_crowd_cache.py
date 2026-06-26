"""
基金扎堆度聚合查询缓存服务

为 FundCrowdAnalysisService 提供两级缓存（L1 内存 FIFO + L2 数据库 CacheEntry），
缓存报告期列表、核心聚合结果（含 stock_name）、行业映射，消除扎堆度聚合的
高频重复计算（ADR-6 修订：引入轻量缓存）。

背景：fund_portfolio 最新期单期约 15 万行，核心聚合 COUNT(DISTINCT
regexp_replace(Fund.name,...)) CPU 密集、索引无法加速；get_rankings 每次聚合
两期（current+prev），且翻页/切换 sector_type/distribution 均重算恒定结果。
季度更新数据天然按 report_period 版本化 → 缓存命中率极高、失效极简。

key 设计（report_period 天然版本化）：
- fund_crowd:periods                                          → list[date]
- fund_crowd:agg:{period_iso}:{scope}                         → {symbol: {"fund_count", "name"}}
- fund_crowd:industry:{period_iso}:{scope}:{sector_type}      → {symbol: [name,...]}

范式参考：src/services/cache/strength_cache.py（L1 OrderedDict + L2 CacheManager）。

失效策略：
- 持仓同步任务（src/services/task_handlers.py sync_fund_portfolio_task）成功后
  调 invalidate_all() 清整个命名空间（同 report_period 补数据 = DELETE+重写，
  见 data_init_fund.py，必须主动失效防脏读）。
- 新报告期天然走新 period_iso key，旧期 key 靠 TTL 过期。
- TTL 仅为兜底，主失效靠上述主动 clear。
"""

import asyncio
import logging
from collections import OrderedDict
from datetime import date
from typing import Any, Awaitable, Callable, Optional

from src.services.cache.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)

# TTL 配置（季度更新数据，TTL 兜底，主失效靠持仓同步后主动 clear）
PERIODS_TTL = 600  # 报告期列表：变更极低，但需 04 同步后较快感知
AGG_TTL = 86400  # 核心聚合：同 period 恒定，24h 兜底
INDUSTRY_TTL = 3600  # 行业映射：sectors/sector_stocks 偶有手动维护

# 内存缓存容量：命名空间内 key 数量有限（periods 1 + agg 2scope×N期 +
# industry 2scope×N期×3type，N≤4 ≈ 33），200 足够
_IN_MEMORY_CACHE_MAX = 200


class FundCrowdCache:
    """
    基金扎堆度聚合专用缓存（L1 内存 FIFO + L2 数据库）。

    per-key asyncio.Lock 实现 single-flight，防止缓存击穿（stampede）：
    同一 key 并发 miss 时只计算一次，其余协程等待结果后从缓存读取。
    """

    def __init__(self):
        self._cache_manager = get_cache_manager()
        self._memory_cache: OrderedDict[str, Any] = OrderedDict()
        self._memory_cache_max = _IN_MEMORY_CACHE_MAX
        self._locks: dict[str, asyncio.Lock] = {}

    # ========== key 生成 ==========

    @staticmethod
    def _periods_key() -> str:
        return "fund_crowd:periods"

    @staticmethod
    def _agg_key(period: date, scope: str) -> str:
        return f"fund_crowd:agg:{period.isoformat()}:{scope}"

    @staticmethod
    def _industry_key(period: date, scope: str, sector_type: str) -> str:
        return f"fund_crowd:industry:{period.isoformat()}:{scope}:{sector_type}"

    # ========== L1 内存缓存（FIFO，仿 StrengthCache）==========

    def _set_memory_cache(self, key: str, value: Any) -> None:
        """写入 L1。已存在则先删后加（刷新位置），容量满则 FIFO 移除最旧。"""
        if key in self._memory_cache:
            del self._memory_cache[key]
        if len(self._memory_cache) >= self._memory_cache_max:
            self._memory_cache.popitem(last=False)
        self._memory_cache[key] = value

    def _get_memory_cache(self, key: str) -> Optional[Any]:
        return self._memory_cache.get(key)

    def _clear_memory_cache(self) -> None:
        self._memory_cache.clear()

    def get_memory_cache_size(self) -> int:
        """L1 条目数（测试断言用）。"""
        return len(self._memory_cache)

    # ========== 通用 get_or_compute（L1 → L2 → single-flight 计算）==========

    async def _get_or_compute(
        self, key: str, ttl: int, compute: Callable[[], Awaitable[Any]]
    ) -> Any:
        # L1 命中
        if (v := self._get_memory_cache(key)) is not None:
            return v
        # L2 命中（回填 L1）
        if (v := await self._cache_manager.get(key)) is not None:
            self._set_memory_cache(key, v)
            return v
        # single-flight：per-key Lock，并发 miss 只计算一次
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            # double-check：持锁期间可能已被其他协程填入
            if (v := self._get_memory_cache(key)) is not None:
                return v
            if (v := await self._cache_manager.get(key)) is not None:
                self._set_memory_cache(key, v)
                return v
            v = await compute()
            await self._cache_manager.set(key, v, ttl)
            self._set_memory_cache(key, v)
            return v

    # ========== 业务方法 ==========

    async def get_or_compute_periods(
        self, compute: Callable[[], Awaitable[list[date]]]
    ) -> list[date]:
        """报告期列表缓存。compute 返回 [] 也缓存（防穿透）。"""
        return await self._get_or_compute(self._periods_key(), PERIODS_TTL, compute)

    async def get_or_compute_agg(
        self,
        period: date,
        scope: str,
        compute: Callable[[], Awaitable[dict[str, dict]]],
    ) -> dict[str, dict]:
        """核心聚合缓存（含 stock_name）。compute 返回 {} 也缓存。"""
        return await self._get_or_compute(self._agg_key(period, scope), AGG_TTL, compute)

    async def get_or_compute_industry(
        self,
        period: date,
        scope: str,
        sector_type: str,
        compute: Callable[[], Awaitable[dict[str, list[str]]]],
    ) -> dict[str, list[str]]:
        """行业映射缓存（按 sector_type 分 key）。"""
        return await self._get_or_compute(
            self._industry_key(period, scope, sector_type), INDUSTRY_TTL, compute
        )

    async def invalidate_all(self) -> int:
        """清整个 fund_crowd 命名空间（L2 + L1）。持仓同步成功后调用。"""
        count = await self._cache_manager.clear_pattern("fund_crowd:%")
        self._clear_memory_cache()
        return count


# ========== 模块级单例 ==========

_fund_crowd_cache: Optional[FundCrowdCache] = None


def get_fund_crowd_cache() -> FundCrowdCache:
    global _fund_crowd_cache
    if _fund_crowd_cache is None:
        _fund_crowd_cache = FundCrowdCache()
    return _fund_crowd_cache


def reset_fund_crowd_cache() -> None:
    """重置单例（测试用，清 L1 内存；L2 由 invalidate_all 清）。"""
    global _fund_crowd_cache
    _fund_crowd_cache = None
