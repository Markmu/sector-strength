"""
Admin API 路由模块

整合所有管理员相关的 API 路由：
- 数据更新管理 (update.py)
- 数据初始化 (init.py)
- 异步任务管理 (tasks.py)
- RBAC 权限管理 (rbac.py)
- 板块分类管理 (sector_classifications.py)
"""

from fastapi import APIRouter
from .update import router as update_router
from .init import router as init_router
from .tasks import router as tasks_router
from .rbac import router as rbac_router
from .sector_classifications import router as sector_classifications_router

# 创建 Admin 主路由
# 注意：不在这里设置统一前缀，因为每个子路由有自己的前缀
router = APIRouter(tags=["Admin"])

# 注册子路由
router.include_router(update_router)  # /api/admin/data/*
router.include_router(init_router)    # /api/admin/init/*
router.include_router(tasks_router)   # /api/admin/tasks/*
router.include_router(rbac_router)    # /api/admin/*
router.include_router(sector_classifications_router)  # /api/admin/sector-classification/*

__all__ = ["router"]
