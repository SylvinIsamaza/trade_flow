"""Add starting_balance to accounts

Revision ID: 5c8e2d3a4f9b
Revises: 3f6b9d7d2c1a
Create Date: 2026-04-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5c8e2d3a4f9b"
down_revision: Union[str, Sequence[str], None] = "3f6b9d7d2c1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("starting_balance", sa.Numeric(precision=18, scale=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "starting_balance")
