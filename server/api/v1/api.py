"""API v1 路由聚合"""
from fastapi import APIRouter
from .endpoints import stocks, sectors, strength, auth, email_queue, admin_sector_classifications, admin_audit_logs

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

# 注册管理员板块分类路由
api_router.include_router(
    admin_sector_classifications.router,
    prefix="/api/v1/admin",
    tags=["admin_sector_classifications"]
)

# 注册管理员审计日志路由
api_router.include_router(
    admin_audit_logs.router,
    prefix="/api/v1/admin",
    tags=["admin_audit_logs"]
)