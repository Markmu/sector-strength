"""rebuild etf_daily table for etf_share_size 接口

Revision ID: d8a3f5c1b2e4
Revises: c4f2a1b9e7d3
Create Date: 2026-08-01 00:02:00

ETF 日份额/净值采集改用 Tushare ``etf_share_size`` 接口（按 trade_date 全量），
一个接口同时返回份额 + 规模 + 净值 + 收盘价，取代旧 fund_share + 逐只 fund_nav 方案。

本迁移删除旧 etf_daily 表并按新结构重建。旧数据丢弃，后续重新同步即可。
etf_basic 不动。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a3f5c1b2e4'
down_revision: Union[str, Sequence[str], None] = 'c4f2a1b9e7d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: drop 旧 etf_daily + 按新结构重建。"""
    # 1. 删除旧 etf_daily（含旧索引）
    op.drop_index('idx_etf_daily_code_date', table_name='etf_daily')
    op.drop_index('idx_etf_daily_date', table_name='etf_daily')
    op.drop_table('etf_daily')

    # 2. 按新结构重建 etf_daily：来源 Tushare etf_share_size 接口
    op.create_table(
        'etf_daily',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日'),
        sa.Column('ts_code', sa.String(length=20), nullable=False, comment='TS代码'),
        # etf_share_size 接口直取字段
        sa.Column('total_share', sa.Numeric(precision=20, scale=4), nullable=True,
                  comment='总份额（万份）'),
        sa.Column('total_size', sa.Numeric(precision=20, scale=4), nullable=True,
                  comment='总规模（万元）'),
        sa.Column('nav', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='单位净值（元）'),
        sa.Column('close', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='收盘价（元）'),
        # 采集时计算字段
        sa.Column('share_change', sa.Numeric(precision=20, scale=4), nullable=True,
                  comment='份额变化（万份，首日null）'),
        sa.Column('net_inflow', sa.Numeric(precision=18, scale=4), nullable=True,
                  comment='净流入额（亿元，nav缺失或首日为null）'),
        sa.Column('change_percent', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='涨跌幅(%)'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code', name='uq_etf_daily_date_code'),
    )
    op.create_index('idx_etf_daily_date', 'etf_daily', ['trade_date'], unique=False)
    op.create_index('idx_etf_daily_code_date', 'etf_daily', ['ts_code', 'trade_date'],
                    unique=False)


def downgrade() -> None:
    """Downgrade schema: 恢复旧 etf_daily 结构（数据不恢复）。"""
    op.drop_index('idx_etf_daily_code_date', table_name='etf_daily')
    op.drop_index('idx_etf_daily_date', table_name='etf_daily')
    op.drop_table('etf_daily')

    # 恢复旧结构（仅 schema，数据已丢）
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
    op.create_index('idx_etf_daily_date', 'etf_daily', ['trade_date'], unique=False)
    op.create_index('idx_etf_daily_code_date', 'etf_daily', ['ts_code', 'trade_date'],
                    unique=False)
