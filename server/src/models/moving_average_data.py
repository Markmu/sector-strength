from sqlalchemy import Column, String, Date, Numeric, DateTime, Integer, Index, UniqueConstraint
from sqlalchemy.sql import func

from .base import Base


class MovingAverageData(Base):
    """均线数据模型"""
    __tablename__ = "moving_average_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    entity_type = Column(String(10), nullable=False, index=True)  # 'stock' or 'sector'
    entity_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # 股票代码或板块代码
    date = Column(Date, nullable=False, index=True)
    period = Column(String(10), nullable=False, index=True)  # '5d', '10d', etc.
    ma_value = Column(Numeric(precision=10, scale=2))
    price_ratio = Column(Numeric(precision=10, scale=4))  # 价格与均线的比率
    trend = Column(Numeric(precision=5, scale=2))  # 趋势方向
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系 - 注意：由于使用了通用的entity_id，无法直接建立外键关系
    # 这些关联需要在业务逻辑层通过entity_type和entity_id来处理

    # 表级约束和索引
    __table_args__ = (
        UniqueConstraint('entity_type', 'entity_id', 'symbol', 'date', 'period',
                        name='uq_moving_average_data_entity_date_period'),
        Index('idx_moving_average_data_entity_date', 'entity_type', 'entity_id', 'date'),
        Index('idx_moving_average_data_symbol_date', 'symbol', 'date'),
        Index('idx_moving_average_data_date_period', 'date', 'period'),
        Index('idx_moving_average_data_entity_period', 'entity_type', 'entity_id', 'period'),
        Index('idx_moving_average_data_symbol_period', 'symbol', 'period'),
        # 移除了冗余的覆盖索引 idx_moving_average_data_cover
        Index('idx_moving_average_data_date_desc', 'date'),
    )

    def __init__(self, **kwargs):
        # Legacy compatibility for old wide MA payloads used in tests.
        if "sector_id" in kwargs and "entity_id" not in kwargs:
            kwargs["entity_id"] = kwargs.pop("sector_id")
            kwargs.setdefault("entity_type", "sector")
        if "entity_id" in kwargs and "symbol" not in kwargs:
            kwargs["symbol"] = str(kwargs["entity_id"])
        if "period" not in kwargs:
            kwargs["period"] = "5d"

        # Prefer ma_5 if provided, otherwise first available legacy MA field.
        if "ma_value" not in kwargs:
            for key in ("ma_5", "ma_10", "ma_20", "ma_30", "ma_60", "ma_90", "ma_120", "ma_240"):
                if key in kwargs:
                    kwargs["ma_value"] = kwargs[key]
                    break
        for key in ("ma_5", "ma_10", "ma_20", "ma_30", "ma_60", "ma_90", "ma_120", "ma_240"):
            kwargs.pop(key, None)
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<MovingAverageData(entity_type={self.entity_type}, entity_id={self.entity_id}, symbol={self.symbol}, period={self.period}, date={self.date})>"
