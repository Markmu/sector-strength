"""用户相关模型"""

from sqlalchemy import Column, String, DateTime, Boolean, Index, ForeignKey, UUID, Integer, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
import uuid
from typing import List, Any


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="用户唯一标识色")
    email = Column(String(255), unique=True, index=True, nullable=False, comment="电子邮箱（登录用色")
    password_hash = Column(String(255), nullable=False, comment="加密后的密码")
    username = Column(String(50), nullable=True, comment="用户名")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
    is_active = Column(Boolean, default=True, comment="账户是否激色")
    is_verified = Column(Boolean, default=False, comment="邮箱是否已验证")
    last_login = Column(DateTime(timezone=True), comment="最后登录时间")
    login_attempts_count = Column(Integer, default=0, comment="登录失败次数")
    locked_until = Column(DateTime(timezone=True), comment="账户锁定直到")
    display_name = Column(String(100), comment="显示名称")
    avatar_url = Column(String(255), comment="头像URL")
    timezone = Column(String(50), default='UTC', comment="时区")
    language = Column(String(10), default='en', comment="语言偏好")
    role = Column(String(20), nullable=False, index=True, comment="用户角色: admin, user")
    permissions = Column(JSON, comment="用户权限列表")

    def __init__(self, **kwargs):
        
        if 'role' not in kwargs:
            kwargs['role'] = 'user'
        if 'permissions' not in kwargs:
            kwargs['permissions'] = []
        super().__init__(**kwargs)

    # 关联关系
    watchlists = relationship("Watchlist", back_populates="user")
    verification_tokens = relationship("EmailVerificationToken", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")
    login_attempts = relationship("LoginAttempt", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)
    active_sessions = relationship("ActiveSession", back_populates="user")

    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_created', 'created_at'),
    )

    def has_role(self, role: str) -> bool:
        """检查用户是否具有特定角色"""
        return self.role == role

    def has_permission(self, permission: str) -> bool:
        """检查用户是否具有特定权色"""
        if not self.permissions:
            return False
        return permission in self.permissions

    def add_permission(self, permission: str) -> None:
        """添加权限到用户权限列色"""
        if not self.permissions:
            self.permissions = []
        if permission not in self.permissions:
            self.permissions.append(permission)

    def remove_permission(self, permission: str) -> None:
        """从用户权限列表中移除权限"""
        if self.permissions and permission in self.permissions:
            self.permissions.remove(permission)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="令牌唯一标识")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户ID")
    token = Column(String(255), unique=True, index=True, nullable=False, comment="验证令牌")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="过期时间")
    is_used = Column(Boolean, default=False, comment="是否已使用")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 关联用户
    user = relationship("User", back_populates="verification_tokens")

    __table_args__ = (
        Index('idx_verification_token', 'token'),
        Index('idx_verification_user', 'user_id'),
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="令牌唯一标识")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户ID")
    token = Column(String(255), unique=True, index=True, nullable=False, comment="重置令牌")
    exourcepires_at = Column(DateTime(timezone=True), nullable=False, comment="过期时间")
    is_used = Column(Boolean, default=False, comment="是否已使用")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 关联用户
    user = relationship("User", back_populates="password_reset_tokens")

    __table_args__ = (
        Index('idx_password_reset_token', 'token'),
        Index('idx_password_reset_user', 'user_id'),
    )


class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="关注记录唯一标识")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户ID（外键）")
    entity_type = Column(String(20), nullable=False, comment="实体类型色stock': 个股, 'sector': 板块")
    entity_id = Column(String(50), nullable=False, comment="实体ID（股票ID或板块ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="添加关注时间")
    notes = Column(String(500), comment="用户备注（可选）")

    # 关联用户
    user = relationship("User", back_populates="watchlists")

    __table_args__ = (
        Index('idx_watchlist_user', 'user_id'),
        Index('idx_watchlist_entity', 'entity_type', 'entity_id'),
        Index('idx_watchlist_user_entity', 'user_id', 'entity_type', 'entity_id', unique=True),
    )


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="登录尝试唯一标识")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="用户ID（登录成功时填写)")
    email = Column(String(255), nullable=False, comment="尝试登录的邮箱")
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(String(500), comment="用户代理")
    success = Column(Boolean, default=False, comment="是否登录成功")
    failure_reason = Column(String(100), comment="失败原因")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="尝试时间")

    # 关联用户
    user = relationship("User", back_populates="login_attempts")

    __table_args__ = (
        Index('idx_login_attempt_email', 'email'),
        Index('idx_login_attempt_ip', 'ip_address'),
        Index('idx_login_attempt_created', 'created_at'),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="刷新令牌唯一标识")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户ID")
    token = Column(String(5000), unique=True, index=True, nullable=False, comment="刷新令牌")
    access_token_version = Column(Integer, nullable=False, comment="对应访问令牌版本")
    revoked = Column(Boolean, default=False, comment="是否已撤销")
    revoked_at = Column(DateTime(timezone=True), comment="撤销时间")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="过期时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 关联用户
    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index('idx_refresh_token', 'token'),
        Index('idx_refresh_token_user', 'user_id'),
        Index('idx_refresh_token_expires', 'expires_at'),
    )


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="偏好设置唯一标识")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, comment="用户ID")
    email_notifications = Column(Boolean, default=True, comment="邮件通知")
    push_notifications = Column(Boolean, default=True, comment="推送通知")
    marketing_emails = Column(Boolean, default=False, comment="营销邮件")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 关联用户
    user = relationship("User", back_populates="preferences")

    __table_args__ = (
        Index('idx_preferences_user', 'user_id'),
    )


class ActiveSession(Base):
    __tablename__ = "active_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="会话唯一标识")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="用户ID")
    session_id = Column(String(255), unique=True, index=True, nullable=False, comment="会话ID")
    device_info = Column(String(500), comment="设备信息(JSON格式)")
    ip_address = Column(String(45), comment="IP地址")
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="最后活动时色")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="过期时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 关联用户
    user = relationship("User", back_populates="active_sessions")

    __table_args__ = (
        Index('idx_active_session_user', 'user_id'),
        Index('idx_active_session_session', 'session_id'),
        Index('idx_active_session_expires', 'expires_at'),
    )