from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date, datetime

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.supporting import Comment
from pydantic import BaseModel

router = APIRouter(prefix="/comments", tags=["Comments"])


# Schemas
class CommentCreate(BaseModel):
    account_id: str
    trade_id: Optional[int] = None
    parent_id: Optional[int] = None
    content: str
    comment_type: Optional[str] = None  # "daily" or "weekly"
    date: Optional[date] = None


class CommentUpdate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: str
    account_id: str
    trade_id: Optional[int]
    user_id: str
    parent_id: Optional[int]
    content: str
    comment_type: Optional[str]
    date: Optional[date]
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


@router.get("/", response_model=List[CommentResponse])
async def get_comments(
    account_id: Optional[int] = None,
    trade_id: Optional[int] = None,
    comment_type: Optional[str] = None,
    date: Optional[date] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comments with optional filters."""
    # Build base query - only comments from user's accounts
    query = select(Comment).join(Account, Comment.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    # Apply filters
    if account_id:
        query = query.where(Comment.account_id == account_id)
    if trade_id:
        query = query.where(Comment.trade_id == trade_id)
    if comment_type:
        query = query.where(Comment.comment_type == comment_type)
    if date:
        query = query.where(Comment.date == date)
    
    # Order and paginate
    query = query.order_by(Comment.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    return comments


@router.post("/", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new comment/journal entry."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == comment_data.account_id,
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
    
    new_comment = Comment(
        account_id=comment_data.account_id,
        trade_id=comment_data.trade_id,
        user_id=current_user.id,
        parent_id=comment_data.parent_id,
        content=comment_data.content,
        comment_type=comment_data.comment_type,
        date=comment_data.date,
    )
    
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)
    
    return new_comment


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comment by ID."""
    result = await db.execute(
        select(Comment)
        .join(Account, Comment.account_id == Account.id)
        .where(
            and_(
                Comment.id == comment_id,
                Account.user_id == current_user.id
            )
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    return comment


@router.put("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: str,
    comment_data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update comment content."""
    result = await db.execute(
        select(Comment)
        .join(Account, Comment.account_id == Account.id)
        .where(
            and_(
                Comment.id == comment_id,
                Account.user_id == current_user.id
            )
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Only allow owner to edit
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this comment"
        )
    
    comment.content = comment_data.content
    await db.commit()
    await db.refresh(comment)
    
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a comment."""
    result = await db.execute(
        select(Comment)
        .join(Account, Comment.account_id == Account.id)
        .where(
            and_(
                Comment.id == comment_id,
                Account.user_id == current_user.id
            )
        )
    )
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Only allow owner to delete
    if comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this comment"
        )
    
    await db.delete(comment)
    await db.commit()