"""
ETF 监控查询 API 路由（第 14 期 plan-03）

端点：
- GET /api/v1/etf-monitor/index-rankings — 指数排行（维度/排序/日期/分页/聚合=各ETF之和）
  （AC-01/02/03/05/13）
- GET /api/v1/etf-monitor/index-detail  — 指数下 ETF 明细（按 netInflow 降序）（AC-04）
- GET /api/v1/etf-monitor/trend         — 指数/单只 × 指标 × 区间 / 完全无数据 hasData=false
  （AC-06/07/08/09）
- GET /api/v1/etf-monitor/latest-date   — 最新有数据交易日

复用声明：
- 路由 + helper 范式：src/api/v1/sector_fund_flow.py（_dict_to_camel / _serialize_value /
  {success,data} 包裹 / Depends(get_current_user)）
- Service：src/services/etf_monitor_service.py

契约（架构 §7.3 + plan-03 §3 #2）：
- 路径：router prefix /etf-monitor + v1 主路由 prefix /v1 = /api/v1/etf-monitor/*
- query 参数名全 snake_case（category/trade_date/sort_by/order/page/page_size/
  index_name/target_type/target_code/metric/days/end_date）
- sort_by/metric 参数值 camelCase（架构 §7.6 特例）
- 响应：{ success: bool, data: {...} } 包裹，data 内字段经 _dict_to_camel 转 camelCase
- 安全（架构 §8.3）：业务 GET 用 get_current_user；query 参数 SQLAlchemy 参数化查询防注入
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_session
from src.models.user import User
from src.services.etf_monitor_service import EtfMonitorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/etf-monitor", tags=["EtfMonitor"])


# ============== Helper ==============


def _serialize_value(val):
    """将 Decimal / date 等类型序列化为 JSON 安全类型（与 sector_fund_flow.py 一致）"""
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


@router.get("/index-rankings")
async def get_index_rankings(
    category: str = Query("broad", description="指数维度: broad/industry/other（默认 broad）"),
    trade_date: Optional[date] = Query(None, description="交易日（YYYY-MM-DD，默认取最新）"),
    sort_by: str = Query(
        "netInflow", description="排序字段: netInflow/shareChange/share（参数值 camelCase，默认 netInflow）"
    ),
    order: str = Query("desc", description="排序方向: desc/asc（默认 desc）"),
    page: int = Query(1, ge=1, description="页码（1-based）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量（上限 100）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    指数排行（AC-01/02/03/05/13）。

    返回按 index_name 聚合的指数列表，每项含 etfCount/totalShare/totalShareChange/
    totalNetInflow（归集 = 该指数各 ETF 之和），按 sort_by + order 排序并分页。
    份额输出亿份（÷10000）；net_inflow 亿元直接 SUM。
    """
    service = EtfMonitorService(session)
    try:
        result = await service.get_index_rankings(
            category=category,
            trade_date=trade_date,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
        )
    except Exception:
        logger.exception(
            "get_index_rankings error, category=%s, trade_date=%s, sort_by=%s, order=%s, page=%d, page_size=%d",
            category, trade_date, sort_by, order, page, page_size,
        )
        raise
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/index-detail")
async def get_index_detail(
    index_name: str = Query(..., description="指数名（如 沪深300）"),
    category: Optional[str] = Query(None, description="指数维度: broad/industry/other（可选）"),
    trade_date: Optional[date] = Query(None, description="交易日（YYYY-MM-DD，默认取最新）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    指数明细（AC-04）。

    返回该指数下的 ETF 明细（tsCode/name/unitNav/share/shareChange/netInflow/
    changePercent），按 netInflow 降序。份额输出亿份（÷10000）。
    """
    service = EtfMonitorService(session)
    try:
        result = await service.get_index_detail(
            index_name=index_name,
            category=category,
            trade_date=trade_date,
        )
    except Exception:
        logger.exception(
            "get_index_detail error, index_name=%s, category=%s, trade_date=%s",
            index_name, category, trade_date,
        )
        raise
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/trend")
async def get_trend(
    target_type: str = Query(..., description="对象类型: index（指数）/ etf（单只ETF）"),
    target_code: str = Query(..., description="对象代码: 指数名（沪深300）或 ts_code（510300.SH）"),
    metric: str = Query("netInflow", description="指标: share（份额）/ netInflow（净流入额，参数值 camelCase，默认 netInflow）"),
    days: int = Query(30, ge=1, le=365, description="区间交易日数（实际有数据的最近 N 个交易日）"),
    end_date: Optional[date] = Query(None, description="区间结束日（YYYY-MM-DD，默认取最新）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    历史趋势（AC-06/07/08/09）。

    返回 target_type(index/etf) + target_code + metric(share/netInflow) 在最近 days 个
    交易日（trade_date <= end_date）的时间序列，trade_date 升序。
    target_type=index 时按 index_name 聚合 SUM（指数各 ETF 之和）；target_type=etf 取单只。
    份额输出亿份（÷10000）；net_inflow 亿元。完全无数据返回 hasData=false + 空 series。
    """
    service = EtfMonitorService(session)
    try:
        result = await service.get_trend(
            target_type=target_type,
            target_code=target_code,
            metric=metric,
            days=days,
            end_date=end_date,
        )
    except Exception:
        logger.exception(
            "get_trend error, target_type=%s, target_code=%s, metric=%s, days=%d, end_date=%s",
            target_type, target_code, metric, days, end_date,
        )
        raise
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/latest-date")
async def get_latest_date(
    category: str = Query("broad", description="指数维度: broad/industry/other（默认 broad）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    最新交易日（日期选择器默认定位）。

    返回该 category 下 etf_daily 最大 trade_date（YYYY-MM-DD 或 null）。
    """
    service = EtfMonitorService(session)
    try:
        result = await service.get_latest_date(category=category)
    except Exception:
        logger.exception("get_latest_date error, category=%s", category)
        raise
    return {"success": True, "data": _dict_to_camel(result)}
