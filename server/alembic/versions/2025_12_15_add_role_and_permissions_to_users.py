"""add role and permissions to users

Revision ID: xxxxxxxx
Revises: cd4f1102bc07
Create Date: 2025-12-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2025_12_15_add_role_and_permissions'
down_revision: Union[str, Sequence[str], None] = 'cd4f1102bc07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加角色和权限字段到users表"""
    # 添加角色字段
    op.add_column(
        'users',
        sa.Column('role', sa.String(20), server_default='user', nullable=False, comment="用户角色: admin, user")
    )
    # 添加权限JSONB字段
    op.add_column(
        'users',
        sa.Column('permissions', postgresql.JSONB(), server_default='[]', nullable=False, comment="用户权限列表")
    )
    # 添加索引优化查询
    op.create_index('idx_users_role', 'users', ['role'])


def downgrade() -> None:
    """移除角色和权限字段"""
    # 移除索引
    op.drop_index('idx_users_role')
    # 移除权限字段
    op.drop_column('users', 'permissions')
    # 移除角色字段
    op.drop_column('users', 'role')
