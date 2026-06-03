"""基金持仓明细模型"""

from sqlalchemy import Column, String, Integer, Numeric, Date, DateTime, Index
from sqlalchemy.sql import func

from .base import Base


class FundPortfolio(Base):
    """基金持仓明细表"""
    __tablename__ = "fund_portfolio"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    fund_ts_code = Column(String(20), nullable=False, comment="基金TS代码")
    report_period = Column(Date, nullable=False, comment="报告期")
    ann_date = Column(Date, comment="公告日期")
    stock_symbol = Column(String(20), nullable=False, comment="持仓股票代码(短码)")
    market_value = Column(Numeric(precision=18, scale=2), comment="持仓市值(元)")
    amount = Column(Numeric(precision=18, scale=2), comment="持仓数量(股)")
    stk_mkv_ratio = Column(Numeric(precision=10, scale=4), comment="占股票市值比")
    stk_float_ratio = Column(Numeric(precision=10, scale=4), comment="占流通股比")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        Index('ix_fund_portfolio_fund_period', 'fund_ts_code', 'report_period'),
        Index('ix_fund_portfolio_symbol_period', 'stock_symbol', 'report_period'),
    )

    def __repr__(self):
        return (
            f"<FundPortfolio(id={self.id}, fund_ts_code={self.fund_ts_code}, "
            f"report_period={self.report_period}, stock_symbol={self.stock_symbol})>"
        )
