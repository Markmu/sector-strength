"""
API 主路由

统一整合所有 API 路由：
- v1 API 路由（业务逻辑：sectors, stocks, strength, rankings, heatmap）
- v1 认证路由（登录、注册、个人资料、密码重置等）
- v1 管理员路由（数据更新、初始化、任务管理、RBAC等）
"""

from fastapi import APIRouter
from .v1 import router as v1_router
from .auth import router as auth_router
from .admin import router as admin_router

# 创建 API 主路由
router = APIRouter()

# ============== 注册所有路由 ==============

# v1 版本路由（业务逻辑）
router.include_router(v1_router)     # /api/v1/*

# 认证路由 - 放在 v1 下
router.include_router(auth_router, prefix="/v1/auth")   # /api/v1/auth/*

# 管理员路由 - 放在 v1 下
router.include_router(admin_router, prefix="/v1/admin")  # /api/v1/admin/*

__all__ = ["router"]
