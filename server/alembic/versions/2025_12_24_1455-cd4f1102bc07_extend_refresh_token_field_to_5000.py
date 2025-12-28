"""extend_refresh_token_field_to_5000

Revision ID: cd4f1102bc07
Revises: 2c84e95c78a4
Create Date: 2025-12-24 14:55:34.874718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd4f1102bc07'
down_revision: Union[str, Sequence[str], None] = '2c84e95c78a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Extend refresh_tokens.token field from VARCHAR(255) to VARCHAR(5000)
    op.alter_column('refresh_tokens', 'token',
                   existing_type=sa.VARCHAR(length=255),
                   type_=sa.VARCHAR(length=5000),
                   existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert refresh_tokens.token field back to VARCHAR(255)
    op.alter_column('refresh_tokens', 'token',
                   existing_type=sa.VARCHAR(length=5000),
                   type_=sa.VARCHAR(length=255),
                   existing_nullable=False)
