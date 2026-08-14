"""本地交易日历模型（第 16 期 A股全市场量价指标）

表 ``trading_calendar_days``，每个自然日唯一一行（含开市/休市标记），承接同步拆分、
非交易日守卫与首页缺口轴（架构 ADR-6）。数据由 ``TradingCalendarRepository.refresh_range``
从 Tushare ``trade_cal(exchange='SSE')`` 闭区间全量拉取后单事务原子 upsert。

- ``cal_date``：自然日，唯一键
- ``is_open``：是否开市（True/False），不过滤——首页缺口轴需要休市日锚点
- ``refresh_batch_id`` / ``refreshed_at``：刷新批次标识，同一次 ``refresh_range``
  写入的全部行共享同一批次值，便于追溯与覆盖判定

GET 读路径禁止实例化 ``TradingCalendar``（会实时访问 Provider），首页与查询一律
读本地表（架构 §8.6）。

仿 ``index_monitor.py`` 范式（Integer 自增主键）。
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    String,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .base import Base


class TradingCalendarDay(Base):
    """本地交易日历表（trading_calendar_days）

    慢变 + 高频混合表，每个自然日唯一（``cal_date`` 唯一）。开市与休市日均写入：
    休市日用于首页缺口轴锚点、非交易日跳过守卫。``refresh_batch_id`` 为 UUID，
    同一次刷新的全部行共享同一值；二次刷新通过 ``cal_date`` upsert 覆盖并整体
    更新批次字段。
    """

    __tablename__ = "trading_calendar_days"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    cal_date = Column(Date, nullable=False, comment="自然日（含开市/休市）")

    is_open = Column(
        Boolean, nullable=False, comment="是否开市（True 开市 / False 休市）"
    )

    refresh_batch_id = Column(
        String(length=36), comment="刷新批次ID（UUID，同批次同值）"
    )
    refreshed_at = Column(
        DateTime(timezone=True), comment="刷新时间（同批次同值）"
    )

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        UniqueConstraint("cal_date", name="uq_trading_calendar_days_cal_date"),
        Index(
            "idx_trading_calendar_days_cal_date_is_open",
            "cal_date",
            "is_open",
        ),
    )

    def __repr__(self):
        return (
            f"<TradingCalendarDay(cal_date={self.cal_date}, "
            f"is_open={self.is_open}, refresh_batch_id={self.refresh_batch_id})>"
        )
