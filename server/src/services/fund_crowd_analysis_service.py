"""
基金扎堆度聚合查询服务

带两级缓存（ADR-6 修订）：L1 内存 FIFO + L2 数据库 CacheEntry，缓存报告期列表、
核心聚合（含 stock_name）、行业映射。消除扎堆度聚合的高频重复计算——核心聚合
COUNT(DISTINCT regexp_replace(Fund.name,...)) 对最新期约 15 万行 CPU 密集、索引
无法加速，且翻页/切换 sector_type/distribution 均重算恒定结果。季度更新数据天然
按 report_period 版本化 → 缓存命中率极高，持仓同步后主动失效。

search 从 SQL WHERE 层移至本服务内存层过滤（基于全量缓存 agg 子集，语义等价
symbol LIKE 'xxx%' OR name ILIKE '%xxx%'，total = len(过滤后) 仍正确）。

复用声明：
- _compute_change_directions 范式：src/services/shareholder_analysis_service.py:264-302
  （Python 内存 dict 对比，按 symbol 维度计算 cur-prev 变化 + "new" 判定）
- 缓存范式：src/services/cache/strength_cache.py（L1 OrderedDict + L2 CacheManager）
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.fund_crowd_repository import FundCrowdRepository
from src.services.cache.fund_crowd_cache import get_fund_crowd_cache

logger = logging.getLogger(__name__)

# ADR-1：被动型 invest_type 枚举（后端定义为常量便于调整，ADR-6 风险对策）
PASSIVE_INVEST_TYPES: tuple[str, ...] = ("被动指数型", "增强指数型")


class FundCrowdAnalysisService:
    """基金扎堆度聚合查询服务（两级缓存 + 内存 search 过滤）。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FundCrowdRepository(session)
        self._cache = get_fund_crowd_cache()

    async def get_rankings(
        self,
        scope: str,
        search: Optional[str],
        page: int,
        page_size: int,
        sector_type: str = "industry",
    ) -> dict:
        """
        扎堆度排行榜（AC-01/02/03/06/07/08）。

        Returns:
            {
                "has_data", "current_period", "prev_period", "has_prev_period",
                "items": [...], "total", "page", "page_size"
            }
            全部 snake_case，由路由层 _dict_to_camel 转 camelCase。
        """
        logger.info(
            "get_rankings called, scope=%s, search=%s, page=%d, page_size=%d, sector_type=%s",
            scope,
            search,
            page,
            page_size,
            sector_type,
        )

        # search 预处理：strip，空串归 None（内存过滤，无需转义 SQL 通配符）
        if search:
            search = search.strip() or None

        # 1. 报告期（缓存；统一 limit=4，供 rankings/distribution 共用同一 key）
        periods = await self._cache.get_or_compute_periods(
            lambda: self.repo.get_report_periods(limit=4)
        )
        if not periods:
            logger.info("get_rankings: no report periods, returning has_data=False")
            return {
                "has_data": False,
                "current_period": None,
                "prev_period": None,
                "has_prev_period": False,
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }

        current_period: date = periods[0]
        prev_period: Optional[date] = periods[1] if len(periods) >= 2 else None
        has_prev_period = prev_period is not None

        # 2. current 期聚合（含 stock_name，缓存；search 在内存层过滤）
        current_agg_all = await self._cache.get_or_compute_agg(
            current_period,
            scope,
            lambda: self._compute_agg_with_names(current_period, scope),
        )
        # 3. prev 期聚合（历史恒定数据，缓存长期复用）
        if has_prev_period:
            prev_agg = await self._cache.get_or_compute_agg(
                prev_period,
                scope,
                lambda: self._compute_agg_with_names(prev_period, scope),
            )
        else:
            prev_agg = {}

        # 4. search 内存过滤（基于全量缓存 agg 子集）
        if search:
            s_lower = search.lower()
            current_agg = {
                sym: agg
                for sym, agg in current_agg_all.items()
                if sym.startswith(search) or s_lower in (agg.get("name") or "").lower()
            }
        else:
            current_agg = current_agg_all

        # 5. 环比对比（ADR-3，Python 内存，复用 06 范式）
        changes = self._compute_changes(current_agg, prev_agg, has_prev_period)

        # 6. JOIN sectors 取 industries（全集缓存，按 sector_type 分 key）
        all_symbols = list(current_agg_all.keys())
        industry_map_all = (
            await self._cache.get_or_compute_industry(
                current_period,
                scope,
                sector_type,
                lambda: self.repo.get_industry_for_stocks(
                    all_symbols, sector_type=sector_type
                ),
            )
            if all_symbols
            else {}
        )

        # 7. 组装 item（用过滤后 current_agg；name 从 agg 取，industries 从全集取）
        items = []
        for symbol, agg in current_agg.items():
            ch = changes.get(symbol, {})
            items.append(
                {
                    "stock_symbol": symbol,
                    "stock_name": agg.get("name"),  # None 兜底
                    "industries": industry_map_all.get(symbol, []),
                    "fund_count": agg["fund_count"],
                    "fund_count_change": ch.get("fund_count_change"),
                    "is_new": ch.get("is_new"),
                }
            )

        # 8. 排序：fund_count DESC, stock_symbol ASC（tiebreaker）
        items.sort(key=lambda x: (-x["fund_count"], x["stock_symbol"]))

        # 9. 分页（search 已在内存过滤 → total = len(current_agg)）
        total = len(items)
        offset = (page - 1) * page_size
        page_items = items[offset : offset + page_size]

        return {
            "has_data": True,
            "current_period": current_period.isoformat(),
            "prev_period": prev_period.isoformat() if prev_period else None,
            "has_prev_period": has_prev_period,
            "items": page_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def _compute_agg_with_names(
        self, report_period: date, scope: str
    ) -> dict[str, dict]:
        """
        缓存 compute 回调：取核心聚合 + 批量 stock_name，合并为
        {symbol: {"fund_count": int, "name": str|None}}。

        name 合并进 agg value（单 key 缓存，减少往返）；name 只依赖 stocks 表，
        与 scope 无关但随 agg 一同取更高效。
        """
        agg = await self.repo.get_crowd_aggregation(
            report_period, scope, PASSIVE_INVEST_TYPES
        )
        if not agg:
            return {}
        names = await self.repo.get_stock_names(list(agg.keys()))
        return {
            sym: {"fund_count": a["fund_count"], "name": names.get(sym)}
            for sym, a in agg.items()
        }

    def _compute_changes(
        self,
        current_agg: dict[str, dict],
        prev_agg: dict[str, dict],
        has_prev_period: bool,
    ) -> dict[str, dict]:
        """
        复用 06 _compute_change_directions 范式，按 stock_symbol 对比 fund_count。

        - has_prev_period=False：所有股票 change 字段统一 None（ADR-3）
        - symbol not in prev_agg → is_new=True（新进），fund_count_change=None
        - symbol in prev_agg → cur - prev 差值，is_new=False
        """
        changes: dict[str, dict] = {}

        if not has_prev_period:
            for symbol in current_agg:
                changes[symbol] = {
                    "fund_count_change": None,
                    "is_new": None,  # ADR-3：has_prev_period=false 时 is_new=null
                }
            return changes

        for symbol, cur in current_agg.items():
            prev = prev_agg.get(symbol)
            if prev is None:
                changes[symbol] = {
                    "fund_count_change": None,  # 新进无变化数值
                    "is_new": True,
                }
            else:
                changes[symbol] = {
                    "fund_count_change": cur["fund_count"] - prev["fund_count"],
                    "is_new": False,
                }
        return changes

    async def get_industry_distribution(
        self, scope: str, sector_type: str = "industry"
    ) -> dict:
        """
        行业分布（AC-04 + ADR-5）：按行业聚合扎堆股数量占比。

        - 一股多行业独立计数（与 06 一致）
        - 无行业关联归「未分类」桶
        - 按 stock_count 降序（前端再 Top N 截断）
        """
        logger.info(
            "get_industry_distribution called, scope=%s, sector_type=%s",
            scope,
            sector_type,
        )

        periods = await self._cache.get_or_compute_periods(
            lambda: self.repo.get_report_periods(limit=4)
        )
        if not periods:
            return {"has_data": False, "current_period": None, "distribution": []}

        current_period: date = periods[0]

        current_agg = await self._cache.get_or_compute_agg(
            current_period,
            scope,
            lambda: self._compute_agg_with_names(current_period, scope),
        )
        all_symbols = list(current_agg.keys())
        if not all_symbols:
            return {
                "has_data": True,
                "current_period": current_period.isoformat(),
                "distribution": [],
            }

        industry_map = await self._cache.get_or_compute_industry(
            current_period,
            scope,
            sector_type,
            lambda: self.repo.get_industry_for_stocks(
                all_symbols, sector_type=sector_type
            ),
        )
        total_stock_count = len(all_symbols)

        # 按行业分组（一股多行业独立计数，与 06 一致）
        industry_stats: dict[str, set[str]] = {}
        for symbol in all_symbols:
            industries = industry_map.get(symbol, [])
            if not industries:
                industries = ["未分类"]
            for ind in industries:
                if ind not in industry_stats:
                    industry_stats[ind] = set()
                industry_stats[ind].add(symbol)

        distribution = [
            {
                "industry": ind,
                "stock_count": len(symbols),  # COUNT DISTINCT stock_symbol
                "percentage": round(len(symbols) / total_stock_count * 100, 4),
            }
            for ind, symbols in industry_stats.items()
        ]
        # 按 stock_count 降序（前端再 Top N 截断）
        distribution.sort(key=lambda x: -x["stock_count"])

        return {
            "has_data": True,
            "current_period": current_period.isoformat(),
            "distribution": distribution,
        }
