from sqlalchemy import Column, String, Integer, Numeric, DateTime, Date, Index, CheckConstraint
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

    # Tushare stock_basic 基础信息字段
    ts_code = Column(String(20), index=True)
    area = Column(String(50))
    industry = Column(String(50))
    fullname = Column(String(200))
    enname = Column(String(200))
    cnspell = Column(String(50))
    market = Column(String(20))  # 市场类型（主板/创业板/科创板/CDR）
    exchange = Column(String(20))  # 交易所（SSE/SZSE/BSE）
    curr_type = Column(String(10))
    list_status = Column(String(5))
    list_date = Column(Date)
    delist_date = Column(Date)
    is_hs = Column(String(5))
    act_name = Column(String(200))
    act_ent_type = Column(String(100))

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
        Index('idx_stocks_exchange', 'exchange'),
    )

    def __repr__(self):
        return f"<Stock(id={self.id}, symbol={self.symbol}, name={self.name})>"
