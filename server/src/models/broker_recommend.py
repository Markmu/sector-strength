"""券商月度金股模型"""

from sqlalchemy import Column, String, Integer, Text, Date, DateTime, Index
from sqlalchemy.sql import func

from .base import Base


class BrokerRecommend(Base):
    """券商月度金股表"""
    __tablename__ = "broker_recommend"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    month = Column(Date, nullable=False, comment="月份标识（该月第一天，MAX 比较键）")
    trade_date = Column(Date, nullable=True, comment="推荐日期（接口返回，同月可能有多个；部分记录缺失为空）")
    ts_code = Column(String(20), nullable=False, comment="Tushare代码")
    symbol = Column(String(10), nullable=False, comment="股票代码(纯数字)")
    broker = Column(String(100), nullable=False, comment="券商名称")
    name = Column(String(100), comment="股票名称(取自接口，仅快照用；查询时以 stocks JOIN 为准)")
    reason = Column(Text, comment="推荐理由")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        Index('ix_broker_symbol_month', 'symbol', 'month'),
        Index('ix_broker_broker_month', 'broker', 'month'),
        Index('ix_broker_month', 'month'),
    )

    def __repr__(self):
        return (
            f"<BrokerRecommend(id={self.id}, ts_code={self.ts_code}, "
            f"broker={self.broker}, month={self.month}, trade_date={self.trade_date})>"
        )
