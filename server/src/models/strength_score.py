"""强度得分模型"""

from sqlalchemy import Column, String, Date, Integer, Numeric, DateTime, Index, text, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class StrengthScore(Base):
    """强度得分模型

    存储个股和板块的强度得分数据，支持不同周期的强度分析
    """
    __tablename__ = "strength_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 实体类型和ID
    entity_type = Column(String(10), nullable=False, index=True, comment="实体类型: stock或sector")  # 'stock' or 'sector'
    entity_id = Column(Integer, nullable=False, index=True, comment="实体ID")
    symbol = Column(String(20), nullable=False, index=True, comment="股票代码或板块代码")

    # 时间和周期
    date = Column(Date, nullable=False, index=True, comment="计算日期")
    # @deprecated: period 字段已废弃，保留仅为向后兼容。所有记录统一使用 'all' 值。
    # 短中长期强度已通过 short_term_score, medium_term_score, long_term_score 字段独立存储。
    period = Column(String(10), nullable=False, index=True, server_default="all", comment="[DEPRECATED] 分析周期（已废弃，固定为 'all'）")

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

    # 个股特有字段
    ma5_score = Column(Numeric(precision=10, scale=4), comment="5日均线得分")
    ma10_score = Column(Numeric(precision=10, scale=4), comment="10日均线得分")
    ma20_score = Column(Numeric(precision=10, scale=4), comment="20日均线得分")
    volume_score = Column(Numeric(precision=10, scale=4), comment="成交量得分")
    momentum_score = Column(Numeric(precision=10, scale=4), comment="动量得分")

    # 板块特有字段
    avg_stock_score = Column(Numeric(precision=10, scale=4), comment="板块内个股平均得分")
    strong_stock_ratio = Column(Numeric(precision=5, scale=4), comment="强势个股占比")
    up_stock_ratio = Column(Numeric(precision=5, scale=4), comment="上涨个股占比")
    volume_ratio = Column(Numeric(precision=10, scale=4), comment="成交量比率")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    # 复合索引和约束
    __table_args__ = (
        # 约束
        CheckConstraint('score >= 0 AND score <= 100', name='chk_strength_scores_score_range'),
        # period 已废弃，固定为 'all'
        CheckConstraint("period = 'all'", name='chk_strength_scores_period'),
        CheckConstraint("entity_type IN ('stock', 'sector')", name='chk_strength_scores_entity_type'),

        # 价格相对均线位置约束 (0=低于, 1=高于)
        CheckConstraint('price_above_ma5 IN (0, 1)', name='chk_strength_scores_price_above_ma5'),
        CheckConstraint('price_above_ma10 IN (0, 1)', name='chk_strength_scores_price_above_ma10'),
        CheckConstraint('price_above_ma20 IN (0, 1)', name='chk_strength_scores_price_above_ma20'),
        CheckConstraint('price_above_ma30 IN (0, 1)', name='chk_strength_scores_price_above_ma30'),
        CheckConstraint('price_above_ma60 IN (0, 1)', name='chk_strength_scores_price_above_ma60'),
        CheckConstraint('price_above_ma90 IN (0, 1)', name='chk_strength_scores_price_above_ma90'),
        CheckConstraint('price_above_ma120 IN (0, 1)', name='chk_strength_scores_price_above_ma120'),
        CheckConstraint('price_above_ma240 IN (0, 1)', name='chk_strength_scores_price_above_ma240'),

        # 优化索引
        Index('idx_strength_scores_symbol_date', 'symbol', text('date DESC'), 'period'),
        Index('idx_strength_scores_score_desc', text('score DESC'), text('date DESC')),

        # 保留原有索引
        Index('idx_strength_scores_entity_period', 'entity_type', 'entity_id', 'period'),
        Index('idx_strength_scores_date_period', 'date', 'period'),
        Index('idx_strength_scores_rank', 'rank'),
        Index('idx_strength_scores_score', 'score'),
    )

    def __repr__(self):
        return (
            f"<StrengthScore(id={self.id}, entity_type={self.entity_type}, "
            f"entity_id={self.entity_id}, date={self.date}, period={self.period}, "
            f"score={self.score}, strength_level={self.strength_level})>"
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

    def get_period_name(self) -> str:
        """获取周期名称

        @deprecated: period 字段已废弃，此方法仅为向后兼容保留。
        """
        period_map = {
            "all": "全部",
            "5d": "5日",
            "10d": "10日",
            "20d": "20日",
            "30d": "30日",
            "60d": "60日",
            "90d": "90日",
            "120d": "120日",
            "240d": "240日"
        }
        return period_map.get(self.period, f"{self.period}周期")