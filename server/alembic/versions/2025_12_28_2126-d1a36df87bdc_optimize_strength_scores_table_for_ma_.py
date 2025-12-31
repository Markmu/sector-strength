"""optimize strength_scores table for ma system

Revision ID: d1a36df87bdc
Revises: f86d52e1be1a
Create Date: 2025-12-28 21:26:28.343058

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1a36df87bdc'
down_revision: Union[str, Sequence[str], None] = 'f86d52e1be1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - optimize strength_scores table for MA system."""

    # 阶段1: 添加 symbol 字段（允许 NULL，用于数据迁移）
    op.add_column('strength_scores', sa.Column('symbol', sa.String(length=20), nullable=True, comment='股票代码或板块代码'))

    # 阶段2: 数据迁移 - 从 stocks 和 sectors 表填充 symbol
    op.execute("""
        -- 填充个股的 symbol
        UPDATE strength_scores ss
        SET symbol = s.symbol
        FROM stocks s
        WHERE ss.entity_type = 'stock' AND ss.entity_id = s.id AND ss.symbol IS NULL;

        -- 填充板块的 symbol（使用 code）
        UPDATE strength_scores ss
        SET symbol = s.code
        FROM sectors s
        WHERE ss.entity_type = 'sector' AND ss.entity_id = s.id AND ss.symbol IS NULL;
    """)

    # 阶段3: 设置 symbol 为 NOT NULL（数据填充完成后）
    op.alter_column('strength_scores', 'symbol',
                    existing_type=sa.String(length=20),
                    nullable=False)

    # 添加核心得分字段
    op.add_column('strength_scores', sa.Column('price_position_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='价格位置得分(0-100)'))
    op.add_column('strength_scores', sa.Column('ma_alignment_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='均线排列得分(0-100)'))
    op.add_column('strength_scores', sa.Column('ma_alignment_state', sa.String(length=20), nullable=True, comment='均线排列状态'))

    # 添加短中长期强度字段
    op.add_column('strength_scores', sa.Column('short_term_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='短期强度得分'))
    op.add_column('strength_scores', sa.Column('medium_term_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='中期强度得分'))
    op.add_column('strength_scores', sa.Column('long_term_score', sa.Numeric(precision=10, scale=2), nullable=True, comment='长期强度得分'))

    # 添加均线数据字段
    op.add_column('strength_scores', sa.Column('current_price', sa.Numeric(precision=10, scale=2), nullable=True, comment='当前价格'))
    op.add_column('strength_scores', sa.Column('ma5', sa.Numeric(precision=10, scale=2), nullable=True, comment='5日均线'))
    op.add_column('strength_scores', sa.Column('ma10', sa.Numeric(precision=10, scale=2), nullable=True, comment='10日均线'))
    op.add_column('strength_scores', sa.Column('ma20', sa.Numeric(precision=10, scale=2), nullable=True, comment='20日均线'))
    op.add_column('strength_scores', sa.Column('ma30', sa.Numeric(precision=10, scale=2), nullable=True, comment='30日均线'))
    op.add_column('strength_scores', sa.Column('ma60', sa.Numeric(precision=10, scale=2), nullable=True, comment='60日均线'))
    op.add_column('strength_scores', sa.Column('ma90', sa.Numeric(precision=10, scale=2), nullable=True, comment='90日均线'))
    op.add_column('strength_scores', sa.Column('ma120', sa.Numeric(precision=10, scale=2), nullable=True, comment='120日均线'))
    op.add_column('strength_scores', sa.Column('ma240', sa.Numeric(precision=10, scale=2), nullable=True, comment='240日均线'))

    # 添加价格相对均线位置字段
    op.add_column('strength_scores', sa.Column('price_above_ma5', sa.Integer(), nullable=True, comment='价格是否高于5日均线'))
    op.add_column('strength_scores', sa.Column('price_above_ma10', sa.Integer(), nullable=True, comment='价格是否高于10日均线'))
    op.add_column('strength_scores', sa.Column('price_above_ma20', sa.Integer(), nullable=True, comment='价格是否高于20日均线'))
    op.add_column('strength_scores', sa.Column('price_above_ma30', sa.Integer(), nullable=True, comment='价格是否高于30日均线'))
    op.add_column('strength_scores', sa.Column('price_above_ma60', sa.Integer(), nullable=True, comment='价格是否高于60日均线'))
    op.add_column('strength_scores', sa.Column('price_above_ma90', sa.Integer(), nullable=True, comment='价格是否高于90日均线'))
    op.add_column('strength_scores', sa.Column('price_above_ma120', sa.Integer(), nullable=True, comment='价格是否高于120日均线'))
    op.add_column('strength_scores', sa.Column('price_above_ma240', sa.Integer(), nullable=True, comment='价格是否高于240日均线'))

    # 添加排名和变化字段
    op.add_column('strength_scores', sa.Column('change_rate_1d', sa.Numeric(precision=5, scale=2), nullable=True, comment='1日得分变化率(%)'))
    op.add_column('strength_scores', sa.Column('strength_grade', sa.String(length=3), nullable=True, comment='强度等级: S+, S, A+, A, B+, B, C+, C, D+, D'))

    # 更新 period 字段注释
    op.alter_column('strength_scores', 'period',
               existing_type=sa.VARCHAR(length=10),
               comment='分析周期: all, 5d, 10d, 20d, 30d, 60d, 90d, 120d, 240d',
               existing_comment='分析周期: 5d, 10d, 20d, 30d, 60d',
               existing_nullable=False)

    # 创建优化索引
    op.create_index('idx_strength_scores_symbol_date', 'strength_scores', ['symbol', sa.text('date DESC'), 'period'], unique=False)
    op.create_index('idx_strength_scores_score_desc', 'strength_scores', [sa.text('score DESC'), sa.text('date DESC')], unique=False)
    op.create_index(op.f('ix_strength_scores_symbol'), 'strength_scores', ['symbol'], unique=False)

    # 添加 CHECK 约束
    op.create_check_constraint(
        'chk_strength_scores_score_range',
        'strength_scores',
        'score >= 0 AND score <= 100'
    )
    op.create_check_constraint(
        'chk_strength_scores_period',
        'strength_scores',
        "period IN ('all', '5d', '10d', '20d', '30d', '60d', '90d', '120d', '240d')"
    )
    op.create_check_constraint(
        'chk_strength_scores_entity_type',
        'strength_scores',
        "entity_type IN ('stock', 'sector')"
    )

    # 添加 price_above_maX 约束 (只能是 0 或 1)
    op.create_check_constraint(
        'chk_strength_scores_price_above_ma5',
        'strength_scores',
        'price_above_ma5 IN (0, 1)'
    )
    op.create_check_constraint(
        'chk_strength_scores_price_above_ma10',
        'strength_scores',
        'price_above_ma10 IN (0, 1)'
    )
    op.create_check_constraint(
        'chk_strength_scores_price_above_ma20',
        'strength_scores',
        'price_above_ma20 IN (0, 1)'
    )
    op.create_check_constraint(
        'chk_strength_scores_price_above_ma30',
        'strength_scores',
        'price_above_ma30 IN (0, 1)'
    )
    op.create_check_constraint(
        'chk_strength_scores_price_above_ma60',
        'strength_scores',
        'price_above_ma60 IN (0, 1)'
    )
    op.create_check_constraint(
        'chk_strength_scores_price_above_ma90',
        'strength_scores',
        'price_above_ma90 IN (0, 1)'
    )
    op.create_check_constraint(
        'chk_strength_scores_price_above_ma120',
        'strength_scores',
        'price_above_ma120 IN (0, 1)'
    )
    op.create_check_constraint(
        'chk_strength_scores_price_above_ma240',
        'strength_scores',
        'price_above_ma240 IN (0, 1)'
    )


def downgrade() -> None:
    """Downgrade schema - revert strength_scores table optimization."""

    # 删除 CHECK 约束（包括新添加的 price_above_maX 约束）
    op.drop_constraint('chk_strength_scores_price_above_ma240', 'strength_scores', type_='check')
    op.drop_constraint('chk_strength_scores_price_above_ma120', 'strength_scores', type_='check')
    op.drop_constraint('chk_strength_scores_price_above_ma90', 'strength_scores', type_='check')
    op.drop_constraint('chk_strength_scores_price_above_ma60', 'strength_scores', type_='check')
    op.drop_constraint('chk_strength_scores_price_above_ma30', 'strength_scores', type_='check')
    op.drop_constraint('chk_strength_scores_price_above_ma20', 'strength_scores', type_='check')
    op.drop_constraint('chk_strength_scores_price_above_ma10', 'strength_scores', type_='check')
    op.drop_constraint('chk_strength_scores_price_above_ma5', 'strength_scores', type_='check')
    op.drop_constraint('chk_strength_scores_entity_type', 'strength_scores', type_='check')
    op.drop_constraint('chk_strength_scores_period', 'strength_scores', type_='check')
    op.drop_constraint('chk_strength_scores_score_range', 'strength_scores', type_='check')

    # 删除索引
    op.drop_index(op.f('ix_strength_scores_symbol'), table_name='strength_scores')
    op.drop_index('idx_strength_scores_symbol_date', table_name='strength_scores')
    op.drop_index('idx_strength_scores_score_desc', table_name='strength_scores')

    # 恢复 period 字段注释
    op.alter_column('strength_scores', 'period',
               existing_type=sa.VARCHAR(length=10),
               comment='分析周期: 5d, 10d, 20d, 30d, 60d',
               existing_comment='分析周期: all, 5d, 10d, 20d, 30d, 60d, 90d, 120d, 240d',
               existing_nullable=False)

    # 删除新增字段
    op.drop_column('strength_scores', 'strength_grade')
    op.drop_column('strength_scores', 'change_rate_1d')
    op.drop_column('strength_scores', 'price_above_ma240')
    op.drop_column('strength_scores', 'price_above_ma120')
    op.drop_column('strength_scores', 'price_above_ma90')
    op.drop_column('strength_scores', 'price_above_ma60')
    op.drop_column('strength_scores', 'price_above_ma30')
    op.drop_column('strength_scores', 'price_above_ma20')
    op.drop_column('strength_scores', 'price_above_ma10')
    op.drop_column('strength_scores', 'price_above_ma5')
    op.drop_column('strength_scores', 'ma240')
    op.drop_column('strength_scores', 'ma120')
    op.drop_column('strength_scores', 'ma90')
    op.drop_column('strength_scores', 'ma60')
    op.drop_column('strength_scores', 'ma30')
    op.drop_column('strength_scores', 'ma20')
    op.drop_column('strength_scores', 'ma10')
    op.drop_column('strength_scores', 'ma5')
    op.drop_column('strength_scores', 'current_price')
    op.drop_column('strength_scores', 'long_term_score')
    op.drop_column('strength_scores', 'medium_term_score')
    op.drop_column('strength_scores', 'short_term_score')
    op.drop_column('strength_scores', 'ma_alignment_state')
    op.drop_column('strength_scores', 'ma_alignment_score')
    op.drop_column('strength_scores', 'price_position_score')

    # 删除 symbol 列前先设为 nullable（PostgreSQL 要求）
    op.alter_column('strength_scores', 'symbol',
                    existing_type=sa.String(length=20),
                    nullable=True)
    op.drop_column('strength_scores', 'symbol')
