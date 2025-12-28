"""add_symbol_to_moving_average_data

Revision ID: 5d8e7a5b3c9f
Revises: ce7f8553132d
Create Date: 2025-12-26 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d8e7a5b3c9f'
down_revision: Union[str, Sequence[str], None] = 'ce7f8553132d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ========================================
    # 步骤1: 添加 symbol 列（先允许为 NULL）
    # ========================================
    op.add_column('moving_average_data',
                  sa.Column('symbol', sa.String(length=20), nullable=True))

    # ========================================
    # 步骤2: 迁移现有数据
    # ========================================
    # 更新股票数据的 symbol
    op.execute("""
        UPDATE moving_average_data mad
        SET symbol = s.symbol
        FROM stocks s
        WHERE mad.entity_type = 'stock' AND mad.entity_id = s.id
    """)

    # 更新板块数据的 symbol
    op.execute("""
        UPDATE moving_average_data mad
        SET symbol = s.code
        FROM sectors s
        WHERE mad.entity_type = 'sector' AND mad.entity_id = s.id
    """)

    # ========================================
    # 步骤3: 将 symbol 列设为 NOT NULL
    # ========================================
    op.alter_column('moving_average_data', 'symbol', nullable=False)

    # ========================================
    # 步骤4: 删除旧的唯一约束
    # ========================================
    op.drop_constraint('uq_moving_average_data_entity_date_period', 'moving_average_data', type_='unique')

    # ========================================
    # 步骤5: 创建新的唯一约束（包含 symbol）
    # ========================================
    op.create_unique_constraint(
        'uq_moving_average_data_entity_date_period',
        'moving_average_data',
        ['entity_type', 'entity_id', 'symbol', 'date', 'period']
    )

    # ========================================
    # 步骤6: 创建新索引
    # ========================================
    op.create_index('idx_moving_average_data_symbol_date', 'moving_average_data', ['symbol', 'date'])
    op.create_index('idx_moving_average_data_symbol_period', 'moving_average_data', ['symbol', 'period'])


def downgrade() -> None:
    """Downgrade schema."""

    # ========================================
    # 回滚: 删除新索引
    # ========================================
    op.drop_index('idx_moving_average_data_symbol_period', table_name='moving_average_data')
    op.drop_index('idx_moving_average_data_symbol_date', table_name='moving_average_data')

    # ========================================
    # 回滚: 删除新的唯一约束
    # ========================================
    op.drop_constraint('uq_moving_average_data_entity_date_period', 'moving_average_data', type_='unique')

    # ========================================
    # 回滚: 创建旧的唯一约束
    # ========================================
    op.create_unique_constraint(
        'uq_moving_average_data_entity_date_period',
        'moving_average_data',
        ['entity_type', 'entity_id', 'date', 'period']
    )

    # ========================================
    # 回滚: 删除 symbol 列
    # ========================================
    op.drop_column('moving_average_data', 'symbol')
