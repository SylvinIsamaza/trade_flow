from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account, Trade
from app.schemas.trade import TradeCreate, TradeUpdate, TradeResponse
from app.utils.id_generator import generate_trade_id

router = APIRouter(prefix="/trades", tags=["Trades"])


@router.get("/", response_model=dict)
async def get_trades(
    account_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    side: Optional[str] = None,
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get trades with optional filters and pagination."""
    from sqlalchemy import func
    
    # Build base query for filtering
    base_query = select(Trade).join(Account, Trade.account_id == Account.id)
    base_query = base_query.where(Account.user_id == current_user.id)
    
    # Apply filters
    if account_id:
        base_query = base_query.where(Trade.account_id == account_id)
    if start_date:
        # Convert date to datetime for comparison (start of day)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        base_query = base_query.where(Trade.executed_at >= start_datetime)
    if end_date:
        # Convert date to datetime for comparison (end of day)
        end_datetime = datetime.combine(end_date, datetime.max.time())
        base_query = base_query.where(Trade.executed_at <= end_datetime)
    if side:
        base_query = base_query.where(Trade.side == side)
    if status:
        base_query = base_query.where(Trade.status == status)
    if symbol:
        base_query = base_query.where(Trade.symbol == symbol)
    
    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Order and paginate
    query = base_query.order_by(Trade.executed_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    trades = result.scalars().all()
    
    # Convert to Pydantic models
    trade_responses = [TradeResponse.model_validate(trade) for trade in trades]
    
    return {
        "items": [tr.model_dump() for tr in trade_responses],
        "total": total,
        "page": (offset // limit) + 1,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0
    }


@router.post("/", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
async def create_trade(
    trade_data: TradeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new trade."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == trade_data.account_id,
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
    
    trade_payload = trade_data.model_dump()
    new_trade = Trade(
        id=generate_trade_id(trade_data.account_id, trade_data.executed_at),
        **trade_payload,
    )
    
    db.add(new_trade)
    await db.commit()
    await db.refresh(new_trade)
    
    return new_trade


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get trade by ID."""
    result = await db.execute(
        select(Trade)
        .join(Account, Trade.account_id == Account.id)
        .where(
            and_(
                Trade.id == trade_id,
                Account.user_id == current_user.id
            )
        )
    )
    trade = result.scalar_one_or_none()
    
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found"
        )
    
    return trade


@router.put("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: str,
    trade_data: TradeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update trade information."""
    result = await db.execute(
        select(Trade)
        .join(Account, Trade.account_id == Account.id)
        .where(
            and_(
                Trade.id == trade_id,
                Account.user_id == current_user.id
            )
        )
    )
    trade = result.scalar_one_or_none()
    
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found"
        )
    
    # Update fields from the request
    update_data = trade_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(trade, field):
            setattr(trade, field, value)
    
    # Mark the object as modified to ensure changes are tracked
    db.add(trade)
    await db.flush()  # Flush changes to DB
    await db.commit()
    await db.refresh(trade)
    
    return trade


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    trade_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a trade."""
    result = await db.execute(
        select(Trade)
        .join(Account, Trade.account_id == Account.id)
        .where(
            and_(
                Trade.id == trade_id,
                Account.user_id == current_user.id
            )
        )
    )
    trade = result.scalar_one_or_none()
    
    if not trade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found"
        )
    
    await db.delete(trade)
    await db.commit()