"""add_stock_basic_fields

Revision ID: 02c292189ee0
Revises: 2025_01_20_0001
Create Date: 2026-06-01 00:51:59.630146

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '02c292189ee0'
down_revision: Union[str, Sequence[str], None] = '2025_01_20_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('stocks', sa.Column('ts_code', sa.String(length=20), nullable=True))
    op.add_column('stocks', sa.Column('area', sa.String(length=50), nullable=True))
    op.add_column('stocks', sa.Column('industry', sa.String(length=50), nullable=True))
    op.add_column('stocks', sa.Column('fullname', sa.String(length=200), nullable=True))
    op.add_column('stocks', sa.Column('enname', sa.String(length=200), nullable=True))
    op.add_column('stocks', sa.Column('cnspell', sa.String(length=50), nullable=True))
    op.add_column('stocks', sa.Column('market', sa.String(length=20), nullable=True))
    op.add_column('stocks', sa.Column('exchange', sa.String(length=20), nullable=True))
    op.add_column('stocks', sa.Column('curr_type', sa.String(length=10), nullable=True))
    op.add_column('stocks', sa.Column('list_status', sa.String(length=5), nullable=True))
    op.add_column('stocks', sa.Column('list_date', sa.Date(), nullable=True))
    op.add_column('stocks', sa.Column('delist_date', sa.Date(), nullable=True))
    op.add_column('stocks', sa.Column('is_hs', sa.String(length=5), nullable=True))
    op.add_column('stocks', sa.Column('act_name', sa.String(length=200), nullable=True))
    op.add_column('stocks', sa.Column('act_ent_type', sa.String(length=100), nullable=True))
    op.create_index('idx_stocks_exchange', 'stocks', ['exchange'], unique=False)
    op.create_index(op.f('ix_stocks_ts_code'), 'stocks', ['ts_code'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_stocks_ts_code'), table_name='stocks')
    op.drop_index('idx_stocks_exchange', table_name='stocks')
    op.drop_column('stocks', 'act_ent_type')
    op.drop_column('stocks', 'act_name')
    op.drop_column('stocks', 'is_hs')
    op.drop_column('stocks', 'delist_date')
    op.drop_column('stocks', 'list_date')
    op.drop_column('stocks', 'list_status')
    op.drop_column('stocks', 'curr_type')
    op.drop_column('stocks', 'exchange')
    op.drop_column('stocks', 'market')
    op.drop_column('stocks', 'cnspell')
    op.drop_column('stocks', 'enname')
    op.drop_column('stocks', 'fullname')
    op.drop_column('stocks', 'industry')
    op.drop_column('stocks', 'area')
    op.drop_column('stocks', 'ts_code')
