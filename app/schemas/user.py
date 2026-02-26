from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime


# User schemas
class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    name: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response (excludes sensitive data)."""
    id: str
    role: str
    created_at: datetime
    is_active: bool = True
    location: Optional[str] = None
    timezone: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_two_factor_enabled: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Schema for user login."""
    username: Optional[EmailStr] = None  # For OAuth2 compatibility
    email: Optional[EmailStr] = None  # For JSON login
    password: str
    two_factor_code: Optional[str] = None
    
    # Helper property to get email from either field
    @property
    def email_or_username(self) -> str:
        return self.email or self.username or ""


class Token(BaseModel):
    """Schema for JWT tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload data."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    type: str = "access"


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    token: Optional[str] = None
    new_password: Optional[str] = None
    confirm_password: Optional[str] = None


class TwoFactorSetup(BaseModel):
    """Schema for 2FA setup response."""
    secret: str
    qr_code_url: str
    backup_codes: List[str]


class TwoFactorVerify(BaseModel):
    """Schema for 2FA verification."""
    code: str
    backup_code: Optional[str] = None