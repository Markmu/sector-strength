"""股东分析聚合查询 API 路由（plan-02）

提供四个用户侧 GET 端点：
- GET /api/v1/shareholder-analysis/overview          — 监控组概览
- GET /api/v1/shareholder-analysis/summary           — 汇总统计 + 变动趋势
- GET /api/v1/shareholder-analysis/industry-distribution — 行业分布
- GET /api/v1/shareholder-analysis/holdings          — 分页持仓列表

参照 funds.py：路由文件内声明 prefix，response 使用 ApiResponse[T] 包裹，
Pydantic model 配置 alias_generator=to_camel + populate_by_name=True。
Decimal → float 由 service 层显式转换（避免前端拿到字符串）。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_session
from src.api.schemas.response import ApiResponse
from src.models.user import User
from src.services.shareholder_analysis_service import ShareholderAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shareholder-analysis", tags=["Shareholder Analysis"])


# ============== Pydantic Response Models ==============


class GroupOverviewItem(BaseModel):
    """监控组概览项（camelCase 输出）"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    group_id: int = Field(..., description="监控组ID")
    group_name: str = Field(..., description="监控组名称")
    description: Optional[str] = Field(None, description="描述")
    stock_count: int = Field(..., description="持仓股票数")
    increase_count: int = Field(..., description="增持股票数")
    decrease_count: int = Field(..., description="减持股票数")
    new_count: int = Field(..., description="新进股票数")
    exit_count: int = Field(..., description="退出股票数")


class OverviewData(BaseModel):
    """监控组概览数据"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    report_periods: List[str] = Field(default_factory=list, description="报告期列表")
    current_period: Optional[str] = Field(None, description="当前报告期")
    has_prev_period: bool = Field(..., description="是否有上一期数据")
    groups: List[GroupOverviewItem] = Field(default_factory=list, description="监控组概览列表")


class SummaryData(BaseModel):
    """汇总统计数据"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    stock_count: int = Field(..., description="持仓股票数")
    total_hold_amount: float = Field(..., description="总持股数")
    avg_hold_float_ratio: float = Field(..., description="平均占流通比")


class TrendData(BaseModel):
    """变动趋势数据"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    increase_count: int = Field(..., description="增持股票数")
    decrease_count: int = Field(..., description="减持股票数")
    new_count: int = Field(..., description="新进股票数")
    exit_count: int = Field(..., description="退出股票数")


class SummaryResponse(BaseModel):
    """汇总 + 趋势响应"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    summary: SummaryData
    trend: TrendData
    has_prev_period: bool


class IndustryItem(BaseModel):
    """行业分布项"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    industry: str = Field(..., description="行业名称")
    stock_count: int = Field(..., description="该行业股票数")
    percentage: float = Field(..., description="占比(%)")


class IndustryDistributionData(BaseModel):
    """行业分布响应"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    distribution: List[IndustryItem] = Field(default_factory=list, description="行业分布列表")


class HoldingItem(BaseModel):
    """持仓股票项"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    symbol: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    total_hold_amount: float = Field(..., description="总持股数")
    total_hold_float_ratio: float = Field(..., description="总占流通比")
    change_direction: Optional[str] = Field(
        None, description="变动方向: increase/decrease/new/unchanged/exit"
    )
    industries: List[str] = Field(default_factory=list, description="所属行业列表")


class HoldingsData(BaseModel):
    """持仓列表响应"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    holdings: List[HoldingItem] = Field(default_factory=list, description="持仓股票列表")
    total: int = Field(..., description="符合条件的总记录数")


class HolderSearchItem(BaseModel):
    """股东搜索结果项（单股东维度入口）"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    holder_name: str = Field(..., description="股东名称(精确，选中后作为查询条件)")


class HolderSearchData(BaseModel):
    """股东搜索响应"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    holders: List[HolderSearchItem] = Field(
        default_factory=list, description="股东名称列表(全库去重)"
    )
    total: int = Field(..., description="去重后总数")


# ============== Helpers ==============


def _parse_group_ids(group_ids: Optional[str]) -> List[int]:
    """解析逗号分隔的 group_ids 字符串为 int 列表；None/空串返回 []。"""
    if not group_ids:
        return []
    result: List[int] = []
    for piece in group_ids.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            result.append(int(piece))
        except ValueError:
            continue
    return result


def _require_holder_filter(
    group_ids: Optional[str], holder_name: Optional[str]
) -> None:
    """校验 group_ids 与 holder_name 至少一个非空，否则抛 400。

    summary / industry-distribution / holdings 三端点共用：单股东维度
    （holder_name）与监控组维度（group_ids）二选一，不可同时为空。
    """
    has_group = bool(group_ids and group_ids.strip())
    has_holder = bool(holder_name and holder_name.strip())
    if not has_group and not has_holder:
        raise HTTPException(
            status_code=400,
            detail="group_ids 与 holder_name 至少需要传一个",
        )


def _to_camel_dict(d: dict) -> dict:
    """递归将 dict 的 snake_case 键转为 camelCase（嵌套 list/dict 也处理）。"""
    result = {}
    for k, v in d.items():
        camel_key = to_camel(k)
        if isinstance(v, dict):
            result[camel_key] = _to_camel_dict(v)
        elif isinstance(v, list):
            result[camel_key] = [
                _to_camel_dict(item) if isinstance(item, dict) else item for item in v
            ]
        else:
            result[camel_key] = v
    return result


# ============== Endpoints ==============


@router.get("/overview", response_model=ApiResponse[OverviewData])
async def get_overview(
    report_period: Optional[str] = Query(None, description="报告期(YYYY-MM-DD)，默认最新期"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """监控组概览：报告期列表 + 各监控组的持仓数与变动趋势统计。"""
    service = ShareholderAnalysisService(session)
    data = await service.get_overview(report_period=report_period)
    return {"success": True, "data": _to_camel_dict(data)}


@router.get("/summary", response_model=ApiResponse[SummaryResponse])
async def get_summary(
    group_ids: Optional[str] = Query(None, description="监控组ID列表(逗号分隔，与 holder_name 二选一)"),
    report_period: Optional[str] = Query(None, description="报告期(YYYY-MM-DD)"),
    industry: Optional[str] = Query(None, description="行业筛选"),
    change_direction: Optional[str] = Query(
        None, description="变动方向筛选: increase/decrease/new/unchanged/exit"
    ),
    holder_name: Optional[str] = Query(None, description="单股东精确名称(与 group_ids 二选一)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """汇总统计 + 变动趋势（trend 不受 change_direction 筛选影响）。"""
    _require_holder_filter(group_ids, holder_name)
    gid_list = _parse_group_ids(group_ids)
    service = ShareholderAnalysisService(session)
    data = await service.get_summary(
        group_ids=gid_list,
        report_period=report_period,
        industry=industry,
        change_direction=change_direction,
        holder_name=holder_name,
    )
    return {"success": True, "data": _to_camel_dict(data)}


@router.get(
    "/industry-distribution", response_model=ApiResponse[IndustryDistributionData]
)
async def get_industry_distribution(
    group_ids: Optional[str] = Query(None, description="监控组ID列表(逗号分隔，与 holder_name 二选一)"),
    report_period: Optional[str] = Query(None, description="报告期(YYYY-MM-DD)"),
    industry: Optional[str] = Query(
        None, description="行业筛选(本接口不生效，行业分布自身是筛选数据源)"
    ),
    change_direction: Optional[str] = Query(
        None, description="变动方向筛选: increase/decrease/new/unchanged/exit"
    ),
    holder_name: Optional[str] = Query(None, description="单股东精确名称(与 group_ids 二选一)"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """行业分布（不受 industry 筛选影响，受 change_direction 筛选影响）。"""
    _require_holder_filter(group_ids, holder_name)
    gid_list = _parse_group_ids(group_ids)
    service = ShareholderAnalysisService(session)
    data = await service.get_industry_distribution(
        group_ids=gid_list,
        report_period=report_period,
        change_direction=change_direction,
        holder_name=holder_name,
    )
    return {"success": True, "data": _to_camel_dict(data)}


@router.get("/holdings", response_model=ApiResponse[HoldingsData])
async def get_holdings(
    group_ids: Optional[str] = Query(None, description="监控组ID列表(逗号分隔，与 holder_name 二选一)"),
    report_period: Optional[str] = Query(None, description="报告期(YYYY-MM-DD)"),
    industry: Optional[str] = Query(None, description="行业筛选"),
    change_direction: Optional[str] = Query(
        None, description="变动方向筛选: increase/decrease/new/unchanged/exit"
    ),
    holder_name: Optional[str] = Query(None, description="单股东精确名称(与 group_ids 二选一)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """分页持仓列表（退出股票展示上期 total_hold_amount / total_hold_float_ratio）。"""
    _require_holder_filter(group_ids, holder_name)
    gid_list = _parse_group_ids(group_ids)
    service = ShareholderAnalysisService(session)
    data = await service.get_holdings(
        group_ids=gid_list,
        report_period=report_period,
        industry=industry,
        change_direction=change_direction,
        holder_name=holder_name,
        page=page,
        page_size=page_size,
    )
    return {"success": True, "data": _to_camel_dict(data)}


@router.get("/holders/search", response_model=ApiResponse[HolderSearchData])
async def search_holders(
    keyword: str = Query(..., min_length=1, description="股东名称关键词(LIKE 模糊匹配，全库去重)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """按股东名称模糊搜索（全库所有报告期 DISTINCT holder_name，分页）。

    单股东持仓查询的搜索入口：选中 holder_name 后用 summary / industry-distribution /
    holdings 端点（holder_name 参数）查询该股东的聚合统计。
    """
    service = ShareholderAnalysisService(session)
    data = await service.search_holders(
        keyword=keyword, page=page, page_size=page_size
    )
    return {"success": True, "data": _to_camel_dict(data)}
