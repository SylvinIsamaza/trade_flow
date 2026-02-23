"""
Summary tables for precomputed analytics.
These tables store aggregated trade statistics for fast dashboard queries.
"""
from datetime import date
from typing import Optional, List
from sqlalchemy import String, Integer, Numeric, Date, DateTime, ForeignKey, ARRAY, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class AccountDailyStats(Base):
    """Daily aggregated statistics for an account."""
    __tablename__ = "account_daily_stats"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Core metrics
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    missed_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    profit_factor: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Win/Loss metrics
    average_win: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    average_loss: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    average_rr: Mapped[float] = mapped_column(Numeric(18, 8), default=0)  # Risk Reward
    best_win: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    worst_loss: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Duration
    average_trade_duration: Mapped[str] = mapped_column(String(20), default="0")
    
    # Streaks
    avg_win_streak: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_win_streak: Mapped[int] = mapped_column(Integer, default=0)
    avg_loss_streak: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_loss_streak: Mapped[int] = mapped_column(Integer, default=0)
    
    # Risk metrics
    recovery_factor: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    max_drawdown: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Volume & fees
    total_volume: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_commission: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Zella Scores (0-100)
    zella_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    win_rate_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    profit_factor_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    avg_win_loss_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    recovery_factor_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_drawdown_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    
    # Relations
    trade_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=lambda: [])
    total_comments: Mapped[int] = mapped_column(Integer, default=0)
    
    __table_args__ = (
        Index("ix_daily_stats_account_date", "account_id", "date", unique=True),
    )


class AccountMonthlyStats(Base):
    """Monthly aggregated statistics for an account."""
    __tablename__ = "account_monthly_stats"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)  # First day of month
    
    # Core metrics
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    missed_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    profit_factor: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Win/Loss metrics
    average_win: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    average_loss: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    average_rr: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    best_win: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    worst_loss: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Duration
    average_trade_duration: Mapped[str] = mapped_column(String(20), default="0")
    
    # Streaks
    avg_win_streak: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_win_streak: Mapped[int] = mapped_column(Integer, default=0)
    avg_loss_streak: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_loss_streak: Mapped[int] = mapped_column(Integer, default=0)
    
    # Risk metrics
    recovery_factor: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    max_drawdown: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Volume & fees
    total_volume: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_commission: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Zella Scores
    zella_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    win_rate_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    profit_factor_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    avg_win_loss_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    recovery_factor_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_drawdown_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    
    # Relations
    trade_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=lambda: [])
    total_comments: Mapped[int] = mapped_column(Integer, default=0)
    
    __table_args__ = (
        Index("ix_monthly_stats_account_month", "account_id", "month", unique=True),
    )


class AccountAllTimeStats(Base):
    """All-time aggregated statistics for an account."""
    __tablename__ = "account_all_time_stats"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, unique=True)
    
    # Core metrics
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    missed_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    profit_factor: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Win/Loss metrics
    average_win: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    average_loss: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    average_rr: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    best_win: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    worst_loss: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Duration
    average_trade_duration: Mapped[str] = mapped_column(String(20), default="0")
    
    # Streaks
    avg_win_streak: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_win_streak: Mapped[int] = mapped_column(Integer, default=0)
    avg_loss_streak: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_loss_streak: Mapped[int] = mapped_column(Integer, default=0)
    
    # Risk metrics
    recovery_factor: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    max_drawdown: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Volume & fees
    total_volume: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_commission: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    
    # Zella Scores
    zella_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    win_rate_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    profit_factor_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    avg_win_loss_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    recovery_factor_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_drawdown_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    
    # Timestamp
    updated_at: Mapped[date] = mapped_column(DateTime, nullable=False)