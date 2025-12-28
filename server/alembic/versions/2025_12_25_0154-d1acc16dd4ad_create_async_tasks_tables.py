"""create_async_tasks_tables

Revision ID: d1acc16dd4ad
Revises: 9935c085b34a
Create Date: 2025-12-25 01:54:22.216162

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd1acc16dd4ad'
down_revision: Union[str, Sequence[str], None] = '9935c085b34a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create async_tasks table
    op.create_table(
        'async_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.String(length=50), nullable=False, comment='任务唯一标识'),
        sa.Column('task_type', sa.String(length=50), nullable=False, comment='任务类型'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending', comment='任务状态: pending, running, completed, failed, cancelled'),
        sa.Column('progress', sa.Integer(), nullable=True, server_default='0', comment='当前进度'),
        sa.Column('total', sa.Integer(), nullable=True, server_default='0', comment='总数量'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0', comment='重试次数'),
        sa.Column('max_retries', sa.Integer(), nullable=True, server_default='3', comment='最大重试次数'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True, server_default='14400', comment='超时时间（秒）'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True, comment='创建者用户ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='创建时间'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='开始时间'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='完成时间'),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True, comment='取消时间'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_async_tasks_status', 'async_tasks', ['status'])
    op.create_index('idx_async_tasks_created_at', 'async_tasks', [sa.text('created_at DESC')])
    op.create_index('idx_async_tasks_task_id', 'async_tasks', ['task_id'], unique=True)

    # Create async_task_params table
    op.create_table(
        'async_task_params',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.String(length=50), nullable=False, comment='任务ID'),
        sa.Column('key', sa.String(length=100), nullable=False, comment='参数键'),
        sa.Column('value', sa.Text(), nullable=True, comment='参数值'),
        sa.ForeignKeyConstraint(['task_id'], ['async_tasks.task_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'key', name='uq_async_task_params_task_key')
    )
    op.create_index('idx_async_task_params_task_id', 'async_task_params', ['task_id'])

    # Create async_task_logs table
    op.create_table(
        'async_task_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.String(length=50), nullable=False, comment='任务ID'),
        sa.Column('level', sa.String(length=20), nullable=False, comment='日志级别: INFO, WARNING, ERROR'),
        sa.Column('message', sa.Text(), nullable=False, comment='日志消息'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='创建时间'),
        sa.ForeignKeyConstraint(['task_id'], ['async_tasks.task_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_async_task_logs_task_id', 'async_task_logs', ['task_id', sa.text('created_at')])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_async_task_logs_task_id', table_name='async_task_logs')
    op.drop_table('async_task_logs')

    op.drop_index('idx_async_task_params_task_id', table_name='async_task_params')
    op.drop_table('async_task_params')

    op.drop_index('idx_async_tasks_task_id', table_name='async_tasks')
    op.drop_index('idx_async_tasks_created_at', table_name='async_tasks')
    op.drop_index('idx_async_tasks_status', table_name='async_tasks')
    op.drop_table('async_tasks')
