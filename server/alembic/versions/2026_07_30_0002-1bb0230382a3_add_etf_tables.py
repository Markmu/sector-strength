"""add etf tables

Revision ID: 1bb0230382a3
Revises: e77af8b630f7
Create Date: 2026-07-30 00:02:46.598055

仅建两张新表（etf_basic / etf_daily）。autogenerate 同时检测到与本期无关的
历史 schema drift（其它表的 comment / index 差异、遗留 sector_classification 表），
本迁移按 plan-01 §3 实现规格 #2 的单表迁移范式手动收敛范围，不夹带无关变更
（参照 2026_07_24_0100-e77af8b630f7_add_sector_fund_flow_table.py）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1bb0230382a3'
down_revision: Union[str, Sequence[str], None] = 'e77af8b630f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create etf_basic + etf_daily tables."""
    # 1. etf_basic：ETF 基础信息（慢变维度），ts_code 唯一，含指数归类结果
    op.create_table(
        'etf_basic',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('ts_code', sa.String(length=20), nullable=False,
                  comment='TS代码，唯一标识'),
        sa.Column('name', sa.String(length=100), nullable=True, comment='ETF名称'),
        sa.Column('management', sa.String(length=200), nullable=True, comment='管理人'),
        sa.Column('fund_type', sa.String(length=50), nullable=True, comment='基金类型'),
        sa.Column('list_date', sa.Date(), nullable=True, comment='上市日期'),
        sa.Column('benchmark', sa.String(length=500), nullable=True,
                  comment='业绩比较基准（跟踪指数文本）'),
        sa.Column('index_name', sa.String(length=100), nullable=True,
                  comment='归集后的跟踪指数名（归集器产出）'),
        sa.Column('category', sa.String(length=20), nullable=True,
                  comment='指数分类: broad/industry/other'),
        sa.Column('status', sa.String(length=20), nullable=True,
                  comment='状态: I 发行中 L 已上市 E 到期'),
        sa.Column('market', sa.String(length=20), nullable=True,
                  comment='市场类型: E 场内'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                  comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ts_code'),
    )
    op.create_index('idx_etf_basic_category', 'etf_basic', ['category'],
                    unique=False)

    # 2. etf_daily：ETF 日份额/净值事实表，(trade_date, ts_code) 唯一，
    #    采集时即计算 share_change / net_inflow 并落库（ADR-3）
    op.create_table(
        'etf_daily',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('trade_date', sa.Date(), nullable=True, comment='交易日'),
        sa.Column('ts_code', sa.String(length=20), nullable=True, comment='TS代码'),
        sa.Column('share', sa.Numeric(precision=20, scale=4), nullable=True,
                  comment='份额（万份）'),
        sa.Column('unit_nav', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='单位净值（元）'),
        sa.Column('share_change', sa.Numeric(precision=20, scale=4), nullable=True,
                  comment='份额变化（万份，首日null）'),
        sa.Column('net_inflow', sa.Numeric(precision=18, scale=4), nullable=True,
                  comment='净流入额（亿元，首日null）'),
        sa.Column('change_percent', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='涨跌幅(%)'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code', name='uq_etf_daily_date_code'),
    )
    op.create_index('idx_etf_daily_date', 'etf_daily', ['trade_date'],
                    unique=False)
    op.create_index('idx_etf_daily_code_date', 'etf_daily', ['ts_code', 'trade_date'],
                    unique=False)


def downgrade() -> None:
    """Downgrade schema: drop etf_daily + etf_basic tables."""
    op.drop_index('idx_etf_daily_code_date', table_name='etf_daily')
    op.drop_index('idx_etf_daily_date', table_name='etf_daily')
    op.drop_table('etf_daily')
    op.drop_index('idx_etf_basic_category', table_name='etf_basic')
    op.drop_table('etf_basic')
