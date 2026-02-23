from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/", response_model=List[AccountResponse])
async def get_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all accounts for current user."""
    result = await db.execute(
        select(Account).where(Account.user_id == current_user.id)
    )
    accounts = result.scalars().all()
    return accounts


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new trading account."""
    new_account = Account(
        user_id=current_user.id,
        broker_name=account_data.broker_name,
        name=account_data.name,
        base_currency=account_data.base_currency,
        account_type=account_data.account_type,
    )
    
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    
    return new_account


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get account by ID."""
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return account


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    account_data: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update account information."""
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    if account_data.broker_name is not None:
        account.broker_name = account_data.broker_name
    if account_data.name is not None:
        account.name = account_data.name
    if account_data.base_currency is not None:
        account.base_currency = account_data.base_currency
    if account_data.account_type is not None:
        account.account_type = account_data.account_type
    
    await db.commit()
    await db.refresh(account)
    
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an account."""
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.user_id == current_user.id
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    await db.delete(account)
    await db.commit()