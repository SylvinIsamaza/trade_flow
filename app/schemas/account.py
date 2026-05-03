from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class AccountBase(BaseModel):
    """Base account schema."""
    broker_name: str
    name: str
    base_currency: str = "USD"
    account_type: str = "DEMO"
    starting_balance: Optional[float] = None


class AccountCreate(AccountBase):
    """Schema for creating a new account."""
    pass


class AccountUpdate(BaseModel):
    """Schema for updating account information."""
    broker_name: Optional[str] = None
    name: Optional[str] = None
    base_currency: Optional[str] = None
    account_type: Optional[str] = None
    starting_balance: Optional[float] = None


class AccountResponse(AccountBase):
    """Schema for account response."""
    id: str
    user_id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)