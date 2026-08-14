"""add market margin daily table

Revision ID: 63164af1c44c
Revises: a7d2e9f4c1b8
Create Date: 2026-08-15 00:02:00.000000

为融资融券数据同步与首页曲线图（第 17 期 plan-01）新建 1 张业务表：
- ``market_margin_daily``：融资融券全市场日汇总事实表，trade_date 唯一，存六指标
  （rzye/rqye/rzmre/rzche/rqmcl/rzrqye，全部 Numeric(20,2)，元/股口径，与 tushare
  ``margin`` 字段同名；rzrqye 服务层重算 = rzye+rqye 之和），承接 spec D3 单表日期级
  原子 upsert 的存储基础。

交易日历表 ``trading_calendar_days`` 已由 16 期迁移 c4b9e2a7f813 交付，本期直接
复用、不重建。按 plan-01 §3 实现规格 #3 的单表迁移范式（照抄
2026_08_14_0001-c4b9e2a7f813_add_market_metrics_and_calendar.py），create_table +
create_index 对称 create/drop，不夹带无关 schema drift。

与 c4b9e2a7f813 的一处主动差异：``updated_at`` 直接带 ``server_default=now()``
（16 期 S1 教训——原迁移漏 server_default 导致首行插入 updated_at 为 NULL，后由
补丁迁移 e5c1f3a90b2d 补齐；本期建表时一步到位）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63164af1c44c'
down_revision: Union[str, Sequence[str], None] = 'a7d2e9f4c1b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create market_margin_daily."""
    # market_margin_daily：融资融券全市场日汇总事实表，trade_date 唯一
    # 六指标与 tushare margin 字段同名，元/股口径；rqyl（融券余量）不入库
    op.create_table(
        'market_margin_daily',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='交易日'),
        sa.Column('rzye', sa.Numeric(precision=20, scale=2), nullable=True,
                  comment='融资余额（元）'),
        sa.Column('rqye', sa.Numeric(precision=20, scale=2), nullable=True,
                  comment='融券余额（元）'),
        sa.Column('rzmre', sa.Numeric(precision=20, scale=2), nullable=True,
                  comment='融资买入额（元）'),
        sa.Column('rzche', sa.Numeric(precision=20, scale=2), nullable=True,
                  comment='融资偿还额（元）'),
        sa.Column('rqmcl', sa.Numeric(precision=20, scale=2), nullable=True,
                  comment='融券卖出量（股）'),
        sa.Column('rzrqye', sa.Numeric(precision=20, scale=2), nullable=True,
                  comment='两融合计余额（元；服务层重算 = rzye+rqye 之和）'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_date', name='uq_market_margin_daily_trade_date'),
    )
    op.create_index('idx_market_margin_daily_trade_date', 'market_margin_daily',
                    ['trade_date'], unique=False)


def downgrade() -> None:
    """Downgrade schema: drop market_margin_daily."""
    op.drop_index('idx_market_margin_daily_trade_date',
                  table_name='market_margin_daily')
    op.drop_table('market_margin_daily')
