from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import time, date, datetime

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.supporting import TradingSession, DailySessionStats, MonthlySessionStats
from pydantic import BaseModel

router = APIRouter(prefix="/sessions", tags=["Trading Sessions"])


# ===== Trading Session Schemas =====
class TradingSessionCreate(BaseModel):
    account_id: str
    name: str  # LONDON, NEW_YORK, ASIA, OTHER
    start_time: time
    end_time: time
    timezone: str


class TradingSessionUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    timezone: Optional[str] = None


class TradingSessionResponse(BaseModel):
    id: str
    account_id: str
    name: str
    start_time: time
    end_time: time
    timezone: str
    
    model_config = {"from_attributes": True}


# ===== Daily Session Stats Schemas =====
class DailySessionStatsResponse(BaseModel):
    account_id: str
    date: date
    session_name: str
    total_pnl: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    trade_ids: List[int]
    
    model_config = {"from_attributes": True}


# ===== Monthly Session Stats Schemas =====
class MonthlySessionStatsResponse(BaseModel):
    account_id: str
    month: date
    session_name: str
    total_pnl: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    
    model_config = {"from_attributes": True}


# ===== Trading Session Endpoints =====
@router.get("/", response_model=List[TradingSessionResponse])
async def get_sessions(
    account_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get trading sessions."""
    query = select(TradingSession).join(Account, TradingSession.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    if account_id:
        query = query.where(TradingSession.account_id == account_id)
    
    result = await db.execute(query.order_by(TradingSession.name))
    return result.scalars().all()


@router.post("/", response_model=TradingSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: TradingSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new trading session."""
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == session_data.account_id,
                Account.user_id == current_user.id
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")
    
    new_session = TradingSession(
        account_id=session_data.account_id,
        name=session_data.name.upper(),
        start_time=session_data.start_time,
        end_time=session_data.end_time,
        timezone=session_data.timezone,
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session


@router.put("/{session_id}", response_model=TradingSessionResponse)
async def update_session(
    session_id: str,
    session_data: TradingSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update trading session."""
    result = await db.execute(
        select(TradingSession)
        .join(Account, TradingSession.account_id == Account.id)
        .where(
            and_(
                TradingSession.id == session_id,
                Account.user_id == current_user.id
            )
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_data.name:
        session.name = session_data.name.upper()
    if session_data.start_time:
        session.start_time = session_data.start_time
    if session_data.end_time:
        session.end_time = session_data.end_time
    if session_data.timezone:
        session.timezone = session_data.timezone
    
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete trading session."""
    result = await db.execute(
        select(TradingSession)
        .join(Account, TradingSession.account_id == Account.id)
        .where(
            and_(
                TradingSession.id == session_id,
                Account.user_id == current_user.id
            )
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await db.delete(session)
    await db.commit()


# ===== Daily Session Stats Endpoints =====
@router.get("/daily-stats", response_model=List[DailySessionStatsResponse])
async def get_daily_session_stats(
    account_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get daily session stats."""
    query = select(DailySessionStats).join(Account, DailySessionStats.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    if account_id:
        query = query.where(DailySessionStats.account_id == account_id)
    if start_date:
        query = query.where(DailySessionStats.date >= start_date)
    if end_date:
        query = query.where(DailySessionStats.date <= end_date)
    
    result = await db.execute(query.order_by(DailySessionStats.date.desc()))
    return result.scalars().all()


# ===== Monthly Session Stats Endpoints =====
@router.get("/monthly-stats", response_model=List[MonthlySessionStatsResponse])
async def get_monthly_session_stats(
    account_id: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get monthly session stats."""
    query = select(MonthlySessionStats).join(Account, MonthlySessionStats.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    if account_id:
        query = query.where(MonthlySessionStats.account_id == account_id)
    if year:
        from datetime import date as date_class
        start_of_year = date_class(year, 1, 1)
        end_of_year = date_class(year + 1, 1, 1)
        query = query.where(
            and_(
                MonthlySessionStats.month >= start_of_year,
                MonthlySessionStats.month < end_of_year
            )
        )
    
    result = await db.execute(query.order_by(MonthlySessionStats.month.desc()))
    return result.scalars().all()