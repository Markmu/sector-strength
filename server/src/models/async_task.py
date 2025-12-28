"""异步任务相关模型"""

from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
from typing import Optional
from datetime import datetime
import uuid


class AsyncTask(Base):
    """异步任务表"""
    __tablename__ = "async_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    task_id = Column(String(50), unique=True, index=True, nullable=False, comment="任务唯一标识")
    task_type = Column(String(50), nullable=False, comment="任务类型")
    status = Column(String(20), nullable=False, default="pending", comment="任务状态: pending, running, completed, failed, cancelled")
    progress = Column(Integer, default=0, comment="当前进度")
    total = Column(Integer, default=0, comment="总数量")
    error_message = Column(Text, comment="错误信息")
    retry_count = Column(Integer, default=0, comment="重试次数")
    max_retries = Column(Integer, default=3, comment="最大重试次数")
    timeout_seconds = Column(Integer, default=14400, comment="超时时间（秒），默认4小时")
    created_by = Column(ForeignKey("users.id"), comment="创建者用户ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    started_at = Column(DateTime(timezone=True), comment="开始时间")
    completed_at = Column(DateTime(timezone=True), comment="完成时间")
    cancelled_at = Column(DateTime(timezone=True), comment="取消时间")

    # 关联关系
    params = relationship("AsyncTaskParam", back_populates="task", cascade="all, delete-orphan")
    logs = relationship("AsyncTaskLog", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_async_tasks_status', 'status'),
        Index('idx_async_tasks_created_at', 'created_at'),
    )

    @property
    def percent(self) -> int:
        """计算进度百分比"""
        if self.total and self.total > 0:
            return int((self.progress / self.total) * 100)
        return 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "taskId": self.task_id,
            "taskType": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "percent": self.percent,
            "errorMessage": self.error_message,
            "retryCount": self.retry_count,
            "maxRetries": self.max_retries,
            "timeoutSeconds": self.timeout_seconds,
            "createdBy": str(self.created_by) if self.created_by else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "cancelledAt": self.cancelled_at.isoformat() if self.cancelled_at else None,
        }


class AsyncTaskParam(Base):
    """异步任务参数表"""
    __tablename__ = "async_task_params"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    task_id = Column(String(50), ForeignKey("async_tasks.task_id", ondelete="CASCADE"), nullable=False, comment="任务ID")
    key = Column(String(100), nullable=False, comment="参数键")
    value = Column(Text, comment="参数值")

    # 关联任务
    task = relationship("AsyncTask", back_populates="params")

    __table_args__ = (
        Index('idx_async_task_params_task_id', 'task_id'),
    )


class AsyncTaskLog(Base):
    """异步任务日志表"""
    __tablename__ = "async_task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    task_id = Column(String(50), ForeignKey("async_tasks.task_id", ondelete="CASCADE"), nullable=False, comment="任务ID")
    level = Column(String(20), nullable=False, comment="日志级别: INFO, WARNING, ERROR")
    message = Column(Text, nullable=False, comment="日志消息")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    # 关联任务
    task = relationship("AsyncTask", back_populates="logs")

    __table_args__ = (
        Index('idx_async_task_logs_task_id', 'task_id', 'created_at'),
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "taskId": self.task_id,
            "level": self.level,
            "message": self.message,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
