from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime
from typing import Optional, List
import secrets
import pyotp


from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.models.supporting import UserNotification
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token, PasswordResetRequest, TwoFactorSetup, TwoFactorVerify
from app.utils.id_generator import generate_user_notification_id


router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Token expiry settings
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        name=user_data.name,
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@router.post("/login")
async def login(
    db: AsyncSession = Depends(get_db),
    json_data: Optional[UserLogin] = None,
):
    """Login with email and password. Accepts JSON body."""
    if not json_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    email = json_data.email or json_data.username
    password = json_data.password
    two_factor_code = json_data.two_factor_code
    
    # Find user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Check if account is locked
    if user.lock_until and user.lock_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked"
        )
    
    # Check 2FA requirement - if 2FA enabled and no code provided
    if user.is_two_factor_enabled and not two_factor_code:
        return JSONResponse(
            status_code=200,
            content={
                "requires_two_factor": True,
                "user_id": str(user.id)
            }
        )
    
    # Verify 2FA if enabled
    if user.is_two_factor_enabled and two_factor_code:
        totp = pyotp.TOTP(user.two_factor_secret or "")
        is_valid = totp.verify(two_factor_code)
        
        # Check if it's a backup code
        backup_codes = user.two_factor_backup_codes or []
        is_backup_code = two_factor_code.upper() in [code.upper() for code in backup_codes]
        
        if is_backup_code:
            is_valid = True
            # Remove the used backup code
            backup_codes = [code for code in backup_codes if code.upper() != two_factor_code.upper()]
            user.two_factor_backup_codes = backup_codes
            await db.commit()
            
            # Check remaining backup codes and create notification if low
            remaining_codes = len(backup_codes)
            if remaining_codes <= 2:
                # Create notification for low backup codes
                notification = UserNotification(
                    id=generate_user_notification_id(),
                    user_id=user.id,
                    title="Backup Codes Running Low",
                    description=f"You only have {remaining_codes} backup code(s) remaining. Please generate new backup codes to avoid being locked out of your account.",
                    type="BACKUP_CODES",
                    meta={"remaining_codes": remaining_codes, "action": "generate_new_codes"}
                )
                db.add(notification)
                await db.commit()
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
    }


@router.post("/refresh")
async def refresh_token(
    db: AsyncSession = Depends(get_db),
    json_data: Optional[dict] = None,
):
    """Refresh access token using refresh token."""
    refresh_token = None
    if json_data and "refresh_token" in json_data:
        refresh_token = json_data.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required"
        )
    
    payload = decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if not payload:
        raise credentials_exception
    
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise credentials_exception
    
    return user


# ===== Password Reset =====
@router.post("/password-reset-request")
async def request_password_reset(email: str, db: AsyncSession = Depends(get_db)):
    """Request password reset."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if not user:
        return {"success": True, "message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    user.password_reset_token = reset_token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    
    await db.commit()
    
    # In production, send email with reset link
    # For now, return the token (development only!)
    return {
        "success": True,
        "message": "Password reset link sent",
        "reset_token": reset_token  # Remove in production!
    }


@router.post("/password-reset")
async def reset_password(reset_data: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    """Reset password with token."""
    if not reset_data.token or not reset_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token and new password are required"
        )
    
    result = await db.execute(
        select(User).where(User.password_reset_token == reset_data.token)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    if user.password_reset_expires and user.password_reset_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Update password
    user.password_hash = get_password_hash(reset_data.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.last_password_reset = datetime.utcnow()
    
    await db.commit()
    
    return {"success": True, "message": "Password reset successfully"}


# ===== Change Password =====
@router.post("/change-password")
async def change_password(
    password_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change password while logged in."""
    current_password = password_data.get("current_password")
    new_password = password_data.get("new_password")
    
    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password and new password are required"
        )
    
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    current_user.password_hash = get_password_hash(new_password)
    current_user.last_password_reset = datetime.utcnow()
    
    await db.commit()
    
    return {"success": True, "message": "Password changed successfully"}


# ===== Two-Factor Authentication =====
@router.post("/2fa/setup", response_model=TwoFactorSetup)
async def setup_2fa(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Setup 2FA - generate secret."""
    
    # Generate secret
    secret = pyotp.random_base32()
    
    # Generate QR code URL
    totp = pyotp.TOTP(secret)
    qr_url = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="TradeFlow"
    )
    
    # Store temporary secret (not enabled yet)
    current_user.two_factor_secret = secret
    current_user.two_factor_backup_codes = [
        secrets.token_hex(4).upper() for _ in range(10)
    ]
    
    await db.commit()
    
    return TwoFactorSetup(
        secret=secret,
        qr_code_url=qr_url,
        backup_codes=current_user.two_factor_backup_codes
    )


@router.post("/2fa/enable", response_model=dict)
async def enable_2fa(
    verification: TwoFactorVerify,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable 2FA after verification."""
    import pyotp
    
    if not current_user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No 2FA setup in progress"
        )
    
    # Verify TOTP code
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(verification.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Enable 2FA - keep the secret for future verification
    current_user.is_two_factor_enabled = True
    # Keep two_factor_secret for login verification
    
    await db.commit()
    
    return {
        "success": True,
        "message": "2FA enabled successfully",
        "backup_codes": current_user.two_factor_backup_codes
    }


@router.post("/2fa/disable", response_model=dict)
async def disable_2fa(
    request_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable 2FA."""
    password = request_data.get("password")
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required"
        )
    if not verify_password(password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect"
        )
    
    current_user.is_two_factor_enabled = False
    current_user.two_factor_secret = None
    current_user.two_factor_backup_codes = None
    
    await db.commit()
    
    return {"success": True, "message": "2FA disabled successfully"}


@router.post("/2fa/verify", response_model=Token)
async def verify_2fa(
    user_id: str,
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """Verify 2FA code during login."""
    import pyotp
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA not enabled for this user"
        )
    
    # Verify TOTP code or backup code
    totp = pyotp.TOTP(user.two_factor_secret or "")
    is_valid = totp.verify(code) or (code in (user.two_factor_backup_codes or []))
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout")
async def logout():
    """Logout endpoint."""
    return {"success": True, "message": "Logged out successfully"}


# ===== User Notifications =====
@router.get("/notifications", response_model=List[dict])
async def get_user_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all notifications for the current user."""
    stmt = select(UserNotification).where(
        UserNotification.user_id == current_user.id
    ).order_by(UserNotification.created_at.desc()).limit(50)
    
    result = await db.execute(stmt)
    notifications = result.scalars().all()
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "description": n.description,
            "type": n.type,
            "meta": n.meta,
            "is_read": n.is_read,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read."""
    stmt = select(UserNotification).where(
        UserNotification.id == notification_id,
        UserNotification.user_id == current_user.id
    )
    
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    await db.commit()
    
    return {"success": True}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read."""
    from sqlalchemy import update
    
    stmt = update(UserNotification).where(
        UserNotification.user_id == current_user.id,
        UserNotification.is_read == False
    ).values(
        is_read=True,
        read_at=datetime.utcnow()
    )
    
    await db.execute(stmt)
    await db.commit()
    
    return {"success": True}