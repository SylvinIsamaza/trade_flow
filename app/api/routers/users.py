from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user information."""
    if user_data.name is not None:
        current_user.name = user_data.name
    if user_data.location is not None:
        current_user.location = user_data.location
    if user_data.timezone is not None:
        current_user.timezone = user_data.timezone
    if user_data.bio is not None:
        current_user.bio = user_data.bio
    if user_data.avatar_url is not None:
        current_user.avatar_url = user_data.avatar_url
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (admin only)."""
    # Only allow users to get their own profile or admins to get any
    if current_user.id != user_id and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user