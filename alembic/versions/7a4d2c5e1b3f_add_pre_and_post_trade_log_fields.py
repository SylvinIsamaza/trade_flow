"""Add pre and post trade log fields

Revision ID: 7a4d2c5e1b3f
Revises: caf17a19d7ed
Create Date: 2026-05-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7a4d2c5e1b3f'
down_revision: Union[str, Sequence[str], None] = 'de6f5efcf373'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add pre and post trade log fields."""
    # PRE-TRADE LOG FIELDS
    # Market Context
    op.add_column('trades', sa.Column('session', sa.String(50), nullable=True))
    op.add_column('trades', sa.Column('higher_timeframe_bias', sa.String(50), nullable=True))
    op.add_column('trades', sa.Column('trend_structure', sa.String(100), nullable=True))
    op.add_column('trades', sa.Column('key_levels', sa.Text(), nullable=True))
    op.add_column('trades', sa.Column('pre_trade_screenshot_url', sa.String(1000), nullable=True))
    
    # Setup Details
    op.add_column('trades', sa.Column('entry_model', sa.String(100), nullable=True))
    op.add_column('trades', sa.Column('reason_for_entry', sa.Text(), nullable=True))
    op.add_column('trades', sa.Column('confirmation_used', sa.Text(), nullable=True))
    
    # Risk Management (additional)
    op.add_column('trades', sa.Column('dollar_amount_risked', sa.Numeric(18, 8), nullable=True))
    op.add_column('trades', sa.Column('percentage_risked', sa.Numeric(6, 2), nullable=True))
    
    # Mental State
    op.add_column('trades', sa.Column('energy_level', sa.Integer(), nullable=True))
    op.add_column('trades', sa.Column('emotions', sa.Text(), nullable=True))
    op.add_column('trades', sa.Column('confidence_level', sa.Integer(), nullable=True))
    op.add_column('trades', sa.Column('forcing_trades', sa.Boolean(), nullable=True))
    op.add_column('trades', sa.Column('sleep_quality', sa.String(50), nullable=True))
    op.add_column('trades', sa.Column('distractions', sa.Text(), nullable=True))
    
    # POST-TRADE LOG FIELDS
    # Trade Outcome
    op.add_column('trades', sa.Column('actual_rr_achieved', sa.Numeric(8, 2), nullable=True))
    op.add_column('trades', sa.Column('pips_gained_lost', sa.Numeric(10, 2), nullable=True))
    
    # Execution Review
    op.add_column('trades', sa.Column('followed_plan', sa.Boolean(), nullable=True))
    op.add_column('trades', sa.Column('entered_too_early', sa.Boolean(), nullable=True))
    op.add_column('trades', sa.Column('moved_sl', sa.Boolean(), nullable=True))
    op.add_column('trades', sa.Column('closed_early_from_fear', sa.Boolean(), nullable=True))
    op.add_column('trades', sa.Column('greed_affected_tp', sa.Boolean(), nullable=True))
    
    # Market Behavior
    op.add_column('trades', sa.Column('what_actually_happened', sa.Text(), nullable=True))
    op.add_column('trades', sa.Column('setup_worked_as_expected', sa.Boolean(), nullable=True))
    op.add_column('trades', sa.Column('abnormal_volatility', sa.Boolean(), nullable=True))
    op.add_column('trades', sa.Column('news_event_involved', sa.Text(), nullable=True))
    
    # Post-Trade Screenshot
    op.add_column('trades', sa.Column('post_trade_screenshot_url', sa.String(1000), nullable=True))
    op.add_column('trades', sa.Column('screenshot_annotations', sa.Text(), nullable=True))
    
    # Lesson Learned
    op.add_column('trades', sa.Column('trade_commentary', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema to remove pre and post trade log fields."""
    # PRE-TRADE LOG FIELDS
    op.drop_column('trades', 'session')
    op.drop_column('trades', 'higher_timeframe_bias')
    op.drop_column('trades', 'trend_structure')
    op.drop_column('trades', 'key_levels')
    op.drop_column('trades', 'pre_trade_screenshot_url')
    op.drop_column('trades', 'entry_model')
    op.drop_column('trades', 'reason_for_entry')
    op.drop_column('trades', 'confirmation_used')
    op.drop_column('trades', 'dollar_amount_risked')
    op.drop_column('trades', 'percentage_risked')
    op.drop_column('trades', 'energy_level')
    op.drop_column('trades', 'emotions')
    op.drop_column('trades', 'confidence_level')
    op.drop_column('trades', 'forcing_trades')
    op.drop_column('trades', 'sleep_quality')
    op.drop_column('trades', 'distractions')
    
    # POST-TRADE LOG FIELDS
    op.drop_column('trades', 'actual_rr_achieved')
    op.drop_column('trades', 'pips_gained_lost')
    op.drop_column('trades', 'followed_plan')
    op.drop_column('trades', 'entered_too_early')
    op.drop_column('trades', 'moved_sl')
    op.drop_column('trades', 'closed_early_from_fear')
    op.drop_column('trades', 'greed_affected_tp')
    op.drop_column('trades', 'what_actually_happened')
    op.drop_column('trades', 'setup_worked_as_expected')
    op.drop_column('trades', 'abnormal_volatility')
    op.drop_column('trades', 'news_event_involved')
    op.drop_column('trades', 'post_trade_screenshot_url')
    op.drop_column('trades', 'screenshot_annotations')
    op.drop_column('trades', 'trade_commentary')
