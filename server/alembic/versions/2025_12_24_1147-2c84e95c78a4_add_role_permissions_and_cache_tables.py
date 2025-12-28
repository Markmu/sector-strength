"""add_role_permissions_and_cache_tables

Revision ID: 2c84e95c78a4
Revises: 6360d3392535
Create Date: 2025-12-24 11:47:42.751130

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c84e95c78a4'
down_revision: Union[str, Sequence[str], None] = '6360d3392535'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create cache_entries table
    op.create_table('cache_entries',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='缓存条目唯一标识符'),
    sa.Column('key', sa.String(length=255), nullable=False, comment='缓存键'),
    sa.Column('value', sa.LargeBinary(), nullable=False, comment='缓存值'),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='过期时间'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cache_entries_id', 'cache_entries', ['id'], unique=False)
    op.create_index('ix_cache_entries_key', 'cache_entries', ['key'], unique=True)
    op.create_index('ix_cache_entries_expires_at', 'cache_entries', ['expires_at'], unique=False)
    op.create_index('ix_cache_key_expires', 'cache_entries', ['key', 'expires_at'], unique=False)

    # Create data_update_logs table
    op.create_table('data_update_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='更新日志唯一标识符'),
    sa.Column('start_time', sa.DateTime(timezone=True), nullable=False, comment='开始时间'),
    sa.Column('end_time', sa.DateTime(timezone=True), nullable=True, comment='结束时间'),
    sa.Column('status', sa.String(length=20), nullable=False, comment='状态: success, error, running'),
    sa.Column('sectors_updated', sa.Integer(), nullable=True, comment='更新的板块数量'),
    sa.Column('stocks_updated', sa.Integer(), nullable=True, comment='更新的股票数量'),
    sa.Column('market_data_updated', sa.Integer(), nullable=True, comment='更新的行情数据数量'),
    sa.Column('calculations_performed', sa.Integer(), nullable=True, comment='执行的计算数量'),
    sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_update_logs_id', 'data_update_logs', ['id'], unique=False)
    op.create_index('ix_data_update_logs_start_time', 'data_update_logs', ['start_time'], unique=False)
    op.create_index('ix_data_update_logs_status', 'data_update_logs', ['status'], unique=False)
    op.create_index('ix_update_logs_start_time', 'data_update_logs', ['start_time'], unique=False)
    op.create_index('ix_update_logs_status_start', 'data_update_logs', ['status', 'start_time'], unique=False)

    # Add role and permissions columns to users table
    # Add column as nullable first
    op.add_column('users', sa.Column('role', sa.String(length=20), nullable=True, comment='用户角色: admin, user'))
    # Set default value for existing rows
    op.execute("UPDATE users SET role = 'user'")
    # Now make it NOT NULL with server_default
    op.alter_column('users', 'role', nullable=False, server_default='user')
    
    # Add permissions column
    op.add_column('users', sa.Column('permissions', sa.JSON(), nullable=True, comment='用户权限列表'))
    op.create_index('ix_users_role', 'users', ['role'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove role and permissions from users
    op.drop_index('ix_users_role', table_name='users')
    op.drop_column('users', 'permissions')
    op.drop_column('users', 'role')

    # Drop data_update_logs table
    op.drop_index('ix_update_logs_status_start', table_name='data_update_logs')
    op.drop_index('ix_update_logs_start_time', table_name='data_update_logs')
    op.drop_index('ix_data_update_logs_status', table_name='data_update_logs')
    op.drop_index('ix_data_update_logs_start_time', table_name='data_update_logs')
    op.drop_index('ix_data_update_logs_id', table_name='data_update_logs')
    op.drop_table('data_update_logs')

    # Drop cache_entries table
    op.drop_index('ix_cache_key_expires', table_name='cache_entries')
    op.drop_index('ix_cache_entries_expires_at', table_name='cache_entries')
    op.drop_index('ix_cache_entries_key', table_name='cache_entries')
    op.drop_index('ix_cache_entries_id', table_name='cache_entries')
    op.drop_table('cache_entries')
