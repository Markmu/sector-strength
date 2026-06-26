"""
缓存服务模块

提供缓存功能，支持多种后端。
"""

from .cache_manager import CacheManager, get_cache_manager, reset_cache_manager
from .backends import DatabaseCache
from .strength_cache import StrengthCache
from .fund_crowd_cache import (
    FundCrowdCache,
    get_fund_crowd_cache,
    reset_fund_crowd_cache,
)

__all__ = [
    "CacheManager",
    "get_cache_manager",
    "reset_cache_manager",
    "DatabaseCache",
    "StrengthCache",
    "FundCrowdCache",
    "get_fund_crowd_cache",
    "reset_fund_crowd_cache",
]
