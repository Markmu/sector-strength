"""
涨停专题查询 API 路由（连板天梯）

端点：
- GET /api/v1/limit/ladder      — 单日连板天梯（板块统计 + 按连板数分层个股）
- GET /api/v1/limit/multi-days  — 多日连板统计表格
- GET /api/v1/limit/list        — 当日涨停个股平铺列表（分页）
- GET /api/v1/limit/latest-date — 最新有数据交易日

复用声明：
- 路由 + helper 范式：src/api/v1/etf_monitor.py（_dict_to_camel / _serialize_value /
  {success,data} 包裹 / Depends(get_current_user)）
- Service：src/services/limit_service.py

契约：
- 路径：router prefix /limit + v1 主路由 prefix /v1 = /api/v1/limit/*
- query 参数名全 snake_case
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
from src.services.limit_service import LimitService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/limit", tags=["Limit"])


# ============== Helper ==============


def _serialize_value(val):
    """将 Decimal / date 等类型序列化为 JSON 安全类型"""
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


@router.get("/ladder")
async def get_ladder(
    trade_date: Optional[date] = Query(None, description="交易日（YYYY-MM-DD，默认取最新）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """单日连板天梯（默认视图）。

    返回涨停最强板块统计 + 按 limit_times（连板数）降序分层的涨停个股。
    """
    service = LimitService(session)
    try:
        result = await service.get_ladder(trade_date=trade_date)
    except Exception:
        logger.exception("get_ladder error, trade_date=%s", trade_date)
        raise
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/multi-days")
async def get_multi_days(
    end_date: Optional[date] = Query(None, description="截止交易日（默认取最新）"),
    days: int = Query(5, ge=1, le=30, description="回溯天数（1-30，默认 5）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """多日连板统计表格视图。取 end_date 之前最近 N 个交易日的每日连板统计。"""
    service = LimitService(session)
    try:
        result = await service.get_ladder_multi_days(end_date=end_date, days=days)
    except Exception:
        logger.exception("get_multi_days error, end_date=%s, days=%d", end_date, days)
        raise
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/list")
async def get_list(
    trade_date: Optional[date] = Query(None, description="交易日（YYYY-MM-DD，默认取最新）"),
    limit_type: Optional[str] = Query(
        None, description="类型筛选: U涨停 / D跌停 / Z炸板（默认全部）"
    ),
    page: int = Query(1, ge=1, description="页码（1-based）"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量（上限 200）"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """当日涨停个股平铺列表（列表视图，分页）。"""
    service = LimitService(session)
    try:
        result = await service.get_ladder_list(
            trade_date=trade_date,
            limit_type=limit_type,
            page=page,
            page_size=page_size,
        )
    except Exception:
        logger.exception(
            "get_list error, trade_date=%s, limit_type=%s, page=%d, page_size=%d",
            trade_date, limit_type, page, page_size,
        )
        raise
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/latest-date")
async def get_latest_date(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """最新有数据交易日。"""
    service = LimitService(session)
    try:
        result = await service.get_latest_date()
    except Exception:
        logger.exception("get_latest_date error")
        raise
    return {"success": True, "data": _dict_to_camel(result)}
