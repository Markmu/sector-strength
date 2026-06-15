"""管理员股东监控组管理 API 端点

提供监控组的列表查询、新增、编辑、删除及匹配股数预览。
所有接口均需管理员权限。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.models.user import User
from src.services.shareholder_group_service import ShareholderGroupService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shareholder-groups", tags=["Admin - Shareholder Groups"])


# ============== 请求模型 ==============


class CreateGroupRequest(BaseModel):
    """新增分组请求"""

    name: str = Field(..., min_length=1, description="组名（唯一）")
    description: Optional[str] = Field(None, description="描述")
    keywords: List[str] = Field(default_factory=list, description="初始关键词列表")


class UpdateGroupRequest(BaseModel):
    """编辑分组请求（所有字段可选）"""

    name: Optional[str] = Field(None, description="新组名")
    description: Optional[str] = Field(None, description="新描述")
    keywords: Optional[List[str]] = Field(None, description="新关键词列表（整体替换）")


# ============== 响应模型（camelCase）==============


class GroupListItem(BaseModel):
    """分组列表项 — 字段经 to_camel 输出为 camelCase"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int = Field(..., description="分组ID")
    name: str = Field(..., description="组名")
    description: Optional[str] = Field(None, description="描述")
    sort_order: int = Field(..., description="排序权重")
    is_system: bool = Field(..., description="是否系统预定义")
    rule_count: int = Field(..., description="关键词规则数")
    matched_stock_count: int = Field(..., description="最新报告期匹配的去重股票数")
    keywords: List[str] = Field(default_factory=list, description="关键词列表")


class PreviewMatchResponse(BaseModel):
    """预览匹配股数响应"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    matched_stock_count: int = Field(..., description="匹配的去重股票数")


# ===== plan-01 新增响应模型 =====


class KeywordCountItem(BaseModel):
    """逐关键词股数项（plan-01 §3 #5）"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    keyword: str = Field(..., description="前端传入的草稿关键词原值")
    matched_stock_count: Optional[int] = Field(
        ..., description="该关键词单独匹配的去重股数；null 表示查询失败"
    )


class PreviewBreakdownData(BaseModel):
    """股数细分响应 data"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[KeywordCountItem] = Field(..., description="逐关键词股数列表")


class KeywordMatchItem(BaseModel):
    """单条明细项"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    symbol: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(
        None, description="股票名称；stocks 表缺失该 symbol 时为 null"
    )
    holder_name: str = Field(..., description="股东名称")


class KeywordMatchesData(BaseModel):
    """明细列表响应 data"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[KeywordMatchItem] = Field(..., description="明细列表")
    total: int = Field(..., description="符合条件的总明细行数")
    page: int = Field(..., description="当前页码（1-based）")
    page_size: int = Field(..., description="每页条数")


def _dict_to_camel(d: dict) -> dict:
    """将 snake_case 字典转为 camelCase 字典（用于 Pydantic model 构造前）。"""
    return {to_camel(k): v for k, v in d.items()}


# ============== 端点 ==============


# 注意：/preview 必须声明在 /{group_id} 之前，避免被动态路径吞掉


@router.get("/preview", response_model=ApiResponse[PreviewMatchResponse])
async def preview_match(
    keywords: str = Query(..., description="逗号分隔的关键词列表"),
    exclude_group_id: Optional[int] = Query(
        None, description="预览时排除的分组ID（可选）"
    ),
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """预览给定关键词在最新报告期匹配的去重股票数。"""
    keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
    service = ShareholderGroupService(session)
    result = await service.preview_match(keyword_list, exclude_group_id)
    return ApiResponse(
        success=True,
        data=PreviewMatchResponse(**_dict_to_camel(result)),
        message=f"匹配 {result['matched_stock_count']} 只股票",
    )


# ===== plan-01 新增端点 =====
# 顺序关键：/preview-breakdown 与 /keyword-matches 必须在 /{group_id} 动态路径之前，
# 否则会被动态路径吞掉（与现有 /preview 的位置约定一致）


@router.get(
    "/preview-breakdown", response_model=ApiResponse[PreviewBreakdownData]
)
async def preview_match_breakdown(
    keywords: str = Query(..., description="逗号分隔的关键词列表"),
    exclude_group_id: Optional[int] = Query(
        None, description="预览时排除的分组ID（可选，本期占位）"
    ),
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """逐关键词查询匹配的去重股票数（AC-01 / AC-07 后端语义）。"""
    keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
    service = ShareholderGroupService(session)
    result = await service.preview_match_breakdown(keyword_list, exclude_group_id)
    return ApiResponse(
        success=True,
        data=PreviewBreakdownData(
            items=[
                KeywordCountItem(**_dict_to_camel(item))
                for item in result["items"]
            ]
        ),
        message=f"共 {len(result['items'])} 个关键词",
    )


@router.get(
    "/keyword-matches", response_model=ApiResponse[KeywordMatchesData]
)
async def get_keyword_matches(
    keyword: str = Query(..., min_length=1, description="单个关键词"),
    page: int = Query(1, ge=1, description="页码（1-based）"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    exclude_group_id: Optional[int] = Query(
        None, description="排除的分组ID（可选，本期占位）"
    ),
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """查询单个关键词匹配的明细列表（AC-03 ~ AC-05）。"""
    service = ShareholderGroupService(session)
    result = await service.list_keyword_matches(
        keyword=keyword.strip(),
        page=page,
        page_size=page_size,
        exclude_group_id=exclude_group_id,
    )
    return ApiResponse(
        success=True,
        data=KeywordMatchesData(**_dict_to_camel(result)),
        message=f"共 {result['total']} 条明细",
    )


@router.get("", response_model=ApiResponse[List[GroupListItem]])
async def list_shareholder_groups(
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """查询所有监控组列表（含规则数、关键词、匹配股数）。"""
    service = ShareholderGroupService(session)
    items = await service.list_groups()
    return ApiResponse(
        success=True,
        data=[GroupListItem(**_dict_to_camel(item)) for item in items],
        message=f"共 {len(items)} 个监控组",
    )


@router.post("", response_model=ApiResponse[GroupListItem], status_code=status.HTTP_200_OK)
async def create_shareholder_group(
    payload: CreateGroupRequest,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """新增监控组（AC-06）。"""
    service = ShareholderGroupService(session)
    try:
        result = await service.create_group(
            name=payload.name,
            description=payload.description,
            keywords=payload.keywords,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e) or "组名已存在",
        )
    return ApiResponse(
        success=True,
        data=GroupListItem(**_dict_to_camel(result)),
        message=f"监控组 '{payload.name}' 创建成功",
    )


@router.get("/{group_id}", response_model=ApiResponse[GroupListItem])
async def get_shareholder_group(
    group_id: int,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """查询单个监控组详情（编辑页按 id 独立加载）。"""
    service = ShareholderGroupService(session)
    try:
        result = await service.get_group(group_id)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="监控组不存在",
        )
    return ApiResponse(
        success=True,
        data=GroupListItem(**_dict_to_camel(result)),
        message="监控组详情",
    )


@router.patch("/{group_id}", response_model=ApiResponse[GroupListItem])
async def update_shareholder_group(
    group_id: int,
    payload: UpdateGroupRequest,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """编辑监控组字段及/或关键词（AC-07）。"""
    service = ShareholderGroupService(session)
    try:
        result = await service.update_group(
            group_id=group_id,
            name=payload.name,
            description=payload.description,
            keywords=payload.keywords,
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="监控组不存在",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e) or "组名已存在",
        )
    return ApiResponse(
        success=True,
        data=GroupListItem(**_dict_to_camel(result)),
        message="监控组已更新",
    )


@router.delete("/{group_id}", response_model=ApiResponse[None])
async def delete_shareholder_group(
    group_id: int,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """删除监控组（CASCADE 自动删除关联规则，AC-10）。"""
    service = ShareholderGroupService(session)
    try:
        await service.delete_group(group_id)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="监控组不存在",
        )
    return ApiResponse(success=True, data=None, message="监控组已删除")
