"""add index monitor tables

Revision ID: f92bfffc49c3
Revises: a2c4e6f8b1d3
Create Date: 2026-08-10 22:03:29.553953

为关键指数监控面板（第 15 期 plan-01）新建 4 张指数数据表：
- ``index_basic``：指数基础信息（慢变维度），ts_code 唯一，含 is_watched 关注标记（ADR-2）
- ``index_daily``：指数日线行情事实表，(trade_date, ts_code) 唯一
- ``index_dailybasic``：指数每日估值指标事实表，(trade_date, ts_code) 唯一
- ``index_weight``：指数成分权重事实表，(index_code, con_code, trade_date) 唯一

autogenerate 同时检测到与本期无关的历史 schema drift（其他表的 comment / index 差异、
遗留 sector_classification 表），本迁移按 plan-01 §3 实现规格 #3 的单表迁移范式手动
收敛范围，不夹带无关变更（参照 2026_07_30_0002-1bb0230382a3_add_etf_tables.py）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f92bfffc49c3'
down_revision: Union[str, Sequence[str], None] = 'a2c4e6f8b1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create index_basic + index_daily + index_dailybasic + index_weight."""
    # 1. index_basic：指数基础信息（慢变维度），ts_code 唯一，is_watched 关注标记（ADR-2）
    op.create_table(
        'index_basic',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('ts_code', sa.String(length=20), nullable=False,
                  comment='TS指数代码，唯一标识（如 000300.SH）'),
        sa.Column('name', sa.String(length=50), nullable=True, comment='指数简称'),
        sa.Column('market', sa.String(length=10), nullable=True,
                  comment='市场: SSE/SZSE/CSI/SW'),
        sa.Column('publisher', sa.String(length=100), nullable=True, comment='发布机构'),
        sa.Column('category', sa.String(length=50), nullable=True, comment='指数类别'),
        sa.Column('base_date', sa.Date(), nullable=True, comment='基期'),
        sa.Column('base_point', sa.Numeric(precision=20, scale=4), nullable=True,
                  comment='基点'),
        sa.Column('list_date', sa.Date(), nullable=True, comment='发布日期'),
        sa.Column('is_watched', sa.Boolean(), nullable=True, comment='是否加入关注清单'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ts_code'),
    )
    op.create_index('idx_index_basic_watched', 'index_basic', ['is_watched'],
                    unique=False)

    # 2. index_daily：指数日线行情事实表，(trade_date, ts_code) 唯一
    #    存储层保持 Tushare 原始单位：vol 手 / amount 千元（API 输出层转亿元）
    op.create_table(
        'index_daily',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日'),
        sa.Column('ts_code', sa.String(length=20), nullable=False, comment='TS指数代码'),
        sa.Column('open', sa.Numeric(precision=20, scale=4), nullable=True, comment='开盘价'),
        sa.Column('high', sa.Numeric(precision=20, scale=4), nullable=True, comment='最高价'),
        sa.Column('low', sa.Numeric(precision=20, scale=4), nullable=True, comment='最低价'),
        sa.Column('close', sa.Numeric(precision=20, scale=4), nullable=True, comment='收盘价'),
        sa.Column('pre_close', sa.Numeric(precision=20, scale=4), nullable=True,
                  comment='前收价'),
        sa.Column('change', sa.Numeric(precision=20, scale=4), nullable=True, comment='涨跌额'),
        sa.Column('pct_chg', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='涨跌幅(%)'),
        sa.Column('vol', sa.Numeric(precision=20, scale=2), nullable=True,
                  comment='成交量（手）'),
        sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=True,
                  comment='成交额（千元）'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code', name='uq_index_daily_date_code'),
    )
    op.create_index('idx_index_daily_date', 'index_daily', ['trade_date'],
                    unique=False)
    op.create_index('idx_index_daily_code_date', 'index_daily', ['ts_code', 'trade_date'],
                    unique=False)

    # 3. index_dailybasic：指数每日估值指标事实表，(trade_date, ts_code) 唯一
    #    仅宽基指数有数据，其余指数返回空（如实提示"暂无估值"）
    op.create_table(
        'index_dailybasic',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日'),
        sa.Column('ts_code', sa.String(length=20), nullable=False, comment='TS指数代码'),
        sa.Column('total_mv', sa.Numeric(precision=24, scale=2), nullable=True,
                  comment='总市值（元）'),
        sa.Column('float_mv', sa.Numeric(precision=24, scale=2), nullable=True,
                  comment='流通市值（元）'),
        sa.Column('total_share', sa.Numeric(precision=24, scale=0), nullable=True,
                  comment='总股本（股）'),
        sa.Column('float_share', sa.Numeric(precision=24, scale=0), nullable=True,
                  comment='流通股本（股）'),
        sa.Column('free_share', sa.Numeric(precision=24, scale=0), nullable=True,
                  comment='自由流通股本（股）'),
        sa.Column('turnover_rate', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='换手率(%)'),
        sa.Column('turnover_rate_f', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='换手率F(%)'),
        sa.Column('pe', sa.Numeric(precision=10, scale=4), nullable=True, comment='市盈率'),
        sa.Column('pe_ttm', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='市盈率TTM'),
        sa.Column('pb', sa.Numeric(precision=10, scale=4), nullable=True, comment='市净率'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', 'ts_code',
                            name='uq_index_dailybasic_date_code'),
    )
    op.create_index('idx_index_dailybasic_date', 'index_dailybasic', ['trade_date'],
                    unique=False)
    op.create_index('idx_index_dailybasic_code_date', 'index_dailybasic',
                    ['ts_code', 'trade_date'], unique=False)

    # 4. index_weight：指数成分权重事实表，(index_code, con_code, trade_date) 唯一
    op.create_table(
        'index_weight',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('index_code', sa.String(length=20), nullable=False,
                  comment='指数TS代码（如 000300.SH）'),
        sa.Column('con_code', sa.String(length=20), nullable=False,
                  comment='成分股TS代码（如 600000.SH）'),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日'),
        sa.Column('weight', sa.Numeric(precision=10, scale=4), nullable=True,
                  comment='权重(%)'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('index_code', 'con_code', 'trade_date',
                            name='uq_index_weight_code_con_date'),
    )
    op.create_index('idx_index_weight_code', 'index_weight', ['index_code'],
                    unique=False)
    op.create_index('idx_index_weight_con_code', 'index_weight', ['con_code'],
                    unique=False)


def downgrade() -> None:
    """Downgrade schema: drop 4 index monitor tables."""
    op.drop_index('idx_index_weight_con_code', table_name='index_weight')
    op.drop_index('idx_index_weight_code', table_name='index_weight')
    op.drop_table('index_weight')
    op.drop_index('idx_index_dailybasic_code_date', table_name='index_dailybasic')
    op.drop_index('idx_index_dailybasic_date', table_name='index_dailybasic')
    op.drop_table('index_dailybasic')
    op.drop_index('idx_index_daily_code_date', table_name='index_daily')
    op.drop_index('idx_index_daily_date', table_name='index_daily')
    op.drop_table('index_daily')
    op.drop_index('idx_index_basic_watched', table_name='index_basic')
    op.drop_table('index_basic')
