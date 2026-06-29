"""券商月度金股聚合查询服务（plan-02）

面向用户的查询服务：股票维度排行、券商维度分组、券商明细、月份列表。
含 latest_month 兜底（AC-10）、行业 JOIN、brokers 预加载聚合、同券商多 reason 归并。

范式参照 src/services/fund_crowd_analysis_service.py（注入 session + repository，
全部返回 snake_case dict，路由层 _dict_to_camel 转 camelCase）。
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.sector_stock import SectorStock
from src.models.stock import Stock
from src.repositories.broker_recommend_repository import BrokerRecommendRepository
from src.services.shareholder_analysis_service import _escape_like_keyword

logger = logging.getLogger(__name__)

# ADR-3：单股百家推荐极端兜底
MAX_BROKERS_PER_STOCK = 100

# 板块类型（与前端 sectorTypes.ts SECTOR_TYPES 一致）
SECTOR_TYPES = ("industry", "concept", "region")


class BrokerRecommendAnalysisService:
    """券商月度金股聚合查询服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BrokerRecommendRepository(session)

    # ========== 行业批量 JOIN（复用 shareholder_analysis 范式）==========

    async def _get_industry_for_stocks(
        self, symbols: list[str], sector_type: str = "industry"
    ) -> dict[str, dict]:
        """批量获取股票的板块关联（显式 JOIN，无 ORM relationship）。

        一只股票可关联多个板块，全部返回。sector_type 决定 JOIN 哪类板块
        （industry/concept/region），用于动态展示当前筛选维度的板块归属。
        范式参照 shareholder_analysis_service._get_industry_for_stocks（line 304-356）。

        Returns:
            { symbol: { "stock_name": str | None, "industries": list[str] } }
        """
        if not symbols:
            return {}

        stmt = (
            select(Stock.symbol, Stock.name, Sector.name)
            .select_from(Stock)
            .outerjoin(SectorStock, SectorStock.stock_code == Stock.symbol)
            .outerjoin(
                Sector,
                and_(
                    Sector.code == SectorStock.sector_code,
                    Sector.type == sector_type,
                ),
            )
            .where(Stock.symbol.in_(symbols))
        )
        result = await self.session.execute(stmt)

        mapping: dict[str, dict] = {}
        for symbol, stock_name, industry_name in result.all():
            if symbol not in mapping:
                mapping[symbol] = {"stock_name": stock_name, "industries": []}
            if (
                industry_name
                and industry_name not in mapping[symbol]["industries"]
            ):
                mapping[symbol]["industries"].append(industry_name)

        # 对传入但 stocks 表缺失的 symbol，补充空结构
        for sym in symbols:
            if sym not in mapping:
                mapping[sym] = {"stock_name": None, "industries": []}

        return mapping

    # ========== 序列化 helper ==========

    @staticmethod
    def _to_float(val: Any) -> Optional[float]:
        """Decimal / 数字 → float；None 保持 None"""
        if val is None:
            return None
        if isinstance(val, Decimal):
            return float(val)
        return val

    # ========== 月份相关 ==========

    async def get_months(self) -> dict:
        """已同步月份列表 + 是否有数据（AC-05）"""
        months = await self.repo.get_months()
        return {
            "has_data": len(months) > 0,
            "months": [m.isoformat() for m in months],
        }

    def _resolve_month(
        self, month: Optional[str], latest: Optional[date]
    ) -> Optional[date]:
        """月份解析：缺省取 latest（MAX(month)）；"YYYY-MM-01" → date"""
        if month:
            return datetime.strptime(month, "%Y-%m-%d").date()
        return latest

    # ========== 股票维度排行（AC-02/03/06/07/10/11）==========

    async def get_stock_ranking(
        self,
        month: Optional[str],
        search: Optional[str],
        page: int,
        page_size: int,
        sector_type: str = "industry",
        sector_name: Optional[str] = None,
    ) -> dict:
        """股票维度卖方共识排行榜

        sector_name 有值时按 sector_type 维度过滤（只保留归属该板块的股票）；
        industries 列始终按 sector_type 维度展示当前板块归属。
        """
        latest = await self.repo.get_latest_month()
        month_date = self._resolve_month(month, latest)

        if month_date is None:
            return {
                "has_data": False,
                "month": None,
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }

        escaped_search = _escape_like_keyword(search.strip()) if search else None
        rows, total = await self.repo.get_stock_ranking(
            month_date,
            escaped_search,
            page,
            page_size,
            sector_type=sector_type,
            sector_name=sector_name,
        )

        if not rows:
            # 所选月无数据 或 搜索无结果 或 板块过滤无匹配
            return {
                "has_data": True,
                "month": month_date.isoformat(),
                "items": [],
                "total": total,
                "page": page,
                "page_size": page_size,
            }

        symbols = [r.symbol for r in rows]
        # industries 列按当前筛选维度（sector_type）展示板块归属
        industries_map = await self._get_industry_for_stocks(symbols, sector_type)
        brokers_map = await self.repo.get_stock_brokers(month_date, symbols)

        items = []
        for row in rows:
            sym = row.symbol
            name = row.name
            industries = industries_map.get(sym, {}).get("industries", [])
            # 聚合同券商多 reason → reasons 数组（去空去重，不丢弃，LIMIT 100 兜底）
            brokers = self._aggregate_brokers(brokers_map.get(sym, []))
            items.append(
                {
                    "symbol": sym,
                    "name": name,
                    "industries": industries,
                    "broker_count": row.broker_count,
                    "brokers": brokers,
                }
            )

        return {
            "has_data": True,
            "month": month_date.isoformat(),
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def _aggregate_brokers(raw_brokers: list[dict]) -> list[dict]:
        """聚合同券商多 reason → {broker, reasons: string[]}（ADR-3）

        同券商多条 reason 合并为一个元素的 reasons 数组（去空去重，不丢弃）。
        单股百家推荐极端场景 LIMIT 100 兜底。
        """
        by_broker: dict[str, list[str]] = {}
        for item in raw_brokers:
            broker = item.get("broker")
            reason = item.get("reason")
            if not broker:
                continue
            if broker not in by_broker:
                by_broker[broker] = []
            if reason and reason not in by_broker[broker]:
                by_broker[broker].append(reason)

        result = [
            {"broker": broker, "reasons": reasons}
            for broker, reasons in by_broker.items()
        ]
        # LIMIT 100 兜底（单股百家极端）
        return result[:MAX_BROKERS_PER_STOCK]

    # ========== 券商维度分组（AC-04/06/07/12）==========

    async def get_broker_list(
        self,
        month: Optional[str],
        search: Optional[str],
        page: int,
        page_size: int,
    ) -> dict:
        """券商维度分组（按本月推荐股票数降序）"""
        latest = await self.repo.get_latest_month()
        month_date = self._resolve_month(month, latest)

        if month_date is None:
            return {
                "has_data": False,
                "month": None,
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }

        escaped_search = _escape_like_keyword(search.strip()) if search else None
        rows, total = await self.repo.get_broker_list(
            month_date, escaped_search, page, page_size
        )

        items = [
            {"broker": row.broker, "stock_count": row.stock_count}
            for row in rows
        ]

        return {
            "has_data": True,
            "month": month_date.isoformat(),
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ========== 券商明细懒加载（AC-13）==========

    async def get_broker_detail(self, month: str, broker: str) -> dict:
        """单券商本月推荐明细（懒加载）"""
        month_date = datetime.strptime(month, "%Y-%m-%d").date()
        rows = await self.repo.get_broker_detail(month_date, broker)

        # 同 symbol 多 reason 合并 → reasons 数组（去空去重，不丢弃）
        by_symbol: dict[str, dict] = {}
        symbols_order: list[str] = []
        for row in rows:
            sym = row.symbol
            if sym not in by_symbol:
                by_symbol[sym] = {"symbol": sym, "name": row.name, "reasons": []}
                symbols_order.append(sym)
            reason = row.reason
            if reason and reason not in by_symbol[sym]["reasons"]:
                by_symbol[sym]["reasons"].append(reason)

        items = [by_symbol[sym] for sym in symbols_order]
        return {"items": items}

    # ========== 板块排行榜（行业/概念/地域，各 Top5）==========

    async def get_sector_rankings(self, month: Optional[str]) -> dict:
        """三类型板块排行榜（各 Top5，按被推荐股票数降序）

        - 月份兜底（缺省取最新）；无数据返回 {has_data: false}
        - 独立计数：一股多板块在各归属板块各计 1 次（COUNT DISTINCT symbol）
        - concept 维度子串模糊排除交易机制类 + 指数成分类干扰概念
          （见 concept_exclusion.is_excluded_concept，覆盖"沪深300样本股"等命名变体）
        - percentage = stock_count / 该月不同被推荐股票总数
        """
        latest = await self.repo.get_latest_month()
        month_date = self._resolve_month(month, latest)

        if month_date is None:
            return {
                "has_data": False,
                "month": None,
                "industry": [],
                "concept": [],
                "region": [],
            }

        total_symbols = await self.repo.get_distinct_symbol_count(month_date)
        denominator = total_symbols if total_symbols > 0 else 1

        result: dict[str, list] = {}
        for sector_type in SECTOR_TYPES:
            rows = await self.repo.get_sector_ranking(
                month_date,
                sector_type,
                exclude_concepts=(sector_type == "concept"),
                limit=5,
            )
            result[sector_type] = [
                {
                    "sector_name": row.name,
                    "stock_count": row.stock_count,
                    "percentage": round(row.stock_count / denominator * 100, 4),
                }
                for row in rows
            ]

        return {
            "has_data": True,
            "month": month_date.isoformat(),
            **result,
        }
