"""涨跌停专题数据模型（连板天梯）

仿 ``etf.py``（Integer 自增主键 + created_at）与 ``sector_fund_flow.py``
（Numeric + UniqueConstraint + Index）范式。三张表均按 trade_date 全量同步，
唯一约束 (trade_date, ts_code)，数据来源 Tushare 涨停专题三接口：

- ``LimitListD``：每日涨跌停/炸板个股明细（limit_list_d 接口，约 200 条/日）
- ``LimitStep``：涨停连板天梯（limit_step 接口，按连板高度分层，约 10 条/日）
- ``LimitCptList``：涨停最强概念板块（limit_cpt_list 接口，约 20 条/日）
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


class LimitListD(Base):
    """每日涨跌停/炸板个股明细表（limit_list_d）

    高频事实表，每个交易日每只股票一条，唯一约束 (trade_date, ts_code)。
    数据来源 Tushare ``limit_list_d`` 接口（不含 ST 股票，数据从 2020 年起）。
    单股板块归属用接口自带的申万 industry 字段（非概念题材维度）。
    """

    __tablename__ = "limit_list_d"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, nullable=False, comment="交易日")
    ts_code = Column(String(20), nullable=False, comment="TS代码")
    name = Column(String(50), comment="股票名称")
    # 申万行业（接口自带，用作个股所属板块展示；非概念题材维度）
    industry = Column(String(50), comment="申万行业（所属板块）")
    close = Column(Numeric(precision=12, scale=4), comment="收盘价（元）")
    pct_chg = Column(Numeric(precision=8, scale=4), comment="涨跌幅(%)")
    # 成交额（元，limit_list_d.amount）
    amount = Column(Numeric(precision=20, scale=4), comment="成交额（元）")
    # 封单成交额（元，limit_amount 常缺失，fd_amount 为实际封单金额）
    fd_amount = Column(Numeric(precision=20, scale=4), comment="封单成交额（元）")
    first_time = Column(String(20), comment="首次封板时间（HH:MM:SS）")
    last_time = Column(String(20), comment="最后封板时间（HH:MM:SS）")
    # 炸板次数（打开次数，0 表示未炸板）
    open_times = Column(Integer, comment="炸板次数")
    # 连板统计描述（如"7天4板""3天2板"，来自 up_stat）
    up_stat = Column(String(30), comment="连板统计（如7天4板）")
    # 连板高度（几连板，1=首板）
    limit_times = Column(Integer, comment="连板数（1=首板）")
    # 涨跌停类型：U涨停 / D跌停 / Z炸板
    limit_type = Column(String(5), comment="类型: U涨停 D跌停 Z炸板")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "ts_code",
            name="uq_limit_list_d_date_code",
        ),
        Index("idx_limit_list_d_date", "trade_date"),
        Index("idx_limit_list_d_date_times", "trade_date", "limit_times"),
    )

    def __repr__(self):
        return (
            f"<LimitListD(trade_date={self.trade_date}, ts_code={self.ts_code}, "
            f"name={self.name}, limit_times={self.limit_times}, "
            f"limit_type={self.limit_type})>"
        )


class LimitStep(Base):
    """涨停连板天梯表（limit_step）

    轻量表，记录当日各连板高度晋级的股票。每个交易日每只股票一条，
    唯一约束 (trade_date, ts_code)。数据来源 Tushare ``limit_step`` 接口。
    """

    __tablename__ = "limit_step"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, nullable=False, comment="交易日")
    ts_code = Column(String(20), nullable=False, comment="TS代码")
    name = Column(String(50), comment="股票名称")
    # 连板高度（几连板，与 limit_list_d.limit_times 口径一致）
    nums = Column(Integer, comment="连板数")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "ts_code",
            name="uq_limit_step_date_code",
        ),
        Index("idx_limit_step_date", "trade_date"),
    )

    def __repr__(self):
        return (
            f"<LimitStep(trade_date={self.trade_date}, ts_code={self.ts_code}, "
            f"name={self.name}, nums={self.nums})>"
        )


class LimitCptList(Base):
    """涨停最强概念板块表（limit_cpt_list）

    轻量表，记录当日涨停家数排名靠前的概念板块。每个交易日每个板块一条，
    唯一约束 (trade_date, ts_code)。数据来源 Tushare ``limit_cpt_list`` 接口。
    """

    __tablename__ = "limit_cpt_list"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    trade_date = Column(Date, nullable=False, comment="交易日")
    ts_code = Column(String(20), nullable=False, comment="板块代码")
    name = Column(String(50), comment="板块名称")
    # 板块连续活跃天数
    days = Column(Integer, comment="连续活跃天数")
    # 板块连板统计描述（如"5天5板"）
    up_stat = Column(String(30), comment="板块连板统计")
    # 连板家数（板块内连板个股数）
    cons_nums = Column(Integer, comment="连板家数")
    # 涨停家数（板块内涨停个股总数）
    up_nums = Column(Integer, comment="涨停家数")
    pct_chg = Column(Numeric(precision=8, scale=4), comment="板块涨跌幅(%)")
    rank = Column(Integer, comment="排名")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "ts_code",
            name="uq_limit_cpt_list_date_code",
        ),
        Index("idx_limit_cpt_list_date", "trade_date"),
    )

    def __repr__(self):
        return (
            f"<LimitCptList(trade_date={self.trade_date}, ts_code={self.ts_code}, "
            f"name={self.name}, up_nums={self.up_nums}, rank={self.rank})>"
        )
