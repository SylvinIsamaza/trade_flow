from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account, Trade
from app.schemas.trade import TradeCreate, TradeUpdate, TradeResponse

router = APIRouter(prefix="/trades", tags=["Trades"])


@router.get("/", response_model=List[TradeResponse])
async def get_trades(
    account_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    side: Optional[str] = None,
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get trades with optional filters."""
    # Build query
    query = select(Trade)
    
    # Join with Account to ensure user owns the account
    query = query.join(Account, Trade.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    # Apply filters
    if account_id:
        query = query.where(Trade.account_id == account_id)
    if start_date:
        query = query.where(Trade.executed_at >= start_date)
    if end_date:
        query = query.where(Trade.executed_at <= end_date)
    if side:
        query = query.where(Trade.side == side)
    if status:
        query = query.where(Trade.status == status)
    if symbol:
        query = query.where(Trade.symbol == symbol)
    
    # Order and paginate
    query = query.order_by(Trade.executed_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    trades = result.scalars().all()
    
    return trades


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
    
    new_trade = Trade(
        account_id=trade_data.account_id,
        symbol=trade_data.symbol,
        side=trade_data.side,
        entry_price=trade_data.entry_price,
        exit_price=trade_data.exit_price,
        close_price=trade_data.close_price,
        quantity=trade_data.quantity,
        pnl=trade_data.pnl,
        commission=trade_data.commission,
        swap=trade_data.swap,
        duration=trade_data.duration,
        trade_type=trade_data.trade_type,
        execution_type=trade_data.execution_type,
        status=trade_data.status,
        stop_loss=trade_data.stop_loss,
        take_profit=trade_data.take_profit,
        setups=trade_data.setups,
        general_tags=trade_data.general_tags,
        exit_tags=trade_data.exit_tags,
        process_tags=trade_data.process_tags,
        notes=trade_data.notes,
        executed_at=trade_data.executed_at,
        date=trade_data.date,
        time=trade_data.time,
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
    
    # Update fields
    update_data = trade_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(trade, field, value)
    
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