"""
基金扎堆股票分析 API 路由（08 期 plan-01）

端点：
- GET /api/v1/fund-crowd-analysis/rankings — 扎堆度排行榜（AC-01/02/03/06/07/08）
- GET /api/v1/fund-crowd-analysis/industry-distribution — 行业分布（AC-04）

复用声明：
- Pydantic to_camel 范式：src/api/v1/funds.py:30-80
- _dict_to_camel / _serialize_value helper：src/api/v1/funds.py:106-124
- Depends(get_current_user) 普通用户认证：与 04/06 一致（非 admin，普通登录用户即可访问）

契约（架构 §7.3 + plan-01 §3 #4/#5）：
- 路径：/api/v1/fund-crowd-analysis/rankings + /industry-distribution（无重复前缀）
- HTTP 方法：GET
- query 参数：scope / search / page / page_size（snake_case）
- 响应：{ success: bool, data: {...} } 包裹，data 内字段经 _dict_to_camel 转 camelCase
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, get_session
from src.models.user import User
from src.services.fund_crowd_analysis_service import FundCrowdAnalysisService
from src.services.data_acquisition.sector_types import is_valid_sector_type

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fund-crowd-analysis", tags=["FundCrowdAnalysis"])


# ============== Pydantic Response Models ==============


class RankingItem(BaseModel):
    """扎堆排行榜单项（API 输出视角 camelCase）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    stock_symbol: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称（stocks 表缺失为 null）")
    industries: list[str] = Field(default_factory=list, description="行业列表（一股多行业）")
    fund_count: int = Field(
        ...,
        description="被多少只基金持有（份额去重 COUNT DISTINCT regexp_replace(Fund.name, '[ACDEHIR]$', ''))",
    )
    fund_count_change: Optional[int] = Field(
        None, description="环比变化基金数（上期无记录或无上期为 null）"
    )
    is_new: Optional[bool] = Field(
        None, description="是否本期新进（has_prev_period=false 时为 null）"
    )


class RankingsData(BaseModel):
    """扎堆排行榜响应数据"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    has_data: bool
    current_period: Optional[str] = Field(None, description="最新报告期（ISO 字符串）")
    prev_period: Optional[str] = Field(None, description="上一报告期（无上期为 null）")
    has_prev_period: bool
    items: list[RankingItem]
    total: int
    page: int
    page_size: int


class IndustryItem(BaseModel):
    """行业分布单项"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    industry: str
    stock_count: int = Field(..., description="该行业扎堆股数量（COUNT DISTINCT）")
    percentage: float = Field(..., description="扎堆股数量占比（%）")


class IndustryDistributionData(BaseModel):
    """行业分布响应数据"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    has_data: bool
    current_period: Optional[str] = None
    distribution: list[IndustryItem]


# ============== Helper ==============


def _serialize_value(val):
    """将 Decimal / date 等类型序列化为 JSON 安全类型（与 funds.py 一致）"""
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
    scope: str = Query(
        "active", description="基金口径：active=仅主动基金（默认），all=全部基金"
    ),
    search: Optional[str] = Query(
        None, description="股票代码前缀或名称包含（不区分大小写）"
    ),
    page: int = Query(1, ge=1, description="页码（1-based）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sector_type: Optional[str] = Query(
        None,
        description="板块类型: industry/concept/region/feature/style/theme（默认 industry）",
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    扎堆度排行榜（AC-01/02/03/06/07/08）

    返回最新报告期扎堆度排行榜，按 fund_count（份额去重 COUNT DISTINCT
    regexp_replace(Fund.name, '[ACDEHIR]$', '')）降序、相同时按 stock_symbol 升序
    次排序。scope=active 排除被动型基金；上一期存在时环比字段按 stock_symbol
    内存对比（含"新进"判定）。
    """
    # scope 容错（边界场景：非 active/all → 默认 active）
    if scope not in ("active", "all"):
        scope = "active"
    # sector_type 容错（None/非法 → 默认 industry，与 scope 容错范式一致）
    if sector_type is None or not is_valid_sector_type(sector_type):
        sector_type = "industry"

    service = FundCrowdAnalysisService(session)
    result = await service.get_rankings(
        scope=scope,
        search=search,
        page=page,
        page_size=page_size,
        sector_type=sector_type,
    )
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/industry-distribution")
async def get_industry_distribution(
    scope: str = Query(
        "active", description="基金口径：active=仅主动基金（默认），all=全部基金"
    ),
    sector_type: Optional[str] = Query(
        None,
        description="板块类型: industry/concept/region/feature/style/theme（默认 industry）",
    ),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    行业分布（AC-04）

    按行业聚合扎堆股数量占比；一股多行业独立计数；
    无行业关联归「未分类」桶；按 stock_count 降序。
    """
    if scope not in ("active", "all"):
        scope = "active"
    if sector_type is None or not is_valid_sector_type(sector_type):
        sector_type = "industry"

    service = FundCrowdAnalysisService(session)
    result = await service.get_industry_distribution(
        scope=scope, sector_type=sector_type
    )
    return {"success": True, "data": _dict_to_camel(result)}
