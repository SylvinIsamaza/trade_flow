"""merge heads

Revision ID: de6f5efcf373
Revises: 4b2eb45e2f22, 5c8e2d3a4f9b
Create Date: 2026-05-12 05:37:13.112808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de6f5efcf373'
down_revision: Union[str, Sequence[str], None] = ('4b2eb45e2f22', '5c8e2d3a4f9b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
