"""指数数据模型（关键指数监控面板，第 15 期）

仿 ``etf.py``（Integer 自增主键 + created_at/updated_at）与
``sector_fund_flow.py``（Numeric + UniqueConstraint + Index）范式。

- ``IndexBasic``：指数基础信息（慢变维度），ts_code 唯一，关注标记位 is_watched。
- ``IndexDaily``：指数日线行情事实表，(trade_date, ts_code) 唯一。
- ``IndexDailyBasic``：指数每日估值指标事实表，(trade_date, ts_code) 唯一。
- ``IndexWeight``：指数成分权重事实表，(index_code, con_code, trade_date) 唯一。
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .base import Base


class IndexBasic(Base):
    """指数基础信息表（index_basic）

    慢变维度表，ts_code 为唯一关联键。数据来源 Tushare ``index_basic`` 接口
    （全量拉取，约 1 万条）。关注标记 ``is_watched`` 取代独立 watchlist 表（ADR-2），
    默认 false；plan-02 的 ``sync_index_basic`` 完成后用一次性 SQL 将 14 只
    预置关注指数置为 true。

    注意：``index_basic(name=...)`` 参数在数据源代理上不生效，不能靠 name 过滤查代码。
    """

    __tablename__ = "index_basic"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    # 唯一关联键（与 index_daily.ts_code 等对应）
    ts_code = Column(String(20), unique=True, nullable=False, comment="TS指数代码，唯一标识（如 000300.SH）")
    name = Column(String(50), comment="指数简称")
    # SSE 上交所 / SZSE 深交所 / CSI 中证指数 / SW 申万
    market = Column(String(10), comment="市场: SSE/SZSE/CSI/SW")
    publisher = Column(String(100), comment="发布机构")
    category = Column(String(50), comment="指数类别")
    base_date = Column(Date, comment="基期")
    base_point = Column(Numeric(precision=20, scale=4), comment="基点")
    list_date = Column(Date, comment="发布日期")
    # 关注标记（ADR-2）：替代独立 watchlist 表，默认 false
    is_watched = Column(Boolean, default=False, comment="是否加入关注清单")
    # 关注清单排序（0 起，越小越靠前）；非关注指数为 NULL
    sort_order = Column(
        Integer, nullable=True, comment="关注清单排序（0 起，越小越靠前）"
    )

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), comment="更新时间"
    )

    __table_args__ = (
        Index("idx_index_basic_watched", "is_watched"),
    )

    def __repr__(self):
        return (
            f"<IndexBasic(ts_code={self.ts_code}, name={self.name}, "
            f"is_watched={self.is_watched})>"
        )


class IndexDaily(Base):
    """指数日线行情事实表（index_daily）

    高频事实表，每个交易日每只指数一条，唯一约束 (trade_date, ts_code)。
    数据来源 Tushare ``index_daily`` 接口（按 ts_code + 日期区间拉取）。

    存储层保持 Tushare 原始单位：
    - ``vol``：成交量（手）
    - ``amount``：成交额（千元）
    API 输出层由 plan-03 将 amount 转亿元（÷10000）。
    """

    __tablename__ = "index_daily"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, nullable=False, comment="交易日")
    ts_code = Column(String(20), nullable=False, comment="TS指数代码")
    # ---- index_daily 接口直取字段 ----
    open = Column(Numeric(precision=20, scale=4), comment="开盘价")
    high = Column(Numeric(precision=20, scale=4), comment="最高价")
    low = Column(Numeric(precision=20, scale=4), comment="最低价")
    close = Column(Numeric(precision=20, scale=4), comment="收盘价")
    pre_close = Column(Numeric(precision=20, scale=4), comment="前收价")
    change = Column(Numeric(precision=20, scale=4), comment="涨跌额")
    pct_chg = Column(Numeric(precision=10, scale=4), comment="涨跌幅(%)")
    vol = Column(Numeric(precision=20, scale=2), comment="成交量（手）")
    amount = Column(Numeric(precision=20, scale=2), comment="成交额（千元）")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "ts_code",
            name="uq_index_daily_date_code",
        ),
        Index("idx_index_daily_date", "trade_date"),
        Index("idx_index_daily_code_date", "ts_code", "trade_date"),
    )

    def __repr__(self):
        return (
            f"<IndexDaily(trade_date={self.trade_date}, ts_code={self.ts_code}, "
            f"close={self.close}, pct_chg={self.pct_chg})>"
        )


class IndexDailyBasic(Base):
    """指数每日估值指标事实表（index_dailybasic）

    高频事实表，唯一约束 (trade_date, ts_code)。数据来源 Tushare
    ``index_dailybasic`` 接口。

    估值覆盖：仅宽基指数有数据（如沪深300/上证50/中证500/上证180/深证成指/
    创业板指等），其余指数（如科创50）返回空列表，由上层如实提示"暂无估值"。
    """

    __tablename__ = "index_dailybasic"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, nullable=False, comment="交易日")
    ts_code = Column(String(20), nullable=False, comment="TS指数代码")
    # ---- 市值（元） ----
    total_mv = Column(Numeric(precision=24, scale=2), comment="总市值（元）")
    float_mv = Column(Numeric(precision=24, scale=2), comment="流通市值（元）")
    # ---- 股本（股） ----
    total_share = Column(Numeric(precision=24, scale=0), comment="总股本（股）")
    float_share = Column(Numeric(precision=24, scale=0), comment="流通股本（股）")
    free_share = Column(Numeric(precision=24, scale=0), comment="自由流通股本（股）")
    # ---- 换手率（%） ----
    turnover_rate = Column(Numeric(precision=10, scale=4), comment="换手率(%)")
    turnover_rate_f = Column(Numeric(precision=10, scale=4), comment="换手率F(%)")
    # ---- 估值指标 ----
    pe = Column(Numeric(precision=10, scale=4), comment="市盈率")
    pe_ttm = Column(Numeric(precision=10, scale=4), comment="市盈率TTM")
    pb = Column(Numeric(precision=10, scale=4), comment="市净率")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "ts_code",
            name="uq_index_dailybasic_date_code",
        ),
        Index("idx_index_dailybasic_date", "trade_date"),
        Index("idx_index_dailybasic_code_date", "ts_code", "trade_date"),
    )

    def __repr__(self):
        return (
            f"<IndexDailyBasic(trade_date={self.trade_date}, ts_code={self.ts_code}, "
            f"pe_ttm={self.pe_ttm}, pb={self.pb})>"
        )


class IndexWeight(Base):
    """指数成分权重事实表（index_weight）

    高频事实表，唯一约束 (index_code, con_code, trade_date)。数据来源 Tushare
    ``index_weight`` 接口（注意接口参数名是 ``index_code``，不是 ts_code）。

    成分股权重通常在指数调整日（如半年报）刷新，其余交易日数据沿用最近一次调整。
    沪深300 实测返回约 300 条。
    """

    __tablename__ = "index_weight"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    index_code = Column(String(20), nullable=False, comment="指数TS代码（如 000300.SH）")
    con_code = Column(String(20), nullable=False, comment="成分股TS代码（如 600000.SH）")
    trade_date = Column(Date, nullable=False, comment="交易日")
    weight = Column(Numeric(precision=10, scale=4), comment="权重(%)")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "index_code",
            "con_code",
            "trade_date",
            name="uq_index_weight_code_con_date",
        ),
        Index("idx_index_weight_code", "index_code"),
        Index("idx_index_weight_con_code", "con_code"),
    )

    def __repr__(self):
        return (
            f"<IndexWeight(index_code={self.index_code}, con_code={self.con_code}, "
            f"trade_date={self.trade_date}, weight={self.weight})>"
        )
