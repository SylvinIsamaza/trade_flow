from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.summary import AccountDailyStats, AccountMonthlyStats, AccountAllTimeStats
from app.schemas.analytics import (
    DailySummaryResponse,
    MonthlySummaryResponse,
    AllTimeSummaryResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


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