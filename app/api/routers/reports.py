from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from collections import defaultdict
from pydantic import BaseModel

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account, Trade

router = APIRouter(prefix="/reports", tags=["Reports"])


class ReportDataPoint(BaseModel):
    """A single data point for reports."""
    key: str
    pnl: float
    count: int
    wins: int
    losses: int
    win_rate: float


class BestWorstStats(BaseModel):
    """Best/worst/most/least statistics."""
    best_key: Optional[str] = None
    best_pnl: float = 0
    worst_key: Optional[str] = None
    worst_pnl: float = 0
    most_key: Optional[str] = None
    most_count: int = 0
    least_key: Optional[str] = None
    least_count: int = 0


class OverviewStats(BaseModel):
    """Overview statistics."""
    total_trades: int = 0
    missed_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0
    total_pnl: float = 0
    average_pnl: float = 0
    average_rr: float = 0
    profit_factor: float = 0
    total_commission: float = 0
    total_volume: float = 0


class SessionStats(BaseModel):
    """Session-based statistics (London, NY, Other)."""
    london: float = 0
    ny: float = 0
    other: float = 0
    london_count: int = 0
    ny_count: int = 0
    other_count: int = 0


class WeeklyStats(BaseModel):
    """Weekly P&L statistics."""
    week_number: int
    week_start: str
    week_end: str
    total_pnl: float
    total_trades: int


class MonthlyStats(BaseModel):
    """Monthly P&L statistics."""
    month: str
    total_pnl: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float


class CompleteReportsResponse(BaseModel):
    """Complete reports data for frontend."""
    account_id: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    
    # By Symbol
    by_symbol: List[ReportDataPoint]
    symbol_best: Optional[BestWorstStats]
    
    # By Day
    by_day: List[ReportDataPoint]
    day_best: Optional[BestWorstStats]
    
    # By Month
    by_month: List[ReportDataPoint]
    month_best: Optional[BestWorstStats]
    
    # By Time (hour)
    by_time: List[ReportDataPoint]
    time_best: Optional[BestWorstStats]
    
    # By Tags
    by_tags: List[ReportDataPoint]
    
    # By Setups
    by_setups: List[ReportDataPoint]
    
    # Overview stats
    overview: OverviewStats
    
    # Session stats
    sessions: SessionStats
    
    # Weekly stats
    weekly: List[WeeklyStats]
    
    # Monthly stats  
    monthly: List[MonthlyStats]
    
    # Equity curve (date, cumulative_pnl)
    equity_curve: List[List[Any]]


def determine_session(executed_at: datetime) -> str:
    """Determine which trading session a trade belongs to."""
    hour = executed_at.hour
    
    # London session: 8:00 - 16:00 UTC
    if 8 <= hour < 16:
        return "london"
    # NY session: 13:00 - 21:00 UTC (overlaps with London)
    elif 13 <= hour < 21:
        return "ny"
    else:
        return "other"


def calculate_report_data(trades: List[Trade], group_by: str) -> List[ReportDataPoint]:
    """Calculate report data grouped by the specified field."""
    data_map: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"pnl": 0, "count": 0, "wins": 0, "losses": 0}
    )
    
    for trade in trades:
        key = ""
        
        if group_by == "symbol":
            key = trade.symbol or "Unknown"
        elif group_by == "day":
            if trade.executed_at:
                key = trade.executed_at.strftime("%A")  # Full day name
            else:
                key = "Unknown"
        elif group_by == "month":
            if trade.executed_at:
                key = trade.executed_at.strftime("%b")  # Short month name
            else:
                key = "Unknown"
        elif group_by == "time":
            if trade.executed_at:
                hour = trade.executed_at.hour
                key = f"{hour:02d}:00"
            else:
                key = "Unknown"
        elif group_by == "tags":
            key = trade.general_tags[0] if trade.general_tags else "No Tag"
        elif group_by == "setups":
            key = trade.setups[0] if trade.setups else "No Setup"
        
        if key:
            data_map[key]["pnl"] += trade.pnl or 0
            data_map[key]["count"] += 1
            if (trade.pnl or 0) > 0:
                data_map[key]["wins"] += 1
            elif (trade.pnl or 0) < 0:
                data_map[key]["losses"] += 1
    
    result = []
    for key, stats in data_map.items():
        win_rate = (stats["wins"] / stats["count"] * 100) if stats["count"] > 0 else 0
        result.append(ReportDataPoint(
            key=key,
            pnl=stats["pnl"],
            count=stats["count"],
            wins=stats["wins"],
            losses=stats["losses"],
            win_rate=win_rate
        ))
    
    # Sort by P&L descending
    result.sort(key=lambda x: x.pnl, reverse=True)
    return result


def calculate_best_worst(data: List[ReportDataPoint]) -> BestWorstStats:
    """Calculate best/worst/most/least from report data."""
    if not data:
        return BestWorstStats()
    
    sorted_by_pnl = sorted(data, key=lambda x: x.pnl, reverse=True)
    sorted_by_count = sorted(data, key=lambda x: x.count, reverse=True)
    
    return BestWorstStats(
        best_key=sorted_by_pnl[0].key if sorted_by_pnl else None,
        best_pnl=sorted_by_pnl[0].pnl if sorted_by_pnl else 0,
        worst_key=sorted_by_pnl[-1].key if sorted_by_pnl else None,
        worst_pnl=sorted_by_pnl[-1].pnl if sorted_by_pnl else 0,
        most_key=sorted_by_count[0].key if sorted_by_count else None,
        most_count=sorted_by_count[0].count if sorted_by_count else 0,
        least_key=sorted_by_count[-1].key if sorted_by_count else None,
        least_count=sorted_by_count[-1].count if sorted_by_count else 0,
    )


@router.get("/complete/{account_id}", response_model=CompleteReportsResponse)
async def get_complete_reports(
    account_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get complete reports data in a single API call.
    
    Returns all report data grouped by symbol, day, month, time, tags, and setups.
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
    
    # Build query for trades
    query = select(Trade).where(Trade.account_id == account_id)
    
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query = query.where(Trade.executed_at >= start_datetime)
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.where(Trade.executed_at <= end_datetime)
    
    query = query.order_by(Trade.executed_at.desc())
    
    result = await db.execute(query)
    trades = result.scalars().all()
    
    # Calculate report data for each group
    by_symbol = calculate_report_data(trades, "symbol")
    by_day = calculate_report_data(trades, "day")
    by_month = calculate_report_data(trades, "month")
    by_time = calculate_report_data(trades, "time")
    by_tags = calculate_report_data(trades, "tags")
    by_setups = calculate_report_data(trades, "setups")
    
    # Calculate best/worst stats
    symbol_best = calculate_best_worst(by_symbol)
    day_best = calculate_best_worst(by_day)
    month_best = calculate_best_worst(by_month)
    time_best = calculate_best_worst(by_time)
    
    # Calculate overview stats
    total_pnl = sum((t.pnl or 0) for t in trades)
    wins = sum(1 for t in trades if (t.pnl or 0) > 0)
    losses = sum(1 for t in trades if (t.pnl or 0) < 0)
    total_wins_pnl = sum((t.pnl or 0) for t in trades if (t.pnl or 0) > 0)
    total_losses_pnl = abs(sum((t.pnl or 0) for t in trades if (t.pnl or 0) < 0))
    
    overview = OverviewStats(
        total_trades=len(trades),
        missed_trades=0,  # Would need missed_trades tracking
        wins=wins,
        losses=losses,
        win_rate=(wins / len(trades) * 100) if trades else 0,
        total_pnl=total_pnl,
        average_pnl=(total_pnl / len(trades)) if trades else 0,
        average_rr=0,  # Would need RR calculation
        total_commission=sum((t.commission or 0) for t in trades),
        total_volume=sum((t.quantity or 0) for t in trades),
    )
    
    # Calculate profit factor
    if total_losses_pnl > 0:
        overview.profit_factor = total_wins_pnl / total_losses_pnl
    
    # Calculate session stats
    sessions = SessionStats()
    for trade in trades:
        if trade.executed_at:
            session = determine_session(trade.executed_at)
            pnl = trade.pnl or 0
            if session == "london":
                sessions.london += pnl
                sessions.london_count += 1
            elif session == "ny":
                sessions.ny += pnl
                sessions.ny_count += 1
            else:
                sessions.other += pnl
                sessions.other_count += 1
    
    # Calculate weekly stats
    weekly_map: Dict[int, Dict[str, Any]] = defaultdict(
        lambda: {"pnl": 0, "trades": 0, "start": None, "end": None}
    )
    for trade in trades:
        if trade.executed_at:
            # Get week number (1-53)
            week_num = trade.executed_at.isocalendar()[1]
            year = trade.executed_at.year
            
            # Get Monday and Sunday of the week
            monday = trade.executed_at - timedelta(days=trade.executed_at.weekday())
            sunday = monday + timedelta(days=6)
            
            weekly_map[week_num]["pnl"] += trade.pnl or 0
            weekly_map[week_num]["trades"] += 1
            if not weekly_map[week_num]["start"]:
                weekly_map[week_num]["start"] = monday
                weekly_map[week_num]["end"] = sunday
    
    weekly = [
        WeeklyStats(
            week_number=week,
            week_start=data["start"].strftime("%Y-%m-%d") if data["start"] else "",
            week_end=data["end"].strftime("%Y-%m-%d") if data["end"] else "",
            total_pnl=data["pnl"],
            total_trades=data["trades"]
        )
        for week, data in sorted(weekly_map.items(), key=lambda x: x[0], reverse=True)
    ]
    
    # Calculate monthly stats
    monthly_map: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"pnl": 0, "trades": 0, "wins": 0, "losses": 0}
    )
    for trade in trades:
        if trade.executed_at:
            month_key = trade.executed_at.strftime("%Y-%m")
            pnl = trade.pnl or 0
            monthly_map[month_key]["pnl"] += pnl
            monthly_map[month_key]["trades"] += 1
            if pnl > 0:
                monthly_map[month_key]["wins"] += 1
            elif pnl < 0:
                monthly_map[month_key]["losses"] += 1
    
    monthly = [
        MonthlyStats(
            month=month,
            total_pnl=data["pnl"],
            total_trades=data["trades"],
            wins=data["wins"],
            losses=data["losses"],
            win_rate=(data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0
        )
        for month, data in sorted(monthly_map.items(), key=lambda x: x[0], reverse=True)
    ]
    
    # Calculate equity curve
    sorted_trades = sorted(trades, key=lambda t: t.executed_at or datetime.min)
    cumulative_pnl = 0
    equity_curve = []
    for trade in sorted_trades:
        if trade.executed_at:
            cumulative_pnl += trade.pnl or 0
            equity_curve.append([
                trade.executed_at.strftime("%Y-%m-%d"),
                round(cumulative_pnl, 2)
            ])
    
    return CompleteReportsResponse(
        account_id=account_id,
        period_start=start_date.isoformat() if start_date else None,
        period_end=end_date.isoformat() if end_date else None,
        by_symbol=by_symbol,
        symbol_best=symbol_best,
        by_day=by_day,
        day_best=day_best,
        by_month=by_month,
        month_best=month_best,
        by_time=by_time,
        time_best=time_best,
        by_tags=by_tags,
        by_setups=by_setups,
        overview=overview,
        sessions=sessions,
        weekly=weekly,
        monthly=monthly,
        equity_curve=equity_curve
    )