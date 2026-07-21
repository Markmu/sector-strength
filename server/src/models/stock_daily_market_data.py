"""股票日线行情数据独立表模型"""

from sqlalchemy import Column, String, Date, Numeric, DateTime, Integer, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.sql import func

from .base import Base


class StockDailyMarketData(Base):
    """股票日线行情数据模型（股票独立表，无 entity_type）"""
    __tablename__ = "stock_daily_market_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    stock_id = Column(Integer, nullable=False, index=True)  # 指向 stocks.id，不加外键约束
    symbol = Column(String(20), nullable=False, index=True)  # 股票代码
    date = Column(Date, nullable=False, index=True)
    open = Column(Numeric(precision=10, scale=2))
    high = Column(Numeric(precision=10, scale=2))
    low = Column(Numeric(precision=10, scale=2))
    close = Column(Numeric(precision=10, scale=2))
    volume = Column(Numeric(precision=15, scale=2))
    turnover = Column(Numeric(precision=15, scale=2))
    change = Column(Numeric(precision=10, scale=2))
    change_percent = Column(Numeric(precision=10, scale=4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 表级约束和索引
    __table_args__ = (
        UniqueConstraint('stock_id', 'date', name='uq_stock_daily_market_data_stock_date'),
        CheckConstraint('high >= low', name='check_stock_dmd_high_low'),
        CheckConstraint('volume >= 0', name='check_stock_dmd_volume_positive'),
        Index('idx_stock_dmd_stock_date', 'stock_id', 'date'),
        Index('idx_stock_dmd_date_range', 'date', 'close', 'volume'),
        Index('idx_stock_dmd_symbol_date', 'symbol', 'date'),
    )

    def __repr__(self):
        return f"<StockDailyMarketData(symbol={self.symbol}, date={self.date})>"
