"""add stock independent tables

Revision ID: dd92f496dfaf
Revises: 687ec547d98e
Create Date: 2026-07-07 01:19:29.994821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd92f496dfaf'
down_revision: Union[str, Sequence[str], None] = '687ec547d98e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. stock_daily_market_data
    op.create_table('stock_daily_market_data',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False, comment='指向 stocks.id，不加外键约束'),
        sa.Column('symbol', sa.String(length=20), nullable=False, comment='股票代码'),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('high', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('low', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('close', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('volume', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('turnover', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('change', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('change_percent', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stock_id', 'date', name='uq_stock_daily_market_data_stock_date'),
        sa.CheckConstraint('high >= low', name='check_stock_dmd_high_low'),
        sa.CheckConstraint('volume >= 0', name='check_stock_dmd_volume_positive'),
    )
    op.create_index('ix_stock_daily_market_data_stock_id', 'stock_daily_market_data', ['stock_id'], unique=False)
    op.create_index('ix_stock_daily_market_data_symbol', 'stock_daily_market_data', ['symbol'], unique=False)
    op.create_index('ix_stock_daily_market_data_date', 'stock_daily_market_data', ['date'], unique=False)
    op.create_index('idx_stock_dmd_stock_date', 'stock_daily_market_data', ['stock_id', 'date'], unique=False)
    op.create_index('idx_stock_dmd_date_range', 'stock_daily_market_data', ['date', 'close', 'volume'], unique=False)
    op.create_index('idx_stock_dmd_symbol_date', 'stock_daily_market_data', ['symbol', 'date'], unique=False)

    # 2. stock_moving_average_data
    op.create_table('stock_moving_average_data',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False, comment='指向 stocks.id，不加外键约束'),
        sa.Column('symbol', sa.String(length=20), nullable=False, comment='股票代码'),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('period', sa.String(length=10), nullable=False, comment='5d, 10d 等真实业务字段'),
        sa.Column('ma_value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('price_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('trend', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stock_id', 'symbol', 'date', 'period',
                            name='uq_stock_moving_average_data_stock_date_period'),
    )
    op.create_index('ix_stock_moving_average_data_stock_id', 'stock_moving_average_data', ['stock_id'], unique=False)
    op.create_index('ix_stock_moving_average_data_symbol', 'stock_moving_average_data', ['symbol'], unique=False)
    op.create_index('ix_stock_moving_average_data_date', 'stock_moving_average_data', ['date'], unique=False)
    op.create_index('ix_stock_moving_average_data_period', 'stock_moving_average_data', ['period'], unique=False)
    op.create_index('idx_stock_mad_stock_date', 'stock_moving_average_data', ['stock_id', 'date'], unique=False)
    op.create_index('idx_stock_mad_symbol_date', 'stock_moving_average_data', ['symbol', 'date'], unique=False)
    op.create_index('idx_stock_mad_date_period', 'stock_moving_average_data', ['date', 'period'], unique=False)
    op.create_index('idx_stock_mad_stock_period', 'stock_moving_average_data', ['stock_id', 'period'], unique=False)
    op.create_index('idx_stock_mad_symbol_period', 'stock_moving_average_data', ['symbol', 'period'], unique=False)
    op.create_index('idx_stock_mad_date_desc', 'stock_moving_average_data', ['date'], unique=False)

    # 3. stock_strength_scores（必须含 percentile 列，ADR-3）
    op.create_table('stock_strength_scores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('stock_id', sa.Integer(), nullable=False, comment='指向 stocks.id，原 entity_id 改名'),
        sa.Column('symbol', sa.String(length=20), nullable=False, comment='股票代码'),
        sa.Column('date', sa.Date(), nullable=False, comment='计算日期'),
        sa.Column('score', sa.Numeric(precision=10, scale=4), nullable=False, comment='综合强度得分(0-100)'),
        sa.Column('rank', sa.Integer(), nullable=True, comment='排名'),
        sa.Column('change_rate', sa.Numeric(precision=10, scale=4), nullable=True, comment='得分变化率(%)'),
        sa.Column('strength_level', sa.String(length=20), nullable=True,
                  comment='强度等级: weak, medium, strong, very_strong'),
        sa.Column('price_position_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='价格位置得分(0-100)'),
        sa.Column('ma_alignment_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='均线排列得分(0-100)'),
        sa.Column('ma_alignment_state', sa.String(length=20), nullable=True, comment='均线排列状态'),
        sa.Column('short_term_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='短期强度得分'),
        sa.Column('medium_term_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='中期强度得分'),
        sa.Column('long_term_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='长期强度得分'),
        sa.Column('current_price', sa.Numeric(precision=10, scale=2), nullable=True, comment='当前价格'),
        sa.Column('ma5', sa.Numeric(precision=10, scale=2), nullable=True, comment='5日均线'),
        sa.Column('ma10', sa.Numeric(precision=10, scale=2), nullable=True, comment='10日均线'),
        sa.Column('ma20', sa.Numeric(precision=10, scale=2), nullable=True, comment='20日均线'),
        sa.Column('ma30', sa.Numeric(precision=10, scale=2), nullable=True, comment='30日均线'),
        sa.Column('ma60', sa.Numeric(precision=10, scale=2), nullable=True, comment='60日均线'),
        sa.Column('ma90', sa.Numeric(precision=10, scale=2), nullable=True, comment='90日均线'),
        sa.Column('ma120', sa.Numeric(precision=10, scale=2), nullable=True, comment='120日均线'),
        sa.Column('ma240', sa.Numeric(precision=10, scale=2), nullable=True, comment='240日均线'),
        sa.Column('price_above_ma5', sa.Integer(), nullable=True, comment='价格是否高于5日均线'),
        sa.Column('price_above_ma10', sa.Integer(), nullable=True, comment='价格是否高于10日均线'),
        sa.Column('price_above_ma20', sa.Integer(), nullable=True, comment='价格是否高于20日均线'),
        sa.Column('price_above_ma30', sa.Integer(), nullable=True, comment='价格是否高于30日均线'),
        sa.Column('price_above_ma60', sa.Integer(), nullable=True, comment='价格是否高于60日均线'),
        sa.Column('price_above_ma90', sa.Integer(), nullable=True, comment='价格是否高于90日均线'),
        sa.Column('price_above_ma120', sa.Integer(), nullable=True, comment='价格是否高于120日均线'),
        sa.Column('price_above_ma240', sa.Integer(), nullable=True, comment='价格是否高于240日均线'),
        sa.Column('change_rate_1d', sa.Numeric(precision=5, scale=2), nullable=True, comment='1日得分变化率(%)'),
        sa.Column('strength_grade', sa.String(length=3), nullable=True,
                  comment='强度等级: S+, S, A+, A, B+, B, C+, C, D+, D'),
        sa.Column('ma5_score', sa.Numeric(precision=10, scale=4), nullable=True, comment='5日均线得分'),
        sa.Column('ma10_score', sa.Numeric(precision=10, scale=4), nullable=True, comment='10日均线得分'),
        sa.Column('ma20_score', sa.Numeric(precision=10, scale=4), nullable=True, comment='20日均线得分'),
        sa.Column('volume_score', sa.Numeric(precision=10, scale=4), nullable=True, comment='成交量得分'),
        sa.Column('momentum_score', sa.Numeric(precision=10, scale=4), nullable=True, comment='动量得分'),
        sa.Column('percentile', sa.Numeric(precision=10, scale=4), nullable=True, comment='百分位'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True,
                  comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stock_id', 'date', name='uq_stock_strength_scores_stock_date'),
        sa.CheckConstraint('score >= 0 AND score <= 100', name='chk_stock_strength_score_range'),
        sa.CheckConstraint('price_above_ma5 IN (0, 1)', name='chk_stock_strength_price_above_ma5'),
        sa.CheckConstraint('price_above_ma10 IN (0, 1)', name='chk_stock_strength_price_above_ma10'),
        sa.CheckConstraint('price_above_ma20 IN (0, 1)', name='chk_stock_strength_price_above_ma20'),
        sa.CheckConstraint('price_above_ma30 IN (0, 1)', name='chk_stock_strength_price_above_ma30'),
        sa.CheckConstraint('price_above_ma60 IN (0, 1)', name='chk_stock_strength_price_above_ma60'),
        sa.CheckConstraint('price_above_ma90 IN (0, 1)', name='chk_stock_strength_price_above_ma90'),
        sa.CheckConstraint('price_above_ma120 IN (0, 1)', name='chk_stock_strength_price_above_ma120'),
        sa.CheckConstraint('price_above_ma240 IN (0, 1)', name='chk_stock_strength_price_above_ma240'),
    )
    op.create_index('ix_stock_strength_scores_stock_id', 'stock_strength_scores', ['stock_id'], unique=False)
    op.create_index('ix_stock_strength_scores_symbol', 'stock_strength_scores', ['symbol'], unique=False)
    op.create_index('ix_stock_strength_scores_date', 'stock_strength_scores', ['date'], unique=False)
    op.create_index('idx_stock_strength_symbol_date', 'stock_strength_scores',
                    ['symbol', sa.text('date DESC')], unique=False)
    op.create_index('idx_stock_strength_score_desc', 'stock_strength_scores',
                    [sa.text('score DESC'), sa.text('date DESC')], unique=False)
    op.create_index('idx_stock_strength_date', 'stock_strength_scores', ['date'], unique=False)
    op.create_index('idx_stock_strength_rank', 'stock_strength_scores', ['rank'], unique=False)
    op.create_index('idx_stock_strength_score', 'stock_strength_scores', ['score'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 逆序：3. stock_strength_scores
    op.drop_index('idx_stock_strength_score', table_name='stock_strength_scores')
    op.drop_index('idx_stock_strength_rank', table_name='stock_strength_scores')
    op.drop_index('idx_stock_strength_date', table_name='stock_strength_scores')
    op.drop_index('idx_stock_strength_score_desc', table_name='stock_strength_scores')
    op.drop_index('idx_stock_strength_symbol_date', table_name='stock_strength_scores')
    op.drop_index('ix_stock_strength_scores_date', table_name='stock_strength_scores')
    op.drop_index('ix_stock_strength_scores_symbol', table_name='stock_strength_scores')
    op.drop_index('ix_stock_strength_scores_stock_id', table_name='stock_strength_scores')
    op.drop_table('stock_strength_scores')

    # 2. stock_moving_average_data
    op.drop_index('idx_stock_mad_date_desc', table_name='stock_moving_average_data')
    op.drop_index('idx_stock_mad_symbol_period', table_name='stock_moving_average_data')
    op.drop_index('idx_stock_mad_stock_period', table_name='stock_moving_average_data')
    op.drop_index('idx_stock_mad_date_period', table_name='stock_moving_average_data')
    op.drop_index('idx_stock_mad_symbol_date', table_name='stock_moving_average_data')
    op.drop_index('idx_stock_mad_stock_date', table_name='stock_moving_average_data')
    op.drop_index('ix_stock_moving_average_data_period', table_name='stock_moving_average_data')
    op.drop_index('ix_stock_moving_average_data_date', table_name='stock_moving_average_data')
    op.drop_index('ix_stock_moving_average_data_symbol', table_name='stock_moving_average_data')
    op.drop_index('ix_stock_moving_average_data_stock_id', table_name='stock_moving_average_data')
    op.drop_table('stock_moving_average_data')

    # 1. stock_daily_market_data
    op.drop_index('idx_stock_dmd_symbol_date', table_name='stock_daily_market_data')
    op.drop_index('idx_stock_dmd_date_range', table_name='stock_daily_market_data')
    op.drop_index('idx_stock_dmd_stock_date', table_name='stock_daily_market_data')
    op.drop_index('ix_stock_daily_market_data_date', table_name='stock_daily_market_data')
    op.drop_index('ix_stock_daily_market_data_symbol', table_name='stock_daily_market_data')
    op.drop_index('ix_stock_daily_market_data_stock_id', table_name='stock_daily_market_data')
    op.drop_table('stock_daily_market_data')
