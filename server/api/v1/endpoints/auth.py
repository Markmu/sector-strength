"""认证 API 端点"""

from fastapi import APIRouter

from src.api.auth.login import router as login_router
from src.api.auth.registration import router as registration_router
from src.api.auth.auth import router as auth_router
from src.api.auth.profile import router as profile_router

router = APIRouter()

# 注册认证相关路由
router.include_router(
    registration_router,
    prefix="/auth",
    tags=["auth"]
)

router.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"]
)

router.include_router(
    login_router,
    prefix="/auth",
    tags=["auth"]
)

# 注册用户资料管理路由
router.include_router(
    profile_router,
    prefix="",
    tags=["user"]
)