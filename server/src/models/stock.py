from sqlalchemy import Column, String, Integer, Numeric, DateTime, Index, CheckConstraint
from sqlalchemy.sql import func

from .base import Base


class Stock(Base):
    """个股模型"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    current_price = Column(Numeric(precision=10, scale=2))
    market_cap = Column(Numeric(precision=15, scale=2))
    strength_score = Column(Numeric(precision=10, scale=4), default=0)
    trend_direction = Column(Numeric(precision=5, scale=2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系需要在业务逻辑层通过 symbol/code 来处理

    # 表级约束和索引
    __table_args__ = (
        CheckConstraint('current_price >= 0', name='check_current_price_positive'),
        CheckConstraint('market_cap >= 0', name='check_market_cap_positive'),
        CheckConstraint('strength_score >= 0 AND strength_score <= 100',
                       name='check_stock_strength_score_range'),
        CheckConstraint('trend_direction >= -1 AND trend_direction <= 1',
                       name='check_stock_trend_direction_range'),
        Index('idx_stocks_market_cap', 'market_cap'),
        Index('idx_stocks_strength_score', 'strength_score'),
    )

    def __repr__(self):
        return f"<Stock(id={self.id}, symbol={self.symbol}, name={self.name})>"
