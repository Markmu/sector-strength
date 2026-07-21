"""股票强度得分独立表模型"""

from sqlalchemy import (
    Column, String, Date, Integer, Numeric, DateTime, Index, text, CheckConstraint, UniqueConstraint
)
from sqlalchemy.sql import func

from .base import Base


class StockStrengthScore(Base):
    """股票强度得分模型（股票独立表）

    存储个股的强度得分数据。无 entity_type、无 period、无板块专属字段。
    显式保留 percentile 列（ADR-3：ranking_service 写个股排名时需要）。
    """
    __tablename__ = "stock_strength_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 实体ID与代码
    stock_id = Column(Integer, nullable=False, index=True)  # 指向 stocks.id，原 entity_id 改名
    symbol = Column(String(20), nullable=False, index=True, comment="股票代码")

    # 时间
    date = Column(Date, nullable=False, index=True, comment="计算日期")

    # 基础得分数据
    score = Column(Numeric(precision=10, scale=4), nullable=False, comment="综合强度得分(0-100)")
    rank = Column(Integer, comment="排名")
    change_rate = Column(Numeric(precision=10, scale=4), default=0, comment="得分变化率(%)")
    strength_level = Column(String(20), comment="强度等级: weak, medium, strong, very_strong")

    # 均线系统核心得分字段
    price_position_score = Column(Numeric(precision=10, scale=2), comment="价格位置得分(0-100)")
    ma_alignment_score = Column(Numeric(precision=10, scale=2), comment="均线排列得分(0-100)")
    ma_alignment_state = Column(String(20), comment="均线排列状态")

    # 短中长期强度得分
    short_term_score = Column(Numeric(precision=10, scale=2), comment="短期强度得分")
    medium_term_score = Column(Numeric(precision=10, scale=2), comment="中期强度得分")
    long_term_score = Column(Numeric(precision=10, scale=2), comment="长期强度得分")

    # 均线数据字段
    current_price = Column(Numeric(precision=10, scale=2), comment="当前价格")
    ma5 = Column(Numeric(precision=10, scale=2), comment="5日均线")
    ma10 = Column(Numeric(precision=10, scale=2), comment="10日均线")
    ma20 = Column(Numeric(precision=10, scale=2), comment="20日均线")
    ma30 = Column(Numeric(precision=10, scale=2), comment="30日均线")
    ma60 = Column(Numeric(precision=10, scale=2), comment="60日均线")
    ma90 = Column(Numeric(precision=10, scale=2), comment="90日均线")
    ma120 = Column(Numeric(precision=10, scale=2), comment="120日均线")
    ma240 = Column(Numeric(precision=10, scale=2), comment="240日均线")

    # 价格相对均线位置 (0=低于, 1=高于)
    price_above_ma5 = Column(Integer, comment="价格是否高于5日均线")
    price_above_ma10 = Column(Integer, comment="价格是否高于10日均线")
    price_above_ma20 = Column(Integer, comment="价格是否高于20日均线")
    price_above_ma30 = Column(Integer, comment="价格是否高于30日均线")
    price_above_ma60 = Column(Integer, comment="价格是否高于60日均线")
    price_above_ma90 = Column(Integer, comment="价格是否高于90日均线")
    price_above_ma120 = Column(Integer, comment="价格是否高于120日均线")
    price_above_ma240 = Column(Integer, comment="价格是否高于240日均线")

    # 排名和变化字段
    change_rate_1d = Column(Numeric(precision=5, scale=2), comment="1日得分变化率(%)")
    strength_grade = Column(String(3), comment="强度等级: S+, S, A+, A, B+, B, C+, C, D+, D")

    # 个股死字段（照搬保留，当前无写入但保留 schema 完整性）
    ma5_score = Column(Numeric(precision=10, scale=4), comment="5日均线得分")
    ma10_score = Column(Numeric(precision=10, scale=4), comment="10日均线得分")
    ma20_score = Column(Numeric(precision=10, scale=4), comment="20日均线得分")
    volume_score = Column(Numeric(precision=10, scale=4), comment="成交量得分")
    momentum_score = Column(Numeric(precision=10, scale=4), comment="动量得分")

    # 百分位（ADR-3 关键：ranking_service.py:91 setattr + strength_snapshot_service.py:342/363 写库，DB 必须有列）
    percentile = Column(Numeric(precision=10, scale=4), comment='百分位')

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 复合索引和约束
    __table_args__ = (
        # 约束
        CheckConstraint('score >= 0 AND score <= 100', name='chk_stock_strength_score_range'),

        # 价格相对均线位置约束 (0=低于, 1=高于)
        CheckConstraint('price_above_ma5 IN (0, 1)', name='chk_stock_strength_price_above_ma5'),
        CheckConstraint('price_above_ma10 IN (0, 1)', name='chk_stock_strength_price_above_ma10'),
        CheckConstraint('price_above_ma20 IN (0, 1)', name='chk_stock_strength_price_above_ma20'),
        CheckConstraint('price_above_ma30 IN (0, 1)', name='chk_stock_strength_price_above_ma30'),
        CheckConstraint('price_above_ma60 IN (0, 1)', name='chk_stock_strength_price_above_ma60'),
        CheckConstraint('price_above_ma90 IN (0, 1)', name='chk_stock_strength_price_above_ma90'),
        CheckConstraint('price_above_ma120 IN (0, 1)', name='chk_stock_strength_price_above_ma120'),
        CheckConstraint('price_above_ma240 IN (0, 1)', name='chk_stock_strength_price_above_ma240'),

        # 新增唯一约束：硬化去重（旧表无）
        UniqueConstraint('stock_id', 'date', name='uq_stock_strength_scores_stock_date'),

        # 优化索引
        Index('idx_stock_strength_symbol_date', 'symbol', text('date DESC')),
        Index('idx_stock_strength_score_desc', text('score DESC'), text('date DESC')),

        # 保留原有索引
        Index('idx_stock_strength_date', 'date'),
        Index('idx_stock_strength_rank', 'rank'),
        Index('idx_stock_strength_score', 'score'),
    )

    def __repr__(self):
        return (
            f"<StockStrengthScore(id={self.id}, stock_id={self.stock_id}, "
            f"date={self.date}, score={self.score}, strength_level={self.strength_level})>"
        )

    @property
    def is_strong(self) -> bool:
        """是否为强势"""
        return self.score >= 75

    @property
    def is_weak(self) -> bool:
        """是否为弱势"""
        return self.score < 50

    def get_strength_level_cn(self) -> str:
        """获取中文强度等级"""
        level_map = {
            "weak": "弱势",
            "medium": "中性",
            "strong": "强势",
            "very_strong": "很强"
        }
        return level_map.get(self.strength_level, "未知")
