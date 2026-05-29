from pydantic import BaseModel, ConfigDict, field_serializer, field_validator, model_validator
from typing import Optional, List, Union
from datetime import datetime, time


class TradeBase(BaseModel):
    """Base trade schema."""
    model_config = ConfigDict(from_attributes=True)
    
    symbol: str
    side: str
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    close_price: Optional[float] = None
    quantity: Optional[float] = None
    pnl: Optional[float] = None
    commission: float = 0
    swap: float = 0
    duration: Optional[str] = None
    trade_type: Optional[str] = None
    execution_type: Optional[str] = None
    status: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # PRE-TRADE LOG FIELDS
    # Market Context
    session: Optional[str] = None  # London, New York, Asian
    higher_timeframe_bias: Optional[str] = None  # Bullish, Bearish, Ranging
    trend_structure: Optional[str] = None  # HH/HL, LH/LL
    key_levels: Optional[str] = None  # Support, resistance, liquidity zones
    pre_trade_screenshot_url: Optional[str] = None
    
    # Setup Details
    entry_model: Optional[str] = None  # SMC, breakout, pullback, scalp, reversal
    reason_for_entry: Optional[str] = None
    confirmation_used: Optional[str] = None
    
    # Risk Management
    dollar_amount_risked: Optional[float] = None
    percentage_risked: Optional[float] = None
    
    # Mental State
    energy_level: Optional[int] = None  # 1-10 scale
    emotions: Optional[str] = None
    confidence_level: Optional[int] = None  # 1-10 scale
    forcing_trades: Optional[bool] = None
    sleep_quality: Optional[str] = None  # good, fair, poor
    distractions: Optional[str] = None
    
    # POST-TRADE LOG FIELDS
    # Trade Outcome
    actual_rr_achieved: Optional[float] = None
    pips_gained_lost: Optional[float] = None
    
    # Execution Review
    followed_plan: Optional[bool] = None
    entered_too_early: Optional[bool] = None
    moved_sl: Optional[bool] = None
    closed_early_from_fear: Optional[bool] = None
    greed_affected_tp: Optional[bool] = None
    
    # Market Behavior
    what_actually_happened: Optional[str] = None
    setup_worked_as_expected: Optional[bool] = None
    abnormal_volatility: Optional[bool] = None
    news_event_involved: Optional[str] = None
    
    # Post-Trade Screenshot
    post_trade_screenshot_url: Optional[str] = None
    screenshot_annotations: Optional[str] = None

    pre_trade_screenshot_url: Optional[str] = None
    pre_trade_screenshot_annotations: Optional[str] = None
    
    # Lesson Learned
    trade_commentary: Optional[str] = None
    
    setups: Optional[List[str]] = None
    general_tags: Optional[List[str]] = None
    exit_tags: Optional[List[str]] = None
    process_tags: Optional[List[str]] = None
    notes: Optional[str] = None
    executed_at: datetime
    closed_at: Optional[datetime] = None
    date: datetime
    time: Optional[str] = None  # Store as string HH:mm
    close_time: Optional[str] = None  # Store as string HH:mm
    
    @field_validator('time', 'close_time', mode='before')
    @classmethod
    def convert_time_to_string(cls, value: Optional[Union[str, time]]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, time):
            return value.strftime('%H:%M')
        return str(value)


class TradeCreate(TradeBase):
    """Schema for creating a new trade."""
    account_id: str


class TradeUpdate(BaseModel):
    """Schema for updating trade information."""
    model_config = ConfigDict(from_attributes=True)
    
    symbol: Optional[str] = None
    side: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    close_price: Optional[float] = None
    quantity: Optional[float] = None
    pnl: Optional[float] = None
    commission: Optional[float] = None
    swap: Optional[float] = None
    duration: Optional[str] = None
    trade_type: Optional[str] = None
    execution_type: Optional[str] = None
    status: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # PRE-TRADE LOG FIELDS
    # Market Context
    session: Optional[str] = None
    higher_timeframe_bias: Optional[str] = None
    trend_structure: Optional[str] = None
    key_levels: Optional[str] = None
    pre_trade_screenshot_url: Optional[str] = None
    
    # Setup Details
    entry_model: Optional[str] = None
    reason_for_entry: Optional[str] = None
    confirmation_used: Optional[str] = None
    
    # Risk Management
    dollar_amount_risked: Optional[float] = None
    percentage_risked: Optional[float] = None
    
    # Mental State
    energy_level: Optional[int] = None
    emotions: Optional[str] = None
    confidence_level: Optional[int] = None
    forcing_trades: Optional[bool] = None
    sleep_quality: Optional[str] = None
    distractions: Optional[str] = None
    
    # POST-TRADE LOG FIELDS
    # Trade Outcome
    actual_rr_achieved: Optional[float] = None
    pips_gained_lost: Optional[float] = None
    
    # Execution Review
    followed_plan: Optional[bool] = None
    entered_too_early: Optional[bool] = None
    moved_sl: Optional[bool] = None
    closed_early_from_fear: Optional[bool] = None
    greed_affected_tp: Optional[bool] = None
    
    # Market Behavior
    what_actually_happened: Optional[str] = None
    setup_worked_as_expected: Optional[bool] = None
    abnormal_volatility: Optional[bool] = None
    news_event_involved: Optional[str] = None
    
    # Post-Trade Screenshot
    post_trade_screenshot_url: Optional[str] = None
    screenshot_annotations: Optional[str] = None
    
    # Lesson Learned
    trade_commentary: Optional[str] = None
    
    setups: Optional[List[str]] = None
    general_tags: Optional[List[str]] = None
    exit_tags: Optional[List[str]] = None
    process_tags: Optional[List[str]] = None
    notes: Optional[str] = None
    executed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    date: Optional[Union[str, datetime]] = None
    time: Optional[str] = None
    close_time: Optional[str] = None
    
    @field_validator('date', 'executed_at', 'closed_at', mode='before')
    @classmethod
    def parse_datetime_fields(cls, value: Optional[Union[str, datetime]]) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Try to parse as ISO format date/datetime
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                pass
            # Try parsing as date only (YYYY-MM-DD)
            try:
                return datetime.strptime(value, '%Y-%m-%d').replace(tzinfo=None)
            except (ValueError, TypeError):
                pass
        return None
    
    @field_validator('time', 'close_time', mode='before')
    @classmethod
    def convert_time_to_string(cls, value: Optional[Union[str, time]]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, time):
            return value.strftime('%H:%M')
        return str(value) if value else None


class TradeResponse(TradeBase):
    """Schema for trade response."""
    id: str
    account_id: str