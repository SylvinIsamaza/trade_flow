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
from app.utils.id_generator import generate_comment_id
from pydantic import BaseModel

router = APIRouter(prefix="/comments", tags=["Comments"])


# Schemas
class CommentCreate(BaseModel):
    account_id: str
    trade_id: Optional[int] = None
    parent_id: Optional[int] = None
    content: str
    comment_type: Optional[str] = None  # "daily" or "weekly"
    date: Optional[str] = None  # Accept string and convert to date


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


@router.get("/", response_model=dict)
async def get_comments(
    account_id: Optional[str] = None,
    trade_id: Optional[int] = None,
    comment_type: Optional[str] = None,
    date: Optional[date] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comments with optional filters and pagination."""
    from sqlalchemy import func
    
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
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Order and paginate
    query = query.order_by(Comment.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    comments = result.scalars().all()
    
    # Convert to Pydantic models
    comment_responses = [CommentResponse.model_validate(c) for c in comments]
    
    return {
        "items": [c.model_dump() for c in comment_responses],
        "total": total,
        "page": (offset // limit) + 1,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0
    }


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
    
    # Convert date string to date object if provided
    comment_date = None
    if comment_data.date:
        try:
            if isinstance(comment_data.date, str):
                comment_date = datetime.strptime(comment_data.date, "%Y-%m-%d").date()
            else:
                comment_date = comment_data.date
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    new_comment = Comment(
        id=generate_comment_id(comment_data.account_id),
        account_id=comment_data.account_id,
        trade_id=comment_data.trade_id,
        user_id=current_user.id,
        parent_id=comment_data.parent_id,
        content=comment_data.content,
        comment_type=comment_data.comment_type,
        date=comment_date,
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