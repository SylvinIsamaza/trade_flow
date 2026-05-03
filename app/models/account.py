import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Time, Numeric, Index, ARRAY
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.utils.id_generator import generate_account_id, generate_trade_id


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

