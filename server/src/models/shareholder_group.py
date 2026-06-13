"""股东监控组模型

定义股东监控组（ShareholderGroup）及其匹配关键词规则（ShareholderGroupRule）。
管理员可维护监控组及其关键词，用于后续聚合分析持仓股东中的机构资金分布。
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ShareholderGroup(Base):
    """股东监控组表

    每个监控组对应一类机构资金（如国家队、外资投行、社保基金等），
    通过 ShareholderGroupRule 关联多个匹配关键词。
    """

    __tablename__ = "shareholder_groups"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    name = Column(String(100), unique=True, nullable=False, comment="组名（唯一）")
    description = Column(Text, nullable=True, comment="描述")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序权重")
    is_system = Column(Boolean, default=False, nullable=False, comment="是否系统预定义")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="更新时间"
    )

    # 关联规则（CASCADE 删除：删组时一并删规则）
    rules = relationship(
        "ShareholderGroupRule",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self):
        return (
            f"<ShareholderGroup(id={self.id}, name={self.name}, "
            f"is_system={self.is_system})>"
        )


class ShareholderGroupRule(Base):
    """股东监控组匹配关键词规则表

    每条规则对应一个关键词，对 top10_float_holders.holder_name 做 LIKE 匹配，
    用于判断某股东是否属于该监控组。
    """

    __tablename__ = "shareholder_group_rules"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    group_id = Column(
        Integer,
        ForeignKey("shareholder_groups.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属监控组ID",
    )
    keyword = Column(String(200), nullable=False, comment="匹配关键词")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    group = relationship("ShareholderGroup", back_populates="rules")

    __table_args__ = (
        Index("ix_sgr_group_id", "group_id"),
    )

    def __repr__(self):
        return (
            f"<ShareholderGroupRule(id={self.id}, group_id={self.group_id}, "
            f"keyword={self.keyword})>"
        )
