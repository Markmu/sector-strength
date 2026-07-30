"""ETF 监控查询服务（第 14 期 plan-03）

提供按跟踪指数聚合的 ETF 监控查询：指数排行（group by index_name + SUM）、
指数明细、历史趋势、最新交易日。所有方法返回 snake_case dict，
由路由层 ``_dict_to_camel`` 转 camelCase。

复用声明：
- Service 构造范式：``src/services/sector_fund_flow_service.py``（service 层直接用
  SQLAlchemy Core，不走 Repository；``__init__(session)`` 持有 AsyncSession）
- JOIN 聚合范式：架构 §6.3/§6.4 查询链路

契约（架构 §6.3/§6.4/§6.5 + §7.2 输出视角 + plan-03 §3 #1）：
- ``get_index_rankings``：JOIN etf_daily + etf_basic 筛 category + trade_date，
  按 index_name 分组 SUM/COUNT，sort_by 参数值 camelCase，分页。
- ``get_index_detail``：JOIN 筛 index_name + category + trade_date，按 netInflow 降序。
- ``get_trend``：取 trade_date <= end_date 的最近 N 个交易日；index 类型先筛该指数
  ts_code 集合再取交易日并集（P-08 修正）；按 trade_date 升序。
- ``get_latest_date``：取该 category 下 etf_daily 最大 trade_date。

单位换算（架构 §7.6）：份额存储万份、API 输出 ÷10000 转亿份；net_inflow 已亿元直接 SUM。
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy import asc, desc, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.etf import EtfBasic, EtfDaily

logger = logging.getLogger(__name__)

# 份额万份 → 亿份换算系数（架构 §7.6）
_SHARE_FACTOR = 10000

# sort_by 白名单（参数值 camelCase，架构 §7.6 特例；非法值回退默认 netInflow）
# 映射到分组聚合列（ sqlalchemy Column 对象在聚合 select 里需引用 func 包装后的列，
# 这里用字符串 key 由方法内解析，避免在定义期引用 select 中聚合列）
_RANK_SORT_KEYS = {"netInflow", "shareChange", "share"}
_DEFAULT_RANK_SORT_BY = "netInflow"
_DEFAULT_ORDER = "desc"


class EtfMonitorService:
    """ETF 监控查询服务（指数排行/明细/趋势/最新日期）。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============== public API ==============

    async def get_index_rankings(
        self,
        category: str = "broad",
        trade_date: Optional[date] = None,
        sort_by: str = _DEFAULT_RANK_SORT_BY,
        order: str = _DEFAULT_ORDER,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """
        指数排行（架构 §6.3 + plan-03 §3 #1）。

        JOIN etf_daily + etf_basic（ts_code），筛 category + trade_date，按
        etf_basic.index_name 分组：COUNT(ts_code) 得 etfCount，SUM(share) 得
        totalShare，SUM(share_change) 得 totalShareChange，SUM(net_inflow) 得
        totalNetInflow。sort_by 参数值 camelCase（netInflow/shareChange/share）。

        单位换算：聚合在万份口径 SUM 后，输出 ÷10000 转亿份；net_inflow 已亿元直接 SUM。

        边界场景：
        - trade_date 未传 → 默认取 latest_date；无数据 → has_data=False
        - sort_by 非法值 → 容错为默认 netInflow
        - 分页超出范围 → 返回空 items + 正确 total

        Returns:
            {
                "has_data", "trade_date",
                "items": [{
                    "index_name", "category", "etf_count",
                    "total_share", "total_share_change", "total_net_inflow"
                }],
                "total", "page", "page_size"
            }
        """
        logger.info(
            "get_index_rankings called, category=%s, trade_date=%s, sort_by=%s, order=%s, page=%d, page_size=%d",
            category, trade_date, sort_by, order, page, page_size,
        )

        # trade_date 默认取最新日期
        if trade_date is None:
            trade_date = await self._get_latest_date_value(category)
        if trade_date is None:
            logger.info("get_index_rankings: no data for category=%s", category)
            return {
                "has_data": False,
                "trade_date": None,
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }

        # sort_by 容错：非法值回退默认
        if sort_by not in _RANK_SORT_KEYS:
            sort_by = _DEFAULT_RANK_SORT_BY

        # 分组聚合：JOIN etf_daily + etf_basic，按 index_name 分组
        # share/share_change 万份口径 SUM 后 ÷10000 转亿份；net_inflow 已亿元。
        # 先聚合到子查询，再外层 SELECT + ORDER BY + 分页，避免 ORDER BY 引用聚合列
        # 时出现 "missing FROM-clause entry"（外层可安全引用 subq.c.*）。
        agg_subq = (
            select(
                EtfBasic.index_name.label("index_name"),
                EtfBasic.category.label("category"),
                func.count(EtfDaily.ts_code).label("etf_count"),
                (func.sum(EtfDaily.share) / _SHARE_FACTOR).label("total_share"),
                (func.sum(EtfDaily.share_change) / _SHARE_FACTOR).label("total_share_change"),
                func.sum(EtfDaily.net_inflow).label("total_net_inflow"),
            )
            .join(EtfBasic, EtfDaily.ts_code == EtfBasic.ts_code)
            .where(
                EtfDaily.trade_date == trade_date,
                EtfBasic.category == category,
                EtfBasic.index_name.isnot(None),
            )
            .group_by(EtfBasic.index_name, EtfBasic.category)
        ).subquery()

        # total：分组前的指数数（子查询 count）
        count_stmt = select(func.count()).select_from(agg_subq)
        total = (await self.session.execute(count_stmt)).scalar_one()

        # 排序：sort_by 映射到聚合列（外层引用 subq.c.*）
        sort_col_map = {
            "netInflow": agg_subq.c.total_net_inflow,
            "shareChange": agg_subq.c.total_share_change,
            "share": agg_subq.c.total_share,
        }
        sort_col = sort_col_map[sort_by]

        outer = select(
            agg_subq.c.index_name,
            agg_subq.c.category,
            agg_subq.c.etf_count,
            agg_subq.c.total_share,
            agg_subq.c.total_share_change,
            agg_subq.c.total_net_inflow,
        )
        if order == "asc":
            outer = outer.order_by(asc(sort_col), asc(agg_subq.c.index_name))
        else:
            outer = outer.order_by(desc(sort_col), asc(agg_subq.c.index_name))

        # 分页
        offset = (page - 1) * page_size
        outer = outer.limit(page_size).offset(offset)

        result = await self.session.execute(outer)
        rows = result.all()

        items = [
            {
                "index_name": row.index_name,
                "category": row.category,
                "etf_count": row.etf_count,
                "total_share": row.total_share,
                "total_share_change": row.total_share_change,
                "total_net_inflow": row.total_net_inflow,
            }
            for row in rows
        ]

        return {
            "has_data": total > 0,
            "trade_date": trade_date,
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_index_detail(
        self,
        index_name: str,
        category: Optional[str] = None,
        trade_date: Optional[date] = None,
    ) -> dict:
        """
        指数明细（架构 §6.4 + plan-03 §3 #1）。

        JOIN etf_daily + etf_basic，筛 index_name（+ category + trade_date），
        返回该指数下的 ETF 明细，按 netInflow 降序。份额输出 ÷10000 亿份。

        边界场景：
        - trade_date 未传 → 默认取 latest_date；无数据 → has_data=False + 空 items
        - index_name 含特殊字符 → SQLAlchemy 参数化查询防注入

        Returns:
            {
                "has_data", "trade_date",
                "items": [{
                    "ts_code", "name", "unit_nav", "share", "share_change",
                    "net_inflow", "change_percent"
                }]
            }
        """
        logger.info(
            "get_index_detail called, index_name=%s, category=%s, trade_date=%s",
            index_name, category, trade_date,
        )

        if not index_name:
            return {"has_data": False, "trade_date": None, "items": []}

        # trade_date 默认取最新日期
        if trade_date is None:
            trade_date = await self._get_latest_date_value(category)

        filters = [
            EtfBasic.index_name == index_name,
            EtfBasic.index_name.isnot(None),
            EtfDaily.ts_code == EtfBasic.ts_code,
        ]
        if category is not None:
            filters.append(EtfBasic.category == category)
        if trade_date is not None:
            filters.append(EtfDaily.trade_date == trade_date)

        stmt = (
            select(
                EtfDaily.ts_code.label("ts_code"),
                EtfBasic.name.label("name"),
                EtfDaily.unit_nav.label("unit_nav"),
                (EtfDaily.share / _SHARE_FACTOR).label("share"),
                (EtfDaily.share_change / _SHARE_FACTOR).label("share_change"),
                EtfDaily.net_inflow.label("net_inflow"),
                EtfDaily.change_percent.label("change_percent"),
            )
            .join(EtfBasic, EtfDaily.ts_code == EtfBasic.ts_code)
            .where(and_(*filters))
            .order_by(desc(EtfDaily.net_inflow))
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            return {
                "has_data": False,
                "trade_date": trade_date,
                "items": [],
            }

        items = [
            {
                "ts_code": row.ts_code,
                "name": row.name,
                "unit_nav": row.unit_nav,
                "share": row.share,
                "share_change": row.share_change,
                "net_inflow": row.net_inflow,
                "change_percent": row.change_percent,
            }
            for row in rows
        ]

        return {
            "has_data": True,
            "trade_date": trade_date,
            "items": items,
        }

    async def get_trend(
        self,
        target_type: str,
        target_code: str,
        metric: str,
        days: int = 30,
        end_date: Optional[date] = None,
    ) -> dict:
        """
        历史趋势（架构 §6.5 + plan-03 §3 #1）。

        取 etf_daily 中 trade_date <= end_date 的最近 ``days`` 个交易日（实际有数据的
        交易日，非日历日），按 metric 取值，trade_date 升序返回。

        - target_type='index'（P-08 修正）：先 JOIN etf_basic 筛 index_name 得该指数的
          ts_code 集合，再取该集合在 etf_daily 中 trade_date <= end_date 的最近 N 个
          distinct 交易日（取该指数全量 ETF 交易日的并集，避免取成全表交易日导致 series
          长度偏差），最后在该 N 日内按 index_name 聚合 SUM。
        - target_type='etf'：按 ts_code 取单只，取该 ts_code 的最近 N 个交易日。
        - metric='share'：取 share（输出亿份 ÷10000）；metric='netInflow'：取 net_inflow（亿元）。

        边界场景：
        - target_code 不存在 / 完全无数据点 → has_data=False + 空 series（架构 §6.5）
        - 历史不足区间 → 返回实际有数据点（少于 N）
        - end_date 未传 → 默认取全表最新交易日

        Returns:
            {"has_data", "metric", "unit", "series": [{"trade_date", "value"}]}
        """
        logger.info(
            "get_trend called, target_type=%s, target_code=%s, metric=%s, days=%d, end_date=%s",
            target_type, target_code, metric, days, end_date,
        )

        # 参数校验 / 默认值
        if target_type not in ("index", "etf"):
            return {"has_data": False, "metric": metric, "unit": None, "series": []}
        if not target_code:
            return {"has_data": False, "metric": metric, "unit": None, "series": []}

        # metric 容错：非法值回退默认 netInflow
        if metric not in ("share", "netInflow"):
            metric = "netInflow"

        # end_date 默认取全表最新交易日
        if end_date is None:
            end_date = await self._get_global_latest_date_value()
        if end_date is None:
            return {
                "has_data": False,
                "metric": metric,
                "unit": self._metric_unit(metric),
                "series": [],
            }

        days = max(1, days)

        # 确定参与聚合的 ts_code 集合
        if target_type == "index":
            # 先 JOIN etf_basic 筛 index_name 得该指数的 ts_code 集合
            ts_codes = await self._get_index_ts_codes(target_code)
            if not ts_codes:
                return {
                    "has_data": False,
                    "metric": metric,
                    "unit": self._metric_unit(metric),
                    "series": [],
                }
        else:
            ts_codes = [target_code]

        # 取该 ts_code 集合在 trade_date <= end_date 的最近 N 个 distinct 交易日
        # （取集合交易日的并集，避免取全表交易日）
        date_stmt = (
            select(EtfDaily.trade_date)
            .where(
                EtfDaily.trade_date <= end_date,
                EtfDaily.ts_code.in_(ts_codes),
            )
            .group_by(EtfDaily.trade_date)
            .order_by(desc(EtfDaily.trade_date))
            .limit(days)
        )
        date_rows = (await self.session.execute(date_stmt)).scalars().all()
        if not date_rows:
            return {
                "has_data": False,
                "metric": metric,
                "unit": self._metric_unit(metric),
                "series": [],
            }
        trade_dates = set(date_rows)

        # 在该 N 日内按 ts_code 集合聚合
        if metric == "share":
            value_expr = func.sum(EtfDaily.share) / _SHARE_FACTOR
        else:  # netInflow（已亿元）
            value_expr = func.sum(EtfDaily.net_inflow)

        agg_stmt = (
            select(
                EtfDaily.trade_date.label("trade_date"),
                value_expr.label("value"),
            )
            .where(
                EtfDaily.trade_date.in_(trade_dates),
                EtfDaily.ts_code.in_(ts_codes),
            )
            .group_by(EtfDaily.trade_date)
            .order_by(asc(EtfDaily.trade_date))
        )
        agg_rows = (await self.session.execute(agg_stmt)).all()
        if not agg_rows:
            return {
                "has_data": False,
                "metric": metric,
                "unit": self._metric_unit(metric),
                "series": [],
            }

        series = [
            {"trade_date": row.trade_date, "value": row.value}
            for row in agg_rows
        ]

        return {
            "has_data": True,
            "metric": metric,
            "unit": self._metric_unit(metric),
            "series": series,
        }

    async def get_latest_date(self, category: str = "broad") -> dict:
        """
        最新交易日（plan-03 §3 #1）。

        返回该 category 下 etf_daily 最大 trade_date（通过 JOIN etf_basic 按 category 筛选）。

        Returns:
            {"has_data", "trade_date"}
        """
        logger.info("get_latest_date called, category=%s", category)
        latest = await self._get_latest_date_value(category)
        return {
            "has_data": latest is not None,
            "trade_date": latest,
        }

    # ============== private helpers ==============

    async def _get_latest_date_value(self, category: Optional[str]) -> Optional[date]:
        """取该 category 下 etf_daily 最大 trade_date（JOIN etf_basic 按 category 筛选）。

        category 为 None 时退化为全表 MAX(trade_date)。
        """
        if category is None:
            stmt = select(func.max(EtfDaily.trade_date))
        else:
            stmt = (
                select(func.max(EtfDaily.trade_date))
                .join(EtfBasic, EtfDaily.ts_code == EtfBasic.ts_code)
                .where(EtfBasic.category == category)
            )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _get_global_latest_date_value(self) -> Optional[date]:
        """全表 MAX(trade_date)（不限 category）。"""
        stmt = select(func.max(EtfDaily.trade_date))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _get_index_ts_codes(self, index_name: str) -> list[str]:
        """取该 index_name 归集的所有 ts_code 集合（从 etf_basic）。"""
        stmt = select(EtfBasic.ts_code).where(EtfBasic.index_name == index_name)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [r for r in rows if r]

    @staticmethod
    def _metric_unit(metric: str) -> str:
        """metric → 单位文案（架构 §7.2 输出视角）。"""
        return "亿份" if metric == "share" else "亿元"
