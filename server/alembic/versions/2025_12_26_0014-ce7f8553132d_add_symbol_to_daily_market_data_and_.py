"""add_symbol_to_daily_market_data_and_change_sector_stocks_to_use_codes

Revision ID: ce7f8553132d
Revises: d1acc16dd4ad
Create Date: 2025-12-26 00:14:01.041016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ce7f8553132d'
down_revision: Union[str, Sequence[str], None] = 'd1acc16dd4ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ========================================
    # 步骤1: 修改 daily_market_data 表
    # ========================================
    # 添加 symbol 列（先允许为 NULL）
    op.add_column('daily_market_data', 
                  sa.Column('symbol', sa.String(length=20), nullable=True))
    
    # 迁移现有数据 - 更新股票数据
    op.execute("""
        UPDATE daily_market_data dmd
        SET symbol = s.symbol
        FROM stocks s
        WHERE dmd.entity_type = 'stock' AND dmd.entity_id = s.id
    """)
    
    # 更新板块数据
    op.execute("""
        UPDATE daily_market_data dmd
        SET symbol = s.code
        FROM sectors s
        WHERE dmd.entity_type = 'sector' AND dmd.entity_id = s.id
    """)
    
    # 将 symbol 列设为 NOT NULL
    op.alter_column('daily_market_data', 'symbol', nullable=False)
    
    # 创建索引
    op.create_index('idx_daily_market_data_symbol_date', 'daily_market_data', ['symbol', 'date'])
    
    # ========================================
    # 步骤2: 修改 sector_stocks 表
    # ========================================
    # 添加新列（先允许为 NULL）
    op.add_column('sector_stocks', 
                  sa.Column('sector_code', sa.String(length=20), nullable=True))
    op.add_column('sector_stocks', 
                  sa.Column('stock_code', sa.String(length=20), nullable=True))
    
    # 迁移数据
    op.execute("""
        UPDATE sector_stocks ss
        SET sector_code = s.code,
            stock_code = st.symbol
        FROM sectors s, stocks st
        WHERE ss.sector_id = s.id AND ss.stock_id = st.id
    """)
    
    # 将新列设为 NOT NULL
    op.alter_column('sector_stocks', 'sector_code', nullable=False)
    op.alter_column('sector_stocks', 'stock_code', nullable=False)
    
    # 删除所有旧索引
    op.drop_index('idx_sector_stocks_sector', table_name='sector_stocks')
    op.drop_index('idx_sector_stocks_stock', table_name='sector_stocks')
    op.drop_index('ix_sector_stocks_sector_id', table_name='sector_stocks')
    op.drop_index('ix_sector_stocks_stock_id', table_name='sector_stocks')
    
    # 删除外键约束
    op.drop_constraint('sector_stocks_sector_id_fkey', 'sector_stocks', type_='foreignkey')
    op.drop_constraint('sector_stocks_stock_id_fkey', 'sector_stocks', type_='foreignkey')
    
    # 删除唯一约束
    op.drop_constraint('uq_sector_stock', 'sector_stocks', type_='unique')
    
    # 删除旧列
    op.drop_column('sector_stocks', 'sector_id')
    op.drop_column('sector_stocks', 'stock_id')
    
    # 创建新索引
    op.create_index('idx_sector_stocks_sector', 'sector_stocks', ['sector_code', 'stock_code'])
    op.create_index('idx_sector_stocks_stock', 'sector_stocks', ['stock_code', 'sector_code'])
    
    # 创建新唯一约束
    op.create_unique_constraint('uq_sector_stock', 'sector_stocks', ['sector_code', 'stock_code'])


def downgrade() -> None:
    """Downgrade schema."""
    # ========================================
    # 回滚 sector_stocks 表的更改
    # ========================================
    # 删除新索引
    op.drop_index('idx_sector_stocks_stock', table_name='sector_stocks')
    op.drop_index('idx_sector_stocks_sector', table_name='sector_stocks')
    
    # 删除新唯一约束
    op.drop_constraint('uq_sector_stock', 'sector_stocks', type_='unique')
    
    # 添加旧列
    op.add_column('sector_stocks', 
                  sa.Column('sector_id', sa.Integer(), nullable=True))
    op.add_column('sector_stocks', 
                  sa.Column('stock_id', sa.Integer(), nullable=True))
    
    # 迁移数据回去
    op.execute("""
        UPDATE sector_stocks ss
        SET sector_id = s.id,
            stock_id = st.id
        FROM sectors s, stocks st
        WHERE ss.sector_code = s.code AND ss.stock_code = st.symbol
    """)
    
    # 将旧列设为 NOT NULL
    op.alter_column('sector_stocks', 'sector_id', nullable=False)
    op.alter_column('sector_stocks', 'stock_id', nullable=False)
    
    # 删除新列
    op.drop_column('sector_stocks', 'stock_code')
    op.drop_column('sector_stocks', 'sector_code')
    
    # 创建旧索引
    op.create_index('ix_sector_stocks_stock_id', 'sector_stocks', ['stock_id'])
    op.create_index('ix_sector_stocks_sector_id', 'sector_stocks', ['sector_id'])
    op.create_index('idx_sector_stocks_stock', 'sector_stocks', ['stock_id', 'sector_id'])
    op.create_index('idx_sector_stocks_sector', 'sector_stocks', ['sector_id', 'stock_id'])
    
    # 创建旧唯一约束
    op.create_unique_constraint('uq_sector_stock', 'sector_stocks', ['sector_id', 'stock_id'])
    
    # 创建外键约束
    op.create_foreign_key('sector_stocks_sector_id_fkey', 'sector_stocks', 'sectors', ['sector_id'], ['id'])
    op.create_foreign_key('sector_stocks_stock_id_fkey', 'sector_stocks', 'stocks', ['stock_id'], ['id'])
    
    # ========================================
    # 回滚 daily_market_data 表的更改
    # ========================================
    # 删除索引
    op.drop_index('idx_daily_market_data_symbol_date', table_name='daily_market_data')
    
    # 删除 symbol 列
    op.drop_column('daily_market_data', 'symbol')
