"""
数据更新历史模型

用于 Story 9.3 的数据更新和补齐功能，记录管理员发起的数据更新任务。
"""

from sqlalchemy import Column, String, Integer, Boolean, Date, DateTime, Index
from sqlalchemy.sql import func

from .base import Base


class UpdateHistory(Base):
    """
    数据更新历史模型

    记录管理员发起的数据更新和补齐任务，包括按日期补齐、按时间段补齐、
    按板块/股票更新等。支持覆盖操作的审计追踪。

    Attributes:
        id: 主键
        task_id: 任务 ID（与异步任务系统关联）
        update_type: 更新类型 (by_date, by_range, sector, stock)
        target_type: 目标类型 (all, sector, stock)
        target_id: 目标 ID（板块代码或股票代码）
        start_date: 开始日期
        end_date: 结束日期
        overwrite: 是否覆盖已有数据
        status: 任务状态 (pending, running, completed, failed, cancelled)
        records_processed: 处理的记录数
        records_created: 新创建的记录数
        records_updated: 更新的记录数
        records_failed: 失败的记录数
        error_message: 错误消息
        created_at: 记录创建时间
        completed_at: 任务完成时间
    """

    __tablename__ = "update_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String(50), unique=True, nullable=True, index=True)
    update_type = Column(String(20), nullable=False, index=True)  # 'by_date', 'by_range', 'sector', 'stock'
    target_type = Column(String(20), index=True)  # 'all', 'sector', 'stock', null = all
    target_id = Column(String(20), index=True)  # sector code or stock symbol
    start_date = Column(Date, index=True)
    end_date = Column(Date, index=True)
    overwrite = Column(Boolean, default=False, nullable=False)
    status = Column(String(20), nullable=False, index=True, default='pending')
    records_processed = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_message = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    # 表级约束和索引
    __table_args__ = (
        Index('ix_update_history_task_id', 'task_id'),
        Index('ix_update_history_status_created', 'status', 'created_at'),
        Index('ix_update_history_type_date', 'update_type', 'start_date'),
    )

    def __repr__(self):
        return (f"<UpdateHistory(id={self.id}, task_id={self.task_id}, "
                f"update_type={self.update_type}, status={self.status})>")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "update_type": self.update_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "overwrite": self.overwrite,
            "status": self.status,
            "records_processed": self.records_processed,
            "records_created": self.records_created,
            "records_updated": self.records_updated,
            "records_failed": self.records_failed,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
