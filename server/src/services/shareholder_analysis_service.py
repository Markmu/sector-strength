"""股东分析聚合查询服务（plan-02）

通过股东监控组关键词 LIKE 匹配将股东归类到监控组，按股票粒度聚合持仓数据，
计算跨期变动方向（increase/decrease/new/exit），关联行业板块，向 overview /
summary / industry-distribution / holdings 四个用户侧 API 提供数据。

参考：
- plan-01 的 `_escape_like_keyword`（关键词 % 和 _ 转义）
- 架构 §6 运行链路 / §7 领域对象与契约 / §8 非功能
"""

import logging
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sector import Sector
from src.models.sector_stock import SectorStock
from src.models.shareholder_group import ShareholderGroup, ShareholderGroupRule
from src.models.stock import Stock
from src.models.top10_float_holder import Top10FloatHolder

logger = logging.getLogger(__name__)

# 报告期列表最多返回最近 N 个
_MAX_REPORT_PERIODS = 4
# "未分类"桶：仅指无行业关联的股票。distribution 返回全量真实行业（前端图表自行
# 截断 Top N 展示），此桶仅当存在无行业股票时追加，不再吸收 Top N 外长尾——
# 保证「分布展示项 ↔ holdings/summary 可筛选项」1:1 口径一致。
_UNDEFINED_INDUSTRY = "未分类"


def _escape_like_keyword(keyword: str) -> str:
    """转义 LIKE 关键词中的 % 和 _ 通配符（架构 §8.3 安全要求）。

    与 plan-01 的实现保持一致。
    """
    return keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _to_float(val: Any) -> Optional[float]:
    """Decimal / 数字 → float；None 保持 None（保证 JSON 序列化为数值而非字符串）。"""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


class ShareholderAnalysisService:
    """股东聚合查询服务。

    所有方法均为 async，通过注入的 AsyncSession 访问数据库。
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============== 内部方法 ==============

    async def _get_report_periods(
        self, report_period: Optional[str]
    ) -> dict:
        """查询最近 N 个报告期，确定 current_period / prev_period。

        Args:
            report_period: 调用方传入的报告期字符串（YYYY-MM-DD），为 None 表示最新期。

        Returns:
            {
                "report_periods": list[str],   # ISO 字符串
                "current_period": str | None,
                "prev_period": str | None,
                "has_prev_period": bool,
            }
        """
        stmt = (
            select(Top10FloatHolder.report_period)
            .distinct()
            .order_by(Top10FloatHolder.report_period.desc())
            .limit(_MAX_REPORT_PERIODS)
        )
        result = await self.session.execute(stmt)
        period_dates: list[date] = [row[0] for row in result.all() if row[0] is not None]

        if not period_dates:
            return {
                "report_periods": [],
                "current_period": None,
                "prev_period": None,
                "has_prev_period": False,
            }

        # 确定当前期
        current_date: Optional[date] = None
        if report_period is not None:
            try:
                current_date = date.fromisoformat(report_period)
            except ValueError:
                current_date = None
        if current_date is None or current_date not in period_dates:
            # 默认取最新期
            current_date = period_dates[0]

        # 确定上一期：DISTINCT 列表中 current 之前最近的一个
        prev_date: Optional[date] = None
        for d in period_dates:
            if d < current_date:
                prev_date = d
                break

        return {
            "report_periods": [d.isoformat() for d in period_dates],
            "current_period": current_date.isoformat(),
            "prev_period": prev_date.isoformat() if prev_date else None,
            "has_prev_period": prev_date is not None,
        }

    async def _get_groups_with_rules(self) -> dict:
        """查询所有分组及其关键词，返回 {group_id: GroupWithRules} 映射。"""
        stmt = select(ShareholderGroup, ShareholderGroupRule).outerjoin(
            ShareholderGroupRule,
            ShareholderGroupRule.group_id == ShareholderGroup.id,
        ).order_by(ShareholderGroup.sort_order, ShareholderGroup.id)
        result = await self.session.execute(stmt)

        groups: dict = {}
        for grp, rule in result.all():
            if grp.id not in groups:
                groups[grp.id] = {
                    "id": grp.id,
                    "name": grp.name,
                    "description": grp.description,
                    "sort_order": grp.sort_order,
                    "keywords": [],
                }
            if rule is not None and rule.keyword:
                groups[grp.id]["keywords"].append(rule.keyword)
        return groups

    async def _get_group_keywords(self, group_ids: list[int]) -> list[str]:
        """获取指定 group_ids 的所有关键词（去重保序）。"""
        if not group_ids:
            return []
        stmt = select(ShareholderGroupRule.keyword).where(
            ShareholderGroupRule.group_id.in_(group_ids)
        )
        result = await self.session.execute(stmt)
        keywords: list[str] = []
        seen: set = set()
        for (kw,) in result.all():
            if kw and kw not in seen:
                seen.add(kw)
                keywords.append(kw)
        return keywords

    async def _match_holdings(
        self,
        group_ids: list[int],
        report_period: date,
        holder_name: Optional[str] = None,
    ) -> dict:
        """按过滤条件匹配明细，按 (symbol, holder_name) 去重后按 symbol 聚合。

        两种过滤入口（二选一，holder_name 优先）：
        - holder_name 非空：单股东精确匹配（holder_name == holder_name）
        - 否则：按 group_ids 的关键词并集 LIKE 匹配（监控组维度）

        Args:
            group_ids: 监控组 ID 列表（holder_name 非空时忽略）
            report_period: 报告期（date 对象）
            holder_name: 单股东精确名称（与 group_ids 互斥，单股东持仓查询入口）

        Returns:
            {
                symbol: {
                    "symbol": str,
                    "total_hold_amount": float,
                    "total_hold_float_ratio": float,
                    "holders": list[dict],  # 已按 holder_name 去重的明细
                }
            }
        """
        # 构造 holder_name 过滤条件：单股东精确匹配 vs 监控组关键词 LIKE 并集
        if holder_name is not None:
            name_filter = Top10FloatHolder.holder_name == holder_name
        else:
            keywords = await self._get_group_keywords(group_ids)
            if not keywords:
                return {}
            like_conditions = [
                Top10FloatHolder.holder_name.like(
                    f"%{_escape_like_keyword(kw)}%", escape="\\"
                )
                for kw in keywords
            ]
            name_filter = or_(*like_conditions)

        # 先取原始明细，按 (symbol, holder_name) 去重（同一股东匹配多组关键词时避免重复）
        # DISTINCT ON (symbol, holder_name) + ORDER BY ... ann_date DESC NULLS LAST：
        # 同一报告期 Tushare 可能返回多个 ann_date 公告版本（初次公告 + 更正公告），
        # 在 SQL 层直接取每个 (symbol, holder_name) 的最新公告版本，避免读到旧版本。
        # （PG 方言；与 fund_repository.ann_date.desc().nulls_last() 写法一致）
        stmt = (
            select(
                Top10FloatHolder.symbol,
                Top10FloatHolder.holder_name,
                Top10FloatHolder.hold_amount,
                Top10FloatHolder.hold_float_ratio,
            )
            .distinct(
                Top10FloatHolder.symbol,
                Top10FloatHolder.holder_name,
            )
            .where(
                and_(
                    Top10FloatHolder.report_period == report_period,
                    name_filter,
                )
            )
            .order_by(
                Top10FloatHolder.symbol,
                Top10FloatHolder.holder_name,
                Top10FloatHolder.ann_date.desc().nulls_last(),
            )
        )
        result = await self.session.execute(stmt)

        # 按 symbol → holder_name 去重（保留首条），同时累积聚合
        aggregated: dict = {}
        seen_holder_keys: set = set()
        for symbol, holder_name, hold_amount, hold_float_ratio in result.all():
            key = (symbol, holder_name)
            if key in seen_holder_keys:
                continue
            seen_holder_keys.add(key)

            if symbol not in aggregated:
                aggregated[symbol] = {
                    "symbol": symbol,
                    "total_hold_amount": Decimal("0"),
                    "total_hold_float_ratio": Decimal("0"),
                    "holders": [],
                }
            if hold_amount is not None:
                aggregated[symbol]["total_hold_amount"] += hold_amount
            if hold_float_ratio is not None:
                aggregated[symbol]["total_hold_float_ratio"] += hold_float_ratio
            aggregated[symbol]["holders"].append(
                {
                    "holder_name": holder_name,
                    "hold_amount": hold_amount,
                    "hold_float_ratio": hold_float_ratio,
                }
            )

        return aggregated

    @staticmethod
    def _compute_change_directions(
        current_holdings: dict, prev_holdings: dict
    ) -> tuple[dict, set]:
        """计算跨期变动方向。

        - current 有 + prev 无 → "new"
        - current 有 + prev 有 + current > prev → "increase"
        - current 有 + prev 有 + current < prev → "decrease"
        - current 有 + prev 有 + current == prev → "unchanged"
        - prev 有 + current 无 → 加入 exit_symbols

        Returns:
            (directions: Dict[symbol, change_direction], exit_symbols: Set[symbol])
        """
        directions: dict = {}
        exit_symbols: set = set()

        for symbol, cur in current_holdings.items():
            cur_amount = cur["total_hold_amount"]
            prev_amount = (
                prev_holdings.get(symbol, {}).get("total_hold_amount")
                if prev_holdings
                else None
            )
            if symbol not in prev_holdings:
                directions[symbol] = "new"
            else:
                if cur_amount > prev_amount:
                    directions[symbol] = "increase"
                elif cur_amount < prev_amount:
                    directions[symbol] = "decrease"
                else:
                    directions[symbol] = "unchanged"

        for symbol in prev_holdings:
            if symbol not in current_holdings:
                exit_symbols.add(symbol)

        return directions, exit_symbols

    async def _get_industry_for_stocks(
        self, symbols: list[str]
    ) -> dict:
        """批量获取股票的行业关联（显式 JOIN，无 ORM relationship）。

        一只股票可关联多个行业板块，全部返回。

        TODO: 当前 industry 板块为 GICS 多级分类（一股平均关联 ~6 个），导致行业
        分布极度分散（单组数百行业、Top 10 仅占 ~20%）。后续可评估"主行业判定"
        （如仅取 GICS 一级 700301-700311，需 sectors 加 level 字段或 code 前缀规则）
        以缓解分散——作为独立任务，本次 bug 修复不纳入。

        Returns:
            { symbol: { "stock_name": str | None, "industries": list[str] } }
        """
        if not symbols:
            return {}

        stmt = (
            select(
                Stock.symbol,
                Stock.name,
                Sector.name,
            )
            .select_from(Stock)
            .outerjoin(
                SectorStock,
                SectorStock.stock_code == Stock.symbol,
            )
            .outerjoin(
                Sector,
                and_(
                    Sector.code == SectorStock.sector_code,
                    Sector.type == "industry",
                ),
            )
            .where(Stock.symbol.in_(symbols))
        )
        result = await self.session.execute(stmt)

        mapping: dict = {}
        for symbol, stock_name, industry_name in result.all():
            if symbol not in mapping:
                mapping[symbol] = {"stock_name": stock_name, "industries": []}
            if industry_name and industry_name not in mapping[symbol]["industries"]:
                mapping[symbol]["industries"].append(industry_name)

        # 对传入但 stocks 表缺失的 symbol，补充空结构（holdings 列表需要 stock_name=None）
        for sym in symbols:
            if sym not in mapping:
                mapping[sym] = {"stock_name": None, "industries": []}

        return mapping

    async def _resolve_period_date(
        self, report_period: Optional[str]
    ) -> Optional[date]:
        """将 YYYY-MM-DD 字符串转为 date；无效返回 None。"""
        if not report_period:
            return None
        try:
            return date.fromisoformat(report_period)
        except ValueError:
            return None

    # ============== 公开方法 ==============

    async def get_overview(self, report_period: Optional[str] = None) -> dict:
        """监控组概览（AC-01 / AC-09 / AC-11）。

        Args:
            report_period: 报告期字符串，None 时取最新期。

        Returns:
            OverviewResponse 数据（snake_case，由 API 层转 camelCase）。
        """
        periods_info = await self._get_report_periods(report_period)
        report_periods = periods_info["report_periods"]
        current_period = periods_info["current_period"]
        prev_period = periods_info["prev_period"]
        has_prev_period = periods_info["has_prev_period"]

        groups_map = await self._get_groups_with_rules()

        if current_period is None or not groups_map:
            return {
                "report_periods": report_periods,
                "current_period": current_period,
                "has_prev_period": has_prev_period,
                "groups": [],
            }

        current_date = await self._resolve_period_date(current_period)
        prev_date = await self._resolve_period_date(prev_period)

        group_overviews = []
        for gid, grp in groups_map.items():
            current_holdings = await self._match_holdings([gid], current_date)
            stock_count = len(current_holdings)

            increase_count = decrease_count = new_count = exit_count = 0
            if has_prev_period and prev_date is not None:
                prev_holdings = await self._match_holdings([gid], prev_date)
                directions, exit_symbols = self._compute_change_directions(
                    current_holdings, prev_holdings
                )
                for direction in directions.values():
                    if direction == "increase":
                        increase_count += 1
                    elif direction == "decrease":
                        decrease_count += 1
                    elif direction == "new":
                        new_count += 1
                exit_count = len(exit_symbols)

            group_overviews.append(
                {
                    "group_id": gid,
                    "group_name": grp["name"],
                    "description": grp.get("description"),
                    "stock_count": stock_count,
                    "increase_count": increase_count,
                    "decrease_count": decrease_count,
                    "new_count": new_count,
                    "exit_count": exit_count,
                }
            )

        # 按 stock_count 降序
        group_overviews.sort(key=lambda g: g["stock_count"], reverse=True)

        return {
            "report_periods": report_periods,
            "current_period": current_period,
            "has_prev_period": has_prev_period,
            "groups": group_overviews,
        }

    async def _aggregate_with_change(
        self,
        group_ids: list[int],
        current_date: date,
        prev_date: Optional[date],
        has_prev_period: bool,
        exit_requested: bool,
        holder_name: Optional[str] = None,
    ) -> dict:
        """汇总匹配 + 变动方向计算，返回统一的中间结构。

        被 get_summary / get_industry_distribution / get_holdings 复用。
        holder_name 非空时切换为单股东精确匹配维度（透传给 _match_holdings）。

        Returns:
            {
                "current_holdings": dict,
                "prev_holdings": dict,            # 无上期时为 {}
                "directions": Dict[symbol, dir],
                "exit_symbols": set,
                "exit_holdings": dict,            # 退出股票的上期聚合，无上期时为 {}
                "has_prev_period": bool,
            }
        """
        current_holdings = await self._match_holdings(
            group_ids, current_date, holder_name=holder_name
        )

        if not has_prev_period or prev_date is None:
            return {
                "current_holdings": current_holdings,
                "prev_holdings": {},
                "directions": {s: None for s in current_holdings},
                "exit_symbols": set(),
                "exit_holdings": {},
                "has_prev_period": False,
            }

        prev_holdings = await self._match_holdings(
            group_ids, prev_date, holder_name=holder_name
        )
        directions, exit_symbols = self._compute_change_directions(
            current_holdings, prev_holdings
        )

        exit_holdings: dict = {}
        if exit_requested and exit_symbols:
            exit_holdings = {
                sym: prev_holdings[sym] for sym in exit_symbols if sym in prev_holdings
            }

        return {
            "current_holdings": current_holdings,
            "prev_holdings": prev_holdings,
            "directions": directions,
            "exit_symbols": exit_symbols,
            "exit_holdings": exit_holdings,
            "has_prev_period": True,
        }

    async def get_summary(
        self,
        group_ids: list[int],
        report_period: str,
        industry: Optional[str] = None,
        change_direction: Optional[str] = None,
        holder_name: Optional[str] = None,
    ) -> dict:
        """汇总统计 + 变动趋势（AC-02 / AC-03 / AC-04 / AC-05 / AC-11）。

        trend 不受 change_direction 筛选影响。
        """
        periods_info = await self._get_report_periods(report_period)
        current_period = periods_info["current_period"]
        prev_period = periods_info["prev_period"]
        has_prev_period = periods_info["has_prev_period"]

        current_date = await self._resolve_period_date(current_period)
        prev_date = await self._resolve_period_date(prev_period)

        if current_date is None:
            return {
                "summary": {
                    "stock_count": 0,
                    "total_hold_amount": 0.0,
                    "avg_hold_float_ratio": 0.0,
                },
                "trend": {
                    "increase_count": 0,
                    "decrease_count": 0,
                    "new_count": 0,
                    "exit_count": 0,
                },
                "has_prev_period": has_prev_period,
            }

        exit_requested = change_direction == "exit"
        agg = await self._aggregate_with_change(
            group_ids=group_ids,
            current_date=current_date,
            prev_date=prev_date,
            has_prev_period=has_prev_period,
            exit_requested=exit_requested,
            holder_name=holder_name,
        )

        current_holdings = agg["current_holdings"]
        directions = agg["directions"]
        exit_holdings = agg["exit_holdings"]

        # 行业关联（仅用于 industry 筛选）
        industry_map = await self._get_industry_for_stocks(
            list(current_holdings.keys())
        )

        # 构造统一列表（current 股票 + exit 股票）
        rows: list[dict] = []
        for symbol, holding in current_holdings.items():
            rows.append(
                {
                    "symbol": symbol,
                    "total_hold_amount": _to_float(holding["total_hold_amount"]),
                    "total_hold_float_ratio": _to_float(
                        holding["total_hold_float_ratio"]
                    ),
                    "change_direction": directions.get(symbol),
                    "industries": industry_map.get(symbol, {}).get("industries", []),
                }
            )
        for symbol, holding in exit_holdings.items():
            rows.append(
                {
                    "symbol": symbol,
                    "total_hold_amount": _to_float(holding["total_hold_amount"]),
                    "total_hold_float_ratio": _to_float(
                        holding["total_hold_float_ratio"]
                    ),
                    "change_direction": "exit",
                    "industries": industry_map.get(symbol, {}).get("industries", []),
                }
            )

        # 应用 industry 筛选（"未分类"对应无行业关联的股票，口径与分布一致）
        if industry is not None:
            if industry == _UNDEFINED_INDUSTRY:
                rows = [r for r in rows if len(r["industries"]) == 0]
            else:
                rows = [r for r in rows if industry in r["industries"]]

        # 应用 change_direction 筛选
        if change_direction is not None:
            rows = [r for r in rows if r["change_direction"] == change_direction]

        # 汇总统计（仅基于筛选后集合）
        stock_count = len(rows)
        total_hold_amount = sum(r["total_hold_amount"] for r in rows)
        # avg_hold_float_ratio：先按股票求 SUM，再对股票集合求简单平均
        if stock_count:
            avg_hold_float_ratio = sum(
                r["total_hold_float_ratio"] for r in rows
            ) / stock_count
        else:
            avg_hold_float_ratio = 0.0

        # trend：不受 change_direction 筛选影响，基于全量 current + exit 计算
        trend = self._compute_trend(
            current_holdings, directions, agg["exit_symbols"], has_prev_period
        )

        return {
            "summary": {
                "stock_count": stock_count,
                "total_hold_amount": total_hold_amount,
                "avg_hold_float_ratio": avg_hold_float_ratio,
            },
            "trend": trend,
            "has_prev_period": has_prev_period,
        }

    @staticmethod
    def _compute_trend(
        current_holdings: dict,
        directions: dict,
        exit_symbols: set,
        has_prev_period: bool,
    ) -> dict:
        """计算变动趋势计数（increase/decrease/new/exit）。

        无上期数据时全部为 0（AC-11）。
        """
        if not has_prev_period:
            return {
                "increase_count": 0,
                "decrease_count": 0,
                "new_count": 0,
                "exit_count": 0,
            }

        increase = decrease = new = 0
        for direction in directions.values():
            if direction == "increase":
                increase += 1
            elif direction == "decrease":
                decrease += 1
            elif direction == "new":
                new += 1
        return {
            "increase_count": increase,
            "decrease_count": decrease,
            "new_count": new,
            "exit_count": len(exit_symbols),
        }

    async def get_industry_distribution(
        self,
        group_ids: list[int],
        report_period: str,
        change_direction: Optional[str] = None,
        holder_name: Optional[str] = None,
    ) -> dict:
        """行业分布（AC-02 / AC-05）。

        - 不受 industry 筛选影响（自身是筛选 UI 的数据源）。
        - change_direction 筛选生效（含 exit）。
        - 一只股票属于多个行业时按独立计数统计。
        """
        periods_info = await self._get_report_periods(report_period)
        current_period = periods_info["current_period"]
        prev_period = periods_info["prev_period"]
        has_prev_period = periods_info["has_prev_period"]

        current_date = await self._resolve_period_date(current_period)
        prev_date = await self._resolve_period_date(prev_period)

        if current_date is None:
            return {"distribution": []}

        exit_requested = change_direction == "exit"
        agg = await self._aggregate_with_change(
            group_ids=group_ids,
            current_date=current_date,
            prev_date=prev_date,
            has_prev_period=has_prev_period,
            exit_requested=exit_requested,
            holder_name=holder_name,
        )

        current_holdings = agg["current_holdings"]
        directions = agg["directions"]
        exit_holdings = agg["exit_holdings"]

        industry_map = await self._get_industry_for_stocks(
            list(current_holdings.keys()) + list(exit_holdings.keys())
        )

        # 构造统一列表
        rows: list[dict] = []
        for symbol in current_holdings:
            rows.append(
                {
                    "symbol": symbol,
                    "change_direction": directions.get(symbol),
                    "industries": industry_map.get(symbol, {}).get("industries", []),
                }
            )
        for symbol in exit_holdings:
            rows.append(
                {
                    "symbol": symbol,
                    "change_direction": "exit",
                    "industries": industry_map.get(symbol, {}).get("industries", []),
                }
            )

        # 仅应用 change_direction 筛选（industry 不生效）
        if change_direction is not None:
            rows = [r for r in rows if r["change_direction"] == change_direction]

        # 按行业分组统计（一只股票多行业时每个行业独立计数）
        industry_counter: dict = defaultdict(int)
        undefined_count = 0  # 无行业关联的股票数（"未分类"桶）
        total_count = 0      # 占比基数（含全部行业计数 + 无行业股票数）
        for r in rows:
            if r["industries"]:
                for ind in r["industries"]:
                    industry_counter[ind] += 1
                    total_count += 1
            else:
                undefined_count += 1
                total_count += 1

        # 全量真实行业（按持仓股票数降序）。distribution 作为筛选数据源返回全量，
        # 前端图表自行截断 Top N 展示；占比基于 total_count（含长尾），故 Top N 占比
        # 之和可能 < 100%——这是真实分散的反映（一只股票可关联多个 industry 板块）。
        sorted_inds = sorted(industry_counter.items(), key=lambda x: x[1], reverse=True)
        items: list[dict] = [
            {
                "industry": ind,
                "stock_count": cnt,
                "percentage": (cnt / total_count * 100) if total_count else 0.0,
            }
            for ind, cnt in sorted_inds
        ]
        # "未分类"仅指无行业关联股票，不再吸收 Top N 外长尾——保证分布口径 = 筛选口径。
        if undefined_count > 0:
            items.append(
                {
                    "industry": _UNDEFINED_INDUSTRY,
                    "stock_count": undefined_count,
                    "percentage": (undefined_count / total_count * 100)
                    if total_count
                    else 0.0,
                }
            )

        # 按 stock_count 降序
        items.sort(key=lambda x: x["stock_count"], reverse=True)

        return {"distribution": items}

    async def get_holdings(
        self,
        group_ids: list[int],
        report_period: str,
        industry: Optional[str] = None,
        change_direction: Optional[str] = None,
        holder_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """分页持仓列表（AC-02 / AC-03 / AC-04 / AC-05 / AC-11）。

        退出股票展示上期 total_hold_amount / total_hold_float_ratio。
        """
        periods_info = await self._get_report_periods(report_period)
        current_period = periods_info["current_period"]
        prev_period = periods_info["prev_period"]
        has_prev_period = periods_info["has_prev_period"]

        current_date = await self._resolve_period_date(current_period)
        prev_date = await self._resolve_period_date(prev_period)

        if current_date is None:
            return {"holdings": [], "total": 0}

        exit_requested = change_direction == "exit"
        agg = await self._aggregate_with_change(
            group_ids=group_ids,
            current_date=current_date,
            prev_date=prev_date,
            has_prev_period=has_prev_period,
            exit_requested=exit_requested,
            holder_name=holder_name,
        )

        current_holdings = agg["current_holdings"]
        directions = agg["directions"]
        exit_holdings = agg["exit_holdings"]

        all_symbols = list(current_holdings.keys()) + list(exit_holdings.keys())
        industry_map = await self._get_industry_for_stocks(all_symbols)

        # 构造统一列表
        rows: list[dict] = []
        for symbol, holding in current_holdings.items():
            rows.append(
                {
                    "symbol": symbol,
                    "stock_name": industry_map.get(symbol, {}).get("stock_name"),
                    "total_hold_amount": _to_float(holding["total_hold_amount"]),
                    "total_hold_float_ratio": _to_float(
                        holding["total_hold_float_ratio"]
                    ),
                    "change_direction": directions.get(symbol),
                    "industries": industry_map.get(symbol, {}).get("industries", []),
                }
            )
        for symbol, holding in exit_holdings.items():
            rows.append(
                {
                    "symbol": symbol,
                    "stock_name": industry_map.get(symbol, {}).get("stock_name"),
                    "total_hold_amount": _to_float(holding["total_hold_amount"]),
                    "total_hold_float_ratio": _to_float(
                        holding["total_hold_float_ratio"]
                    ),
                    "change_direction": "exit",
                    "industries": industry_map.get(symbol, {}).get("industries", []),
                }
            )

        # 应用 industry 筛选（"未分类"对应无行业关联的股票，口径与分布一致）
        if industry is not None:
            if industry == _UNDEFINED_INDUSTRY:
                rows = [r for r in rows if len(r["industries"]) == 0]
            else:
                rows = [r for r in rows if industry in r["industries"]]

        # 应用 change_direction 筛选
        if change_direction is not None:
            rows = [r for r in rows if r["change_direction"] == change_direction]

        # 按 symbol 排序
        rows.sort(key=lambda r: r["symbol"])

        total = len(rows)
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        page_rows = rows[start:end]

        return {"holdings": page_rows, "total": total}

    async def search_holders(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """按 holder_name 模糊搜索股东（全库所有报告期去重）。

        单股东持仓查询的搜索入口：返回 DISTINCT holder_name 列表（分页），
        选中后用精确 holder_name 调 get_summary / get_holdings 等（holder_name 维度）。

        Args:
            keyword: 搜索关键词（LIKE %keyword%，% 和 _ 已转义）
            page: 页码，从 1 开始
            page_size: 每页数量

        Returns:
            {"holders": [{"holder_name": str}], "total": int}
        """
        escaped = f"%{_escape_like_keyword(keyword)}%"
        name_not_null = Top10FloatHolder.holder_name.isnot(None)
        like_cond = Top10FloatHolder.holder_name.like(escaped, escape="\\")

        # total：DISTINCT holder_name 的总数
        distinct_subq = (
            select(Top10FloatHolder.holder_name)
            .distinct()
            .where(and_(name_not_null, like_cond))
        ).subquery()
        total = (
            await self.session.execute(
                select(func.count()).select_from(distinct_subq)
            )
        ).scalar_one()

        # 分页列表（按 holder_name 升序）
        list_stmt = (
            select(Top10FloatHolder.holder_name)
            .distinct()
            .where(and_(name_not_null, like_cond))
            .order_by(Top10FloatHolder.holder_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(list_stmt)
        holders = [{"holder_name": name} for (name,) in result.all() if name]

        return {"holders": holders, "total": total}
