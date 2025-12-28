from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, DateTime, Index, CheckConstraint
from sqlalchemy.sql import func

from .base import Base


class Sector(Base):
    """板块模型"""
    __tablename__ = "sectors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    code = Column(String(20), nullable=False, unique=True, index=True)
    type = Column(String(20), nullable=False, index=True)  # 'industry' or 'concept'
    description = Column(Text)
    strength_score = Column(Numeric(precision=10, scale=4), default=0)
    trend_direction = Column(Numeric(precision=5, scale=2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系需要在业务逻辑层通过 code 来处理

    # 表级约束和索引
    __table_args__ = (
        CheckConstraint('strength_score >= 0 AND strength_score <= 100',
                       name='check_sector_strength_score_range'),
        Index('idx_sectors_type_score', 'type', 'strength_score'),
    )

    def __repr__(self):
        return f"<Sector(id={self.id}, name={self.name}, code={self.code})>"
