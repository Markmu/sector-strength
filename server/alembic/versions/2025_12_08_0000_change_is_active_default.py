"""change default value of is_active to True

Revision ID: 2025_12_08_0000_change_is_active_default
Revises: 0584f1f4cc88
Create Date: 2025-12-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025_12_08_0000_change_is_active_default'
down_revision = '0584f1f4cc88'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 修改users表中is_active列的默认值为True
    # 注意：这不会影响已存在的行，只会影响新插入的行
    op.alter_column(
        'users',
        'is_active',
        existing_type=sa.Boolean(),
        default=True,
        server_default=None  # 清除原有的server_default
    )


def downgrade() -> None:
    # 回滚默认值为False
    op.alter_column(
        'users',
        'is_active',
        existing_type=sa.Boolean(),
        default=False,
        server_default=None
    )
