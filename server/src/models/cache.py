"""
数据库缓存模型

用于 Story 3-5 的数据库缓存实现，提供持久化缓存存储。
"""

from sqlalchemy import Column, String, LargeBinary, DateTime, Integer, Index
from sqlalchemy.sql import func

from .base import Base


class CacheEntry(Base):
    """
    缓存条目模型

    使用数据库表存储缓存数据，支持分布式部署。
    数据使用 pickle 序列化为二进制存储。

    Attributes:
        id: 主键
        key: 缓存键（唯一）
        value: 缓存值（pickle 序列化的二进制数据）
        expires_at: 过期时间
        created_at: 创建时间
    """

    __tablename__ = "cache_entries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(LargeBinary, nullable=False)  # pickle 序列化数据
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 表级约束和索引
    __table_args__ = (
        Index('ix_cache_key_expires', 'key', 'expires_at'),
    )

    def __repr__(self):
        return f"<CacheEntry(id={self.id}, key={self.key}, expires_at={self.expires_at})>"
