from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date


class DailySummaryResponse(BaseModel):
    """Daily summary response schema."""
    account_id: str
    date: date
    total_pnl: float
    total_trades: int
    missed_trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    average_rr: float
    best_win: float
    worst_loss: float
    average_trade_duration: str
    avg_win_streak: float
    max_win_streak: int
    avg_loss_streak: float
    max_loss_streak: int
    recovery_factor: float
    max_drawdown: float
    total_volume: float
    total_commission: float
    zella_score: float
    win_rate_score: float
    profit_factor_score: float
    avg_win_loss_score: float
    recovery_factor_score: float
    max_drawdown_score: float
    trade_ids: List[int]
    total_comments: int
    
    model_config = ConfigDict(from_attributes=True)


class MonthlySummaryResponse(BaseModel):
    """Monthly summary response schema."""
    account_id: str
    month: date
    total_pnl: float
    total_trades: int
    missed_trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    average_rr: float
    best_win: float
    worst_loss: float
    average_trade_duration: str
    avg_win_streak: float
    max_win_streak: int
    avg_loss_streak: float
    max_loss_streak: int
    recovery_factor: float
    max_drawdown: float
    total_volume: float
    total_commission: float
    zella_score: float
    win_rate_score: float
    profit_factor_score: float
    avg_win_loss_score: float
    recovery_factor_score: float
    max_drawdown_score: float
    trade_ids: List[int]
    total_comments: int
    
    model_config = ConfigDict(from_attributes=True)


class AllTimeSummaryResponse(BaseModel):
    """All-time summary response schema."""
    account_id: str
    total_pnl: float
    total_trades: int
    missed_trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    average_rr: float
    best_win: float
    worst_loss: float
    average_trade_duration: str
    avg_win_streak: float
    max_win_streak: int
    avg_loss_streak: float
    max_loss_streak: int
    recovery_factor: float
    max_drawdown: float
    total_volume: float
    total_commission: float
    zella_score: float
    win_rate_score: float
    profit_factor_score: float
    avg_win_loss_score: float
    recovery_factor_score: float
    max_drawdown_score: float
    updated_at: date
    
    model_config = ConfigDict(from_attributes=True)