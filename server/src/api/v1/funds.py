"""
基金业务 API 路由

提供基金列表、详情、持仓、反查等 REST API 端点。
"""

import logging
from typing import Optional
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, get_current_user
from src.api.exceptions import NotFoundError
from src.api.schemas.response import ApiResponse, PaginatedData
from src.models.user import User
from src.repositories.fund_repository import FundRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/funds", tags=["Funds"])


# ============== Pydantic Response Models ==============


class FundOut(BaseModel):
    """基金基本信息输出"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    ts_code: str = Field(..., description="TS代码")
    name: str = Field(..., description="基金名称")
    management: Optional[str] = Field(None, description="管理人")
    custodian: Optional[str] = Field(None, description="托管人")
    fund_type: Optional[str] = Field(None, description="基金类型")
    invest_type: Optional[str] = Field(None, description="投资类型")
    benchmark: Optional[str] = Field(None, description="业绩比较基准")
    market: Optional[str] = Field(None, description="市场类型")
    found_date: Optional[date] = Field(None, description="成立日期")
    list_date: Optional[date] = Field(None, description="上市日期")
    delist_date: Optional[date] = Field(None, description="退市日期")
    status: Optional[str] = Field(None, description="状态")
    has_portfolio: Optional[bool] = Field(None, description="是否有持仓记录")


class FundListOut(BaseModel):
    """基金列表项（含 has_portfolio）"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    ts_code: str = Field(..., description="TS代码")
    name: str = Field(..., description="基金名称")
    management: Optional[str] = Field(None, description="管理人")
    custodian: Optional[str] = Field(None, description="托管人")
    fund_type: Optional[str] = Field(None, description="基金类型")
    invest_type: Optional[str] = Field(None, description="投资类型")
    benchmark: Optional[str] = Field(None, description="业绩比较基准")
    market: Optional[str] = Field(None, description="市场类型")
    found_date: Optional[date] = Field(None, description="成立日期")
    list_date: Optional[date] = Field(None, description="上市日期")
    delist_date: Optional[date] = Field(None, description="退市日期")
    status: Optional[str] = Field(None, description="状态")
    has_portfolio: Optional[bool] = Field(None, description="是否有持仓记录")


class FundPortfolioOut(BaseModel):
    """基金持仓明细输出"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    fund_ts_code: str = Field(..., description="基金TS代码")
    report_period: Optional[date] = Field(None, description="报告期")
    ann_date: Optional[date] = Field(None, description="公告日期")
    stock_symbol: str = Field(..., description="持仓股票代码")
    stock_name: Optional[str] = Field(None, description="持仓股票名称")
    market_value: Optional[float] = Field(None, description="持仓市值")
    amount: Optional[float] = Field(None, description="持仓数量")
    stk_mkv_ratio: Optional[float] = Field(None, description="占股票市值比")
    stk_float_ratio: Optional[float] = Field(None, description="占流通股比")


class ReverseLookupItem(BaseModel):
    """反查结果项"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    fund_ts_code: str = Field(..., description="基金TS代码")
    fund_name: Optional[str] = Field(None, description="基金名称")
    fund_type: Optional[str] = Field(None, description="基金类型")
    management: Optional[str] = Field(None, description="管理人")
    stock_symbol: str = Field(..., description="股票代码")
    report_period: Optional[date] = Field(None, description="报告期")
    stk_mkv_ratio: Optional[float] = Field(None, description="占股票市值比")
    stk_float_ratio: Optional[float] = Field(None, description="占流通股比")
    market_value: Optional[float] = Field(None, description="持仓市值")
    amount: Optional[float] = Field(None, description="持仓数量")


# ============== Helper ==============


def _serialize_value(val):
    """将 Decimal / date 等类型序列化为 JSON 安全类型"""
    if val is None:
        return None
    from decimal import Decimal
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (date, datetime)):
        return val.isoformat() if not isinstance(val, datetime) else val.isoformat()
    return val


def _dict_to_camel(d: dict) -> dict:
    """将字典的 snake_case 键转为 camelCase"""
    result = {}
    for k, v in d.items():
        camel_key = to_camel(k)
        result[camel_key] = _serialize_value(v)
    return result


# ============== Endpoints ==============


@router.get("")
async def list_funds(
    search: Optional[str] = Query(None, description="搜索关键词（ts_code前缀或名称包含）"),
    market: Optional[str] = Query(None, description="市场类型: E=场内, O=场外"),
    fund_type: Optional[str] = Query(None, description="基金类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    获取基金列表

    支持搜索（ts_code 前缀 + 名称包含，不区分大小写）、市场过滤、类型过滤、分页。
    列表项包含 has_portfolio 标记（L1 降级支持）。
    """
    repo = FundRepository(session)
    items, total = await repo.list_with_filters(
        search=search,
        market=market,
        fund_type=fund_type,
        page=page,
        page_size=page_size,
    )

    # 转换为 camelCase 字典
    camel_items = [_dict_to_camel(item) for item in items]

    paginated = PaginatedData.create(camel_items, total, page, page_size)
    camel_data = _dict_to_camel(paginated.model_dump())
    camel_data["items"] = camel_items  # items 已经是 camelCase，避免二次转换
    return {"success": True, "data": camel_data}


@router.get("/reverse-lookup")
async def reverse_lookup(
    symbol: str = Query(..., min_length=1, description="股票代码（纯数字或带后缀如 600519.SH）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    股票反查：查询重仓该股票的基金列表

    仅返回 stk_mkv_ratio >= 1.0 的记录，按占净值比降序。
    symbol 格式归一化：接受纯数字或带后缀。
    """
    repo = FundRepository(session)
    items, total, meta = await repo.reverse_lookup(
        symbol=symbol,
        page=page,
        page_size=page_size,
    )

    # 如果股票不存在，返回 404
    if meta.get("stock_name") is None:
        raise NotFoundError(f"Stock not found: {symbol}")

    # 转换为 camelCase 字典
    camel_items = [_dict_to_camel(item) for item in items]
    camel_meta = _dict_to_camel(meta)

    paginated = PaginatedData.create(camel_items, total, page, page_size)
    camel_data = _dict_to_camel(paginated.model_dump())
    camel_data["items"] = camel_items  # items 已经是 camelCase，避免二次转换
    # 将元信息合并到分页数据中
    camel_data.update(camel_meta)

    return {"success": True, "data": camel_data}


@router.get("/{ts_code}")
async def get_fund_detail(
    ts_code: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    获取基金详情

    根据 ts_code 查询单条基金基本信息。
    """
    repo = FundRepository(session)
    fund = await repo.get_by_ts_code(ts_code)

    if not fund:
        raise NotFoundError(f"Fund not found: {ts_code}")

    # 转换为字典并序列化
    data = {
        "ts_code": fund.ts_code,
        "name": fund.name,
        "management": fund.management,
        "custodian": fund.custodian,
        "fund_type": fund.fund_type,
        "invest_type": fund.invest_type,
        "benchmark": fund.benchmark,
        "market": fund.market,
        "found_date": _serialize_value(fund.found_date),
        "list_date": _serialize_value(fund.list_date),
        "delist_date": _serialize_value(fund.delist_date),
        "status": fund.status,
    }
    camel_data = _dict_to_camel(data)

    return {"success": True, "data": camel_data}


@router.get("/{ts_code}/portfolio")
async def get_fund_portfolio(
    ts_code: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    获取基金最新持仓明细

    返回该基金最新报告期的持仓列表，按 stk_mkv_ratio DESC 排序。
    附带元信息：isPortfolioEmpty / hasPortfolio / latestReportPeriod / latestAnnDate
    """
    repo = FundRepository(session)

    # 先检查基金是否存在
    fund = await repo.get_by_ts_code(ts_code)
    if not fund:
        raise NotFoundError(f"Fund not found: {ts_code}")

    items, total, meta = await repo.get_latest_portfolio(
        fund_ts_code=ts_code,
        page=page,
        page_size=page_size,
    )

    # 转换为 camelCase 字典
    camel_items = [_dict_to_camel(item) for item in items]
    camel_meta = _dict_to_camel(meta)

    paginated = PaginatedData.create(camel_items, total, page, page_size)
    camel_data = _dict_to_camel(paginated.model_dump())
    camel_data["items"] = camel_items  # items 已经是 camelCase，避免二次转换
    # 将元信息合并到分页数据中
    camel_data.update(camel_meta)

    return {"success": True, "data": camel_data}
