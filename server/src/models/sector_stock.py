from sqlalchemy import Column, String, Integer, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func

from .base import Base


class SectorStock(Base):
    """板块-个股关联模型（使用代码关联）"""
    __tablename__ = "sector_stocks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sector_code = Column(String(20), nullable=False, index=True)  # 板块代码
    stock_code = Column(String(20), nullable=False, index=True)  # 股票代码
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 表级约束和索引
    __table_args__ = (
        UniqueConstraint('sector_code', 'stock_code', name='uq_sector_stock'),
        Index('idx_sector_stocks_sector', 'sector_code', 'stock_code'),
        Index('idx_sector_stocks_stock', 'stock_code', 'sector_code'),
    )

    def __repr__(self):
        return f"<SectorStock(sector_code={self.sector_code}, stock_code={self.stock_code})>"
