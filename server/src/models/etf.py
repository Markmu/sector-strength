"""ETF 基础信息与日份额数据模型

仿 ``fund.py``（Integer 自增主键 + created_at/updated_at）与
``sector_fund_flow.py``（Numeric + UniqueConstraint + Index）范式。

- ``EtfBasic``：ETF 基础信息（慢变维度），ts_code 唯一。来源 Tushare
  ``etf_basic`` 接口（list_status='L' 仅上市），跟踪指数用官方 index_code /
  index_name 直接入库，不再做文本归类。
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

    慢变维度表，ts_code 为唯一关联键。数据来源 Tushare ``etf_basic`` 接口
    （list_status='L' 仅上市 ETF）。跟踪指数直接用官方 index_code / index_name，
    不再做 benchmark 文本归类。
    """

    __tablename__ = "etf_basic"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    # 唯一关联键（与 etf_daily.ts_code 对应）
    ts_code = Column(String(20), unique=True, nullable=False, comment="TS代码，唯一标识")
    name = Column(String(100), comment="ETF简称（etf_basic.csname）")
    full_name = Column(String(200), comment="基金全称（etf_basic.cname）")
    # 跟踪指数（官方直取，取代旧 benchmark 文本归类）
    index_code = Column(String(20), comment="跟踪指数代码（etf_basic.index_code）")
    index_name = Column(String(100), comment="跟踪指数名（etf_basic.index_name）")
    list_date = Column(Date, comment="上市日期")
    setup_date = Column(Date, comment="设立日期")
    # L 上市 / D 退市 / P 待上市（采集时固定筛 list_status='L'）
    list_status = Column(String(10), comment="存续状态: L上市 D退市 P待上市")
    exchange = Column(String(10), comment="交易所: SH/SZ")
    mgr_name = Column(String(100), comment="基金管理人简称")
    etf_type = Column(String(20), comment="投资通道类型（境内/QDII）")

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), comment="更新时间"
    )

    __table_args__ = (
        Index("idx_etf_basic_index_code", "index_code"),
    )

    def __repr__(self):
        return (
            f"<EtfBasic(ts_code={self.ts_code}, name={self.name}, "
            f"index_code={self.index_code})>"
        )


class EtfDaily(Base):
    """ETF 日份额/规模/净值事实表（etf_daily）

    高频事实表，每个交易日每只 ETF 一条，唯一约束 (trade_date, ts_code)。
    数据来源 Tushare ``etf_share_size`` 接口（按 trade_date 全量），采集时即计算
    share_change / net_inflow / change_percent 并落库，查询直接读现成字段。
    """

    __tablename__ = "etf_daily"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, nullable=False, comment="交易日")
    ts_code = Column(String(20), nullable=False, comment="TS代码")
    # ---- etf_share_size 接口直取字段 ----
    # 总份额（万份，与 fund_share.fd_share 口径一致；etf_share_size.total_share）
    total_share = Column(Numeric(precision=20, scale=4), comment="总份额（万份）")
    # 总规模（万元，etf_share_size.total_size；÷10000 转亿元展示）
    total_size = Column(Numeric(precision=20, scale=4), comment="总规模（万元）")
    # 单位净值（元，etf_share_size.nav；部分日期可能缺失）
    nav = Column(Numeric(precision=10, scale=4), comment="单位净值（元）")
    # 二级市场收盘价（元，etf_share_size.close；部分日期可能缺失）
    close = Column(Numeric(precision=10, scale=4), comment="收盘价（元）")
    # ---- 采集时计算字段 ----
    # 份额变化 = 当日 total_share − 前日 total_share（万份），首日无前日数据为 null
    share_change = Column(
        Numeric(precision=20, scale=4), comment="份额变化（万份，首日null）"
    )
    # 净流入额 = share_change × nav / 10000（亿元），nav 缺失时为 null
    net_inflow = Column(
        Numeric(precision=18, scale=4), comment="净流入额（亿元，nav缺失或首日为null）"
    )
    # 涨跌幅(%) = (当日close − 前日close) / 前日close × 100，close 缺失时为 null
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
            f"total_share={self.total_share}, net_inflow={self.net_inflow})>"
        )
