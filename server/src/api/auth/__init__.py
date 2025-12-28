"""认证API模块 - 整合所有认证相关路由"""

from fastapi import APIRouter
from .login import router as login_router
from .registration import router as registration_router
from .auth import router as auth_router
from .profile import router as profile_router
from .password_reset import router as password_reset_router

# 创建认证主路由
# 注意：不设置前缀，由主路由 (router.py) 统一添加 /v1/auth
router = APIRouter(tags=["Authentication"])

# 注册子路由 - 不带额外前缀，路径由子路由定义
router.include_router(login_router)
router.include_router(registration_router)
router.include_router(auth_router)
router.include_router(profile_router)
router.include_router(password_reset_router)

__all__ = ["router"]
