"""全市场量价日汇总模型（第 16 期 A股全市场量价指标）

表 ``market_daily_metrics``，每个交易日一行，存储全市场（沪深北 A 股完整集合）
的成交量（股）、成交额（元）与简单平均价（元，4 位）。数据由 plan-03 汇总服务在
完整性通过后 Decimal 原子 upsert 写入（架构 ADR-4：单表日期级原子 upsert）。

- ``volume_shares``：成交量（股，Tushare 手×100 在服务层转换）
- ``amount_yuan``：成交额（元，Tushare 千元×1000 在服务层转换）
- ``average_price``：简单平均价（元，存 4 位、展示 2 位）

仿 ``index_monitor.py`` 范式（Integer 自增主键 + created_at/updated_at）。
"""

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .base import Base


class MarketDailyMetric(Base):
    """全市场量价日汇总事实表（market_daily_metrics）

    高频事实表，每个交易日唯一一条（``trade_date`` 唯一）。存储层统一股/元口径；
    前端显示层由 plan-07 将成交额 ÷1e8 转亿展示。平均价存 4 位小数、展示 2 位。

    ``expected_stock_count`` / ``daily_quote_count`` / ``suspended_stock_count``
    / ``final_stock_count`` 记录当日参与集合的各阶段计数（plan-03 L/D/P/G 生命周期
    构造与 suspend_d 停牌证据，见架构 ADR-2/ADR-3）。
    """

    __tablename__ = "market_daily_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, nullable=False, comment="交易日")

    # ---- 成交量价指标（股/元口径） ----
    volume_shares = Column(
        Numeric(precision=24, scale=2), comment="成交量（股）"
    )
    amount_yuan = Column(
        Numeric(precision=24, scale=2), comment="成交额（元）"
    )
    average_price = Column(
        Numeric(precision=16, scale=4), comment="简单平均价（元，存4位）"
    )

    # ---- 参与集合各阶段计数 ----
    expected_stock_count = Column(Integer, comment="预期参与股票数（L/D/P 联合集合）")
    daily_quote_count = Column(Integer, comment="当日实际取到行情的股票数")
    suspended_stock_count = Column(Integer, comment="当日全天停牌股票数（suspend_d 整日停牌）")
    final_stock_count = Column(Integer, comment="最终参与汇总的股票数（含停牌补值）")

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    __table_args__ = (
        UniqueConstraint("trade_date", name="uq_market_daily_metrics_trade_date"),
        Index("idx_market_daily_metrics_trade_date", "trade_date"),
    )

    def __repr__(self):
        return (
            f"<MarketDailyMetric(trade_date={self.trade_date}, "
            f"volume_shares={self.volume_shares}, amount_yuan={self.amount_yuan}, "
            f"average_price={self.average_price})>"
        )
