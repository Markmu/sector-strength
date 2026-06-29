"""券商月度金股聚合查询 Repository（plan-02）

封装 broker_recommend 表的聚合查询：股票维度排行、券商维度分组、券商明细、
月份列表。search 用 _escape_like_keyword 转义 %/_，参数绑定防注入。
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.broker_recommend import BrokerRecommend
from src.models.sector import Sector
from src.models.sector_stock import SectorStock
from src.models.stock import Stock
from src.repositories.base import BaseRepository
from src.services.concept_exclusion import is_excluded_concept
from src.services.shareholder_analysis_service import _escape_like_keyword

logger = logging.getLogger(__name__)


class BrokerRecommendRepository(BaseRepository[BrokerRecommend]):
    """券商月度金股聚合查询 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(BrokerRecommend, session)

    async def get_months(self) -> list[date]:
        """已同步月份列表（降序）"""
        result = await self.session.execute(
            select(BrokerRecommend.month)
            .distinct()
            .order_by(BrokerRecommend.month.desc())
        )
        return [row[0] for row in result.all()]

    async def get_latest_month(self) -> Optional[date]:
        """最新已同步月份（MAX(month)，YYYYMM 值最大者）"""
        months = await self.get_months()
        return months[0] if months else None

    async def get_stock_ranking(
        self,
        month: date,
        search: Optional[str],
        page: int,
        page_size: int,
        sector_type: Optional[str] = None,
        sector_name: Optional[str] = None,
    ) -> tuple[list, int]:
        """股票维度排行（AC-02/06/07/11）

        GROUP BY symbol + COUNT(DISTINCT broker)，按 broker_count DESC, symbol ASC。
        search: symbol 前缀匹配 OR name 包含匹配（_escape_like_keyword 转义）。
        sector_name 有值时：JOIN SectorStock + Sector（按 sector_type），inner join
        限定到归属该板块的股票；无值时保持原 LEFT JOIN Stock。
        返回 (rows, total)，total = 符合条件的不同 symbol 总数。
        """
        broker_count = func.count(func.distinct(BrokerRecommend.broker)).label(
            "broker_count"
        )

        # 公共 WHERE 子句
        conditions = [BrokerRecommend.month == month]
        if search:
            escaped = _escape_like_keyword(search)
            conditions.append(
                or_(
                    BrokerRecommend.symbol.like(escaped + "%"),
                    Stock.name.ilike("%" + escaped + "%"),
                )
            )
        # 板块过滤（sector_name 有值才生效）
        if sector_name and sector_type:
            conditions.append(Sector.type == sector_type)
            conditions.append(Sector.name == sector_name)

        def _build_stock_select(symbol_only: bool):
            """构建主/total 用的 select（统一 join 链路）。

            symbol_only=True 时只选 symbol（total 子查询用）；False 时选 symbol/name/broker_count。
            """
            if symbol_only:
                cols: tuple = (BrokerRecommend.symbol,)
            else:
                cols = (
                    BrokerRecommend.symbol,
                    func.max(Stock.name).label("name"),
                    broker_count,
                )
            stmt = select(*cols).select_from(BrokerRecommend)
            # 股票名 JOIN（始终 LEFT JOIN，name 用 MAX 聚合）
            stmt = stmt.outerjoin(Stock, Stock.symbol == BrokerRecommend.symbol)
            # 板块过滤 JOIN（sector_name 有值时 inner join）
            if sector_name and sector_type:
                stmt = stmt.join(
                    SectorStock,
                    SectorStock.stock_code == BrokerRecommend.symbol,
                ).join(
                    Sector,
                    and_(
                        Sector.code == SectorStock.sector_code,
                        Sector.type == sector_type,
                    ),
                )
            stmt = stmt.where(*conditions)
            return stmt

        # 主查询（分页 + 排序）
        main_stmt = (
            _build_stock_select(symbol_only=False)
            .group_by(BrokerRecommend.symbol)
            .order_by(broker_count.desc(), BrokerRecommend.symbol.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows_result = await self.session.execute(main_stmt)
        rows = rows_result.all()

        # total 查询（符合条件的不同 symbol 数）
        total_stmt = (
            select(func.count())
            .select_from(
                _build_stock_select(symbol_only=True)
                .group_by(BrokerRecommend.symbol)
                .subquery()
            )
        )
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar_one()

        return rows, total

    async def get_stock_brokers(
        self, month: date, symbols: list[str]
    ) -> dict[str, list[dict]]:
        """预加载（ADR-3）：批量获取多只股票的推荐券商+理由

        返回 {symbol: [{broker, reason}, ...]}（同券商多 reason 由 service 层归并）。
        """
        if not symbols:
            return {}
        result = await self.session.execute(
            select(
                BrokerRecommend.symbol,
                BrokerRecommend.broker,
                BrokerRecommend.reason,
            )
            .where(
                BrokerRecommend.month == month,
                BrokerRecommend.symbol.in_(symbols),
            )
        )
        mapping: dict[str, list[dict]] = {s: [] for s in symbols}
        for row in result.all():
            sym, broker, reason = row[0], row[1], row[2]
            if sym not in mapping:
                mapping[sym] = []
            mapping[sym].append({"broker": broker, "reason": reason})
        return mapping

    async def get_broker_list(
        self,
        month: date,
        search: Optional[str],
        page: int,
        page_size: int,
    ) -> tuple[list, int]:
        """券商维度分组（AC-04/06/07/12）

        GROUP BY broker + COUNT(DISTINCT symbol)，按 stock_count DESC, broker ASC。
        返回 (rows, total)。
        """
        stock_count = func.count(func.distinct(BrokerRecommend.symbol)).label(
            "stock_count"
        )

        conditions = [BrokerRecommend.month == month]
        if search:
            escaped = _escape_like_keyword(search)
            conditions.append(BrokerRecommend.broker.ilike("%" + escaped + "%"))

        main_stmt = (
            select(BrokerRecommend.broker, stock_count)
            .where(*conditions)
            .group_by(BrokerRecommend.broker)
            .order_by(stock_count.desc(), BrokerRecommend.broker.asc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows_result = await self.session.execute(main_stmt)
        rows = rows_result.all()

        total_stmt = (
            select(func.count())
            .select_from(
                select(BrokerRecommend.broker)
                .where(*conditions)
                .group_by(BrokerRecommend.broker)
                .subquery()
            )
        )
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar_one()

        return rows, total

    async def get_broker_detail(self, month: date, broker: str) -> list:
        """券商明细（AC-13，懒加载）

        broker 精确匹配（=，不做 LIKE 避免误匹配），按 symbol 升序。
        返回 rows: [(symbol, name, reason), ...]（同 symbol 多 reason 由 service 归并）。
        """
        result = await self.session.execute(
            select(
                BrokerRecommend.symbol,
                Stock.name,
                BrokerRecommend.reason,
            )
            .select_from(BrokerRecommend)
            .outerjoin(Stock, Stock.symbol == BrokerRecommend.symbol)
            .where(
                BrokerRecommend.month == month,
                BrokerRecommend.broker == broker,
            )
            .order_by(BrokerRecommend.symbol.asc())
        )
        return result.all()

    async def get_distinct_symbol_count(self, month: date) -> int:
        """该月不同被推荐股票总数（板块占比的分母）"""
        result = await self.session.execute(
            select(func.count(func.distinct(BrokerRecommend.symbol))).where(
                BrokerRecommend.month == month
            )
        )
        return result.scalar_one()

    async def get_sector_ranking(
        self,
        month: date,
        sector_type: str,
        exclude_concepts: bool = False,
        limit: int = 5,
    ) -> list:
        """板块排行榜：按 sector_type 维度统计被推荐股票数，降序取 Top N

        JOIN BrokerRecommend → SectorStock → Sector（按 type 过滤），inner join
        （只统计有板块归属的股票）。
        GROUP BY Sector.name，COUNT(DISTINCT BrokerRecommend.symbol)。
        exclude_concepts=True 时（concept 维度）用 is_excluded_concept 子串模糊匹配
        排除交易机制类 + 指数成分类干扰概念。

        返回 rows: [(sector_name, stock_count), ...]，按 stock_count DESC, name ASC，limit 条。
        """
        stock_count = func.count(func.distinct(BrokerRecommend.symbol)).label(
            "stock_count"
        )
        stmt = (
            select(Sector.name, stock_count)
            .select_from(BrokerRecommend)
            .join(
                SectorStock, SectorStock.stock_code == BrokerRecommend.symbol
            )
            .join(
                Sector,
                and_(
                    Sector.code == SectorStock.sector_code,
                    Sector.type == sector_type,
                ),
            )
            .where(BrokerRecommend.month == month)
            .group_by(Sector.name)
            .order_by(stock_count.desc(), Sector.name.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # 内存层过滤干扰概念（concept 维度子串模糊匹配，见 concept_exclusion.is_excluded_concept）
        if exclude_concepts:
            rows = [r for r in rows if not is_excluded_concept(r.name)]

        # 过滤后再截断 limit（避免被排除项挤掉有效 Top N）
        return rows[:limit]

