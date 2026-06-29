"""券商月度金股分析 API 路由（09 期 plan-02）

端点：
- GET /api/v1/broker-recommend-analysis/months — 月份列表（AC-05/09）
- GET /api/v1/broker-recommend-analysis/stock-ranking — 股票维度排行（AC-02/03/06/07/10/11）
- GET /api/v1/broker-recommend-analysis/broker-list — 券商维度分组（AC-04/06/07/12）
- GET /api/v1/broker-recommend-analysis/broker-detail — 券商明细懒加载（AC-13）

复用声明：
- Pydantic to_camel / _dict_to_camel / _serialize_value helper：范式照搬 fund_crowd_analysis.py
- Depends(get_current_user) 普通用户认证：与 06/08 一致
- query 参数 snake_case（page_size），响应输出 camelCase
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
from src.services.broker_recommend_analysis_service import (
    BrokerRecommendAnalysisService,
)
from src.services.data_acquisition.sector_types import is_valid_sector_type

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/broker-recommend-analysis", tags=["BrokerRecommendAnalysis"]
)


# ============== Pydantic Response Models ==============


class BrokerBrief(BaseModel):
    """推荐券商简项（含聚合后的 reasons 数组）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    broker: str
    reasons: list[str] = Field(default_factory=list)


class StockRankingItem(BaseModel):
    """股票维度排行单项（API 输出视角 camelCase）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    symbol: str
    name: Optional[str] = Field(None, description="股票名称（stocks 表缺失为 null）")
    industries: list[str] = Field(default_factory=list, description="行业列表")
    broker_count: int = Field(..., description="推荐券商家数（COUNT DISTINCT broker）")
    brokers: list[BrokerBrief] = Field(
        default_factory=list, description="全部推荐券商及理由（预加载）"
    )


class BrokerGroupItem(BaseModel):
    """券商维度分组单项"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    broker: str
    stock_count: int = Field(..., description="本月推荐股票数")


class BrokerDetailItem(BaseModel):
    """券商明细单项（懒加载）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    symbol: str
    name: Optional[str] = Field(None, description="股票名称")
    reasons: list[str] = Field(
        default_factory=list, description="推荐理由数组（同 symbol 多记录合并去空去重）"
    )


class RankingData(BaseModel):
    """通用列表响应数据"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    has_data: bool
    month: Optional[str] = Field(None, description="当前月份（ISO 字符串 YYYY-MM-01）")
    total: int
    page: int
    page_size: int
    items: list = Field(default_factory=list)


class MonthsData(BaseModel):
    """月份列表响应数据"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    has_data: bool
    months: list[str] = Field(default_factory=list)


class SectorRankingItem(BaseModel):
    """板块排行榜单项"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    sector_name: str
    stock_count: int
    percentage: float


class SectorRankingsData(BaseModel):
    """三类型板块排行榜响应数据"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    has_data: bool
    month: Optional[str] = Field(None, description="当前月份（ISO 字符串）")
    industry: list[SectorRankingItem] = Field(default_factory=list)
    concept: list[SectorRankingItem] = Field(default_factory=list)
    region: list[SectorRankingItem] = Field(default_factory=list)


class BrokerDetailData(BaseModel):
    """券商明细响应数据"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[BrokerDetailItem] = Field(default_factory=list)


# ============== Helper（范式照搬 fund_crowd_analysis.py）==============


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


@router.get("/months")
async def get_months(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """已同步月份列表（AC-05/09）"""
    service = BrokerRecommendAnalysisService(session)
    result = await service.get_months()
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/stock-ranking")
async def get_stock_ranking(
    month: Optional[str] = Query(None, description="月份 YYYY-MM-DD（缺省取最新）"),
    search: Optional[str] = Query(None, description="股票代码前缀或名称包含"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    sector_type: Optional[str] = Query(
        None, description="板块类型: industry/concept/region（默认 industry）"
    ),
    sector_name: Optional[str] = Query(
        None, description="板块名称筛选（按 sector_type 精确匹配板块名）"
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """股票维度卖方共识排行榜（AC-02/03/06/07/10/11）

    支持按板块过滤：sector_type 选维度（行业/概念/地域），sector_name 选具体板块名。
    industries 列始终按 sector_type 维度展示当前板块归属。
    """
    # sector_type 容错（None/非法 → 默认 industry）
    if sector_type is None or not is_valid_sector_type(sector_type):
        sector_type = "industry"
    service = BrokerRecommendAnalysisService(session)
    result = await service.get_stock_ranking(
        month, search, page, page_size, sector_type=sector_type, sector_name=sector_name
    )
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/sector-rankings")
async def get_sector_rankings(
    month: Optional[str] = Query(None, description="月份 YYYY-MM-DD（缺省取最新）"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """三类型板块排行榜（行业/概念/地域，各 Top5，按被推荐股票数降序）"""
    service = BrokerRecommendAnalysisService(session)
    result = await service.get_sector_rankings(month)
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/broker-list")
async def get_broker_list(
    month: Optional[str] = Query(None, description="月份 YYYY-MM-DD（缺省取最新）"),
    search: Optional[str] = Query(None, description="券商名称包含"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """券商维度分组（AC-04/06/07/12）"""
    service = BrokerRecommendAnalysisService(session)
    result = await service.get_broker_list(month, search, page, page_size)
    return {"success": True, "data": _dict_to_camel(result)}


@router.get("/broker-detail")
async def get_broker_detail(
    month: str = Query(..., description="月份 YYYY-MM-DD（必填）"),
    broker: str = Query(..., description="券商名称（必填，精确匹配）"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """券商明细懒加载（AC-13）"""
    service = BrokerRecommendAnalysisService(session)
    result = await service.get_broker_detail(month, broker)
    return {"success": True, "data": _dict_to_camel(result)}
