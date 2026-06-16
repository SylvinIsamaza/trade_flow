"""Add ticket to trades

Revision ID: 8b7c9d1a2f4e
Revises: caf17a19d7ed
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b7c9d1a2f4e'
down_revision: Union[str, Sequence[str], None] = 'caf17a19d7ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('trades', sa.Column('ticket', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('trades', 'ticket')
