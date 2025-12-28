"""
数据更新日志模型

用于 Story 3-5 的更新历史记录，追踪数据更新任务。
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Index
from sqlalchemy.sql import func

from .base import Base


class DataUpdateLog(Base):
    """
    数据更新日志模型

    记录每次数据更新任务的详细信息，包括开始时间、结束时间、
    状态、更新数量等。用于监控和调试数据更新流程。

    Attributes:
        id: 主键
        start_time: 任务开始时间
        end_time: 任务结束时间
        status: 任务状态 (running, completed, failed)
        sectors_updated: 更新的板块数量
        stocks_updated: 更新的股票数量
        market_data_updated: 更新的行情数据数量
        calculations_performed: 执行的计算次数
        error_message: 错误消息（如果失败）
        created_at: 记录创建时间
    """

    __tablename__ = "data_update_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True))
    status = Column(
        String(20),
        nullable=False,
        index=True,
    )  # 'running', 'completed', 'failed'
    sectors_updated = Column(Integer, default=0)
    stocks_updated = Column(Integer, default=0)
    market_data_updated = Column(Integer, default=0)
    calculations_performed = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 表级约束和索引
    __table_args__ = (
        Index('ix_update_logs_start_time', 'start_time'),
        Index('ix_update_logs_status_start', 'status', 'start_time'),
    )

    def __repr__(self):
        return f"<DataUpdateLog(id={self.id}, status={self.status}, start_time={self.start_time})>"
