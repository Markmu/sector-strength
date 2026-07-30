"""
Admin API 路由模块

整合所有管理员相关的 API 路由：
- 数据初始化 (init.py)
- 基金数据同步 (init_funds.py)
- 股票十大流通股东同步 (init_top10_holders.py)
- 异步任务管理 (tasks.py)
- RBAC 权限管理 (rbac.py)
"""

from fastapi import APIRouter
from .init import router as init_router
from .init_funds import router as init_funds_router
from .init_top10_holders import router as init_top10_holders_router
from .init_broker_recommend import router as init_broker_recommend_router
from .init_sector_fund_flow import router as init_sector_fund_flow_router
from .init_etf_history import router as init_etf_history_router
from .init_etf_daily import router as init_etf_daily_router  # 第 14 期 plan-03
from .init_etf_basic import router as init_etf_basic_router
from .tasks import router as tasks_router
from .rbac import router as rbac_router
from .data_status import router as data_status_router
from .users import router as users_router
from .shareholder_groups import router as shareholder_groups_router

# 创建 Admin 主路由
# 注意：不在这里设置统一前缀，因为每个子路由有自己的前缀
router = APIRouter(tags=["Admin"])

# 注册子路由
router.include_router(init_router)    # /api/admin/init/*
router.include_router(init_funds_router)  # /api/admin/init/funds, /api/admin/init/fund-portfolio
router.include_router(init_top10_holders_router)  # /api/admin/init/top10-holders
router.include_router(init_broker_recommend_router)  # /api/admin/init/broker-recommend
router.include_router(init_sector_fund_flow_router)  # /api/admin/init/sector-fund-flow
router.include_router(init_etf_history_router)  # /api/admin/init/etf-history
router.include_router(init_etf_daily_router)  # /api/admin/init/etf-daily（第 14 期 plan-03）
router.include_router(init_etf_basic_router)  # /api/admin/init/etf-basic
router.include_router(tasks_router)   # /api/admin/tasks/*
router.include_router(rbac_router)    # /api/admin/*
router.include_router(data_status_router)  # /api/admin/data/*
router.include_router(users_router)  # /api/admin/users/*
router.include_router(shareholder_groups_router)  # /api/admin/shareholder-groups/*

__all__ = ["router"]
