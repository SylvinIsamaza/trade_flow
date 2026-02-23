"""
Supporting tables for comments, files, notifications, jobs, strategies, notes, tags, etc.
"""
from datetime import date, time
from typing import Optional, List
from sqlalchemy import (
    String, Text, Integer, Numeric, Date, DateTime, Time,
    ForeignKey, ARRAY, Index, JSON, Boolean, Enum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import DeclarativeBase
from app.models.base import Base, TimestampMixin
from app.utils.id_generator import (
    generate_comment_id, generate_file_id, generate_notification_id,
    generate_strategy_id, generate_folder_id, generate_note_id,
    generate_tag_id, generate_insight_id, generate_session_id, generate_job_id
)
import enum


# ============================================
# Comments
# ============================================

class CommentType(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"


class Comment(Base, TimestampMixin):
    """Raw comments on trades/days."""
    __tablename__ = "comments"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    trade_id: Mapped[Optional[str]] = mapped_column(String(35), ForeignKey("trades.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(String(20), ForeignKey("users.id"), nullable=False, index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String(30), ForeignKey("comments.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # For referencing daily/weekly stats
    comment_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # daily/weekly
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class CommentsDailySummary(Base):
    """Daily comment count summary."""
    __tablename__ = "comments_daily_summary"
    
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    total_comments: Mapped[int] = mapped_column(Integer, default=0)


class CommentsMonthlySummary(Base):
    """Monthly comment count summary."""
    __tablename__ = "comments_monthly_summary"
    
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), primary_key=True)
    month: Mapped[date] = mapped_column(Date, primary_key=True)  # First day of month
    total_comments: Mapped[int] = mapped_column(Integer, default=0)


# ============================================
# Files
# ============================================

class File(Base, TimestampMixin):
    """Uploaded files (screenshots, statements, etc.)."""
    __tablename__ = "files"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # MIME type


# ============================================
# Notifications
# ============================================

class NotificationType(enum.Enum):
    TRADE = "TRADE"
    ACHIEVEMENT = "ACHIEVEMENT"
    INSIGHT = "INSIGHT"
    SYSTEM = "SYSTEM"
    IMPORT = "IMPORT"


class Notification(Base, TimestampMixin):
    """User notifications."""
    __tablename__ = "notifications"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)


# ============================================
# Background Jobs
# ============================================

class JobStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobType(enum.Enum):
    AGGREGATE_DAILY_STATS = "AGGREGATE_DAILY_STATS"
    AGGREGATE_MONTHLY_STATS = "AGGREGATE_MONTHLY_STATS"
    IMPORT_TRADES = "IMPORT_TRADES"
    GENERATE_REPORT = "GENERATE_REPORT"
    SYNC_BROKER = "SYNC_BROKER"


class BackgroundJob(Base, TimestampMixin):
    """Background job tracking."""
    __tablename__ = "background_jobs"
    
    id: Mapped[str] = mapped_column(String(25), primary_key=True, default=lambda: generate_job_id())
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=JobStatus.PENDING.value)
    scheduled_at: Mapped[Optional[date]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[date]] = mapped_column(DateTime(timezone=True), nullable=True)


# ============================================
# Strategies
# ============================================

class Strategy(Base, TimestampMixin):
    """Trading strategies."""
    __tablename__ = "strategies"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entry_rules: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=lambda: [])
    exit_rules: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=lambda: [])
    risk_rules: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=lambda: [])
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color


# ============================================
# Notes & Folders
# ============================================

class Folder(Base, TimestampMixin):
    """Note folders."""
    __tablename__ = "folders"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Note(Base, TimestampMixin):
    """Trading notes."""
    __tablename__ = "notes"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    folder_id: Mapped[Optional[str]] = mapped_column(String(30), ForeignKey("folders.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=lambda: [])
    date: Mapped[date] = mapped_column(Date, nullable=False)


# ============================================
# Tags
# ============================================

class TagType(enum.Enum):
    SETUP = "SETUP"
    GENERAL = "GENERAL"
    EXIT = "EXIT"
    PROCESS = "PROCESS"


class Tag(Base, TimestampMixin):
    """Master tag list."""
    __tablename__ = "tags"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # SETUP, GENERAL, EXIT, PROCESS
    strategy_id: Mapped[Optional[str]] = mapped_column(String(30), ForeignKey("strategies.id"), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)


# ============================================
# AI Insights
# ============================================

class InsightType(enum.Enum):
    PERFORMANCE = "PERFORMANCE"
    PSYCHOLOGY = "PSYCHOLOGY"
    STRATEGY = "STRATEGY"


class AIInsight(Base, TimestampMixin):
    """AI-generated trading insights."""
    __tablename__ = "ai_insights"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # PERFORMANCE, PSYCHOLOGY, STRATEGY


# ============================================
# Session Analytics
# ============================================

class SessionName(enum.Enum):
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    ASIA = "ASIA"
    OTHER = "OTHER"


class TradingSession(Base):
    """Trading session configuration."""
    __tablename__ = "trading_sessions"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # LONDON, NEW_YORK, ASIA, OTHER
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)


class DailySessionStats(Base):
    """Daily session performance."""
    __tablename__ = "daily_session_stats"
    
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    session_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    trade_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=lambda: [])


class MonthlySessionStats(Base):
    """Monthly session performance."""
    __tablename__ = "monthly_session_stats"
    
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), primary_key=True)
    month: Mapped[date] = mapped_column(Date, primary_key=True)
    session_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)


# ============================================
# Streak Analytics
# ============================================

class StreakRecord(Base):
    """Daily streak tracking."""
    __tablename__ = "streak_records"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    current_win_streak: Mapped[int] = mapped_column(Integer, default=0)
    max_win_streak: Mapped[int] = mapped_column(Integer, default=0)
    current_loss_streak: Mapped[int] = mapped_column(Integer, default=0)
    max_loss_streak: Mapped[int] = mapped_column(Integer, default=0)
    average_win_streak: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    average_loss_streak: Mapped[float] = mapped_column(Numeric(5, 2), default=0)


# ============================================
# Time-Based Analytics
# ============================================

class PnLByTimeInterval(Base):
    """P&L by time of day."""
    __tablename__ = "pnl_by_time_interval"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    interval_start: Mapped[time] = mapped_column(Time, nullable=False)
    interval_end: Mapped[time] = mapped_column(Time, nullable=False)
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)


class PnLByDayOfWeek(Base):
    """P&L by day of week."""
    __tablename__ = "pnl_by_day_of_week"
    
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), primary_key=True)
    day_of_week: Mapped[int] = mapped_column(Integer, primary_key=True)  # 0=Sunday, 6=Saturday
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)


class PnLByTimeHeld(Base):
    """P&L by trade duration."""
    __tablename__ = "pnl_by_time_held"
    
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), primary_key=True)
    duration_range: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g., "0-30m", "30m-1h"
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)


# ============================================
# Weekly Analytics
# ============================================

class WeeklyStats(Base):
    """Weekly performance."""
    __tablename__ = "weekly_stats"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    trade_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=lambda: [])


# ============================================
# Strategy Analytics
# ============================================

class StrategyDailyStats(Base):
    """Daily strategy performance."""
    __tablename__ = "strategy_daily_stats"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    strategy_id: Mapped[str] = mapped_column(String(30), ForeignKey("strategies.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    profit_factor: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    expectancy: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    trade_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=lambda: [])


class StrategyMonthlyStats(Base):
    """Monthly strategy performance."""
    __tablename__ = "strategy_monthly_stats"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    strategy_id: Mapped[str] = mapped_column(String(30), ForeignKey("strategies.id"), nullable=False, index=True)
    month: Mapped[date] = mapped_column(Date, nullable=False)
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    profit_factor: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    expectancy: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    trade_ids: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=lambda: [])


class StrategyAllTimeStats(Base):
    """All-time strategy performance."""
    __tablename__ = "strategy_all_time_stats"
    
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(30), ForeignKey("accounts.id"), nullable=False, index=True)
    strategy_id: Mapped[str] = mapped_column(String(30), ForeignKey("strategies.id"), nullable=False)
    total_pnl: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    profit_factor: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    expectancy: Mapped[float] = mapped_column(Numeric(18, 8), default=0)
    updated_at: Mapped[date] = mapped_column(DateTime, nullable=False)