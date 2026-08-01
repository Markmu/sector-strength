"""涨停专题查询服务（连板天梯）

提供连板天梯页面所需的查询：
- ``get_ladder(trade_date)``：单日天梯 = 涨停最强板块(limit_cpt_list)
  + 按 limit_times 分层的个股(limit_list_d，仅涨停 U)
- ``get_ladder_multi_days(end_date, days)``：多日表格，近 N 日每日涨停/连板统计
- ``get_ladder_list(trade_date, page, page_size)``：当日全部涨停个股平铺列表（分页）
- ``get_latest_date()``：最新有数据的交易日

所有方法返回 snake_case dict，由路由层 ``_dict_to_camel`` 转 camelCase。
仿 ``etf_monitor_service.py``（service 层直接用 SQLAlchemy Core，__init__(session)）。
"""

import logging
from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.limit import LimitListD, LimitStep, LimitCptList

logger = logging.getLogger(__name__)


class LimitService:
    """涨停专题查询服务（连板天梯 / 多日统计 / 个股列表 / 最新日期）。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============== public API ==============

    async def get_ladder(self, trade_date: Optional[date] = None) -> dict:
        """
        单日连板天梯（默认视图）。

        返回结构：
        {
            "has_data": bool,
            "trade_date": str | None,
            "sectors": [{ name, up_nums, cons_nums, days, up_stat, pct_chg }],
            "levels": [
                {
                    "limit_times": int,      # 连板数
                    "count": int,            # 该层个股数
                    "stocks": [{ ts_code, name, industry, close, pct_chg,
                                 fd_amount, first_time, open_times, up_stat }]
                }
            ]
        }

        - sectors 来自 limit_cpt_list，按 up_nums 降序
        - levels 来自 limit_list_d（仅 limit_type='U' 涨停），按 limit_times 降序分层，
          层内按 fd_amount（封单额）降序

        边界：
        - trade_date 未传 → 默认取 latest_date；无数据 → has_data=False
        """
        if trade_date is None:
            trade_date = await self._get_latest_date()

        if trade_date is None:
            return self._empty_ladder()

        # 涨停最强板块（limit_cpt_list）
        sector_rows = await self.session.execute(
            select(
                LimitCptList.name,
                LimitCptList.up_nums,
                LimitCptList.cons_nums,
                LimitCptList.days,
                LimitCptList.up_stat,
                LimitCptList.pct_chg,
                LimitCptList.rank,
            )
            .where(LimitCptList.trade_date == trade_date)
            .order_by(asc(LimitCptList.rank))
        )
        sectors = [
            {
                "name": r.name,
                "up_nums": r.up_nums,
                "cons_nums": r.cons_nums,
                "days": r.days,
                "up_stat": r.up_stat,
                "pct_chg": r.pct_chg,
            }
            for r in sector_rows
        ]

        # 涨停个股明细（limit_list_d，仅 U 涨停），按 limit_times 降序 + fd_amount 降序
        stock_rows = await self.session.execute(
            select(
                LimitListD.ts_code,
                LimitListD.name,
                LimitListD.industry,
                LimitListD.close,
                LimitListD.pct_chg,
                LimitListD.fd_amount,
                LimitListD.first_time,
                LimitListD.last_time,
                LimitListD.open_times,
                LimitListD.up_stat,
                LimitListD.limit_times,
                LimitListD.amount,
            )
            .where(
                LimitListD.trade_date == trade_date,
                LimitListD.limit_type == "U",
            )
            .order_by(
                desc(LimitListD.limit_times),
                desc(LimitListD.fd_amount),
            )
        )
        stock_list = stock_rows.all()

        if not stock_list and not sectors:
            return self._empty_ladder()

        # 按 limit_times 分层
        levels_map = defaultdict(list)
        for r in stock_list:
            lt = r.limit_times or 1
            levels_map[lt].append(
                {
                    "ts_code": r.ts_code,
                    "name": r.name,
                    "industry": r.industry,
                    "close": r.close,
                    "pct_chg": r.pct_chg,
                    "fd_amount": r.fd_amount,
                    "first_time": r.first_time,
                    "last_time": r.last_time,
                    "open_times": r.open_times,
                    "up_stat": r.up_stat,
                }
            )

        levels = [
            {"limit_times": lt, "count": len(stocks), "stocks": stocks}
            for lt, stocks in sorted(levels_map.items(), reverse=True)
        ]

        return {
            "has_data": True,
            "trade_date": trade_date.isoformat(),
            "sectors": sectors,
            "levels": levels,
        }

    async def get_ladder_multi_days(
        self, end_date: Optional[date] = None, days: int = 5
    ) -> dict:
        """
        多日连板统计表格视图。

        取 end_date 之前（含）最近 N 个有数据的交易日，统计每日：
        涨停总数、各连板高度（≥2板）的家数。

        返回结构：
        {
            "has_data": bool,
            "end_date": str | None,
            "days": int,
            "items": [{
                "trade_date": str,
                "total_up": int,          # 涨停总数
                "limit_up_2": int,        # 2连板家数
                "limit_up_3": int,        # 3连板家数
                ...
                "max_times": int,         # 当日最高连板数
            }]
        }
        """
        if end_date is None:
            end_date = await self._get_latest_date()

        if end_date is None:
            return {"has_data": False, "end_date": None, "days": days, "items": []}

        # 取 end_date 之前最近 N 个有数据的交易日（distinct trade_date 降序）
        date_rows = await self.session.execute(
            select(LimitListD.trade_date)
            .where(LimitListD.trade_date <= end_date)
            .group_by(LimitListD.trade_date)
            .order_by(desc(LimitListD.trade_date))
            .limit(days)
        )
        trade_dates = [r[0] for r in date_rows]
        trade_dates.sort(reverse=True)

        if not trade_dates:
            return {"has_data": False, "end_date": end_date.isoformat(),
                    "days": days, "items": []}

        # 每日按 limit_times 分组计数（仅 U 涨停）
        count_rows = await self.session.execute(
            select(
                LimitListD.trade_date,
                LimitListD.limit_times,
                func.count().label("cnt"),
            )
            .where(
                LimitListD.trade_date.in_(trade_dates),
                LimitListD.limit_type == "U",
            )
            .group_by(LimitListD.trade_date, LimitListD.limit_times)
        )

        # 组装 { trade_date: { limit_times: count } }
        daily_map = defaultdict(lambda: defaultdict(int))
        for r in count_rows:
            daily_map[r.trade_date][r.limit_times or 1] += r[2]

        items = []
        for td in trade_dates:
            counts = daily_map[td]
            total_up = sum(counts.values())
            max_times = max(counts.keys()) if counts else 0
            item = {
                "trade_date": td.isoformat(),
                "total_up": total_up,
                "max_times": max_times,
            }
            # 各连板高度的家数（2 ~ max_times）
            for lt in range(2, (max_times or 1) + 1):
                item[f"limit_up_{lt}"] = counts.get(lt, 0)
            items.append(item)

        return {
            "has_data": True,
            "end_date": end_date.isoformat(),
            "days": days,
            "items": items,
        }

    async def get_ladder_list(
        self,
        trade_date: Optional[date] = None,
        limit_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """
        当日涨停个股平铺列表（列表视图，分页）。

        返回结构：
        {
            "has_data": bool,
            "trade_date": str | None,
            "items": [{ ts_code, name, industry, close, pct_chg, fd_amount,
                        first_time, open_times, up_stat, limit_times, limit_type }],
            "total": int, "page": int, "page_size": int
        }

        Args:
            limit_type: 可选筛选 U涨停 / D跌停 / Z炸板，默认全部
        """
        if trade_date is None:
            trade_date = await self._get_latest_date()

        if trade_date is None:
            return self._empty_list(page, page_size)

        conditions = [LimitListD.trade_date == trade_date]
        if limit_type:
            conditions.append(LimitListD.limit_type == limit_type)

        # 总数
        total_result = await self.session.execute(
            select(func.count()).select_from(LimitListD).where(*conditions)
        )
        total = total_result.scalar() or 0

        if total == 0:
            return self._empty_list(page, page_size)

        # 分页查询，按 limit_times 降序 + fd_amount 降序
        offset = (page - 1) * page_size
        rows = await self.session.execute(
            select(
                LimitListD.ts_code,
                LimitListD.name,
                LimitListD.industry,
                LimitListD.close,
                LimitListD.pct_chg,
                LimitListD.fd_amount,
                LimitListD.first_time,
                LimitListD.last_time,
                LimitListD.open_times,
                LimitListD.up_stat,
                LimitListD.limit_times,
                LimitListD.limit_type,
                LimitListD.amount,
            )
            .where(*conditions)
            .order_by(
                desc(LimitListD.limit_times),
                desc(LimitListD.fd_amount),
            )
            .offset(offset)
            .limit(page_size)
        )

        items = [
            {
                "ts_code": r.ts_code,
                "name": r.name,
                "industry": r.industry,
                "close": r.close,
                "pct_chg": r.pct_chg,
                "fd_amount": r.fd_amount,
                "first_time": r.first_time,
                "last_time": r.last_time,
                "open_times": r.open_times,
                "up_stat": r.up_stat,
                "limit_times": r.limit_times,
                "limit_type": r.limit_type,
                "amount": r.amount,
            }
            for r in rows
        ]

        return {
            "has_data": True,
            "trade_date": trade_date.isoformat(),
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_latest_date(self) -> dict:
        """最新有数据的交易日。"""
        d = await self._get_latest_date()
        return {"has_data": d is not None, "trade_date": d.isoformat() if d else None}

    # ============== private ==============

    async def _get_latest_date(self) -> Optional[date]:
        """取 limit_list_d 表中最大的 trade_date"""
        result = await self.session.execute(
            select(func.max(LimitListD.trade_date))
        )
        return result.scalar()

    @staticmethod
    def _empty_ladder() -> dict:
        return {"has_data": False, "trade_date": None, "sectors": [], "levels": []}

    @staticmethod
    def _empty_list(page: int, page_size: int) -> dict:
        return {
            "has_data": False,
            "trade_date": None,
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        }
