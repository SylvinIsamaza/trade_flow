from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.supporting import Strategy
from pydantic import BaseModel

from app.utils.id_generator import generate_strategy_id

router = APIRouter(prefix="/strategies", tags=["Strategies"])


# Schemas
class StrategyCreate(BaseModel):
    account_id: str
    name: str
    description: Optional[str] = None
    entry_rules: Optional[List[str]] = []
    exit_rules: Optional[List[str]] = []
    risk_rules: Optional[List[str]] = []
    color: Optional[str] = None


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    entry_rules: Optional[List[str]] = None
    exit_rules: Optional[List[str]] = None
    risk_rules: Optional[List[str]] = None
    color: Optional[str] = None


class StrategyResponse(BaseModel):
    id: str
    account_id: str
    name: str
    description: Optional[str]
    entry_rules: List[str]
    exit_rules: List[str]
    risk_rules: List[str]
    color: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}


@router.get("/", response_model=dict)
async def get_strategies(
    account_id: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get strategies with optional filters and pagination."""
    from sqlalchemy import func
    
    # Build base query
    query = select(Strategy).join(Account, Strategy.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    # Apply filters
    if account_id:
        query = query.where(Strategy.account_id == account_id)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Order and paginate
    query = query.order_by(Strategy.name).offset(offset).limit(limit)
    
    result = await db.execute(query)
    strategies = result.scalars().all()
    
    # Convert to Pydantic models
    strategy_responses = [StrategyResponse.model_validate(s) for s in strategies]
    
    return {
        "items": [s.model_dump() for s in strategy_responses],
        "total": total,
        "page": (offset // limit) + 1,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0
    }


@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new strategy."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == strategy_data.account_id,
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
    
    new_strategy = Strategy(
        id=generate_strategy_id(strategy_data.account_id),
        account_id=strategy_data.account_id,
        name=strategy_data.name,
        description=strategy_data.description,
        entry_rules=strategy_data.entry_rules or [],
        exit_rules=strategy_data.exit_rules or [],
        risk_rules=strategy_data.risk_rules or [],
        color=strategy_data.color,
    )
    
    db.add(new_strategy)
    await db.commit()
    await db.refresh(new_strategy)
    
    return new_strategy


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get strategy by ID."""
    result = await db.execute(
        select(Strategy)
        .join(Account, Strategy.account_id == Account.id)
        .where(
            and_(
                Strategy.id == strategy_id,
                Account.user_id == current_user.id
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    return strategy


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    strategy_data: StrategyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update strategy."""
    result = await db.execute(
        select(Strategy)
        .join(Account, Strategy.account_id == Account.id)
        .where(
            and_(
                Strategy.id == strategy_id,
                Account.user_id == current_user.id
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Update fields
    update_data = strategy_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(strategy, field):
            setattr(strategy, field, value)
    
    db.add(strategy)
    await db.flush()
    await db.commit()
    await db.refresh(strategy)
    
    return strategy


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a strategy."""
    result = await db.execute(
        select(Strategy)
        .join(Account, Strategy.account_id == Account.id)
        .where(
            and_(
                Strategy.id == strategy_id,
                Account.user_id == current_user.id
            )
        )
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    await db.delete(strategy)
    await db.commit()