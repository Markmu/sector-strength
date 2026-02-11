"""
API v1 路由模块

整合所有 v1 版本的 API 路由（故事 3-4 范围）。

注意：Admin 和 auth 路由在主路由 (router.py) 中统一注册。
"""

from fastapi import APIRouter

# 故事 3-4 实现的业务路由
from .sectors import router as sectors_router
from .stocks import router as stocks_router
from .strength import router as strength_router
from .rankings import router as rankings_router
from .heatmap import router as heatmap_router
from .market_index import router as market_index_router
from .analysis import router as analysis_router  # 板块强度分析
from .sector_classifications import router as sector_classifications_router  # 板块分类
from .admin import router as admin_legacy_router  # legacy /v1/admin/data/*

# 创建 v1 主路由
router = APIRouter(prefix="/v1", tags=["v1"])

# 注册子路由
router.include_router(sectors_router)        # /api/v1/sectors/*
router.include_router(stocks_router)         # /api/v1/stocks/*
router.include_router(strength_router)       # /api/v1/strength/*
router.include_router(rankings_router)       # /api/v1/rankings/*
router.include_router(heatmap_router)        # /api/v1/heatmap/*
router.include_router(market_index_router)   # /api/v1/market-index/*
router.include_router(analysis_router)       # /api/v1/analysis/*
router.include_router(sector_classifications_router)  # /api/v1/sector-classifications/*
router.include_router(admin_legacy_router)   # /api/v1/admin/data/* (legacy)

__all__ = ["router"]
