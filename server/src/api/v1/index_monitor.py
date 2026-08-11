"""
指数监控查询 API 路由（第 15 期 plan-03）

端点：
- GET  /api/v1/index-monitor/overview   — 关注指数总览（AC-01/12）
- GET  /api/v1/index-monitor/trend      — 多指数走势（AC-02）
- GET  /api/v1/index-monitor/valuation  — 单指数估值水位（AC-03）
- GET  /api/v1/index-monitor/weights    — 成分权重 + 集中度（AC-04）
- GET  /api/v1/index-monitor/watchlist  — 关注清单（AC-07）
- PUT  /api/v1/index-monitor/watchlist  — 全量更新关注清单（AC-07）

复用声明：
- 路由 + helper 范式：src/api/v1/etf_monitor.py（_dict_to_camel / _serialize_value /
  {success,data} 包裹 / Depends(get_current_user)）
- 4 个模型：src/models/index_monitor.py（IndexBasic / IndexDaily /
  IndexDailyBasic / IndexWeight）
- stocks 表 JOIN：src/models/stock.py（Stock.ts_code ↔ IndexWeight.con_code）

契约（架构 §7.3 + plan-03 §3）：
- 路径：router prefix /index-monitor + v1 主路由 prefix /v1 = /api/v1/index-monitor/*
- query 参数名全 snake_case（ts_codes/start_date/end_date/ts_code/index_code/top_n）
- 响应：{ success: bool, data: {...} } 包裹，data 内字段经 _dict_to_camel 转 camelCase
- 单位换算：index_daily.amount 存储为千元，输出层 ÷10000 转亿元
- 安全（架构 §8.3）：所有端点用 get_current_user；query 参数 SQLAlchemy 参数化查询防注入
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic.alias_generators import to_camel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_session
from src.models.index_monitor import (
    IndexBasic,
    IndexDaily,
    IndexDailyBasic,
    IndexWeight,
)
from src.models.stock import Stock
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/index-monitor", tags=["IndexMonitor"])


# ============== Helper ==============


def _serialize_value(val):
    """将 Decimal / date 等类型序列化为 JSON 安全类型（与 etf_monitor.py 一致）"""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return val


def _dict_to_camel(d: dict) -> dict:
    """将字典的 snake_case 键转为 camelCase（递归处理嵌套 dict / list）"""
    result = {}
    for k, v in d.items():
        camel_key = to_camel(k)
        if isinstance(v, dict):
            result[camel_key] = _dict_to_camel(v)
        elif isinstance(v, list):
            result[camel_key] = [
                _dict_to_camel(item) if isinstance(item, dict) else _serialize_value(item)
                for item in v
            ]
        else:
            result[camel_key] = _serialize_value(v)
    return result


# ============== Endpoints ==============


@router.get("/overview")
async def get_overview(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    关注指数总览（AC-01/12）。

    流程：
    1. SELECT MAX(trade_date) FROM index_daily 获取最近有数据交易日；
    2. 查 index_basic WHERE is_watched=true 关注指数；
    3. 对每只关注指数查 index_daily 当日行情（close/pct_chg/amount）；
    4. LEFT JOIN index_dailybasic 取 pe_ttm（无估值为 null）；
    5. amount ÷10000 转亿元输出。

    返回 { success, data: { indices: [...], tradeDate } }。
    当日无数据时回退最近有数据交易日（AC-12）。
    """
    try:
        # 1. 最近有数据交易日
        latest_date_row = await session.execute(select(func.max(IndexDaily.trade_date)))
        latest_date = latest_date_row.scalar_one_or_none()

        if latest_date is None:
            logger.debug("overview: index_daily 无任何数据，返回空列表")
            return {
                "success": True,
                "data": _dict_to_camel({"indices": [], "trade_date": None}),
            }

        # 2. 关注指数
        watched_res = await session.execute(
            select(IndexBasic).where(IndexBasic.is_watched.is_(True))
        )
        watched_list = watched_res.scalars().all()

        if not watched_list:
            logger.debug("overview: 无关注指数，返回空列表")
            return {
                "success": True,
                "data": _dict_to_camel({"indices": [], "trade_date": latest_date}),
            }

        watched_codes = [b.ts_code for b in watched_list]
        watched_name_map = {b.ts_code: b.name for b in watched_list}

        # 3. 关注指数当日行情
        daily_res = await session.execute(
            select(IndexDaily).where(
                IndexDaily.trade_date == latest_date,
                IndexDaily.ts_code.in_(watched_codes),
            )
        )
        daily_list = daily_res.scalars().all()
        daily_map = {d.ts_code: d for d in daily_list}

        # 4. 关注指数当日估值（LEFT JOIN，pe_ttm 可空）
        val_res = await session.execute(
            select(IndexDailyBasic.ts_code, IndexDailyBasic.pe_ttm).where(
                IndexDailyBasic.trade_date == latest_date,
                IndexDailyBasic.ts_code.in_(watched_codes),
            )
        )
        pe_map = {row[0]: row[1] for row in val_res.all()}

        # 5. 组装（amount 千元 → 亿元 ÷10000）
        indices = []
        for ts_code in watched_codes:
            d = daily_map.get(ts_code)
            if d is None:
                # 当日无行情：仍返回基础信息，行情字段为 null
                indices.append(
                    {
                        "ts_code": ts_code,
                        "name": watched_name_map.get(ts_code),
                        "close": None,
                        "pct_chg": None,
                        "amount": None,
                        "pe_ttm": pe_map.get(ts_code),
                    }
                )
                continue
            amount_yuan = d.amount / 10000 if d.amount is not None else None
            indices.append(
                {
                    "ts_code": ts_code,
                    "name": watched_name_map.get(ts_code),
                    "close": d.close,
                    "pct_chg": d.pct_chg,
                    "amount": amount_yuan,
                    "pe_ttm": pe_map.get(ts_code),
                }
            )

        logger.debug(
            "overview: trade_date=%s, watched=%d, indices=%d",
            latest_date,
            len(watched_codes),
            len(indices),
        )
        return {
            "success": True,
            "data": _dict_to_camel(
                {"indices": indices, "trade_date": latest_date}
            ),
        }
    except Exception:
        logger.exception("get_overview error")
        raise


@router.get("/trend")
async def get_trend(
    ts_codes: str = Query(..., description="指数代码列表，逗号分隔（最多前 6 只生效）"),
    start_date: Optional[date] = Query(None, description="起始日（YYYY-MM-DD，默认近1年）"),
    end_date: Optional[date] = Query(None, description="结束日（YYYY-MM-DD，默认今天）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    多指数走势（AC-02）。

    逻辑：
    - 拆分 ts_codes（逗号分隔），最多取前 6 只；
    - 查 index_daily WHERE ts_code IN(...) AND trade_date BETWEEN start AND end，
      按 trade_date 升序；
    - 按 ts_code 分组为 series。

    返回 { success, data: { series: [...], hasData } }。
    """
    try:
        # 拆分 ts_codes，最多前 6 只
        code_list = [c.strip() for c in ts_codes.split(",") if c.strip()]
        code_list = code_list[:6]

        if not code_list:
            logger.debug("trend: ts_codes 为空，返回空 series")
            return {
                "success": True,
                "data": _dict_to_camel({"series": [], "has_data": False}),
            }

        # 默认区间：近 1 年
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        # 查 index_daily
        res = await session.execute(
            select(IndexDaily)
            .where(
                IndexDaily.ts_code.in_(code_list),
                IndexDaily.trade_date >= start_date,
                IndexDaily.trade_date <= end_date,
            )
            .order_by(IndexDaily.trade_date.asc())
        )
        daily_list = res.scalars().all()

        # 取指数名称（从 index_basic）
        name_res = await session.execute(
            select(IndexBasic.ts_code, IndexBasic.name).where(
                IndexBasic.ts_code.in_(code_list)
            )
        )
        name_map = {row[0]: row[1] for row in name_res.all()}

        # 按 ts_code 分组
        series_map: dict[str, list[dict]] = {c: [] for c in code_list}
        for d in daily_list:
            series_map.setdefault(d.ts_code, []).append(
                {
                    "trade_date": d.trade_date,
                    "close": d.close,
                    "pct_chg": d.pct_chg,
                }
            )

        series = [
            {
                "ts_code": c,
                "name": name_map.get(c),
                "points": series_map.get(c, []),
            }
            for c in code_list
        ]

        has_data = len(daily_list) > 0
        logger.debug(
            "trend: ts_codes=%s, start=%s, end=%s, rows=%d, series=%d",
            code_list,
            start_date,
            end_date,
            len(daily_list),
            len(series),
        )
        return {
            "success": True,
            "data": _dict_to_camel(
                {"series": series, "has_data": has_data}
            ),
        }
    except Exception:
        logger.exception(
            "get_trend error, ts_codes=%s, start_date=%s, end_date=%s",
            ts_codes,
            start_date,
            end_date,
        )
        raise


@router.get("/valuation")
async def get_valuation(
    ts_code: str = Query(..., description="指数代码（如 000300.SH）"),
    start_date: Optional[date] = Query(None, description="起始日（YYYY-MM-DD，默认近1年）"),
    end_date: Optional[date] = Query(None, description="结束日（YYYY-MM-DD，默认今天）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    单指数估值水位（AC-03）。

    逻辑：
    - 查 index_dailybasic WHERE ts_code=? AND trade_date BETWEEN start AND end，
      按 trade_date 升序；
    - 无数据返回 hasData=false 空序列（如科创50 暂无估值）。

    返回 { success, data: { tsCode, points: [...], hasData } }。
    """
    try:
        # 默认区间：近 1 年
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        res = await session.execute(
            select(IndexDailyBasic)
            .where(
                IndexDailyBasic.ts_code == ts_code,
                IndexDailyBasic.trade_date >= start_date,
                IndexDailyBasic.trade_date <= end_date,
            )
            .order_by(IndexDailyBasic.trade_date.asc())
        )
        rows = res.scalars().all()

        if not rows:
            logger.debug("valuation: ts_code=%s 无估值数据", ts_code)
            return {
                "success": True,
                "data": _dict_to_camel(
                    {
                        "ts_code": ts_code,
                        "points": [],
                        "has_data": False,
                    }
                ),
            }

        points = [
            {
                "trade_date": r.trade_date,
                "pe_ttm": r.pe_ttm,
                "pb": r.pb,
                "turnover_rate": r.turnover_rate,
            }
            for r in rows
        ]
        logger.debug(
            "valuation: ts_code=%s, start=%s, end=%s, points=%d",
            ts_code,
            start_date,
            end_date,
            len(points),
        )
        return {
            "success": True,
            "data": _dict_to_camel(
                {
                    "ts_code": ts_code,
                    "points": points,
                    "has_data": True,
                }
            ),
        }
    except Exception:
        logger.exception(
            "get_valuation error, ts_code=%s, start_date=%s, end_date=%s",
            ts_code,
            start_date,
            end_date,
        )
        raise


@router.get("/weights")
async def get_weights(
    index_code: str = Query(..., description="指数代码（如 000300.SH）"),
    top_n: int = Query(20, ge=1, le=100, description="返回前 N 权重股（默认 20）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    成分权重 + 集中度（AC-04）。

    逻辑：
    - 取该指数最近一个 trade_date 的权重记录；
    - ORDER BY weight DESC 取前 N；
    - LEFT JOIN stocks 表取成分股 name（con_code ↔ Stock.ts_code，格式都是 .SH/.SZ），
      无匹配显示 con_code 作为 fallback；
    - 计算集中度 top5 / top10（基于最近月全量权重合计）。

    返回 { success, data: { indexCode, tradeDate, weights, concentration: {top5, top10} } }。
    """
    try:
        # 1. 找最近 trade_date
        latest_date_res = await session.execute(
            select(func.max(IndexWeight.trade_date)).where(
                IndexWeight.index_code == index_code
            )
        )
        latest_date = latest_date_res.scalar_one_or_none()

        if latest_date is None:
            logger.debug("weights: index_code=%s 无权重数据", index_code)
            return {
                "success": True,
                "data": _dict_to_camel(
                    {
                        "index_code": index_code,
                        "trade_date": None,
                        "weights": [],
                        "concentration": {"top5": None, "top10": None},
                    }
                ),
            }

        # 2. 取最近 trade_date 的全部权重记录（用于集中度计算）
        all_res = await session.execute(
            select(IndexWeight.con_code, IndexWeight.weight)
            .where(
                IndexWeight.index_code == index_code,
                IndexWeight.trade_date == latest_date,
            )
            .order_by(IndexWeight.weight.desc())
        )
        all_rows = all_res.all()

        # 3. 取前 N 条并 JOIN stocks 取 name
        top_rows = all_rows[:top_n]
        top_con_codes = [r[0] for r in top_rows]

        name_res = await session.execute(
            select(Stock.ts_code, Stock.name).where(Stock.ts_code.in_(top_con_codes))
        )
        name_map = {row[0]: row[1] for row in name_res.all()}

        weights = [
            {
                "con_code": con_code,
                "name": name_map.get(con_code) or con_code,  # 无匹配 fallback 显示 con_code
                "weight": weight,
            }
            for con_code, weight in top_rows
        ]

        # 4. 集中度：基于最近月全量权重，前5/前10 合计
        sorted_weights = [float(r[1]) for r in all_rows if r[1] is not None]
        top5 = sum(sorted_weights[:5]) if len(sorted_weights) >= 1 else None
        top10 = sum(sorted_weights[:10]) if len(sorted_weights) >= 1 else None

        logger.debug(
            "weights: index_code=%s, trade_date=%s, total=%d, top_n=%d, returned=%d",
            index_code,
            latest_date,
            len(all_rows),
            top_n,
            len(weights),
        )
        return {
            "success": True,
            "data": _dict_to_camel(
                {
                    "index_code": index_code,
                    "trade_date": latest_date,
                    "weights": weights,
                    "concentration": {"top5": top5, "top10": top10},
                }
            ),
        }
    except Exception:
        logger.exception(
            "get_weights error, index_code=%s, top_n=%d", index_code, top_n
        )
        raise


@router.get("/watchlist")
async def get_watchlist(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    关注清单（AC-07）。

    查 index_basic WHERE is_watched=true，每项返回
    { tsCode, name, market, hasValuation }，其中 hasValuation 表示该指数
    是否在 index_dailybasic 有估值数据。
    """
    try:
        res = await session.execute(
            select(IndexBasic).where(IndexBasic.is_watched.is_(True))
        )
        watched = res.scalars().all()

        if not watched:
            logger.debug("watchlist: 无关注指数")
            return {"success": True, "data": _dict_to_camel({"watchlist": []})}

        ts_codes = [b.ts_code for b in watched]

        # 查哪些指数在 dailybasic 有数据
        val_res = await session.execute(
            select(IndexDailyBasic.ts_code)
            .where(IndexDailyBasic.ts_code.in_(ts_codes))
            .distinct()
        )
        has_val_codes = {row[0] for row in val_res.all()}

        watchlist = [
            {
                "ts_code": b.ts_code,
                "name": b.name,
                "market": b.market,
                "has_valuation": b.ts_code in has_val_codes,
            }
            for b in watched
        ]
        logger.debug("watchlist: count=%d", len(watchlist))
        return {"success": True, "data": _dict_to_camel({"watchlist": watchlist})}
    except Exception:
        logger.exception("get_watchlist error")
        raise


@router.put("/watchlist")
async def update_watchlist(
    body: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    全量更新关注清单（AC-07）。

    body: { "ts_codes": ["000300.SH", ...] } — 全量列表。

    逻辑：
    1. UPDATE index_basic SET is_watched=false（清空）；
    2. UPDATE index_basic SET is_watched=true WHERE ts_code IN(...)（设置新列表）。

    返回 { success, data: { updated: N } }（N = 实际命中的行数）。
    """
    try:
        ts_codes_raw = body.get("ts_codes", []) if isinstance(body, dict) else []
        ts_codes = [str(c).strip() for c in ts_codes_raw if str(c).strip()]

        # 1. 清空关注标记
        await session.execute(update(IndexBasic).values(is_watched=False))

        # 2. 设置新列表
        updated = 0
        if ts_codes:
            res = await session.execute(
                update(IndexBasic)
                .where(IndexBasic.ts_code.in_(ts_codes))
                .values(is_watched=True)
            )
            updated = res.rowcount or 0

        await session.commit()
        logger.debug("update_watchlist: requested=%d, updated=%d", len(ts_codes), updated)
        return {"success": True, "data": _dict_to_camel({"updated": updated})}
    except Exception:
        await session.rollback()
        logger.exception("update_watchlist error, body=%s", body)
        raise
