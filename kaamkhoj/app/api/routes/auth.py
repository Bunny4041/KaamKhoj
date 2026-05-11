from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    PasswordResetRequest, PasswordResetConfirm, ChangePasswordRequest, UserResponse
)
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    create_email_verification_token, create_password_reset_token, verify_email_token
)
from app.api.deps import get_current_user
from app.services.notification_service import send_verification_email, send_password_reset_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
    )
    db.add(user)
    await db.flush()

    # Send verification email in background
    token = create_email_verification_token(user.email)
    background_tasks.add_task(send_verification_email, user.email, user.full_name, token)
    background_tasks.add_task(send_welcome_email, user.email, user.full_name)

    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled. Contact support.")

    # Update last login
    user.last_login = datetime.now(timezone.utc)

    return TokenResponse(
        access_token=create_access_token(user.id, {"role": user.role}),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    decoded = decode_token(payload.refresh_token, token_type="refresh")
    user_id = decoded["sub"]

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return TokenResponse(
        access_token=create_access_token(user.id, {"role": user.role}),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        role=user.role,
    )


@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    email = verify_email_token(token)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"message": "Email already verified"}
    user.is_verified = True
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/forgot-password")
async def forgot_password(
    payload: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    # Always return 200 to avoid email enumeration
    if user:
        token = create_password_reset_token(user.email)
        background_tasks.add_task(send_password_reset_email, user.email, user.full_name, token)
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    payload: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    email = verify_email_token(payload.token)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = hash_password(payload.new_password)
    return {"message": "Password reset successfully. Please log in."}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
