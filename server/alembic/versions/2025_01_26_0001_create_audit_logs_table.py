"""create audit logs table

Revision ID: 2025_01_26_0001
Revises: 2025_01_20_0001
Create Date: 2026-01-26

用于记录所有管理员操作，满足 NFR-SEC-006、NFR-SEC-007、NFR-SEC-008 要求。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2025_01_26_0001'
down_revision: Union[str, Sequence[str], None] = '2025_01_20_0001'
branch_labels: Union[str, None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create audit_logs table with constraints and indexes."""

    # Create sequence for id
    op.execute("CREATE SEQUENCE audit_logs_id_seq")

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), server_default=sa.text("nextval('audit_logs_id_seq')"), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='操作用户 ID'),
        sa.Column('username', sa.String(100), nullable=False, comment='操作用户名（冗余存储）'),
        sa.Column('action', sa.String(100), nullable=False, comment='操作类型：test_classification, init_data, update_data 等'),
        sa.Column('resource_type', sa.String(50), comment='资源类型：sector, stock, user 等'),
        sa.Column('resource_id', sa.String(100), comment='资源 ID'),
        sa.Column('details', postgresql.JSONB(), comment='操作详情（扩展字段）'),
        sa.Column('ip_address', sa.String(45), comment='操作来源 IP 地址（支持 IPv6）'),
        sa.Column('user_agent', sa.Text(), comment='用户代理字符串'),
        sa.Column('status', sa.String(20), server_default='success', nullable=False, comment='操作状态：success, failed, partial'),
        sa.Column('result', sa.Text(), comment='操作结果描述'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False, comment='操作时间'),
        sa.CheckConstraint("status IN ('success', 'failed', 'partial')", name='ck_audit_status_values')
    )

    # 创建索引优化查询性能
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_logs_status', 'audit_logs', ['status'])

    # 复合索引
    op.create_index('ix_audit_logs_user_action', 'audit_logs', ['user_id', 'action'])
    op.create_index('ix_audit_logs_action_created', 'audit_logs', ['action', 'created_at'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_status_created', 'audit_logs', ['status', 'created_at'])


def downgrade() -> None:
    """Downgrade schema - drop audit_logs table."""

    # 按相反顺序删除：复合索引 -> 普通索引 -> 表 -> 序列
    op.drop_index('ix_audit_logs_status_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_action', table_name='audit_logs')
    op.drop_index('idx_audit_logs_status', table_name='audit_logs')
    op.drop_index('idx_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('idx_audit_logs_action', table_name='audit_logs')
    op.drop_index('idx_audit_logs_user_id', table_name='audit_logs')

    op.drop_table('audit_logs')
    op.execute("DROP SEQUENCE IF EXISTS audit_logs_id_seq")
