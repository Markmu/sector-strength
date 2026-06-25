"""
基金扎堆度聚合查询服务

实时聚合（无缓存），完全复用 04 期 fund_portfolio + funds + sectors + sector_stocks
+ stocks 数据源。覆盖 AC-01/02/03/04/06/07/08 的后端语义。

复用声明：
- _compute_change_directions 范式：src/services/shareholder_analysis_service.py:264-302
  （Python 内存 dict 对比，按 symbol 维度计算 cur-prev 变化 + "new" 判定）
- _escape_like_keyword：src/services/shareholder_group_service.py:86-95
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.fund_crowd_repository import FundCrowdRepository

logger = logging.getLogger(__name__)

# ADR-1：被动型 invest_type 枚举（后端定义为常量便于调整，ADR-6 风险对策）
PASSIVE_INVEST_TYPES: tuple[str, ...] = ("被动指数型", "增强指数型")


def _escape_like_keyword(keyword: str) -> str:
    """转义 LIKE 关键词中的 % 和 _ 通配符（架构 §8.3 安全要求）。"""
    return keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class FundCrowdAnalysisService:
    """基金扎堆度聚合查询服务（实时聚合，无缓存）。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FundCrowdRepository(session)

    async def get_rankings(
        self,
        scope: str,
        search: Optional[str],
        page: int,
        page_size: int,
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
            "get_rankings called, scope=%s, search=%s, page=%d, page_size=%d",
            scope,
            search,
            page,
            page_size,
        )

        # search 转义（若非空）
        escaped_search: Optional[str] = None
        if search:
            search_stripped = search.strip()
            if search_stripped:
                escaped_search = _escape_like_keyword(search_stripped)
            else:
                search = None

        # 1. 确定报告期（最新期 + 上一期）
        periods = await self.repo.get_report_periods(limit=4)
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

        # 2. current 期聚合（含 search SQL 层过滤，路径 A）
        try:
            current_agg = await self.repo.get_crowd_aggregation(
                current_period,
                scope,
                PASSIVE_INVEST_TYPES,
                search=search,
                escaped_search=escaped_search,
            )
        except Exception:
            logger.exception(
                "get_rankings: current aggregation failed, period=%s, scope=%s",
                current_period,
                scope,
            )
            raise

        # 3. prev 期聚合（仅 has_prev_period 时；环比对比不应用 search 过滤，
        #    因为 is_new 判定需要全集对比，且 prev 期本身就是历史基准）
        if has_prev_period:
            prev_agg = await self.repo.get_crowd_aggregation(
                prev_period,
                scope,
                PASSIVE_INVEST_TYPES,
            )
        else:
            prev_agg = {}

        # 4. 环比对比（ADR-3，Python 内存，复用 06 _compute_change_directions 范式）
        changes = self._compute_changes(current_agg, prev_agg, has_prev_period)

        # 5. JOIN stocks 取 stock_name + JOIN sectors 取 industries
        all_symbols = list(current_agg.keys())
        stock_names = (
            await self.repo.get_stock_names(all_symbols) if all_symbols else {}
        )
        industry_map = (
            await self.repo.get_industry_for_stocks(all_symbols) if all_symbols else {}
        )

        # 6. 组装 item
        items = []
        for symbol, agg in current_agg.items():
            ch = changes.get(symbol, {})
            items.append(
                {
                    "stock_symbol": symbol,
                    "stock_name": stock_names.get(symbol),  # None 兜底
                    "industries": industry_map.get(symbol, []),
                    "fund_count": agg["fund_count"],
                    "fund_count_change": ch.get("fund_count_change"),
                    "is_new": ch.get("is_new"),
                }
            )

        # 7. 排序：fund_count DESC, stock_symbol ASC（tiebreaker）
        items.sort(key=lambda x: (-x["fund_count"], x["stock_symbol"]))

        # 8. 分页（search 已在 SQL WHERE 层过滤 → total = len(current_agg)）
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

    async def get_industry_distribution(self, scope: str) -> dict:
        """
        行业分布（AC-04 + ADR-5）：按行业聚合扎堆股数量占比。

        - 一股多行业独立计数（与 06 一致）
        - 无行业关联归「未分类」桶
        - 按 stock_count 降序（前端再 Top N 截断）
        """
        logger.info("get_industry_distribution called, scope=%s", scope)

        periods = await self.repo.get_report_periods(limit=2)
        if not periods:
            return {"has_data": False, "current_period": None, "distribution": []}

        current_period: date = periods[0]

        current_agg = await self.repo.get_crowd_aggregation(
            current_period,
            scope,
            PASSIVE_INVEST_TYPES,
        )
        all_symbols = list(current_agg.keys())
        if not all_symbols:
            return {
                "has_data": True,
                "current_period": current_period.isoformat(),
                "distribution": [],
            }

        industry_map = await self.repo.get_industry_for_stocks(all_symbols)
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
