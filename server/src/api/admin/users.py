"""
管理员用户管理 API 端点

提供用户列表查询、搜索、统计、信息编辑、角色与状态管理，所有接口均需管理员权限。
"""

import logging
import math
import uuid
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, require_admin
from src.api.schemas.response import ApiResponse
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Admin - Users"])


# ============== 请求/响应模型 ==============

class UserListItem(BaseModel):
    """用户列表项（驼峰字段）"""
    id: str = Field(..., description="用户ID")
    email: str = Field(..., description="邮箱")
    username: Optional[str] = Field(None, description="用户名")
    role: str = Field(..., description="角色: admin/user")
    isActive: bool = Field(..., description="账户是否激活")
    createdAt: datetime = Field(..., description="注册时间")
    lastLoginAt: Optional[datetime] = Field(None, description="最后登录时间")


class UserListResponse(BaseModel):
    """用户列表分页响应"""
    items: List[UserListItem] = Field(default_factory=list, description="用户列表")
    total: int = Field(..., ge=0, description="总记录数")
    page: int = Field(..., ge=1, description="当前页码")
    pageSize: int = Field(..., ge=1, le=100, description="每页数量")
    totalPages: int = Field(..., ge=0, description="总页数")


class UserStatsResponse(BaseModel):
    """用户统计响应"""
    total: int = Field(..., ge=0, description="用户总数")
    byRole: dict = Field(..., description="按角色统计 {admin, user}")
    byStatus: dict = Field(..., description="按状态统计 {active, banned}")


class UserUpdateRequest(BaseModel):
    """用户信息编辑请求"""
    username: Optional[str] = Field(None, max_length=50, description="用户名")


class RoleUpdateRequest(BaseModel):
    """角色修改请求"""
    role: Literal["admin", "user"] = Field(..., description="新角色")


class StatusUpdateRequest(BaseModel):
    """激活/禁用请求"""
    isActive: bool = Field(..., description="是否激活（true=活跃，false=禁用）")


# ============== 工具函数 ==============

def _to_list_item(user: User) -> UserListItem:
    """将 ORM User 映射为驼峰命名响应项"""
    return UserListItem(
        id=str(user.id),
        email=user.email,
        username=user.username,
        role=user.role,
        isActive=bool(user.is_active),
        createdAt=user.created_at,
        lastLoginAt=user.last_login,
    )


def _ensure_not_self(target: User, current: User, action: str) -> None:
    """禁止管理员对自己执行写操作"""
    if target.id == current.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不能修改自己的{action}",
        )


async def _get_user_or_404(session: AsyncSession, user_id: str) -> User:
    """根据 user_id 查询用户，不存在则抛 404"""
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    result = await session.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return user


# ============== 端点 ==============

@router.get("", response_model=ApiResponse[UserListResponse])
async def list_users(
    q: Optional[str] = Query(None, description="搜索关键字，匹配 email/username"),
    page: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """
    获取用户列表（分页 + 搜索）

    - q 为空时返回全部用户
    - 按 created_at 倒序
    """
    offset = (page - 1) * pageSize

    # 基础查询
    base_stmt = select(User)
    count_stmt = select(func.count(User.id))

    if q:
        keyword = f"%{q.strip()}%"
        condition = or_(
            User.email.ilike(keyword),
            User.username.ilike(keyword),
        )
        base_stmt = base_stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    # 总数
    total_result = await session.execute(count_stmt)
    total = int(total_result.scalar_one() or 0)

    # 分页数据
    list_stmt = base_stmt.order_by(User.created_at.desc()).offset(offset).limit(pageSize)
    result = await session.execute(list_stmt)
    users = result.scalars().all()

    total_pages = math.ceil(total / pageSize) if total > 0 else 0

    return ApiResponse(
        success=True,
        data=UserListResponse(
            items=[_to_list_item(u) for u in users],
            total=total,
            page=page,
            pageSize=pageSize,
            totalPages=total_pages,
        ),
        message=f"共 {total} 个用户",
    )


@router.get("/stats", response_model=ApiResponse[UserStatsResponse])
async def get_user_stats(
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """获取用户统计信息（总数 + 按角色 + 按状态）"""
    total = int(
        (await session.execute(select(func.count(User.id)))).scalar_one() or 0
    )
    admin_count = int(
        (await session.execute(
            select(func.count(User.id)).where(User.role == "admin")
        )).scalar_one() or 0
    )
    active_count = int(
        (await session.execute(
            select(func.count(User.id)).where(User.is_active == True)  # noqa: E712
        )).scalar_one() or 0
    )
    banned_count = total - active_count

    return ApiResponse(
        success=True,
        data=UserStatsResponse(
            total=total,
            byRole={"admin": admin_count, "user": total - admin_count},
            byStatus={"active": active_count, "banned": banned_count},
        ),
        message="用户统计信息",
    )


@router.patch("/{user_id}", response_model=ApiResponse[UserListItem])
async def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """编辑用户信息（目前仅支持 username）"""
    user = await _get_user_or_404(session, user_id)

    if payload.username is not None:
        user.username = payload.username.strip() or None

    await session.commit()
    await session.refresh(user)

    logger.info(f"User {user_id} updated by admin {_admin.id}")

    return ApiResponse(
        success=True,
        data=_to_list_item(user),
        message="用户信息已更新",
    )


@router.patch("/{user_id}/role", response_model=ApiResponse[UserListItem])
async def update_user_role(
    user_id: str,
    payload: RoleUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """修改用户角色（admin / user）"""
    user = await _get_user_or_404(session, user_id)
    _ensure_not_self(user, _admin, "角色")

    user.role = payload.role
    await session.commit()
    await session.refresh(user)

    logger.info(f"User {user_id} role changed to {payload.role} by admin {_admin.id}")

    return ApiResponse(
        success=True,
        data=_to_list_item(user),
        message=f"角色已更新为 {payload.role}",
    )


@router.patch("/{user_id}/status", response_model=ApiResponse[UserListItem])
async def update_user_status(
    user_id: str,
    payload: StatusUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """激活或禁用用户（isActive=true 为激活，false 为禁用）"""
    user = await _get_user_or_404(session, user_id)
    _ensure_not_self(user, _admin, "状态")

    user.is_active = payload.isActive
    await session.commit()
    await session.refresh(user)

    logger.info(
        f"User {user_id} status changed to isActive={payload.isActive} by admin {_admin.id}"
    )

    return ApiResponse(
        success=True,
        data=_to_list_item(user),
        message="已激活" if payload.isActive else "已禁用",
    )
