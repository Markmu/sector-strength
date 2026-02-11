"""板块分类模型

板块强弱分类数据模型，存储根据缠论理论计算的板块分类结果。
"""
import decimal
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class SectorClassification(Base):
    """板块分类模型

    存储板块根据缠论均线理论的分类结果，包括分类级别（第1-9类）
    和反弹/调整状态。

    Attributes:
        id: 主键（自增整数，无业务含义）
        sector_id: 外键，关联 sectors.id
        symbol: 板块编码
        classification_date: 分类日期
        classification_level: 分类级别（1-9）
        state: 状态（'反弹' or '调整'）
        current_price: 当前价格
        change_percent: 涨跌幅百分比
        ma_5 至 ma_240: 各周期均线值
        price_5_days_ago: 5天前价格
        created_at: 创建时间（UTC）
    """
    __tablename__ = 'sector_classification'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sector_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('sectors.id'),
        nullable=False,
        index=True
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)  # 板块编码
    classification_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    classification_level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-9
    state: Mapped[str] = mapped_column(String(10), nullable=False)  # '反弹' or '调整'
    current_price: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    change_percent: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(5, 2))
    ma_5: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    ma_10: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    ma_20: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    ma_30: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    ma_60: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    ma_90: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    ma_120: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    ma_240: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    price_5_days_ago: Mapped[Optional[decimal.Decimal]] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<SectorClassification("
            f"id={self.id}, "
            f"sector_id={self.sector_id}, "
            f"symbol={self.symbol}, "
            f"level={self.classification_level}, "
            f"state={self.state})>"
        )
