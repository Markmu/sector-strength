"""add market metrics and calendar tables

Revision ID: c4b9e2a7f813
Revises: 7e3309ce89da
Create Date: 2026-08-14 00:01:00.000000

为 A股全市场量价指标（第 16 期 plan-01）新建 2 张业务支持表：
- ``market_daily_metrics``：全市场量价日汇总事实表，trade_date 唯一，存成交量（股）、
  成交额（元）、简单平均价（元，4 位）与参与集合各阶段计数（架构 ADR-4 单表日期级原子 upsert）
- ``trading_calendar_days``：本地交易日历表，cal_date 唯一，含开市/休市标记与刷新批次
  （refresh_batch_id/refreshed_at），承接同步拆分、非交易日守卫与首页缺口轴（架构 ADR-6）

按 plan-01 §3 实现规格 #3 的单表迁移范式（参照
2026_08_10_0001-f92bfffc49c3_add_index_monitor_tables.py），逐表 create_table + create_index，
不夹带无关 schema drift。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4b9e2a7f813'
down_revision: Union[str, Sequence[str], None] = '7e3309ce89da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create market_daily_metrics + trading_calendar_days."""
    # 1. market_daily_metrics：全市场量价日汇总事实表，trade_date 唯一
    #    存储层统一股/元口径；平均价存 4 位、展示 2 位
    op.create_table(
        'market_daily_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日'),
        sa.Column('volume_shares', sa.Numeric(precision=24, scale=2), nullable=True,
                  comment='成交量（股）'),
        sa.Column('amount_yuan', sa.Numeric(precision=24, scale=2), nullable=True,
                  comment='成交额（元）'),
        sa.Column('average_price', sa.Numeric(precision=16, scale=4), nullable=True,
                  comment='简单平均价（元，存4位）'),
        sa.Column('expected_stock_count', sa.Integer(), nullable=True,
                  comment='预期参与股票数（L/D/P 联合集合）'),
        sa.Column('daily_quote_count', sa.Integer(), nullable=True,
                  comment='当日实际取到行情的股票数'),
        sa.Column('suspended_stock_count', sa.Integer(), nullable=True,
                  comment='当日全天停牌股票数（suspend_d 整日停牌）'),
        sa.Column('final_stock_count', sa.Integer(), nullable=True,
                  comment='最终参与汇总的股票数（含停牌补值）'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                  comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', name='uq_market_daily_metrics_trade_date'),
    )
    op.create_index('idx_market_daily_metrics_trade_date', 'market_daily_metrics',
                    ['trade_date'], unique=False)

    # 2. trading_calendar_days：本地交易日历表，cal_date 唯一，含开/休市标记
    #    refresh_batch_id/refreshed_at 标识同一次 refresh_range 的全部行
    op.create_table(
        'trading_calendar_days',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('cal_date', sa.Date(), nullable=False, comment='自然日（含开市/休市）'),
        sa.Column('is_open', sa.Boolean(), nullable=False,
                  comment='是否开市（True 开市 / False 休市）'),
        sa.Column('refresh_batch_id', sa.String(length=36), nullable=True,
                  comment='刷新批次ID（UUID，同批次同值）'),
        sa.Column('refreshed_at', sa.DateTime(timezone=True), nullable=True,
                  comment='刷新时间（同批次同值）'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cal_date', name='uq_trading_calendar_days_cal_date'),
    )
    op.create_index(
        'idx_trading_calendar_days_cal_date_is_open',
        'trading_calendar_days',
        ['cal_date', 'is_open'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema: drop trading_calendar_days + market_daily_metrics."""
    op.drop_index(
        'idx_trading_calendar_days_cal_date_is_open',
        table_name='trading_calendar_days',
    )
    op.drop_table('trading_calendar_days')
    op.drop_index('idx_market_daily_metrics_trade_date', table_name='market_daily_metrics')
    op.drop_table('market_daily_metrics')
