"""
审计日志模型

用于记录所有管理员操作，满足合规要求和问题排查需求。
(NFR-SEC-006, NFR-SEC-007, NFR-SEC-008)
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from .base import Base


class AuditLog(Base):
    """
    审计日志模型

    记录管理员的所有操作，包括操作人、操作时间、操作类型、
    操作内容、IP 地址、操作结果等。用于事后追溯和责任认定。

    Attributes:
        id: 主键
        user_id: 操作用户 ID
        username: 操作用户名（冗余存储，防止用户删除后无法追溯）
        action: 操作类型（如 test_classification, init_data, update_data 等）
        resource_type: 资源类型（sector, stock, user 等）
        resource_id: 资源 ID
        details: 操作详情（JSONB 格式，存储扩展信息）
        ip_address: 操作来源 IP 地址
        user_agent: 用户代理字符串
        status: 操作状态（success, failed, partial）
        result: 操作结果描述
        created_at: 记录创建时间（操作时间）
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    details = Column(JSONB)
    ip_address = Column(String(45))  # 支持 IPv6
    user_agent = Column(Text)
    status = Column(String(20), nullable=False, default="success", index=True)
    result = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # 复合索引优化查询性能
    __table_args__ = (
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_status_created", "status", "created_at"),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user={self.username}, action={self.action}, status={self.status})>"
