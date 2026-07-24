from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Numeric,
    Integer,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .base import Base


class SectorFundFlow(Base):
    """板块资金流（同花顺即时）采样数据模型

    每条记录对应某个交易日某采样分钟（精度到分钟）下，
    单个行业/概念板块的资金流快照。盘中每分钟全量采样，
    同一采样分钟重复触发通过 on_conflict_do_update 覆盖最新值。
    """

    __tablename__ = "sector_fund_flow"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trade_date = Column(Date, nullable=False, index=True)  # 交易日
    # 精度到分钟：秒/微秒由调用方置零，保证同分钟重采命中唯一约束
    sample_time = Column(DateTime, nullable=False)
    sector_type = Column(String(20), nullable=False)  # industry / concept
    sector_name = Column(String(100), nullable=False)
    sector_index = Column(Numeric(precision=15, scale=2))  # 行业指数
    change_percent = Column(Numeric(precision=10, scale=4))  # 行业-涨跌幅(%)
    inflow = Column(Numeric(precision=15, scale=2))  # 流入资金(亿元)
    outflow = Column(Numeric(precision=15, scale=2))  # 流出资金(亿元)
    net_inflow = Column(Numeric(precision=15, scale=2))  # 净额(亿元)
    company_count = Column(Integer)  # 公司家数
    leading_stock = Column(String(50))  # 领涨股
    leading_stock_change = Column(Numeric(precision=10, scale=4))  # 领涨股-涨跌幅(%)
    current_price = Column(Numeric(precision=15, scale=2))  # 领涨股当前价
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "sample_time",
            "sector_type",
            "sector_name",
            name="uq_sector_fund_flow_sample",
        ),
        Index("idx_sff_date_type", "trade_date", "sector_type"),
        Index(
            "idx_sff_date_type_name_time",
            "trade_date",
            "sector_type",
            "sector_name",
            "sample_time",
        ),
    )

    def __repr__(self):
        return (
            f"<SectorFundFlow(trade_date={self.trade_date}, "
            f"sample_time={self.sample_time}, sector_type={self.sector_type}, "
            f"sector_name={self.sector_name}, net_inflow={self.net_inflow})>"
        )
