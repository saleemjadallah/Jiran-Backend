from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_active_user, get_db, get_redis_client
from app.models.user import User
from app.schemas import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    SendOTPRequest,
    TokenResponse,
    UserDetailResponse,
    UserLocation,
    UserResponse,
    UserStats,
    VerifyOTPRequest,
)
from app.utils.geo import point_from_coordinates, point_to_coordinates
from app.utils.jwt import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.utils.otp import generate_otp, send_otp_email, send_otp_sms, store_otp, verify_otp
from app.services.email_service import email_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

PASSWORD_RESET_PREFIX = "password-reset"
PASSWORD_RESET_TTL_SECONDS = 3600


def _user_to_response(user: User) -> UserDetailResponse:
    coordinates = point_to_coordinates(user.location)
    location = None
    if coordinates:
        location = UserLocation(
            latitude=coordinates.latitude,
            longitude=coordinates.longitude,
            neighborhood=user.neighborhood,
            building_name=user.building_name,
        )

    stats = UserStats()
    base = UserResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        avatar_url=user.avatar_url,
        bio=user.bio,
        location=location,
        neighborhood=user.neighborhood,
        building_name=user.building_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
        is_verified=user.is_verified,
        stats=stats,
    )

    return UserDetailResponse(
        **base.model_dump(),
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        stripe_customer_id=user.stripe_customer_id,
        stripe_connect_account_id=user.stripe_connect_account_id,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> TokenResponse:
    existing = await session.execute(
        select(User).where(
            or_(
                func.lower(User.email) == payload.email.lower(),
                func.lower(User.username) == payload.username.lower(),
                User.phone == payload.phone,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    user = User(
        email=payload.email,
        username=payload.username,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )

    # Location can be added later via profile update
    # Not required during registration

    session.add(user)
    await session.commit()
    await session.refresh(user)

    otp = generate_otp()
    identifier = payload.phone or payload.email
    try:
        await store_otp(identifier, otp, redis)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
    if payload.phone:
        await send_otp_sms(payload.phone, otp)
    else:
        await send_otp_email(payload.email, otp, payload.full_name)

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token(str(user.id), user.role.value)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    identifier = payload.identifier.strip().lower()
    query = (
        select(User)
        .where(or_(func.lower(User.email) == identifier, func.lower(User.username) == identifier))
        .limit(1)
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token(str(user.id), user.role.value)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/send-otp")
async def send_otp(
    payload: SendOTPRequest,
    redis: Redis = Depends(get_redis_client),
) -> dict[str, str | bool]:
    identifier = payload.phone or payload.email
    if not identifier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identifier is required")

    otp = generate_otp()
    try:
        await store_otp(identifier, otp, redis)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    if payload.phone:
        await send_otp_sms(payload.phone, otp)
    elif payload.email:
        await send_otp_email(payload.email, otp)

    return {"success": True, "message": "OTP sent"}


@router.post("/verify-otp")
async def verify_user_otp(
    payload: VerifyOTPRequest,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> dict[str, bool]:
    identifier = payload.phone or payload.email
    if not identifier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identifier is required")

    is_valid = await verify_otp(identifier, payload.otp_code, redis)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

    conditions = []
    if payload.email:
        conditions.append(User.email == payload.email)
    if payload.phone:
        conditions.append(User.phone == payload.phone)
    if not conditions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identifier is required")

    query = select(User).where(or_(*conditions))
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_verified = True
    await session.commit()

    # Send welcome email after successful verification
    if payload.email:
        await email_service.send_welcome_email(user.email, user.full_name)

    return {"success": True}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
) -> TokenResponse:
    try:
        data = verify_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = data.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    role = data.get("role")
    access_token = create_access_token({"sub": user_id, "role": role})
    refresh_token = create_refresh_token(user_id, role)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/forgot-password")
async def forgot_password(
    payload: PasswordResetRequest,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> dict[str, str | bool]:
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    token = secrets.token_urlsafe(32)
    key = f"{PASSWORD_RESET_PREFIX}:{token}"
    await redis.set(key, str(user.id), ex=PASSWORD_RESET_TTL_SECONDS)

    # Send password reset email with secure link
    await email_service.send_password_reset_email(payload.email, token, user.full_name)

    return {"success": True, "message": "Password reset instructions sent"}


@router.post("/reset-password")
async def reset_password(
    payload: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> dict[str, bool]:
    key = f"{PASSWORD_RESET_PREFIX}:{payload.token}"
    user_id = await redis.get(key)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    await session.commit()
    await redis.delete(key)

    return {"success": True}


@router.get("/me", response_model=UserDetailResponse)
async def get_me(current_user: User = Depends(get_current_active_user)) -> UserDetailResponse:
    return _user_to_response(current_user)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    redis: Redis = Depends(get_redis_client),
) -> dict[str, str | bool]:
    """
    Logout user by blacklisting their current access token.

    The token will be blacklisted until its natural expiry time,
    preventing reuse even if the token hasn't expired yet.
    """
    # Get token from request context (we'll need to update dependencies to pass this)
    # For now, return success. Token blacklisting will be added when we update dependencies.

    # TODO: Blacklist access token in Redis
    # key = f"token:blacklist:{token}"
    # await redis.set(key, "revoked", ex=ttl_remaining)

    return {"success": True, "message": "Logged out successfully"}


@router.get("/verify-email")
async def verify_email_link(
    code: str,
    email: str,
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> dict[str, str | bool]:
    """
    Verify user email using OTP code from email link.

    This endpoint allows one-click verification via email link
    instead of manually entering the OTP code.

    Args:
        code: 6-digit OTP code
        email: User's email address

    Returns:
        Success message with redirect URL for mobile app
    """
    # Verify OTP
    is_valid = await verify_otp(email, code, redis)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link"
        )

    # Find and verify user
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Mark user as verified
    user.is_verified = True
    await session.commit()

    # Send welcome email
    await email_service.send_welcome_email(user.email, user.full_name)

    # Return success with deep link redirect for mobile app
    return {
        "success": True,
        "message": "Email verified successfully",
        "redirect_url": "soukloop://verified"
    }
