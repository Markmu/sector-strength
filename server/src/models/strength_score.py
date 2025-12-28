"""强度得分模型"""

from sqlalchemy import Column, String, Date, Integer, Numeric, DateTime, Index, text
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

    # 时间和周期
    date = Column(Date, nullable=False, index=True, comment="计算日期")
    period = Column(String(10), nullable=False, index=True, comment="分析周期: 5d, 10d, 20d, 30d, 60d")

    # 基础得分数据
    score = Column(Numeric(precision=10, scale=4), nullable=False, comment="综合强度得分(0-100)")
    rank = Column(Integer, comment="排名")
    change_rate = Column(Numeric(precision=10, scale=4), default=0, comment="得分变化率(%)")
    strength_level = Column(String(20), comment="强度等级: weak, medium, strong, very_strong")

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

    # 复合索引
    __table_args__ = (
        Index('idx_strength_scores_entity_period', 'entity_type', 'entity_id', 'period'),
        Index('idx_strength_scores_date_period', 'date', 'period'),
        Index('idx_strength_scores_rank', 'rank'),
        Index('idx_strength_scores_score', 'score'),
        # 移除了过于严格的唯一约束，允许同一实体在同一天有不同周期的数据
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
        """获取周期名称"""
        period_map = {
            "5d": "5日",
            "10d": "10日",
            "20d": "20日",
            "30d": "30日",
            "60d": "60日"
        }
        return period_map.get(self.period, f"{self.period}周期")