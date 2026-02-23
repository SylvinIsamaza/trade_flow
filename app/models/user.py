import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Boolean, Integer, DateTime, Enum, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.utils.id_generator import generate_user_id


class UserRole(enum.Enum):
    """User role enumeration."""
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base, TimestampMixin):
    """User model for authentication and profile."""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(20), primary_key=True, default=generate_user_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(10), default=UserRole.USER.value, nullable=False)
    
    # Profile fields
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Authentication
    is_two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    two_factor_backup_codes: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    
    # Password reset
    password_reset_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_password_reset: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Account security
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    lock_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    accounts: Mapped[List["Account"]] = relationship(cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"