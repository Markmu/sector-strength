"""empty message

Revision ID: f13c3f36c847
Revises: 0584f1f4cc88, 2025_12_08_0000_change_is_active_default
Create Date: 2025-12-13 00:04:50.866389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f13c3f36c847'
down_revision: Union[str, Sequence[str], None] = ('0584f1f4cc88', '2025_12_08_0000_change_is_active_default')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
