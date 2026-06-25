"""
基金扎堆度聚合查询 Repository

专为 08 期「基金扎堆股票分析」新建的独立 Repository，只读聚合 04 期
fund_portfolio + funds + sectors + sector_stocks + stocks 数据，不引入缓存层 /
预计算表（ADR-6）。

复用声明：
- BaseRepository：src/repositories/base.py:18（泛型基类）
- FundPortfolio 模型：src/models/fund_portfolio.py（fund_ts_code/report_period/
  stock_symbol/stk_float_ratio 等字段已确认满足扎堆度聚合）
- Fund 模型：src/models/fund.py（JOIN 取 invest_type 做 scope 过滤）
- _get_industry_for_stocks JOIN 范式：src/services/shareholder_analysis_service.py:304-352
"""

from datetime import date
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.fund import Fund
from src.models.fund_portfolio import FundPortfolio
from src.models.sector import Sector
from src.models.sector_stock import SectorStock
from src.models.stock import Stock
from src.repositories.base import BaseRepository


class FundCrowdRepository(BaseRepository[FundPortfolio]):
    """基金扎堆度聚合查询 Repository（只读聚合，无写入操作）。"""

    def __init__(self, session: AsyncSession):
        super().__init__(FundPortfolio, session)

    async def get_report_periods(self, limit: int = 4) -> list[date]:
        """返回最近 N 个报告期降序（空表返回 []）。"""
        stmt = (
            select(FundPortfolio.report_period)
            .distinct()
            .order_by(FundPortfolio.report_period.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_crowd_aggregation(
        self,
        report_period: date,
        scope: str,
        passive_invest_types: tuple[str, ...],
        search: Optional[str] = None,
        escaped_search: Optional[str] = None,
    ) -> dict[str, dict]:
        """
        核心聚合方法（ADR-2 + ADR-1）。

        Args:
            report_period: 报告期
            scope: 基金口径（"active" / "all"）
            passive_invest_types: 被动型 invest_type 枚举（由 Service 层常量传入）
            search: 原始 search 关键词（仅用于判定是否触发过滤）
            escaped_search: 已转义 LIKE 通配符的 search 关键词

        Returns:
            { stock_symbol: { "fund_count": int } }
            空表 / 无匹配返回 {}

        护栏：
        - 持仓计入无阈值（ADR-2，存在即重仓）
        - 仅 A 股：length(stock_symbol)=6 排除港股（港股代码补齐5位，见 data_init_fund.py）
        - QDII 基金整体排除：fund_type IS DISTINCT FROM 'QDII'（兼容 NULL）
        - 主动型 = invest_type NOT IN (...) OR invest_type IS NULL（必须 .is_(None)）
        - 份额去重：fund_count = COUNT(DISTINCT regexp_replace(Fund.name, '[ACDEHIR]$', ''))
          （A/C/D/E/H/I/R 等份额后缀合并为同一基金）
        - search 在 SQL WHERE 层过滤（路径 A），保证分页 total 正确
        """
        stmt = (
            select(
                FundPortfolio.stock_symbol,
                # 份额去重：按基金名去份额后缀后再 DISTINCT 计数（PostgreSQL regexp_replace 透传）
                func.count(
                    func.distinct(
                        func.regexp_replace(Fund.name, "[ACDEHIR]$", "")
                    )
                ).label("fund_count"),
            )
            .select_from(FundPortfolio)
            .join(Fund, Fund.ts_code == FundPortfolio.fund_ts_code)
            .where(FundPortfolio.report_period == report_period)
            # 护栏：仅 A 股持仓计入扎堆，排除港股。
            #   A 股代码统一 6 位，港股代码补齐 5 位（见 data_init_fund.py 港股代码补齐5位）。
            .where(func.length(FundPortfolio.stock_symbol) == 6)
            # 护栏：排除 QDII 基金（投资海外的基金，持仓多为港股/美股，不应计入 A 股扎堆）。
            #   is_distinct_from 兼容 fund_type IS NULL（现有数据可能未填 fund_type，仍计入）。
            .where(Fund.fund_type.is_distinct_from("QDII"))
        )

        if scope == "active":
            # ADR-1：被动判定 = invest_type IN ('被动指数型', '增强指数型')；
            # 主动判定 = NOT IN (...) OR invest_type IS NULL（NULL 必须显式包含）
            stmt = stmt.where(
                or_(
                    Fund.invest_type.notin_(passive_invest_types),
                    Fund.invest_type.is_(None),
                )
            )
        # scope == "all"：无 invest_type 过滤

        if search and escaped_search is not None:
            # 路径 A：LEFT JOIN stocks 提前到聚合 SQL 中以支持 stock_name ILIKE
            stmt = stmt.outerjoin(Stock, Stock.symbol == FundPortfolio.stock_symbol)
            stmt = stmt.where(
                or_(
                    FundPortfolio.stock_symbol.like(f"{escaped_search}%", escape="\\"),
                    Stock.name.ilike(f"%{escaped_search}%", escape="\\"),
                )
            )

        stmt = stmt.group_by(FundPortfolio.stock_symbol)

        result = await self.session.execute(stmt)
        agg: dict[str, dict] = {}
        for symbol, fund_count in result.all():
            agg[symbol] = {
                "fund_count": int(fund_count or 0),
            }
        return agg

    async def get_industry_for_stocks(
        self, symbols: list[str]
    ) -> dict[str, list[str]]:
        """
        批量获取股票的行业关联（复用 06 _get_industry_for_stocks 范式）。

        一只股票可关联多个行业板块，全部返回（ADR-5）。
        stocks 表缺失的 symbol 在结果中不存在，由 Service 层兜底为 []。

        Returns:
            { symbol: [industry_name, ...] }
        """
        if not symbols:
            return {}

        stmt = (
            select(Stock.symbol, Sector.name)
            .select_from(Stock)
            .outerjoin(SectorStock, SectorStock.stock_code == Stock.symbol)
            .outerjoin(
                Sector,
                and_(Sector.code == SectorStock.sector_code, Sector.type == "industry"),
            )
            .where(Stock.symbol.in_(symbols))
        )
        result = await self.session.execute(stmt)

        mapping: dict[str, list[str]] = {}
        for symbol, industry_name in result.all():
            if symbol not in mapping:
                mapping[symbol] = []
            if industry_name and industry_name not in mapping[symbol]:
                mapping[symbol].append(industry_name)
        return mapping

    async def get_stock_names(
        self, symbols: list[str]
    ) -> dict[str, Optional[str]]:
        """
        批量取股票名（L2 降级：stocks 表缺失的 symbol 返回的 dict 缺该 key，
        Service 层 .get(symbol) 兜底 None → stockName=null）。

        Returns:
            { symbol: name | None }
        """
        if not symbols:
            return {}
        stmt = select(Stock.symbol, Stock.name).where(Stock.symbol.in_(symbols))
        result = await self.session.execute(stmt)
        return {symbol: name for symbol, name in result.all()}
