from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account, Trade
from app.models.summary import AccountDailyStats, AccountMonthlyStats, AccountAllTimeStats
from app.schemas.analytics import (
    DailySummaryResponse,
    MonthlySummaryResponse,
    AllTimeSummaryResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# Helper functions to calculate stats from trades
def calculate_streaks(trades: List[Any]) -> Dict[str, float]:
    """Calculate win/loss streaks from sorted trades."""
    if not trades:
        return {
            "avg_win_streak": 0,
            "max_win_streak": 0,
            "avg_loss_streak": 0,
            "max_loss_streak": 0,
        }
    
    # Sort trades by date
    sorted_trades = sorted(trades, key=lambda t: get_trade_date_string(t))
    
    win_streaks = []
    loss_streaks = []
    current_win_streak = 0
    current_loss_streak = 0
    
    for trade in sorted_trades:
        if trade.pnl and trade.pnl > 0:
            current_win_streak += 1
            if current_loss_streak > 0:
                loss_streaks.append(current_loss_streak)
                current_loss_streak = 0
        elif trade.pnl and trade.pnl < 0:
            current_loss_streak += 1
            if current_win_streak > 0:
                win_streaks.append(current_win_streak)
                current_win_streak = 0
    
    # Add any remaining streaks
    if current_win_streak > 0:
        win_streaks.append(current_win_streak)
    if current_loss_streak > 0:
        loss_streaks.append(current_loss_streak)
    
    return {
        "avg_win_streak": sum(win_streaks) / len(win_streaks) if win_streaks else 0,
        "max_win_streak": max(win_streaks) if win_streaks else 0,
        "avg_loss_streak": sum(loss_streaks) / len(loss_streaks) if loss_streaks else 0,
        "max_loss_streak": max(loss_streaks) if loss_streaks else 0,
    }


def calculate_pnl_by_day_of_week(trades: List[Any]) -> Dict[str, Any]:
    """Calculate P&L grouped by day of week."""
    days = [ 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat','Sun']
    day_data = {day: 0.0 for day in days}
    day_trades = {day: 0 for day in days}
    
    for trade in trades:
        if trade.date:
            date_str = get_trade_date_string(trade)
            try:
                trade_date = datetime.strptime(date_str, "%Y-%m-%d")
                day_index = trade_date.weekday()
                day_name = days[day_index]
                day_data[day_name] = (day_data[day_name] or 0) + (trade.pnl or 0)
                day_trades[day_name] = (day_trades[day_name] or 0) + 1
            except:
                pass
    
    return {
        "days": days,
        "data": [day_data[day] for day in days],
        "trade_count": [day_trades[day] for day in days],
    }


def calculate_win_rate_by_day_of_week(trades: List[Any]) -> List[int]:
    """Calculate win rate by day of week."""
    days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    day_wins = {day: 0 for day in days}
    day_losses = {day: 0 for day in days}
    
    for trade in trades:
        if trade.date:
            date_str = get_trade_date_string(trade)
            try:
                trade_date = datetime.strptime(date_str, "%Y-%m-%d")
                day_index = trade_date.weekday()
                day_name = days[day_index]
                if trade.pnl and trade.pnl > 0:
                    day_wins[day_name] = (day_wins[day_name] or 0) + 1
                elif trade.pnl and trade.pnl < 0:
                    day_losses[day_name] = (day_losses[day_name] or 0) + 1
            except:
                pass
    
    return [
        round((day_wins[day] / (day_wins[day] + day_losses[day])) * 100)
        if (day_wins[day] + day_losses[day]) > 0 else 0
        for day in days
    ]


def calculate_trades_by_session(trades: List[Any]) -> Dict[str, int]:
    """Calculate trades grouped by trading session (London, NY, Other)."""
    sessions = {"London": 0, "NY": 0, "Other": 0}
    
    for trade in trades:
        if trade.time:
            try:
                time_str = str(trade.time)
                hour_match = time_str.split(':')[0]
                if hour_match:
                    hour = int(hour_match)
                    if 7 <= hour < 12:
                        sessions["London"] += 1
                    elif 13 <= hour < 17:
                        sessions["NY"] += 1
                    else:
                        sessions["Other"] += 1
            except:
                sessions["Other"] += 1
    
    total = sum(sessions.values())
    if total == 0:
        return {"London": 0, "NY": 0, "Other": 0}
    
    return {
        "London": round((sessions["London"] / total) * 100),
        "NY": round((sessions["NY"] / total) * 100),
        "Other": round((sessions["Other"] / total) * 100),
    }


def calculate_pnl_by_time_held(trades: List[Any]) -> Dict[str, Any]:
    """Calculate P&L grouped by duration buckets."""
    buckets = [
        {"label": "0-30m", "min": 0, "max": 30},
        {"label": "30m-1h", "min": 30, "max": 60},
        {"label": "1h-2h", "min": 60, "max": 120},
        {"label": "2h-3h", "min": 120, "max": 180},
        {"label": "3h+", "min": 180, "max": 999999},
    ]
    
    bucket_wins = [0] * len(buckets)
    bucket_losses = [0] * len(buckets)
    
    for trade in trades:
        if trade.duration and trade.pnl is not None:
            duration_str = str(trade.duration).lower()
            minutes = 0
            
            hour_match = duration_str.find('h')
            min_match = duration_str.find('m')
            
            if hour_match >= 0:
                try:
                    hours = int(duration_str[:hour_match].split()[-1])
                    minutes += hours * 60
                except:
                    pass
            
            if min_match >= 0:
                try:
                    mins_start = duration_str.find(' ') + 1 if duration_str.find(' ') >= 0 else 0
                    mins = int(duration_str[mins_start:min_match])
                    minutes += mins
                except:
                    pass
            
            if minutes > 0:
                idx = next((i for i, b in enumerate(buckets) if b["min"] <= minutes < b["max"]), None)
                if idx is not None:
                    if trade.pnl > 0:
                        bucket_wins[idx] += 1
                    elif trade.pnl < 0:
                        bucket_losses[idx] += 1
    
    return {
        "labels": [b["label"] for b in buckets],
        "wins": bucket_wins,
        "losses": bucket_losses,
    }


def calculate_pnl_by_week(trades: List[Any]) -> List[Dict[str, Any]]:
    """Calculate P&L grouped by week."""
    week_data: Dict[str, Dict[str, Any]] = {}
    
    for trade in trades:
        if trade.date:
            date_str = get_trade_date_string(trade)
            try:
                trade_date = datetime.strptime(date_str, "%Y-%m-%d")
                year = trade_date.year
                day = trade_date.weekday()
                diff = trade_date.day - day + (day - 6 if day == 6 else 1)
                week_num = (diff - 1) // 7 + 1
                week_key = f"{year}-W{week_num}"
                
                if week_key not in week_data:
                    week_data[week_key] = {"pnl": 0, "count": 0}
                week_data[week_key]["pnl"] = (week_data[week_key]["pnl"] or 0) + (trade.pnl or 0)
                week_data[week_key]["count"] = (week_data[week_key]["count"] or 0) + 1
            except:
                pass
    
    sorted_weeks = sorted(week_data.keys(), reverse=True)[:6]
    return [
        {"week": week, "pnl": week_data[week]["pnl"], "count": week_data[week]["count"]}
        for week in sorted_weeks
    ]


def calculate_scatter_data(trades: List[Any]) -> Dict[str, List[List[Any]]]:
    """Calculate scatter data for duration vs P&L."""
    winning_data: List[List[Any]] = []
    losing_data: List[List[Any]] = []
    
    for trade in trades:
        if trade.duration and trade.pnl is not None:
            duration_str = str(trade.duration).lower()
            minutes = 0
            
            hour_match = duration_str.find('h')
            min_match = duration_str.find('m')
            
            if hour_match >= 0:
                try:
                    hours = int(duration_str[:hour_match].split()[-1])
                    minutes += hours * 60
                except:
                    pass
            
            if min_match >= 0:
                try:
                    mins_start = duration_str.find(' ') + 1 if duration_str.find(' ') >= 0 else 0
                    mins = int(duration_str[mins_start:min_match])
                    minutes += mins
                except:
                    pass
            
            if minutes > 0:
                if trade.pnl > 0:
                    winning_data.append([minutes, trade.pnl])
                elif trade.pnl < 0:
                    losing_data.append([minutes, trade.pnl])
    
    return {
        "winning": winning_data,
        "losing": losing_data,
    }


def calculate_average_duration(trades: List[Any]) -> str:
    """Calculate average trade duration."""
    total_minutes = 0
    count = 0
    
    for trade in trades:
        if trade.duration:
            duration_str = str(trade.duration).lower()
            minutes = 0
            
            hour_match = duration_str.find('h')
            min_match = duration_str.find('m')
            
            if hour_match >= 0:
                try:
                    hours = int(duration_str[:hour_match].split()[-1])
                    minutes += hours * 60
                except:
                    pass
            
            if min_match >= 0:
                try:
                    mins_start = duration_str.find(' ') + 1 if duration_str.find(' ') >= 0 else 0
                    mins = int(duration_str[mins_start:min_match])
                    minutes += mins
                except:
                    pass
            
            if minutes > 0:
                total_minutes += minutes
                count += 1
    
    if count == 0:
        return "0m"
    
    avg_mins = round(total_minutes / count)
    if avg_mins >= 60:
        hours = avg_mins // 60
        mins = avg_mins % 60
        return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
    
    return f"{avg_mins}m"


def calculate_stats_from_trades(trades: List[Any]) -> Dict[str, Any]:
    """Calculate all statistics from raw trade data."""
    if not trades:
        return {
            "total_trades": 0,
            "total_profit": 0.0,
            "missed_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "average_rr": 0.0,
            "best_win": 0.0,
            "worst_loss": 0.0,
            "average_trade_duration": "0m",
            "total_commission": 0.0,
            "total_swap": 0.0,
            "avg_win_streak": 0.0,
            "max_win_streak": 0,
            "avg_loss_streak": 0.0,
            "max_loss_streak": 0,
            "recovery_factor": 0.0,
            "max_drawdown": 0.0,
        }
    
    wins = [t for t in trades if t.pnl and float(t.pnl) > 0]
    losses = [t for t in trades if t.pnl and float(t.pnl) < 0]
    
    total_trades = len(trades)
    gross_pnl = float(sum(float(t.pnl) for t in trades if t.pnl))
    total_commission = float(sum(float(t.commission) for t in trades if t.commission))
    total_swap = float(sum(float(t.swap) for t in trades if t.swap))
    total_profit = gross_pnl - abs(total_commission) + total_swap
    
    winners = len(wins)
    losers = len(losses)
    win_rate = (winners / total_trades * 100) if total_trades > 0 else 0.0
    
    total_wins = sum(float(t.pnl) for t in wins) if wins else 0.0
    total_losses = abs(sum(float(t.pnl) for t in losses)) if losses else 0.0
    profit_factor = float(total_wins / total_losses) if total_losses > 0 else 0.0
    
    average_win = float(total_wins / winners) if winners > 0 else 0.0
    average_loss = float(total_losses / losers) if losers > 0 else 0.0
    best_win = float(max((float(t.pnl) for t in wins), default=0)) if wins else 0.0
    worst_loss = float(min((float(t.pnl) for t in losses), default=0)) if losses else 0.0
    average_rr = abs(float(average_win / average_loss)) if average_loss > 0 else 0.0
    
    # Calculate streaks
    streak_data = calculate_streaks(trades)
    
    # Calculate average duration
    avg_duration = calculate_average_duration(trades)
    
    # Calculate recovery factor and max drawdown (simplified)
    recovery_factor = float(total_profit / abs(worst_loss)) if worst_loss != 0 else 0.0
    max_drawdown = 0.0  # Simplified - would need historical equity data
    
    return {
        "total_trades": total_trades,
        "total_profit": total_profit,
        "missed_trades": 0,
        "wins": winners,
        "losses": losers,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "average_win": average_win,
        "average_loss": average_loss,
        "average_rr": average_rr,
        "best_win": best_win,
        "worst_loss": worst_loss,
        "average_trade_duration": avg_duration,
        "total_commission": total_commission,
        "total_swap": total_swap,
        "avg_win_streak": float(streak_data["avg_win_streak"]),
        "max_win_streak": int(streak_data["max_win_streak"]),
        "avg_loss_streak": float(streak_data["avg_loss_streak"]),
        "max_loss_streak": int(streak_data["max_loss_streak"]),
        "recovery_factor": recovery_factor,
        "max_drawdown": max_drawdown,
    }


def get_trade_date_string(trade: Any) -> str:
    """Get date string from trade, handling both datetime and string types."""
    if not trade.date:
        return ""
    if isinstance(trade.date, str):
        return trade.date
    # It's a datetime object
    return trade.date.strftime("%Y-%m-%d")


def calculate_daily_stats(trades: List[Any]) -> List[Dict[str, Any]]:
    """Calculate daily statistics from trades."""
    daily_data: Dict[str, List[Any]] = {}
    
    for trade in trades:
        if trade.date:
            date_str = get_trade_date_string(trade)
            if date_str not in daily_data:
                daily_data[date_str] = []
            daily_data[date_str].append(trade)
    
    daily_stats = []
    for date in sorted(daily_data.keys(), reverse=True):
        day_trades = daily_data[date]
        stats = calculate_stats_from_trades(day_trades)
        stats["date"] = date
        stats["account_id"] = day_trades[0].account_id if day_trades else None
        daily_stats.append(stats)
    
    return daily_stats


def calculate_monthly_stats(trades: List[Any]) -> List[Dict[str, Any]]:
    """Calculate monthly statistics from trades."""
    monthly_data: Dict[str, List[Any]] = {}
    
    for trade in trades:
        if trade.date:
            date_str = get_trade_date_string(trade)
            month = date_str[:7]  # YYYY-MM
            if month not in monthly_data:
                monthly_data[month] = []
            monthly_data[month].append(trade)
    
    monthly_stats = []
    for month in sorted(monthly_data.keys(), reverse=True):
        month_trades = monthly_data[month]
        stats = calculate_stats_from_trades(month_trades)
        stats["month"] = month
        stats["account_id"] = month_trades[0].account_id if month_trades else None
        monthly_stats.append(stats)
    
    return monthly_stats


class CompleteAnalyticsResponse(BaseModel):
    """Response model for complete analytics data."""
    account_id: str
    all_time: Optional[Dict[str, Any]] = None
    daily: List[Dict[str, Any]] = []
    monthly: List[Dict[str, Any]] = []
    recent_trades: List[Dict[str, Any]] = []
    statistics: Dict[str, Any] = {}
    charts: Dict[str, Any] = {}


@router.get("/complete/{account_id}", response_model=CompleteAnalyticsResponse)
async def get_complete_analytics(
    account_id: str,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=200),
    start_date: Optional[str] = Query(default=None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date filter (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get complete analytics for an account in a single call.
    
    Returns:
        - All-time statistics (or filtered by date range if provided)
        - Daily summaries for the date range
        - Monthly summaries
        - Recent trades
    """
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == account_id,
                Account.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    response = CompleteAnalyticsResponse(account_id=account_id)
    
    # Get all trades for the account
    result = await db.execute(
        select(Trade).where(Trade.account_id == account_id)
    )
    all_trades = result.scalars().all()
    
    # Determine the date range to use
    if start_date and end_date:
        # Use custom date range
        from datetime import datetime
        try:
            filter_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            filter_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            filter_start = None
            filter_end = None
    else:
        # Use days parameter
        from datetime import timedelta
        filter_end = datetime.now().date()
        filter_start = filter_end - timedelta(days=days)
    
    # Filter trades by date range
    if filter_start and filter_end:
        filtered_trades = [
            t for t in all_trades
            if t.date and (t.date.date() if hasattr(t.date, 'date') else t.date) >= filter_start
            and t.date and (t.date.date() if hasattr(t.date, 'date') else t.date) <= filter_end
        ]
    else:
        filtered_trades = all_trades
    
    # Calculate all-time stats from filtered trades
    response.all_time = calculate_stats_from_trades(filtered_trades)
    
    # Calculate daily stats from filtered trades
    response.daily = calculate_daily_stats(filtered_trades)
    
    # Calculate monthly stats from all trades (for the full account history)
    response.monthly = calculate_monthly_stats(all_trades)
    
    # Get recent trades (within date range if provided)
    if filter_start and filter_end:
        result = await db.execute(
            select(Trade)
            .where(Trade.account_id == account_id)
            .order_by(Trade.executed_at.desc())
            .limit(limit)
        )
        trades = result.scalars().all()
        # Filter trades to date range
        recent_trades = [
            t for t in trades
            if t.date and (t.date.date() if hasattr(t.date, 'date') else t.date) >= filter_start
            and t.date and (t.date.date() if hasattr(t.date, 'date') else t.date) <= filter_end
        ]
    else:
        result = await db.execute(
            select(Trade)
            .where(Trade.account_id == account_id)
            .order_by(Trade.executed_at.desc())
            .limit(limit)
        )
        recent_trades = result.scalars().all()
    
    response.recent_trades = [
        {
            "id": trade.id,
            "account_id": trade.account_id,
            "symbol": trade.symbol,
            "side": trade.side,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "close_price": trade.close_price,
            "quantity": trade.quantity,
            "pnl": trade.pnl,
            "commission": trade.commission,
            "swap": trade.swap,
            "duration": trade.duration,
            "trade_type": trade.trade_type,
            "execution_type": trade.execution_type,
            "status": trade.status,
            "stop_loss": trade.stop_loss,
            "take_profit": trade.take_profit,
            "setups": trade.setups or [],
            "general_tags": trade.general_tags or [],
            "exit_tags": trade.exit_tags or [],
            "process_tags": trade.process_tags or [],
            "notes": trade.notes,
            "executed_at": trade.executed_at.isoformat() if trade.executed_at else None,
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
            "date": trade.date,
            "time": trade.time,
            "close_time": trade.close_time,
        }
        for trade in recent_trades
    ]
    
    # Calculate additional statistics
    if response.daily:
        # Calculate streak info
        current_streak = 0
        best_streak = 0
        for day in response.daily:
            if day.get("total_profit", 0) > 0:
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = 0
        
        response.statistics = {
            "current_streak": current_streak,
            "best_streak": best_streak,
            "days_with_data": len(response.daily),
            "profitable_days": len([d for d in response.daily if d.get("total_profit", 0) > 0]),
            "losing_days": len([d for d in response.daily if d.get("total_profit", 0) < 0]),
            "total_months_with_data": len(response.monthly),
        }
    
    # Calculate chart data from filtered trades (respects date range)
    response.charts = {
        "pnl_by_day_of_week": calculate_pnl_by_day_of_week(filtered_trades),
        "win_rate_by_day_of_week": calculate_win_rate_by_day_of_week(filtered_trades),
        "trades_by_session": calculate_trades_by_session(filtered_trades),
        "pnl_by_time_held": calculate_pnl_by_time_held(filtered_trades),
        "pnl_by_week": calculate_pnl_by_week(filtered_trades),
        "scatter_data": calculate_scatter_data(filtered_trades),
    }
    
    return response


@router.get("/daily/{account_id}", response_model=List[DailySummaryResponse])
async def get_daily_summary(
    account_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get daily summary for an account."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == account_id,
                Account.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Get daily stats
    query = select(AccountDailyStats).where(AccountDailyStats.account_id == account_id)
    
    if start_date:
        query = query.where(AccountDailyStats.date >= start_date)
    if end_date:
        query = query.where(AccountDailyStats.date <= end_date)
    
    query = query.order_by(AccountDailyStats.date.desc()).limit(limit)
    
    result = await db.execute(query)
    stats = result.scalars().all()
    
    return stats


@router.get("/daily/{account_id}/date/{date_value}", response_model=DailySummaryResponse)
async def get_daily_summary_by_date(
    account_id: str,
    date_value: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get daily summary for a specific date."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == account_id,
                Account.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Get daily stats for date
    result = await db.execute(
        select(AccountDailyStats).where(
            and_(
                AccountDailyStats.account_id == account_id,
                AccountDailyStats.date == date_value
            )
        )
    )
    stats = result.scalar_one_or_none()
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily summary not found for this date"
        )
    
    return stats


@router.get("/monthly/{account_id}", response_model=List[MonthlySummaryResponse])
async def get_monthly_summary(
    account_id: str,
    year: Optional[int] = None,
    limit: int = 12,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get monthly summary for an account."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == account_id,
                Account.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Get monthly stats
    query = select(AccountMonthlyStats).where(AccountMonthlyStats.account_id == account_id)
    
    if year:
        # Filter by year (month starts with the year)
        from datetime import date as date_class
        start_of_year = date_class(year, 1, 1)
        end_of_year = date_class(year + 1, 1, 1)
        query = query.where(
            and_(
                AccountMonthlyStats.month >= start_of_year,
                AccountMonthlyStats.month < end_of_year
            )
        )
    
    query = query.order_by(AccountMonthlyStats.month.desc()).limit(limit)
    
    result = await db.execute(query)
    stats = result.scalars().all()
    
    return stats


@router.get("/all-time/{account_id}", response_model=AllTimeSummaryResponse)
async def get_all_time_summary(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all-time summary for an account."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == account_id,
                Account.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Get all-time stats
    result = await db.execute(
        select(AccountAllTimeStats).where(AccountAllTimeStats.account_id == account_id)
    )
    stats = result.scalar_one_or_none()
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="All-time summary not found"
        )
    
    return stats


def calculate_zella_score(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate  Score based on trading metrics."""
    # Convert all values to float to handle decimal.Decimal
    win_rate = float(stats.get("win_rate", 0))
    profit_factor = float(stats.get("profit_factor", 0))
    avg_rr = float(stats.get("average_rr", 0))
    
    # Win rate score (0-100)
    win_rate_score = min(win_rate, 60) * (100/60)
    
    # Profit factor score (0-100) - scale based on typical values
    profit_factor_score = min(profit_factor / 3 * 100, 100)
    
    # Average R:R score (0-100) - scale based on typical values
    avg_rr_score = min(avg_rr / 4 * 100, 100)
    
    # Consistency score - based on day win %
    day_win_rate = float(stats.get("day_win_rate", 0))
    consistency_score = day_win_rate
    
    # Recovery factor score (if available)
    recovery_factor = float(stats.get("recovery_factor", 1))
    recovery_score = min(recovery_factor / 3 * 100, 100)
    
    # Max drawdown score (inverse - lower is better)
    max_dd = float(stats.get("max_drawdown", 0))
    dd_score = max(0, 100 - max_dd)
    
    # Calculate overall Zella Score (weighted average)
    zella_score = (
        win_rate_score * 0.15 +
        profit_factor_score * 0.20 +
        avg_rr_score * 0.20 +
        consistency_score * 0.20 +
        recovery_score * 0.10 +
        dd_score * 0.15
    )
    
    return {
        "zella_score": round(float(zella_score), 2),
        "win_rate_score": round(float(win_rate_score), 2),
        "profit_factor_score": round(float(profit_factor_score), 2),
        "avg_win_loss_score": round(float(avg_rr_score), 2),
        "consistency_score": round(float(consistency_score), 2),
        "recovery_factor_score": round(float(recovery_score), 2),
        "max_drawdown_score": round(float(dd_score), 2),
    }


def calculate_day_win_rate(daily_stats: List[Dict[str, Any]]) -> float:
    """Calculate the percentage of profitable days."""
    if not daily_stats:
        return 0.0
    profitable_days = sum(1 for day in daily_stats if float(day.get("total_profit", 0)) > 0)
    return round((profitable_days / len(daily_stats)) * 100, 2)


class DashboardResponse(BaseModel):
    """Response model for dashboard data."""
    account_id: str
    # Balance information
    starting_balance: Optional[float] = None
    current_balance: float
    # Summary stats
    net_pnl: float
    total_trades: int
    win_rate: float
    profit_factor: float
    day_win_rate: float
    average_win_loss: float
    # Score data
    zella_score: float
    win_rate_score: float
    profit_factor_score: float
    avg_win_loss_score: float
    recovery_factor_score: float
    max_drawdown_score: float
    # Detailed stats
    wins: int
    losses: int
    total_commission: float
    best_win: float
    worst_loss: float
    average_trade_duration: str
    avg_win_streak: float
    max_win_streak: float
    avg_loss_streak: float
    max_loss_streak: float
    # Calendar data
    daily_summaries: List[Dict[str, Any]]
    # Recent trades
    recent_trades: List[Dict[str, Any]]
    # Chart data
    charts: Dict[str, Any]
    # Last import timestamp
    last_import: Optional[str] = None


@router.get("/dashboard/{account_id}", response_model=DashboardResponse)
async def get_dashboard(
    account_id: str,
    start_date: Optional[str] = Query(default=None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date filter (YYYY-MM-DD)"),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get complete dashboard data with filtering support.
    
    Returns all data needed for the dashboard in a single call:
    - Summary statistics (P&L, win rate, profit factor, etc.)
    -  score breakdown
    - Daily summaries for calendar
    - Recent trades
    - Chart data for visualizations
    """
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == account_id,
                Account.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Get all trades for the account
    result = await db.execute(
        select(Trade).where(Trade.account_id == account_id)
    )
    all_trades = result.scalars().all()
    
    # Determine the date range to use
    from datetime import datetime, timedelta
    
    if start_date and end_date:
        try:
            filter_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            filter_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            filter_start = None
            filter_end = None
    else:
        # Default to last 30 days if no filter
        filter_end = datetime.now().date()
        filter_start = filter_end - timedelta(days=30)
    
    # Filter trades by date range
    if filter_start and filter_end:
        filtered_trades = [
            t for t in all_trades
            if t.date and (t.date.date() if hasattr(t.date, 'date') else t.date) >= filter_start
            and t.date and (t.date.date() if hasattr(t.date, 'date') else t.date) <= filter_end
        ]
    else:
        filtered_trades = all_trades
    
    # Calculate stats from filtered trades
    stats = calculate_stats_from_trades(filtered_trades)
    
    # Calculate daily summaries for calendar
    daily_summaries = calculate_daily_stats(filtered_trades)
    
    # Calculate day win rate
    day_win_rate = calculate_day_win_rate(daily_summaries)
    
    # Calculate zella score
    stats["day_win_rate"] = day_win_rate
    zella_scores = calculate_zella_score(stats)
    
    # Get recent trades
    sorted_trades = sorted(filtered_trades, key=lambda t: t.executed_at if t.executed_at else datetime.min, reverse=True)
    recent_trades_list = sorted_trades[:limit]
    
    recent_trades = [
        {
            "id": trade.id,
            "account_id": trade.account_id,
            "symbol": trade.symbol,
            "side": trade.side,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "close_price": trade.close_price,
            "quantity": trade.quantity,
            "pnl": trade.pnl,
            "commission": trade.commission,
            "swap": trade.swap,
            "duration": trade.duration,
            "trade_type": trade.trade_type,
            "execution_type": trade.execution_type,
            "status": trade.status,
            "stop_loss": trade.stop_loss,
            "take_profit": trade.take_profit,
            "setups": trade.setups or [],
            "general_tags": trade.general_tags or [],
            "exit_tags": trade.exit_tags or [],
            "process_tags": trade.process_tags or [],
            "notes": trade.notes,
            "executed_at": trade.executed_at.isoformat() if trade.executed_at else None,
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
            "date": trade.date,
            "time": trade.time,
            "close_time": trade.close_time,
        }
        for trade in recent_trades_list
    ]
    
    # Calculate chart data
    charts = {
        "pnl_by_day_of_week": calculate_pnl_by_day_of_week(filtered_trades),
        "win_rate_by_day_of_week": calculate_win_rate_by_day_of_week(filtered_trades),
        "trades_by_session": calculate_trades_by_session(filtered_trades),
        "pnl_by_time_held": calculate_pnl_by_time_held(filtered_trades),
    }
    
    # Get the last trade's created_at timestamp for "last import"
    last_import = None
    if all_trades:
        sorted_by_created = sorted(all_trades, key=lambda t: t.created_at if t.created_at else datetime.min, reverse=True)
        if sorted_by_created and sorted_by_created[0].created_at:
            last_import = sorted_by_created[0].created_at.isoformat()
    
    # Calculate balance
    starting_balance = float(account.starting_balance) if account.starting_balance else 0
    total_pnl = float(stats.get("total_profit", 0))
    current_balance = starting_balance + total_pnl
    
    return DashboardResponse(
        account_id=account_id,
        starting_balance=starting_balance if starting_balance > 0 else None,
        current_balance=current_balance,
        net_pnl=total_pnl,
        total_trades=int(stats.get("total_trades", 0)),
        win_rate=float(stats.get("win_rate", 0)),
        profit_factor=float(stats.get("profit_factor", 0)),
        day_win_rate=float(day_win_rate),
        average_win_loss=float(stats.get("average_rr", 0)),
        zella_score=float(zella_scores.get("zella_score", 0)),
        win_rate_score=float(zella_scores.get("win_rate_score", 0)),
        profit_factor_score=float(zella_scores.get("profit_factor_score", 0)),
        avg_win_loss_score=float(zella_scores.get("avg_win_loss_score", 0)),
        recovery_factor_score=float(zella_scores.get("recovery_factor_score", 0)),
        max_drawdown_score=float(zella_scores.get("max_drawdown_score", 0)),
        wins=int(stats.get("wins", 0)),
        losses=int(stats.get("losses", 0)),
        total_commission=float(stats.get("total_commission", 0)),
        best_win=float(stats.get("best_win", 0)),
        worst_loss=float(stats.get("worst_loss", 0)),
        average_trade_duration=str(stats.get("average_trade_duration", "0m")),
        avg_win_streak=float(stats.get("avg_win_streak", 0)),
        max_win_streak=float(stats.get("max_win_streak", 0)),
        avg_loss_streak=float(stats.get("avg_loss_streak", 0)),
        max_loss_streak=float(stats.get("max_loss_streak", 0)),
        daily_summaries=daily_summaries,
        recent_trades=recent_trades,
        charts=charts,
        last_import=last_import,
    )