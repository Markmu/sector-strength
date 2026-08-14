"""add updated_at serverdefault market daily metrics

Revision ID: e5c1f3a90b2d
Revises: c4b9e2a7f813
Create Date: 2026-08-14 00:02:00.000000

plan-03 后补丁（S1）：为 ``market_daily_metrics.updated_at`` 补 ``server_default=now()``。

背景：plan-01 迁移 c4b9e2a7f813 建 ``market_daily_metrics`` 时，``updated_at`` 列仅有
``onupdate``（覆盖写时刷新）但无 ``server_default``，导致首行插入时 ``updated_at`` 为
NULL。``MarketMetricsService`` 的 ``on_conflict_do_update`` 在覆盖路径已显式写
``func.now()``，但首行插入仍依赖列默认值。

本迁移对该列补 ``server_default=now()``，使首行插入即有 ``updated_at``。c4b9e2a7f813
已在本地库 upgrade 过，故以独立小迁移 ``alter_column`` 方式落地（不直接改原迁移文件）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5c1f3a90b2d'
down_revision: Union[str, Sequence[str], None] = 'c4b9e2a7f813'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: 给 market_daily_metrics.updated_at 补 server_default=now()。"""
    op.alter_column(
        'market_daily_metrics',
        'updated_at',
        existing_type=sa.DateTime(timezone=True),
        server_default=sa.text('now()'),
        existing_comment='更新时间',
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema: 移除 market_daily_metrics.updated_at 的 server_default。"""
    op.alter_column(
        'market_daily_metrics',
        'updated_at',
        existing_type=sa.DateTime(timezone=True),
        server_default=None,
        existing_comment='更新时间',
        existing_nullable=True,
    )
