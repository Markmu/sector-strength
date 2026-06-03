"""基金基本信息模型"""

from sqlalchemy import Column, String, Integer, Date, DateTime, Index
from sqlalchemy.sql import func

from .base import Base


class Fund(Base):
    """基金基本信息表"""
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    ts_code = Column(String(20), unique=True, nullable=False, comment="TS代码，唯一标识")
    name = Column(String(100), nullable=False, comment="基金名称")
    management = Column(String(200), comment="管理人")
    custodian = Column(String(200), comment="托管人")
    fund_type = Column(String(50), comment="基金类型")
    invest_type = Column(String(50), comment="投资类型")
    benchmark = Column(String(500), comment="业绩比较基准")
    market = Column(String(20), comment="市场类型: E 场内 O 场外")
    found_date = Column(Date, comment="成立日期")
    list_date = Column(Date, comment="上市日期")
    delist_date = Column(Date, comment="退市日期")
    status = Column(String(20), comment="状态: D 存续 I 发行 E 到期")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        Index('idx_funds_name', 'name'),
    )

    def __repr__(self):
        return f"<Fund(id={self.id}, ts_code={self.ts_code}, name={self.name})>"
