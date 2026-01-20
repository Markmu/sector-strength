"""create sector classification table

Revision ID: 2025_01_20_0001
Revises: deprecate_period
Create Date: 2026-01-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2025_01_20_0001'
down_revision: Union[str, Sequence[str], None] = 'deprecate_period'
branch_labels: Union[str, None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create sector_classification table with constraints and indexes."""

    # Create sequence for id
    op.execute("CREATE SEQUENCE sector_classification_id_seq")

    op.create_table(
        'sector_classification',
        sa.Column('id', sa.Integer(), server_default=sa.text("nextval('sector_classification_id_seq')"), nullable=False),
        sa.Column('sector_id', sa.Integer(), sa.ForeignKey('sectors.id'), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False, comment='板块编码'),
        sa.Column('classification_date', sa.Date(), nullable=False),
        sa.Column('classification_level', sa.Integer(), nullable=False, comment='分类级别: 1-9'),
        sa.Column('state', sa.String(10), nullable=False, comment='状态: 反弹/调整'),
        sa.Column('current_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('change_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('ma_5', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ma_10', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ma_20', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ma_30', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ma_60', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ma_90', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ma_120', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ma_240', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('price_5_days_ago', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('sector_id', 'classification_date', name='uq_sector_classification_sector_date'),
        sa.CheckConstraint('classification_level BETWEEN 1 AND 9', name='ck_classification_level_range'),
        sa.CheckConstraint("state IN ('反弹', '调整')", name='ck_state_values')
    )
    op.create_index('idx_sector_classification_date', 'sector_classification', ['classification_date'])
    op.create_index('idx_sector_classification_sector', 'sector_classification', ['sector_id'])


def downgrade() -> None:
    """Downgrade schema - drop sector_classification table."""

    # 按相反顺序删除：索引 -> 表 -> 序列
    op.drop_index('idx_sector_classification_sector', table_name='sector_classification')
    op.drop_index('idx_sector_classification_date', table_name='sector_classification')
    op.drop_table('sector_classification')
    op.execute("DROP SEQUENCE IF EXISTS sector_classification_id_seq")
