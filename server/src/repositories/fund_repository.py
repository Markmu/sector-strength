"""
基金数据访问仓库

提供基金相关的数据库查询操作。
"""

from typing import Any

from sqlalchemy import select, func, exists, and_, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import label

from src.models.fund import Fund
from src.models.fund_portfolio import FundPortfolio
from src.models.stock import Stock
from src.repositories.base import BaseRepository


class FundRepository(BaseRepository[Fund]):
    """
    基金数据仓库

    继承 BaseRepository，提供基金相关的数据访问方法。
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Fund, session)

    async def list_with_filters(
        self,
        search: str | None = None,
        market: list[str] | None = None,
        fund_type: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """
        基金列表查询（含搜索、过滤、分页、L1 降级 has_portfolio 标记）

        Args:
            search: 搜索关键词（ts_code 前缀匹配 OR name 包含匹配，ilike 不区分大小写）
            market: 市场类型过滤列表（E=场内, O=场外）
            fund_type: 基金类型过滤列表（任一匹配即命中）
            page: 页码（从 1 开始）
            page_size: 每页数量

        Returns:
            (items, total) — items 为字典列表（含 has_portfolio 字段），total 为总数
        """
        # L1 降级：EXISTS 子查询判断是否有持仓记录
        has_portfolio_subq = (
            select(literal_column("1"))
            .select_from(FundPortfolio)
            .where(FundPortfolio.fund_ts_code == Fund.ts_code)
            .correlate(Fund)
        )

        # 主查询：Fund 字段 + has_portfolio 标记
        stmt = select(
            Fund,
            label("has_portfolio", exists(has_portfolio_subq)),
        )

        # WHERE 子句
        conditions = []
        if search:
            search_ilike = f"%{search}%"
            conditions.append(
                (Fund.ts_code.ilike(f"{search}%")) | (Fund.name.ilike(search_ilike))
            )
        if market:
            conditions.append(Fund.market.in_(market))
        if fund_type:
            conditions.append(Fund.fund_type.in_(fund_type))

        if conditions:
            stmt = stmt.where(*conditions)

        # ORDER BY ts_code ASC
        stmt = stmt.order_by(Fund.ts_code.asc())

        # 计算总数
        count_subq = stmt.subquery()
        count_stmt = select(func.count()).select_from(count_subq)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # 执行查询
        result = await self.session.execute(stmt)
        rows = result.all()

        # 转换为字典列表
        items = []
        for row in rows:
            fund = row[0]
            has_portfolio = row[1]
            items.append({
                "ts_code": fund.ts_code,
                "name": fund.name,
                "management": fund.management,
                "custodian": fund.custodian,
                "fund_type": fund.fund_type,
                "invest_type": fund.invest_type,
                "benchmark": fund.benchmark,
                "market": fund.market,
                "found_date": fund.found_date,
                "list_date": fund.list_date,
                "delist_date": fund.delist_date,
                "status": fund.status,
                "has_portfolio": has_portfolio,
            })

        return items, total

    async def get_by_ts_code(self, ts_code: str) -> Fund | None:
        """
        根据业务键 ts_code 查询基金

        Args:
            ts_code: 基金 TS 代码

        Returns:
            Fund 对象或 None
        """
        stmt = select(Fund).where(Fund.ts_code == ts_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_portfolio(
        self,
        fund_ts_code: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int, dict]:
        """
        获取基金最新报告期持仓明细

        含元信息：is_portfolio_empty, has_portfolio, latest_report_period, latest_ann_date

        Args:
            fund_ts_code: 基金 TS 代码
            page: 页码
            page_size: 每页数量

        Returns:
            (items, total, meta) — items 为字典列表，total 为最新期持仓数，meta 为元信息字典
        """
        # 元信息查询
        # 1. has_portfolio: 该基金是否有任何历史持仓记录
        has_portfolio_stmt = select(
            exists(
                select(literal_column("1"))
                .select_from(FundPortfolio)
                .where(FundPortfolio.fund_ts_code == fund_ts_code)
            )
        )
        has_portfolio_result = await self.session.execute(has_portfolio_stmt)
        has_portfolio = has_portfolio_result.scalar() or False

        # 2. latest_report_period: 该基金最新已有报告期
        latest_period_stmt = select(
            func.max(FundPortfolio.report_period)
        ).where(FundPortfolio.fund_ts_code == fund_ts_code)
        latest_period_result = await self.session.execute(latest_period_stmt)
        latest_report_period = latest_period_result.scalar()

        # 3. latest_ann_date: 最新报告期的公告日（按 ann_date DESC 取最新）
        latest_ann_date = None
        if latest_report_period is not None:
            ann_date_stmt = (
                select(FundPortfolio.ann_date)
                .where(
                    and_(
                        FundPortfolio.fund_ts_code == fund_ts_code,
                        FundPortfolio.report_period == latest_report_period,
                    )
                )
                .order_by(FundPortfolio.ann_date.desc().nulls_last())
                .limit(1)
            )
            ann_date_result = await self.session.execute(ann_date_stmt)
            latest_ann_date = ann_date_result.scalar()

        # 主查询：最新报告期持仓明细 + LEFT JOIN stocks 取 stock_name
        latest_period_subq = (
            select(func.max(FundPortfolio.report_period))
            .where(FundPortfolio.fund_ts_code == fund_ts_code)
            .scalar_subquery()
        )

        stmt = (
            select(
                FundPortfolio,
                Stock.name.label("stock_name"),
            )
            .outerjoin(
                Stock,
                Stock.symbol == FundPortfolio.stock_symbol,
            )
            .where(
                and_(
                    FundPortfolio.fund_ts_code == fund_ts_code,
                    FundPortfolio.report_period == latest_period_subq,
                )
            )
            .order_by(FundPortfolio.stk_mkv_ratio.desc().nulls_last())
        )

        # 计算总数
        count_subq = stmt.subquery()
        count_stmt = select(func.count()).select_from(count_subq)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # 执行查询
        result = await self.session.execute(stmt)
        rows = result.all()

        # 转换为字典列表
        items = []
        for row in rows:
            portfolio = row[0]
            stock_name = row[1]
            items.append({
                "fund_ts_code": portfolio.fund_ts_code,
                "report_period": portfolio.report_period,
                "ann_date": portfolio.ann_date,
                "stock_symbol": portfolio.stock_symbol,
                "stock_name": stock_name,
                "market_value": portfolio.market_value,
                "amount": portfolio.amount,
                "stk_mkv_ratio": portfolio.stk_mkv_ratio,
                "stk_float_ratio": portfolio.stk_float_ratio,
            })

        # 元信息
        is_portfolio_empty = total == 0
        meta = {
            "is_portfolio_empty": is_portfolio_empty,
            "has_portfolio": has_portfolio,
            "latest_report_period": latest_report_period,
            "latest_ann_date": latest_ann_date,
        }

        return items, total, meta

    async def reverse_lookup(
        self,
        symbol: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int, dict]:
        """
        股票反查：查询重仓该股票的基金列表

        仅返回 stk_mkv_ratio >= 1.0 的记录，按 stk_mkv_ratio DESC 排序。
        附带元信息：stock_name, report_period

        Args:
            symbol: 股票代码（接受纯数字如 "600519" 或带后缀如 "600519.SH"）
            page: 页码
            page_size: 每页数量

        Returns:
            (items, total, meta) — items 为字典列表，total 为总数，meta 为元信息
        """
        # symbol 格式归一化：去除后缀，保留纯数字部分
        normalized_symbol = symbol.split(".")[0] if "." in symbol else symbol

        # 查询 stocks 表确认 symbol 存在并获取 stock_name
        stock_stmt = select(Stock).where(Stock.symbol == normalized_symbol)
        stock_result = await self.session.execute(stock_stmt)
        stock = stock_result.scalar_one_or_none()

        if not stock:
            return [], 0, {"stock_name": None, "report_period": None}

        stock_name = stock.name

        # 主查询：stk_mkv_ratio >= 1.0 + 最新报告期
        # 取全局最新报告期
        global_latest_period_subq = (
            select(func.max(FundPortfolio.report_period))
            .scalar_subquery()
        )

        # 同时获取该 symbol 对应的最新报告期（用于元信息）
        symbol_latest_period_stmt = (
            select(func.max(FundPortfolio.report_period))
            .where(FundPortfolio.stock_symbol == normalized_symbol)
        )
        symbol_latest_period_result = await self.session.execute(symbol_latest_period_stmt)
        report_period = symbol_latest_period_result.scalar()

        stmt = (
            select(
                FundPortfolio,
                Fund.name.label("fund_name"),
                Fund.fund_type.label("fund_type"),
                Fund.management.label("management"),
            )
            .join(
                Fund,
                Fund.ts_code == FundPortfolio.fund_ts_code,
            )
            .where(
                and_(
                    FundPortfolio.stock_symbol == normalized_symbol,
                    FundPortfolio.stk_mkv_ratio >= 1.0,
                    FundPortfolio.report_period == global_latest_period_subq,
                )
            )
            .order_by(FundPortfolio.stk_mkv_ratio.desc().nulls_last())
        )

        # 计算总数
        count_subq = stmt.subquery()
        count_stmt = select(func.count()).select_from(count_subq)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        # 执行查询
        result = await self.session.execute(stmt)
        rows = result.all()

        # 转换为字典列表
        items = []
        for row in rows:
            portfolio = row[0]
            fund_name = row[1]
            fund_type = row[2]
            management = row[3]
            items.append({
                "fund_ts_code": portfolio.fund_ts_code,
                "fund_name": fund_name,
                "fund_type": fund_type,
                "management": management,
                "stock_symbol": portfolio.stock_symbol,
                "report_period": portfolio.report_period,
                "stk_mkv_ratio": portfolio.stk_mkv_ratio,
                "stk_float_ratio": portfolio.stk_float_ratio,
                "market_value": portfolio.market_value,
                "amount": portfolio.amount,
            })

        meta = {
            "stock_name": stock_name,
            "report_period": report_period,
        }

        return items, total, meta
