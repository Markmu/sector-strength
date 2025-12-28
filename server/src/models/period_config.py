from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, Index, CheckConstraint, func

from .base import Base


class PeriodConfig(Base):
    """周期配置模型"""
    __tablename__ = "period_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    period = Column(String(10), nullable=False, unique=True, index=True)  # '5d', '10d', '20d', etc.
    name = Column(String(50), nullable=False)  # '5日均线', '10日均线'
    days = Column(Integer, nullable=False)
    weight = Column(Numeric(precision=5, scale=2), nullable=False, default=1.0)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 表级约束和索引
    __table_args__ = (
        CheckConstraint('days > 0', name='check_days_positive'),
        CheckConstraint('weight > 0', name='check_weight_positive'),
        Index('idx_period_configs_active', 'is_active', 'days'),
    )

    def __repr__(self):
        return f"<PeriodConfig(id={self.id}, period={self.period}, name={self.name})>"