"""create broker_recommend table

Revision ID: 5213982a184e
Revises: f5e4d3c2b1a0
Create Date: 2026-06-28 03:11:35.131706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5213982a184e'
down_revision: Union[str, Sequence[str], None] = 'f5e4d3c2b1a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建券商月度金股表。

    注意：仅创建 broker_recommend 表与索引；autogenerate 检测到的既有 DB 与模型
    历史不同步噪音（sector_classification 表删除、fund_portfolio 索引、funds 注释）
    已手动剔除，避免误删既有数据。
    """
    op.create_table('broker_recommend',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('month', sa.Date(), nullable=False, comment='月份标识（该月第一天，MAX 比较键）'),
        sa.Column('trade_date', sa.Date(), nullable=False, comment='推荐日期（接口返回，同月可能有多个）'),
        sa.Column('ts_code', sa.String(length=20), nullable=False, comment='Tushare代码'),
        sa.Column('symbol', sa.String(length=10), nullable=False, comment='股票代码(纯数字)'),
        sa.Column('broker', sa.String(length=100), nullable=False, comment='券商名称'),
        sa.Column('name', sa.String(length=100), nullable=True, comment='股票名称(取自接口，仅快照用；查询时以 stocks JOIN 为准)'),
        sa.Column('reason', sa.Text(), nullable=True, comment='推荐理由'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_broker_symbol_month', 'broker_recommend', ['symbol', 'month'], unique=False)
    op.create_index('ix_broker_broker_month', 'broker_recommend', ['broker', 'month'], unique=False)
    op.create_index('ix_broker_month', 'broker_recommend', ['month'], unique=False)


def downgrade() -> None:
    """删除券商月度金股表。"""
    op.drop_index('ix_broker_month', table_name='broker_recommend')
    op.drop_index('ix_broker_broker_month', table_name='broker_recommend')
    op.drop_index('ix_broker_symbol_month', table_name='broker_recommend')
    op.drop_table('broker_recommend')
