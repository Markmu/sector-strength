"""股票均线数据独立表模型"""

from sqlalchemy import Column, String, Date, Numeric, DateTime, Integer, Index, UniqueConstraint
from sqlalchemy.sql import func

from .base import Base


class StockMovingAverageData(Base):
    """股票均线数据模型（股票独立表，无 entity_type，保留 period 业务字段）"""
    __tablename__ = "stock_moving_average_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    stock_id = Column(Integer, nullable=False, index=True)  # 指向 stocks.id，不加外键约束
    symbol = Column(String(20), nullable=False, index=True)  # 股票代码
    date = Column(Date, nullable=False, index=True)
    period = Column(String(10), nullable=False, index=True)  # '5d', '10d' 等真实业务字段
    ma_value = Column(Numeric(precision=10, scale=2))
    price_ratio = Column(Numeric(precision=10, scale=4))  # 价格与均线的比率
    trend = Column(Numeric(precision=5, scale=2))  # 趋势方向
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 表级约束和索引
    __table_args__ = (
        UniqueConstraint('stock_id', 'symbol', 'date', 'period',
                         name='uq_stock_moving_average_data_stock_date_period'),
        Index('idx_stock_mad_stock_date', 'stock_id', 'date'),
        Index('idx_stock_mad_symbol_date', 'symbol', 'date'),
        Index('idx_stock_mad_date_period', 'date', 'period'),
        Index('idx_stock_mad_stock_period', 'stock_id', 'period'),
        Index('idx_stock_mad_symbol_period', 'symbol', 'period'),
        Index('idx_stock_mad_date_desc', 'date'),
    )

    def __repr__(self):
        return (
            f"<StockMovingAverageData(stock_id={self.stock_id}, symbol={self.symbol}, "
            f"period={self.period}, date={self.date})>"
        )
