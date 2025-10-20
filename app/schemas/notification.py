"""Notification Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.notification import DevicePlatform, NotificationType


class NotificationBase(BaseModel):
    """Base notification schema with common fields."""

    notification_type: NotificationType
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    data: dict[str, Any] | None = None


class NotificationResponse(NotificationBase):
    """Response schema for notification."""

    id: str
    user_id: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Response schema for notification list."""

    success: bool = True
    data: list[NotificationResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class NotificationUnreadCountResponse(BaseModel):
    """Response schema for unread notification count."""

    success: bool = True
    unread_count: int


class MarkNotificationReadRequest(BaseModel):
    """Request schema for marking notification as read."""

    pass  # No fields needed, notification ID comes from URL


class DeviceTokenRegisterRequest(BaseModel):
    """Request schema for registering a device token."""

    fcm_token: str = Field(..., min_length=1, max_length=512)
    platform: DevicePlatform
    device_id: str = Field(..., min_length=1, max_length=255)

    @field_validator("fcm_token")
    @classmethod
    def validate_fcm_token(cls, v: str) -> str:
        """Validate FCM token format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("FCM token cannot be empty")
        return v.strip()

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        """Validate device ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Device ID cannot be empty")
        return v.strip()


class DeviceTokenResponse(BaseModel):
    """Response schema for device token."""

    success: bool = True
    message: str = "Device registered successfully"


class DeviceTokenUnregisterRequest(BaseModel):
    """Request schema for unregistering a device token."""

    device_id: str = Field(..., min_length=1, max_length=255)


class NotificationSettingsResponse(BaseModel):
    """Response schema for notification settings."""

    success: bool = True
    data: dict[str, Any]


class NotificationSettingsUpdateRequest(BaseModel):
    """Request schema for updating notification settings."""

    push_enabled: bool | None = None
    email_enabled: bool | None = None
    notification_types: dict[str, bool] | None = None

    @field_validator("notification_types")
    @classmethod
    def validate_notification_types(cls, v: dict[str, bool] | None) -> dict[str, bool] | None:
        """Validate notification types dictionary."""
        if v is None:
            return v

        # Validate that all keys are valid notification types
        valid_types = {nt.value for nt in NotificationType}
        for key in v.keys():
            if key not in valid_types:
                raise ValueError(f"Invalid notification type: {key}")

        return v
