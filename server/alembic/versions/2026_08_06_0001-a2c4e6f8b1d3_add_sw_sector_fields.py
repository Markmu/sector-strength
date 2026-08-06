"""add level/parent_code fields to sectors for 申万行业分类

Revision ID: a2c4e6f8b1d3
Revises: e5b7c9d3f6a1
Create Date: 2026-08-06 00:01:00

为 sectors 表新增申万行业分类专用字段：
- ``level``：行业层级（L1/L2/L3），申万专用；同花顺板块为空
- ``parent_code``：父级行业代码（申万层级树），一级为空；同花顺为空

新增组合索引 ``idx_sectors_type_level`` 便于按申万层级查询。
两个字段均 nullable，不影响现有同花顺（industry/concept/region）数据。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2c4e6f8b1d3'
down_revision: Union[str, Sequence[str], None] = 'e5b7c9d3f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: sectors 表新增申万行业分类字段。"""
    op.add_column(
        'sectors',
        sa.Column(
            'level',
            sa.String(length=5),
            nullable=True,
            comment='行业层级（L1/L2/L3，申万专用；同花顺为空）',
        ),
    )
    op.add_column(
        'sectors',
        sa.Column(
            'parent_code',
            sa.String(length=20),
            nullable=True,
            comment='父级行业代码（申万层级树；同花顺为空）',
        ),
    )
    op.create_index(
        'idx_sectors_type_level',
        'sectors',
        ['type', 'level'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema: 移除申万行业分类字段。"""
    op.drop_index('idx_sectors_type_level', table_name='sectors')
    op.drop_column('sectors', 'parent_code')
    op.drop_column('sectors', 'level')
