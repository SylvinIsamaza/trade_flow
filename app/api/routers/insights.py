from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date, datetime

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.supporting import AIInsight
from pydantic import BaseModel

router = APIRouter(prefix="/insights", tags=["AI Insights"])


# Schemas
class AIInsightCreate(BaseModel):
    account_id: str
    date: date
    title: str
    content: str
    type: str  # PERFORMANCE, PSYCHOLOGY, STRATEGY


class AIInsightResponse(BaseModel):
    id: str
    account_id: str
    date: date
    title: str
    content: str
    type: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


@router.get("/", response_model=List[AIInsightResponse])
async def get_insights(
    account_id: Optional[int] = None,
    insight_type: Optional[str] = Query(None, alias="type"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get AI insights with filters."""
    query = select(AIInsight).join(Account, AIInsight.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    if account_id:
        query = query.where(AIInsight.account_id == account_id)
    if insight_type:
        query = query.where(AIInsight.type == insight_type)
    if start_date:
        query = query.where(AIInsight.date >= start_date)
    if end_date:
        query = query.where(AIInsight.date <= end_date)
    
    query = query.order_by(AIInsight.date.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=AIInsightResponse, status_code=status.HTTP_201_CREATED)
async def create_insight(
    insight_data: AIInsightCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new AI insight."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == insight_data.account_id,
                Account.user_id == current_user.id
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Validate type
    valid_types = ["PERFORMANCE", "PSYCHOLOGY", "STRATEGY"]
    if insight_data.type.upper() not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Insight type must be one of: {', '.join(valid_types)}"
        )
    
    new_insight = AIInsight(
        account_id=insight_data.account_id,
        date=insight_data.date,
        title=insight_data.title,
        content=insight_data.content,
        type=insight_data.type.upper(),
    )
    db.add(new_insight)
    await db.commit()
    await db.refresh(new_insight)
    return new_insight


@router.get("/{insight_id}", response_model=AIInsightResponse)
async def get_insight(
    insight_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get insight by ID."""
    result = await db.execute(
        select(AIInsight)
        .join(Account, AIInsight.account_id == Account.id)
        .where(
            and_(
                AIInsight.id == insight_id,
                Account.user_id == current_user.id
            )
        )
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight


@router.delete("/{insight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insight(
    insight_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an insight."""
    result = await db.execute(
        select(AIInsight)
        .join(Account, AIInsight.account_id == Account.id)
        .where(
            and_(
                AIInsight.id == insight_id,
                Account.user_id == current_user.id
            )
        )
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    
    await db.delete(insight)
    await db.commit()