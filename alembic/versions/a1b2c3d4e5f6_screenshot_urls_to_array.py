"""Convert screenshot url columns to text for JSON array storage and add annotation field

Revision ID: a1b2c3d4e5f6
Revises: 7a4d2c5e1b3f
Create Date: 2026-05-27 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7a4d2c5e1b3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert String(1000) -> Text so JSON arrays of URLs fit without truncation
    op.alter_column('trades', 'pre_trade_screenshot_url',
                    type_=sa.Text(),
                    existing_nullable=True)
    op.alter_column('trades', 'post_trade_screenshot_url',
                    type_=sa.Text(),
                    existing_nullable=True)

    # Add the annotation column that was missing
    op.add_column('trades', sa.Column('pre_trade_screenshot_annotation', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('trades', 'pre_trade_screenshot_annotation')
    op.alter_column('trades', 'post_trade_screenshot_url',
                    type_=sa.String(1000),
                    existing_nullable=True)
    op.alter_column('trades', 'pre_trade_screenshot_url',
                    type_=sa.String(1000),
                    existing_nullable=True)
