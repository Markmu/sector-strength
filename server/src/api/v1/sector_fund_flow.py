"""
板块资金流查询 API 路由（13 期 plan-02）

端点：
- GET /api/v1/sector-fund-flow/rankings — 资金流排行榜（最新采样点）（AC-01/02/03/04/10/12）
- GET /api/v1/sector-fund-flow/timeseries — 盘中变化曲线（按板块名分组）（AC-06/08）
- GET /api/v1/sector-fund-flow/latest-date — 最新交易日

复用声明：
- 路由 + helper 范式：src/api/v1/fund_crowd_analysis.py（_dict_to_camel / _serialize_value / {success,data} 包裹 / Depends(get_current_user)）
- sector_type 容错：src/services/data_acquisition/sector_types.is_valid_sector_type
- Service：src/services/sector_fund_flow_service.py

契约（架构 §7.3 + plan-02 §3 #2）：
- 路径：router prefix /sector-fund-flow + v1 主路由 prefix /v1 = /api/v1/sector-fund-flow/*
- query 参数 snake_case：sector_type / trade_date / sort_by / order / page / page_size / sector_names
- 响应：{ success: bool, data: {...} } 包裹，data 内字段经 _dict_to_camel 转 camelCase
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
from src.services.data_acquisition.sector_types import is_valid_sector_type
from src.services.sector_fund_flow_service import SectorFundFlowService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sector-fund-flow", tags=["SectorFundFlow"])


# ============== Helper ==============


def _serialize_value(val):
    """将 Decimal / date 等类型序列化为 JSON 安全类型（与 fund_crowd_analysis.py 一致）"""
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


@router.get("/rankings")
async def get_rankings(
    sector_type: str = Query(
        "industry", description="板块类型: industry/concept/region（默认 industry）"
    ),
    trade_date: Optional[date] = Query(None, description="交易日（YYYY-MM-DD，可选，默认取最新）"),
    sort_by: str = Query(
        "net_inflow", description="排序字段: net_inflow/inflow/outflow（默认 net_inflow）"
    ),
    order: str = Query("desc", description="排序方向: desc/asc（默认 desc）"),
    page: int = Query(1, ge=1, description="页码（1-based）"),
    page_size: int = Query(20, ge=1, le=500, description="每页数量（上限 500，支持变化视图全量取板块候选）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    板块资金流排行榜（AC-01/02/03/04/10/12）。

    返回最新采样点的板块资金流排行，按 sort_by + order 排序并分页。
    每个板块仅保留该交易日最新一次采样；sector_id 通过 LEFT JOIN sectors
    按 sector_name 匹配取（匹配不上为 null）。
    """
    # sector_type 容错（None/非法 → 默认 industry）
    if sector_type is None or not is_valid_sector_type(sector_type):
        sector_type = "industry"

    service = SectorFundFlowService(session)
    try:
        result = await service.get_rankings(
            sector_type=sector_type,
            trade_date=trade_date,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
        )
    except Exception:
        logger.exception(
            "get_rankings error, sector_type=%s, trade_date=%s, sort_by=%s, order=%s, page=%d, page_size=%d",
            sector_type,
            trade_date,
            sort_by,
            order,
            page,
            page_size,
        )
        raise
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/timeseries")
async def get_timeseries(
    sector_names: Optional[str] = Query(
        None, description="板块名列表（逗号分隔，如 电网设备,半导体）"
    ),
    sector_type: str = Query(
        "industry", description="板块类型: industry/concept/region（默认 industry）"
    ),
    trade_date: Optional[date] = Query(None, description="交易日（YYYY-MM-DD，可选，默认取最新）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    盘中资金流变化曲线（AC-06/08）。

    返回指定板块名（逗号分隔）在指定交易日下的净额时间序列，
    按板块名分组、sample_time 升序。无数据返回 has_data=false + 空 series。
    """
    # sector_type 容错
    if sector_type is None or not is_valid_sector_type(sector_type):
        sector_type = "industry"

    # sector_names 逗号分隔 → list（strip，过滤空串）
    names_list: list[str] = []
    if sector_names:
        names_list = [n.strip() for n in sector_names.split(",") if n.strip()]

    service = SectorFundFlowService(session)
    try:
        result = await service.get_timeseries(
            sector_names=names_list,
            sector_type=sector_type,
            trade_date=trade_date,
        )
    except Exception:
        logger.exception(
            "get_timeseries error, sector_names=%s, sector_type=%s, trade_date=%s",
            sector_names,
            sector_type,
            trade_date,
        )
        raise
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/latest-date")
async def get_latest_date(
    sector_type: str = Query(
        "industry", description="板块类型: industry/concept/region（默认 industry）"
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    最新交易日（AC 隐含）。

    返回 sector_fund_flow 表中该 sector_type 下的最大 trade_date（YYYY-MM-DD 或 null）。
    """
    # sector_type 容错
    if sector_type is None or not is_valid_sector_type(sector_type):
        sector_type = "industry"

    service = SectorFundFlowService(session)
    try:
        result = await service.get_latest_date(sector_type=sector_type)
    except Exception:
        logger.exception("get_latest_date error, sector_type=%s", sector_type)
        raise
    return {"success": True, "data": _dict_to_camel(result)}
