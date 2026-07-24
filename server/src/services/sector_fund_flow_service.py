"""
板块资金流查询服务

提供板块资金流排行（最新采样点）、盘中变化曲线（时间序列）、最新交易日查询。
所有方法返回 snake_case dict，由路由层 _dict_to_camel 转 camelCase。

复用声明：
- Service 构造范式：src/services/fund_crowd_analysis_service.py:44（__init__(session)）
- 最新采样点子查询：架构 §6.2 排行链路（每 sector_name 取 MAX(sample_time)）
- LEFT JOIN sectors 取 sector_id：src/models/sector.py:12（sectors.name 有索引）

契约（架构 §6.2/§6.3 + plan-02 §3）：
- get_rankings：返回最新采样点排行，按净额/流入/流出排序 + 分页
- get_timeseries：按板块名分组返回 sample_time 升序的净额序列
- get_latest_date：返回 MAX(trade_date)（YYYY-MM-DD 或 null）
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy import desc, asc, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.sector_fund_flow import SectorFundFlow

logger = logging.getLogger(__name__)

# 排序字段白名单（防注入 + 容错：非法值回退默认 net_inflow）
_SORT_COLUMN_MAP = {
    "net_inflow": SectorFundFlow.net_inflow,
    "inflow": SectorFundFlow.inflow,
    "outflow": SectorFundFlow.outflow,
}
_DEFAULT_SORT_BY = "net_inflow"
_DEFAULT_ORDER = "desc"


class SectorFundFlowService:
    """板块资金流查询服务（排行/曲线/最新日期）。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============== public API ==============

    async def get_rankings(
        self,
        sector_type: str = "industry",
        trade_date: Optional[date] = None,
        sort_by: str = _DEFAULT_SORT_BY,
        order: str = _DEFAULT_ORDER,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """
        板块资金流排行榜（架构 §6.2 + plan-02 §3 #1）。

        取该 trade_date + sector_type 下每个 sector_name 的最新采样点，
        LEFT JOIN sectors 取 sector_id（匹配不上为 null），按指定字段排序后分页。
        rank 按当前排序结果的全局序号编号（offset + 页内序号 + 1）。

        边界场景：
        - trade_date 未传 → 默认取 latest_date；无数据 → has_data=False
        - sort_by 非法值 → 容错为默认 net_inflow
        - order 非 asc → 默认 desc

        Returns:
            {
                "has_data", "trade_date", "items": [{
                    "rank", "sector_name", "sector_id", "change_percent",
                    "inflow", "outflow", "net_inflow", "company_count",
                    "leading_stock", "leading_stock_change", "current_price"
                }], "total", "page", "page_size"
            }
        """
        logger.info(
            "get_rankings called, sector_type=%s, trade_date=%s, sort_by=%s, order=%s, page=%d, page_size=%d",
            sector_type,
            trade_date,
            sort_by,
            order,
            page,
            page_size,
        )

        # trade_date 默认取最新日期
        if trade_date is None:
            trade_date = await self._get_latest_date_value(sector_type)
        if trade_date is None:
            logger.info("get_rankings: no data for sector_type=%s", sector_type)
            return {
                "has_data": False,
                "trade_date": None,
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }

        # 子查询：每 sector_name 的最新采样点（走 idx_sff_date_type_name_time）
        latest_subq = (
            select(
                SectorFundFlow.sector_name.label("sub_sector_name"),
                func.max(SectorFundFlow.sample_time).label("max_sample_time"),
            )
            .where(
                SectorFundFlow.trade_date == trade_date,
                SectorFundFlow.sector_type == sector_type,
            )
            .group_by(SectorFundFlow.sector_name)
            .subquery()
        )

        # 主查询：JOIN 子查询锁定最新采样点，LEFT JOIN sectors 取 sector_id
        stmt = (
            select(
                SectorFundFlow,
                Sector.id.label("sector_id"),
            )
            .join(
                latest_subq,
                and_(
                    SectorFundFlow.sector_name == latest_subq.c.sub_sector_name,
                    SectorFundFlow.sample_time == latest_subq.c.max_sample_time,
                ),
            )
            .outerjoin(Sector, Sector.name == SectorFundFlow.sector_name)
            .where(
                SectorFundFlow.trade_date == trade_date,
                SectorFundFlow.sector_type == sector_type,
            )
        )

        # total（基于子查询行数，即板块数）
        count_stmt = select(func.count()).select_from(latest_subq)
        total = (await self.session.execute(count_stmt)).scalar_one()

        # 排序：sort_by 容错（非法值 → 默认），order 非 asc → desc
        sort_col = _SORT_COLUMN_MAP.get(sort_by, _SORT_COLUMN_MAP[_DEFAULT_SORT_BY])
        if order == "asc":
            stmt = stmt.order_by(asc(sort_col), asc(SectorFundFlow.sector_name))
        else:
            stmt = stmt.order_by(desc(sort_col), asc(SectorFundFlow.sector_name))

        # 分页
        offset = (page - 1) * page_size
        stmt = stmt.limit(page_size).offset(offset)

        result = await self.session.execute(stmt)
        rows = result.all()

        items = []
        base_rank = offset + 1
        for idx, (flow, sector_id) in enumerate(rows):
            items.append(
                {
                    "rank": base_rank + idx,
                    "sector_name": flow.sector_name,
                    "sector_id": sector_id,
                    "change_percent": flow.change_percent,
                    "inflow": flow.inflow,
                    "outflow": flow.outflow,
                    "net_inflow": flow.net_inflow,
                    "company_count": flow.company_count,
                    "leading_stock": flow.leading_stock,
                    "leading_stock_change": flow.leading_stock_change,
                    "current_price": flow.current_price,
                }
            )

        return {
            "has_data": total > 0,
            "trade_date": trade_date,
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_timeseries(
        self,
        sector_names: list[str],
        sector_type: str = "industry",
        trade_date: Optional[date] = None,
    ) -> dict:
        """
        盘中资金流变化曲线（架构 §6.3 + plan-02 §3 #1）。

        取该 trade_date + sector_type + sector_names(IN) 下所有采样点，
        按 sample_time 升序，再按 sector_name 分组。

        边界场景：
        - sector_names 为空 → 直接返回空 series
        - trade_date 未传 → 默认取 latest_date；无数据 → has_data=False
        - 无数据 → has_data=False + 空 series

        Returns:
            {
                "has_data", "trade_date",
                "series": [{"sector_name", "data": [{"sample_time", "net_inflow"}]}]
            }
        """
        logger.info(
            "get_timeseries called, sector_names=%s, sector_type=%s, trade_date=%s",
            sector_names,
            sector_type,
            trade_date,
        )

        # sector_names 为空 → 空 series
        if not sector_names:
            return {
                "has_data": False,
                "trade_date": None,
                "series": [],
            }

        # trade_date 默认取最新日期
        if trade_date is None:
            trade_date = await self._get_latest_date_value(sector_type)
        if trade_date is None:
            return {
                "has_data": False,
                "trade_date": None,
                "series": [],
            }

        stmt = (
            select(SectorFundFlow.sector_name, SectorFundFlow.sample_time, SectorFundFlow.net_inflow)
            .where(
                SectorFundFlow.trade_date == trade_date,
                SectorFundFlow.sector_type == sector_type,
                SectorFundFlow.sector_name.in_(sector_names),
            )
            .order_by(SectorFundFlow.sample_time.asc(), SectorFundFlow.sector_name.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows:
            return {
                "has_data": False,
                "trade_date": trade_date,
                "series": [],
            }

        # 按 sector_name 分组，保留请求顺序中存在的板块
        grouped: dict[str, list[dict]] = {}
        for sector_name, sample_time, net_inflow in rows:
            grouped.setdefault(sector_name, []).append(
                {"sample_time": sample_time, "net_inflow": net_inflow}
            )

        # series 顺序按请求 sector_names 中存在数据的顺序
        series = [
            {"sector_name": name, "data": grouped[name]}
            for name in sector_names
            if name in grouped
        ]

        return {
            "has_data": True,
            "trade_date": trade_date,
            "series": series,
        }

    async def get_latest_date(self, sector_type: str = "industry") -> dict:
        """
        最新交易日（plan-02 §3 #1）。

        Returns:
            {"latest_date": "YYYY-MM-DD" or null}
        """
        logger.info("get_latest_date called, sector_type=%s", sector_type)
        latest = await self._get_latest_date_value(sector_type)
        return {"latest_date": latest}

    # ============== private helpers ==============

    async def _get_latest_date_value(self, sector_type: str) -> Optional[date]:
        """SELECT MAX(trade_date) FROM sector_fund_flow WHERE sector_type=:t"""
        stmt = select(func.max(SectorFundFlow.trade_date)).where(
            SectorFundFlow.sector_type == sector_type
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
