import enum
import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Time, Numeric, Index, ARRAY
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.utils.id_generator import generate_account_id, generate_trade_id


class JSONEncodedList(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            return json.dumps(value)
        return json.dumps([value])

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return [value] if value else []


class AccountType(enum.Enum):
    """Account type enumeration."""
    DEMO = "DEMO"
    LIVE = "LIVE"
    PROP = "PROP"


class TradeStatus(enum.Enum):
    """Trade status enumeration."""
    WIN = "WIN"
    LOSS = "LOSS"
    BE = "BE"  # Break Even


class TradeSide(enum.Enum):
    """Trade side enumeration."""
    LONG = "LONG"
    SHORT = "SHORT"


class Account(Base, TimestampMixin):
    """Account model representing a trading account."""
    __tablename__ = "accounts"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=lambda: generate_account_id("demo"))
    user_id: Mapped[str] = mapped_column(String(20), ForeignKey("users.id"), nullable=False, index=True)
    broker_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Display name
    account_type: Mapped[str] = mapped_column(String(10), default=AccountType.DEMO.value, nullable=False)
    starting_balance: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    
    # Relationships - keep simple to avoid circular import issues
    user: Mapped["User"] = relationship(back_populates="accounts")
    trades: Mapped[List["Trade"]] = relationship(cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name={self.name}, broker={self.broker_name})>"


class Trade(Base, TimestampMixin):
    """Trade model representing a single trade."""
    __tablename__ = "trades"
    __table_args__ = (
        Index("ix_trades_account_executed_at", "account_id", "executed_at"),
    )
    
    id: Mapped[str] = mapped_column(String(35), primary_key=True, default=lambda: generate_trade_id(""))
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    
    # Trade details
    symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # LONG or SHORT
    ticket: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entry_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    close_price: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    quantity: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    pnl: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)  # Profit/Loss
    commission: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    swap: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Trade metadata
    duration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "1h 30m"
    trade_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    execution_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # WIN, LOSS, BE
    
    # Risk management
    stop_loss: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    take_profit: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    
    # PRE-TRADE LOG FIELDS
    # Market Context
    session: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # London, New York, Asian
    higher_timeframe_bias: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Bullish, Bearish, Ranging
    trend_structure: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # HH/HL, LH/LL, etc.
    key_levels: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Support, resistance, liquidity zones
    pre_trade_screenshot_url: Mapped[Optional[List[str]]] = mapped_column(JSONEncodedList, nullable=True)  # Screenshot before entry
    pre_trade_screenshot_annotation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Setup Details
    entry_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # SMC, breakout, pullback, scalp, reversal
    entry_checklist_items: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    reason_for_entry: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmation_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Risk Management (additional)
    dollar_amount_risked: Mapped[Optional[float]] = mapped_column(Numeric(18, 8), nullable=True)
    percentage_risked: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)  # e.g., 2.5 for 2.5%
    risk_checklist_items: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Mental State
    energy_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-10 scale
    emotions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-10 scale
    forcing_trades: Mapped[Optional[bool]] = mapped_column(nullable=True)
    sleep_quality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # good, fair, poor
    distractions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # POST-TRADE LOG FIELDS
    # Trade Outcome
    actual_rr_achieved: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    pips_gained_lost: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Execution Review
    followed_plan: Mapped[Optional[bool]] = mapped_column(nullable=True)
    entered_too_early: Mapped[Optional[bool]] = mapped_column(nullable=True)
    moved_sl: Mapped[Optional[bool]] = mapped_column(nullable=True)
    closed_early_from_fear: Mapped[Optional[bool]] = mapped_column(nullable=True)
    greed_affected_tp: Mapped[Optional[bool]] = mapped_column(nullable=True)
    
    # Market Behavior
    what_actually_happened: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    setup_worked_as_expected: Mapped[Optional[bool]] = mapped_column(nullable=True)
    abnormal_volatility: Mapped[Optional[bool]] = mapped_column(nullable=True)
    news_event_involved: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Post-Trade Screenshot
    post_trade_screenshot_url: Mapped[Optional[List[str]]] = mapped_column(JSONEncodedList, nullable=True)
    screenshot_annotations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Markings: Entry, Exit, Mistakes, etc.
    
    # Lesson Learned
    trade_commentary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Tags
    setups: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    general_tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    exit_tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    process_tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # When trade was closed
    date: Mapped[datetime] = mapped_column(nullable=False)  # YYYY-MM-DD
    time: Mapped[Optional[datetime.time]] = mapped_column(Time, nullable=True)  # HH:mm
    close_time: Mapped[Optional[datetime.time]] = mapped_column(Time, nullable=True)  # HH:mm when closed
    
    # Relationships
    account: Mapped["Account"] = relationship()
    
    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, symbol={self.symbol}, side={self.side}, pnl={self.pnl})>"

