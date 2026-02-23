from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.supporting import Notification
from pydantic import BaseModel

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# Schemas
class NotificationResponse(BaseModel):
    id: str
    account_id: str
    type: str
    message: str
    is_read: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    account_id: Optional[int] = None,
    unread_only: bool = False,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications."""
    query = select(Notification).join(Account, Notification.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    if account_id:
        query = query.where(Notification.account_id == account_id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    
    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/unread-count")
async def get_unread_count(
    account_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get unread notification count."""
    query = select(Notification).join(Account, Notification.account_id == Account.id)
    query = query.where(
        and_(
            Account.user_id == current_user.id,
            Notification.is_read == False
        )
    )
    
    if account_id:
        query = query.where(Notification.account_id == account_id)
    
    result = await db.execute(query)
    count = len(result.scalars().all())
    
    return {"unread_count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark notification as read."""
    result = await db.execute(
        select(Notification)
        .join(Account, Notification.account_id == Account.id)
        .where(
            and_(
                Notification.id == notification_id,
                Account.user_id == current_user.id
            )
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    
    return notification


@router.post("/read-all")
async def mark_all_as_read(
    account_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read."""
    query = (
        update(Notification)
        .where(Notification.account_id == Account.id)
        .where(Account.user_id == current_user.id)
        .values(is_read=True)
    )
    
    if account_id:
        query = query.where(Notification.account_id == account_id)
    
    await db.execute(query)
    await db.commit()
    
    return {"success": True}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a notification."""
    result = await db.execute(
        select(Notification)
        .join(Account, Notification.account_id == Account.id)
        .where(
            and_(
                Notification.id == notification_id,
                Account.user_id == current_user.id
            )
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    await db.delete(notification)
    await db.commit()