"""
缓存后端模块

导出可用的缓存后端实现。
"""

from .db_cache import DatabaseCache

__all__ = ["DatabaseCache"]
