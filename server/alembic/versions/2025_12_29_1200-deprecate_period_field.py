"""deprecate period field in strength_scores table

Revision ID: deprecate_period
Revises: d1a36df87bdc
Create Date: 2025-12-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'deprecate_period'
down_revision: Union[str, Sequence[str], None] = 'd1a36df87bdc'
branch_labels: Union[str, None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - deprecate period field, constraint to only allow 'all'."""

    # 删除旧的 period 约束
    op.drop_constraint('chk_strength_scores_period', 'strength_scores', type_='check')

    # 添加新的约束，只允许 'all'
    op.create_check_constraint(
        'chk_strength_scores_period',
        'strength_scores',
        "period = 'all'"
    )

    # 更新列注释
    op.execute("""
        COMMENT ON COLUMN strength_scores.period IS '[DEPRECATED] 分析周期（已废弃，固定为 ''all''）'
    """)

    # 确保 period 字段有默认值 'all'
    op.alter_column('strength_scores', 'period',
                    existing_type=sa.VARCHAR(length=10),
                    server_default='all',
                    existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema - restore period field constraint."""

    # 删除新约束
    op.drop_constraint('chk_strength_scores_period', 'strength_scores', type_='check')

    # 恢复旧约束，允许多个周期值
    op.create_check_constraint(
        'chk_strength_scores_period',
        'strength_scores',
        "period IN ('all', '5d', '10d', '20d', '30d', '60d', '90d', '120d', '240d')"
    )

    # 恢复列注释
    op.execute("""
        COMMENT ON COLUMN strength_scores.period IS '分析周期: all, 5d, 10d, 20d, 30d, 60d, 90d, 120d, 240d'
    """)

    # 移除默认值
    op.alter_column('strength_scores', 'period',
                    existing_type=sa.VARCHAR(length=10),
                    server_default=None,
                    existing_nullable=False)
