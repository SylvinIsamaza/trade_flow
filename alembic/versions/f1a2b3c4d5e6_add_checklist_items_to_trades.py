"""add checklist items to trades

Revision ID: f1a2b3c4d5e6
Revises: de6f5efcf373, a1b2c3d4e5f6
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = ('de6f5efcf373', 'a1b2c3d4e5f6')
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('trades', sa.Column('entry_checklist_items', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('trades', sa.Column('risk_checklist_items', postgresql.ARRAY(sa.String()), nullable=True))


def downgrade() -> None:
    op.drop_column('trades', 'risk_checklist_items')
    op.drop_column('trades', 'entry_checklist_items')
