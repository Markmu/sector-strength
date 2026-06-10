"""股票十大流通股东模型"""

from sqlalchemy import Column, String, Integer, Numeric, Date, DateTime, Index
from sqlalchemy.sql import func

from .base import Base


class Top10FloatHolder(Base):
    """股票十大流通股东表"""
    __tablename__ = "top10_float_holders"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    symbol = Column(String(10), nullable=False, comment="股票代码(纯数字,如600000)")
    ts_code = Column(String(20), nullable=False, comment="Tushare代码(如600000.SH)")
    report_period = Column(Date, nullable=False, comment="报告期")
    ann_date = Column(Date, comment="公告日期")
    holder_name = Column(String(100), nullable=False, comment="股东名称")
    hold_amount = Column(Numeric(precision=20, scale=2), comment="持股数量(股)")
    hold_ratio = Column(Numeric(precision=10, scale=4), comment="占总股本比例(%)")
    hold_float_ratio = Column(Numeric(precision=10, scale=4), comment="占流通股本比例(%)")
    hold_change = Column(Numeric(precision=20, scale=2), comment="持股变动")
    holder_type = Column(String(50), comment="股东类型")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        Index('ix_top10_symbol_period', 'symbol', 'report_period'),
        Index('ix_top10_report_period', 'report_period'),
    )

    def __repr__(self):
        return (
            f"<Top10FloatHolder(id={self.id}, ts_code={self.ts_code}, "
            f"report_period={self.report_period}, holder_name={self.holder_name})>"
        )
