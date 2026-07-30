"""ETF 基础信息与日份额数据模型（第 14 期）

仿 ``fund.py``（Integer 自增主键 + created_at/updated_at）与
``sector_fund_flow.py``（Numeric + UniqueConstraint + Index）范式。

- ``EtfBasic``：ETF 基础信息（慢变维度），ts_code 唯一，含指数归类结果。
- ``EtfDaily``：ETF 日份额/净值事实表，(trade_date, ts_code) 唯一，
  采集时即计算 share_change / net_inflow（ADR-3）。
"""

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


class EtfBasic(Base):
    """ETF 基础信息表（etf_basic）

    慢变维度表，ts_code 为唯一关联键。``index_name`` / ``category`` 由
    ``EtfIndexClassifier`` 从 benchmark 文本归集产出（ADR-2）。
    """

    __tablename__ = "etf_basic"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    # 唯一关联键（与 etf_daily.ts_code 对应）
    ts_code = Column(String(20), unique=True, nullable=False, comment="TS代码，唯一标识")
    name = Column(String(100), comment="ETF名称")
    management = Column(String(200), comment="管理人")
    fund_type = Column(String(50), comment="基金类型")
    list_date = Column(Date, comment="上市日期")
    benchmark = Column(String(500), comment="业绩比较基准（跟踪指数文本）")
    index_name = Column(String(100), comment="归集后的跟踪指数名（归集器产出）")
    # broad 宽基 / industry 行业 / other 未覆盖兜底
    category = Column(String(20), comment="指数分类: broad/industry/other")
    status = Column(String(20), comment="状态: I 发行中 L 已上市 E 到期")
    market = Column(String(20), default="E", comment="市场类型: E 场内")

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), comment="更新时间"
    )

    __table_args__ = (
        Index("idx_etf_basic_category", "category"),
    )

    def __repr__(self):
        return (
            f"<EtfBasic(ts_code={self.ts_code}, name={self.name}, "
            f"category={self.category})>"
        )


class EtfDaily(Base):
    """ETF 日份额/净值事实表（etf_daily）

    高频事实表，每个交易日每只 ETF 一条，唯一约束 (trade_date, ts_code)。
    采集时即计算 share_change / net_inflow 并落库（ADR-3），查询直接读现成字段。
    """

    __tablename__ = "etf_daily"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, index=True, comment="交易日")
    ts_code = Column(String(20), comment="TS代码")
    # 份额单位：万份（与 fund_share.fd_share 口径一致）
    share = Column(Numeric(precision=20, scale=4), comment="份额（万份）")
    # 单位净值：元
    unit_nav = Column(Numeric(precision=10, scale=4), comment="单位净值（元）")
    # 份额变化 = 当日份额 − 前日份额（万份），首日无前日数据为 null
    share_change = Column(
        Numeric(precision=20, scale=4), comment="份额变化（万份，首日null）"
    )
    # 净流入额 = share_change × unit_nav / 10000（亿元）
    net_inflow = Column(
        Numeric(precision=18, scale=4), comment="净流入额（亿元，首日null）"
    )
    # ETF 二级市场涨跌幅（%）：当前数据源 fund_daily 不可用，首版存 null（TODO）
    change_percent = Column(Numeric(precision=10, scale=4), comment="涨跌幅(%)")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "ts_code",
            name="uq_etf_daily_date_code",
        ),
        Index("idx_etf_daily_date", "trade_date"),
        Index("idx_etf_daily_code_date", "ts_code", "trade_date"),
    )

    def __repr__(self):
        return (
            f"<EtfDaily(trade_date={self.trade_date}, ts_code={self.ts_code}, "
            f"share={self.share}, net_inflow={self.net_inflow})>"
        )
