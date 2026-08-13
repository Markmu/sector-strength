"""add index_basic sort_order

Revision ID: 7e3309ce89da
Revises: f92bfffc49c3
Create Date: 2026-08-13 22:34:00

为 index_basic 增加 sort_order 列，支持关注清单排序：
- GET /index-monitor/watchlist 与 /overview 按 sort_order 升序返回（主页展示顺序）
- PUT /index-monitor/watchlist 按 ts_codes 数组顺序写入 sort_order
- 非关注指数 sort_order 为 NULL

数据回填：对已存在的关注指数（is_watched=true）按当前展示顺序（id 升序）
赋 sort_order 0..N-1，保证迁移前后主页顺序不变。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e3309ce89da'
down_revision: Union[str, Sequence[str], None] = 'f92bfffc49c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: index_basic 增加 sort_order 列并回填现有关注指数顺序。"""
    op.add_column(
        'index_basic',
        sa.Column(
            'sort_order',
            sa.Integer(),
            nullable=True,
            comment='关注清单排序（0 起，越小越靠前）',
        ),
    )
    # 回填：现有关注指数按 id 升序（即当前无 ORDER BY 时的自然展示顺序）
    # 赋 0..N-1，避免迁移后主页顺序跳变。
    op.execute(
        """
        UPDATE index_basic SET sort_order = ranked.rn - 1
        FROM (
            SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn
            FROM index_basic
            WHERE is_watched IS TRUE
        ) ranked
        WHERE index_basic.id = ranked.id
        """
    )


def downgrade() -> None:
    """Downgrade schema: 删除 sort_order 列。"""
    op.drop_column('index_basic', 'sort_order')
