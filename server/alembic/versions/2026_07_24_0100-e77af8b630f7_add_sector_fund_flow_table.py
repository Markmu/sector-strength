"""add sector fund flow table

Revision ID: e77af8b630f7
Revises: dd92f496dfaf
Create Date: 2026-07-24 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e77af8b630f7'
down_revision: Union[str, Sequence[str], None] = 'dd92f496dfaf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create sector_fund_flow table."""
    op.create_table(
        'sector_fund_flow',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日'),
        sa.Column('sample_time', sa.DateTime(), nullable=False,
                  comment='采样时间，精度到分钟（秒/微秒置零）'),
        sa.Column('sector_type', sa.String(length=20), nullable=False,
                  comment='板块类型: industry / concept'),
        sa.Column('sector_name', sa.String(length=100), nullable=False, comment='板块名称'),
        sa.Column('sector_index', sa.Numeric(precision=15, scale=2), nullable=True,
                  comment='行业指数'),
        sa.Column('change_percent', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='行业-涨跌幅(%)'),
        sa.Column('inflow', sa.Numeric(precision=15, scale=2), nullable=True, comment='流入资金(亿元)'),
        sa.Column('outflow', sa.Numeric(precision=15, scale=2), nullable=True, comment='流出资金(亿元)'),
        sa.Column('net_inflow', sa.Numeric(precision=15, scale=2), nullable=True, comment='净额(亿元)'),
        sa.Column('company_count', sa.Integer(), nullable=True, comment='公司家数'),
        sa.Column('leading_stock', sa.String(length=50), nullable=True, comment='领涨股'),
        sa.Column('leading_stock_change', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='领涨股-涨跌幅(%)'),
        sa.Column('current_price', sa.Numeric(precision=15, scale=2), nullable=True,
                  comment='领涨股当前价'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'sample_time', 'sector_type', 'sector_name',
                            name='uq_sector_fund_flow_sample'),
    )
    op.create_index('ix_sector_fund_flow_trade_date', 'sector_fund_flow', ['trade_date'],
                    unique=False)
    op.create_index('ix_sector_fund_flow_sector_type', 'sector_fund_flow', ['sector_type'],
                    unique=False)
    op.create_index('idx_sff_date_type', 'sector_fund_flow', ['trade_date', 'sector_type'],
                    unique=False)
    op.create_index(
        'idx_sff_date_type_name_time', 'sector_fund_flow',
        ['trade_date', 'sector_type', 'sector_name', 'sample_time'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema: drop sector_fund_flow table."""
    op.drop_index('idx_sff_date_type_name_time', table_name='sector_fund_flow')
    op.drop_index('idx_sff_date_type', table_name='sector_fund_flow')
    op.drop_index('ix_sector_fund_flow_sector_type', table_name='sector_fund_flow')
    op.drop_index('ix_sector_fund_flow_trade_date', table_name='sector_fund_flow')
    op.drop_table('sector_fund_flow')
