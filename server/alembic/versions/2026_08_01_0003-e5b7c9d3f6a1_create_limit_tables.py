"""create limit tables for 涨跌停专题三接口

Revision ID: e5b7c9d3f6a1
Revises: d8a3f5c1b2e4
Create Date: 2026-08-01 00:03:00

新增三张涨跌停专题表，数据来源 Tushare 涨停专题接口：
- ``limit_list_d``：每日涨跌停/炸板个股明细（limit_list_d 接口）
- ``limit_step``：涨停连板天梯（limit_step 接口）
- ``limit_cpt_list``：涨停最强概念板块（limit_cpt_list 接口）

三表均按 trade_date 全量同步，唯一约束 (trade_date, ts_code)。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b7c9d3f6a1'
down_revision: Union[str, Sequence[str], None] = 'd8a3f5c1b2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: 创建三张涨跌停专题表。"""

    # 1. limit_list_d — 每日涨跌停/炸板个股明细
    op.create_table(
        'limit_list_d',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日'),
        sa.Column('ts_code', sa.String(length=20), nullable=False, comment='TS代码'),
        sa.Column('name', sa.String(length=50), nullable=True, comment='股票名称'),
        sa.Column('industry', sa.String(length=50), nullable=True,
                  comment='申万行业（所属板块）'),
        sa.Column('close', sa.Numeric(precision=12, scale=4), nullable=True,
                  comment='收盘价（元）'),
        sa.Column('pct_chg', sa.Numeric(precision=8, scale=4), nullable=True,
                  comment='涨跌幅(%)'),
        sa.Column('amount', sa.Numeric(precision=20, scale=4), nullable=True,
                  comment='成交额（元）'),
        sa.Column('fd_amount', sa.Numeric(precision=20, scale=4), nullable=True,
                  comment='封单成交额（元）'),
        sa.Column('first_time', sa.String(length=20), nullable=True,
                  comment='首次封板时间（HH:MM:SS）'),
        sa.Column('last_time', sa.String(length=20), nullable=True,
                  comment='最后封板时间（HH:MM:SS）'),
        sa.Column('open_times', sa.Integer(), nullable=True, comment='炸板次数'),
        sa.Column('up_stat', sa.String(length=30), nullable=True,
                  comment='连板统计（如7天4板）'),
        sa.Column('limit_times', sa.Integer(), nullable=True,
                  comment='连板数（1=首板）'),
        sa.Column('limit_type', sa.String(length=5), nullable=True,
                  comment='类型: U涨停 D跌停 Z炸板'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code',
                            name='uq_limit_list_d_date_code'),
    )
    op.create_index('idx_limit_list_d_date', 'limit_list_d', ['trade_date'],
                    unique=False)
    op.create_index('idx_limit_list_d_date_times', 'limit_list_d',
                    ['trade_date', 'limit_times'], unique=False)

    # 2. limit_step — 涨停连板天梯
    op.create_table(
        'limit_step',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日'),
        sa.Column('ts_code', sa.String(length=20), nullable=False, comment='TS代码'),
        sa.Column('name', sa.String(length=50), nullable=True, comment='股票名称'),
        sa.Column('nums', sa.Integer(), nullable=True, comment='连板数'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code',
                            name='uq_limit_step_date_code'),
    )
    op.create_index('idx_limit_step_date', 'limit_step', ['trade_date'],
                    unique=False)

    # 3. limit_cpt_list — 涨停最强概念板块
    op.create_table(
        'limit_cpt_list',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日'),
        sa.Column('ts_code', sa.String(length=20), nullable=False, comment='板块代码'),
        sa.Column('name', sa.String(length=50), nullable=True, comment='板块名称'),
        sa.Column('days', sa.Integer(), nullable=True, comment='连续活跃天数'),
        sa.Column('up_stat', sa.String(length=30), nullable=True,
                  comment='板块连板统计'),
        sa.Column('cons_nums', sa.Integer(), nullable=True, comment='连板家数'),
        sa.Column('up_nums', sa.Integer(), nullable=True, comment='涨停家数'),
        sa.Column('pct_chg', sa.Numeric(precision=8, scale=4), nullable=True,
                  comment='板块涨跌幅(%)'),
        sa.Column('rank', sa.Integer(), nullable=True, comment='排名'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code',
                            name='uq_limit_cpt_list_date_code'),
    )
    op.create_index('idx_limit_cpt_list_date', 'limit_cpt_list', ['trade_date'],
                    unique=False)


def downgrade() -> None:
    """Downgrade schema: 删除三张涨跌停专题表。"""
    op.drop_index('idx_limit_cpt_list_date', table_name='limit_cpt_list')
    op.drop_table('limit_cpt_list')

    op.drop_index('idx_limit_step_date', table_name='limit_step')
    op.drop_table('limit_step')

    op.drop_index('idx_limit_list_d_date_times', table_name='limit_list_d')
    op.drop_index('idx_limit_list_d_date', table_name='limit_list_d')
    op.drop_table('limit_list_d')
