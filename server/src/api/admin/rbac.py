"""
RBAC (基于角色的访问控制) API 端点

提供管理员权限验证相关的 API 接口。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.deps import get_current_user
from src.api.schemas.response import ApiResponse
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin Auth"])


class AdminCheckResponse(BaseModel):
    """管理员权限检查响应"""
    is_admin: bool = Field(..., description="是否为管理员")
    user_id: str = Field(..., description="用户ID")
    email: str = Field(..., description="用户邮箱")
    role: str = Field(..., description="用户角色")


@router.get("/check", response_model=ApiResponse[AdminCheckResponse])
async def check_admin_permission(
    current_user: User = Depends(get_current_user)
):
    """
    验证管理员权限

    返回当前用户的管理员权限状态。
    非管理员用户也可以访问此端点来检查自己的权限。
    """
    return ApiResponse(
        success=True,
        data=AdminCheckResponse(
            is_admin=current_user.has_role("admin"),
            user_id=str(current_user.id),
            email=current_user.email,
            role=current_user.role
        )
    )
