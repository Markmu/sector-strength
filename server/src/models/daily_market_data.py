from sqlalchemy import Column, String, Date, Numeric, DateTime, Integer, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.sql import func

from .base import Base


class DailyMarketData(Base):
    """日线行情数据模型"""
    __tablename__ = "daily_market_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    entity_type = Column(String(10), nullable=False, index=True)  # 'stock' or 'sector'
    entity_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # 股票代码或板块代码
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

    # 关联关系 - 注意：由于使用了通用的entity_id，无法直接建立外键关系
    # 这些关联需要在业务逻辑层通过entity_type和entity_id来处理

    # 表级约束和索引
    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', 'date', name='uq_daily_market_data_entity_date'),
        CheckConstraint('high >= low', name='check_high_low'),
        CheckConstraint('volume >= 0', name='check_volume_positive'),
        # 移除了不实用的价格约束：high >= open 和 high >= close
        Index('idx_daily_market_data_entity_date', 'entity_type', 'entity_id', 'date'),
        Index('idx_daily_market_data_date_range', 'date', 'close', 'volume'),
        # 覆盖索引用于常见查询
        Index('idx_daily_market_data_cover', 'entity_type', 'entity_id', 'date',
              'close', 'change_percent', 'volume'),
        Index('idx_daily_market_data_entity_date_desc', 'entity_type', 'entity_id', 'date'),
        Index('idx_daily_market_data_symbol_date', 'symbol', 'date'),
    )

    def __init__(self, **kwargs):
        # Legacy test compatibility: map old sector_* and *_price fields.
        if "sector_id" in kwargs and "entity_id" not in kwargs:
            kwargs["entity_id"] = kwargs.pop("sector_id")
            kwargs.setdefault("entity_type", "sector")
        if "open_price" in kwargs and "open" not in kwargs:
            kwargs["open"] = kwargs.pop("open_price")
        if "high_price" in kwargs and "high" not in kwargs:
            kwargs["high"] = kwargs.pop("high_price")
        if "low_price" in kwargs and "low" not in kwargs:
            kwargs["low"] = kwargs.pop("low_price")
        if "close_price" in kwargs and "close" not in kwargs:
            kwargs["close"] = kwargs.pop("close_price")
        if "entity_id" in kwargs and "symbol" not in kwargs:
            kwargs["symbol"] = str(kwargs["entity_id"])
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<DailyMarketData(entity_type={self.entity_type}, symbol={self.symbol}, date={self.date})>"
