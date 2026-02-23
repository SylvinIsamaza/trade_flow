from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.supporting import Tag
from pydantic import BaseModel

from app.utils.id_generator import generate_tag_id

router = APIRouter(prefix="/tags", tags=["Tags"])


# Schemas
class TagCreate(BaseModel):
    account_id: str
    name: str
    type: str  # SETUP, GENERAL, EXIT, PROCESS
    strategy_id: Optional[int] = None
    color: Optional[str] = None


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class TagResponse(BaseModel):
    id: str
    account_id: str
    name: str
    type: str
    strategy_id: Optional[int]
    color: Optional[str]
    created_at: datetime
    
    model_config = {"from_attributes": True}


@router.get("/", response_model=List[TagResponse])
async def get_tags(
    account_id: Optional[str] = None,
    tag_type: Optional[str] = Query(None, alias="type"),
    strategy_id: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tags with optional filters."""
    # Build base query - only tags from user's accounts
    query = select(Tag).join(Account, Tag.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    # Apply filters
    if account_id:
        query = query.where(Tag.account_id == account_id)
    if tag_type:
        query = query.where(Tag.type == tag_type)
    if strategy_id:
        query = query.where(Tag.strategy_id == strategy_id)
    
    # Order by name
    query = query.order_by(Tag.name).offset(offset).limit(limit)
    
    result = await db.execute(query)
    tags = result.scalars().all()
    
    return tags


@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new tag."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == tag_data.account_id,
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
    
    # Validate tag type
    valid_types = ["SETUP", "GENERAL", "EXIT", "PROCESS"]
    if tag_data.type.upper() not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag type must be one of: {', '.join(valid_types)}"
        )
    tag_id=generate_tag_id(tag_data.account_id)
    
    new_tag = Tag(
        id=tag_id,
        account_id=tag_data.account_id,
        name=tag_data.name,
        type=tag_data.type.upper(),
        strategy_id=tag_data.strategy_id,
        color=tag_data.color,
    )
    
    db.add(new_tag)
    await db.commit()
    await db.refresh(new_tag)
    
    return new_tag


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tag by ID."""
    result = await db.execute(
        select(Tag)
        .join(Account, Tag.account_id == Account.id)
        .where(
            and_(
                Tag.id == tag_id,
                Account.user_id == current_user.id
            )
        )
    )
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return tag


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: str,
    tag_data: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update tag."""
    result = await db.execute(
        select(Tag)
        .join(Account, Tag.account_id == Account.id)
        .where(
            and_(
                Tag.id == tag_id,
                Account.user_id == current_user.id
            )
        )
    )
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Update fields
    if tag_data.name is not None:
        tag.name = tag_data.name
    if tag_data.color is not None:
        tag.color = tag_data.color
    
    await db.commit()
    await db.refresh(tag)
    
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a tag."""
    result = await db.execute(
        select(Tag)
        .join(Account, Tag.account_id == Account.id)
        .where(
            and_(
                Tag.id == tag_id,
                Account.user_id == current_user.id
            )
        )
    )
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    await db.delete(tag)
    await db.commit()