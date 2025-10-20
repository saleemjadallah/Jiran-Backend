"""
Notification endpoints: Get notifications, mark as read, device registration, settings
"""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.notification import DevicePlatform, DeviceToken, Notification
from app.models.user import User
from app.schemas.base import APIResponse
from app.schemas.notification import (
    DeviceTokenRegisterRequest,
    DeviceTokenResponse,
    DeviceTokenUnregisterRequest,
    NotificationListResponse,
    NotificationResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdateRequest,
    NotificationUnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# === Notification Endpoints ===


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get notifications",
    description="Get notifications for current user with pagination and filtering",
)
async def get_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get notifications for current user.

    - Returns paginated list of notifications
    - Can filter by unread only
    - Sorted by created_at DESC (most recent first)
    """
    # Build base query
    query = select(Notification).where(Notification.user_id == current_user.id)

    # Filter by unread if requested
    if unread_only:
        query = query.where(Notification.is_read == False)  # noqa: E712

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    notifications = result.scalars().all()

    # Convert to response models
    notification_list = [NotificationResponse.model_validate(n) for n in notifications]

    return NotificationListResponse(
        data=notification_list,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(page * per_page) < total,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count",
    description="Get count of unread notifications for current user",
)
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get unread notification count.

    - Returns count of unread notifications
    - Used for notification badge display
    """
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
    )
    unread_count = result.scalar()

    return NotificationUnreadCountResponse(unread_count=unread_count)


@router.patch(
    "/{notification_id}/read",
    response_model=APIResponse[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark notification as read",
    description="Mark a specific notification as read",
)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark notification as read.

    - Sets is_read = True
    - Sets read_at timestamp
    """
    # Get notification
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # Mark as read
    notification.is_read = True
    notification.read_at = datetime.utcnow()

    await db.commit()
    await db.refresh(notification)

    return APIResponse(data=NotificationResponse.model_validate(notification))


@router.patch(
    "/read-all",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
    description="Mark all notifications as read for current user",
)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark all notifications as read.

    - Sets is_read = True for all unread notifications
    - Sets read_at timestamp
    """
    # Update all unread notifications
    from sqlalchemy import update

    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True, read_at=datetime.utcnow())
    )

    await db.execute(stmt)
    await db.commit()

    return APIResponse(data={"message": "All notifications marked as read"})


@router.delete(
    "/{notification_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete notification",
    description="Delete a specific notification",
)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete notification.

    - Removes notification from database
    """
    # Get notification
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    # Delete notification
    await db.delete(notification)
    await db.commit()

    return APIResponse(data={"message": "Notification deleted successfully"})


# === Device Token Endpoints ===


@router.post(
    "/register-device",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Register device for push notifications",
    description="Register FCM device token for push notifications",
)
async def register_device(
    token_data: DeviceTokenRegisterRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register device for push notifications.

    - Creates or updates device token
    - Associates FCM token with user
    - Replaces existing token if device_id already exists
    """
    # Check if device already registered
    result = await db.execute(select(DeviceToken).where(DeviceToken.device_id == token_data.device_id))
    existing_token = result.scalar_one_or_none()

    if existing_token:
        # Update existing token
        existing_token.fcm_token = token_data.fcm_token
        existing_token.platform = token_data.platform
        existing_token.user_id = current_user.id  # Update user if device switched accounts
        await db.commit()
    else:
        # Create new device token
        device_token = DeviceToken(
            user_id=current_user.id,
            fcm_token=token_data.fcm_token,
            platform=token_data.platform,
            device_id=token_data.device_id,
        )
        db.add(device_token)
        await db.commit()

    return DeviceTokenResponse(message="Device registered successfully")


@router.delete(
    "/unregister-device",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Unregister device",
    description="Remove device token (e.g., on logout)",
)
async def unregister_device(
    unregister_data: DeviceTokenUnregisterRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unregister device.

    - Removes device token from database
    - User will no longer receive push notifications on this device
    """
    # Find device token
    result = await db.execute(
        select(DeviceToken).where(
            DeviceToken.device_id == unregister_data.device_id,
            DeviceToken.user_id == current_user.id,
        )
    )
    device_token = result.scalar_one_or_none()

    if not device_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device token not found",
        )

    # Delete device token
    await db.delete(device_token)
    await db.commit()

    return APIResponse(data={"message": "Device unregistered successfully"})


# === Notification Settings Endpoints ===


@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get notification settings",
    description="Get notification preferences for current user",
)
async def get_notification_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get notification settings.

    Returns user's notification preferences.
    TODO: Implement notification_settings table or store in user metadata.
    """
    # TODO: Implement notification settings storage
    # For now, return default settings
    default_settings = {
        "push_enabled": True,
        "email_enabled": True,
        "notification_types": {
            "new_follower": True,
            "new_message": True,
            "new_offer": True,
            "offer_accepted": True,
            "offer_declined": True,
            "product_sold": True,
            "transaction_completed": True,
            "review_received": True,
            "stream_started": True,
            "price_drop": True,
            "verification_approved": True,
            "verification_rejected": True,
        },
    }

    return NotificationSettingsResponse(data=default_settings)


@router.patch(
    "/settings",
    response_model=NotificationSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update notification settings",
    description="Update notification preferences",
)
async def update_notification_settings(
    settings_data: NotificationSettingsUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update notification settings.

    Updates user's notification preferences.
    TODO: Implement notification_settings table or store in user metadata.
    """
    # TODO: Implement notification settings storage
    # For now, return the settings that were sent
    updated_settings = {
        "push_enabled": settings_data.push_enabled
        if settings_data.push_enabled is not None
        else True,
        "email_enabled": settings_data.email_enabled
        if settings_data.email_enabled is not None
        else True,
        "notification_types": settings_data.notification_types or {},
    }

    return NotificationSettingsResponse(data=updated_settings)
