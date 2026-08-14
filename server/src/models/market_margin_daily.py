"""融资融券全市场日汇总模型（第 17 期 融资融券数据同步与首页曲线图）

表 ``market_margin_daily``，每个交易日一行，存储全市场（对接口返回全部交易所
行求和，实测沪 SSE/深 SZSE/北 BSE 三行，2026-08-14 裁定）融资融券日汇总指标
（元/股口径）。数据由 plan-03 汇总服务对 tushare ``margin`` 接口单日全部交易所
行原始数据五字段求和并重算 ``rzrqye`` 后 Decimal 原子
upsert 写入（spec D3：单表日期级原子 upsert）。

- 六指标列与 tushare ``margin`` 字段同名：``rzye``/``rqye``/``rzmre``/``rzche``
  /``rqmcl``/``rzrqye``，全部 Numeric(20,2)（万亿级两融余额 = 10^12 元，余量充足）
- ``rzrqye`` 由服务层重算 = sum(rzye) + sum(rqye)（spec D2：禁止直接 sum 每行）
- tushare 返回的 ``rqyl``（融券余量，股）不入库（spec REQ-2 存储字段不含 rqyl），
  采集层保留原样、聚合时丢弃

仿 ``market_daily_metric.py`` 范式（唯一约束 + 索引 + 双时间戳）。注意（16 期 S1
教训）：ORM ``onupdate`` 不会在 ``on_conflict_do_update`` 路径触发——updated_at
显式刷新由 plan-03 的 ``_atomic_upsert`` 在 ``set_`` 中写 ``func.now()`` 承担，
模型层保持与 market_daily_metric.py 同款双机制即可。
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


class MarketMarginDaily(Base):
    """融资融券全市场日汇总事实表（market_margin_daily）

    高频事实表，每个交易日唯一一条（``trade_date`` 唯一）。存储层统一元/股口径；
    前端显示层由 plan-07 将余额类指标 ÷1e8 转亿展示。六指标由 plan-03 对沪深
    全部交易所行原始数据求和（rzrqye 重算）后写入，rqyl 不入库。
    """

    __tablename__ = "market_margin_daily"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, nullable=False, comment="交易日")

    # ---- 融资融券六指标（元/股口径，与 tushare margin 字段同名） ----
    rzye = Column(
        Numeric(precision=20, scale=2), comment="融资余额（元）"
    )
    rqye = Column(
        Numeric(precision=20, scale=2), comment="融券余额（元）"
    )
    rzmre = Column(
        Numeric(precision=20, scale=2), comment="融资买入额（元）"
    )
    rzche = Column(
        Numeric(precision=20, scale=2), comment="融资偿还额（元）"
    )
    rqmcl = Column(
        Numeric(precision=20, scale=2), comment="融券卖出量（股）"
    )
    rzrqye = Column(
        Numeric(precision=20, scale=2),
        comment="两融合计余额（元；服务层重算 = rzye+rqye 之和）",
    )

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
        UniqueConstraint("trade_date", name="uq_market_margin_daily_trade_date"),
        Index("idx_market_margin_daily_trade_date", "trade_date"),
    )

    def __repr__(self):
        return (
            f"<MarketMarginDaily(trade_date={self.trade_date}, "
            f"rzye={self.rzye}, rqye={self.rqye}, rzrqye={self.rzrqye})>"
        )
