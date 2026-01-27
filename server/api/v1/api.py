"""API v1 路由聚合"""
from fastapi import APIRouter
from .endpoints import stocks, sectors, strength, auth, email_queue

api_router = APIRouter()

# 注册各个模块的路由
api_router.include_router(
    stocks.router,
    prefix="/api/v1",
    tags=["stocks"]
)

api_router.include_router(
    sectors.router,
    prefix="/api/v1",
    tags=["sectors"]
)

api_router.include_router(
    strength.router,
    prefix="/api/v1",
    tags=["strength"]
)

# 注册认证路由 - 使用不同的路径格式以符合故事要求
api_router.include_router(
    auth.router,
    prefix="/api/v1",
    tags=["auth"]
)

# 注册邮件队列管理路由
api_router.include_router(
    email_queue.router,
    prefix="/api/v1",
    tags=["email_queue"]
)