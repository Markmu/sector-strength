"""allow null trade_date in broker_recommend

Revision ID: 687ec547d98e
Revises: 5213982a184e
Create Date: 2026-06-29 00:01:42.100067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '687ec547d98e'
down_revision: Union[str, Sequence[str], None] = '5213982a184e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """broker_recommend.trade_date 改为可空。

    部分券商金股记录接口返回的 trade_date 缺失（NotNullViolationError），
    trade_date 为推荐日期用于追溯，非核心字段（核心月份标识为 month），允许为空。
    """
    op.alter_column(
        'broker_recommend',
        'trade_date',
        existing_type=sa.Date(),
        nullable=True,
    )


def downgrade() -> None:
    """恢复 trade_date 为 NOT NULL。"""
    op.alter_column(
        'broker_recommend',
        'trade_date',
        existing_type=sa.Date(),
        nullable=False,
    )
