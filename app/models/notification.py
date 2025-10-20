"""Notification models for push notifications and in-app alerts.

This module defines models for:
- Notifications: In-app and push notifications
- DeviceTokens: FCM tokens for push notification delivery
- NotificationSettings: User preferences for notifications
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class NotificationType(str, Enum):
    """Types of notifications that can be sent."""

    # Social
    NEW_FOLLOWER = "new_follower"

    # Messaging
    NEW_MESSAGE = "new_message"

    # Offers & Transactions
    NEW_OFFER = "new_offer"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    OFFER_COUNTERED = "offer_countered"

    # Sales & Products
    PRODUCT_SOLD = "product_sold"
    TRANSACTION_COMPLETED = "transaction_completed"
    PRICE_DROP = "price_drop"

    # Reviews
    REVIEW_RECEIVED = "review_received"

    # Live Streaming
    STREAM_STARTED = "stream_started"
    STREAM_ENDED = "stream_ended"

    # Verification
    VERIFICATION_APPROVED = "verification_approved"
    VERIFICATION_REJECTED = "verification_rejected"

    # System
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class DevicePlatform(str, Enum):
    """Mobile device platforms."""

    IOS = "ios"
    ANDROID = "android"


class Notification(UUIDPrimaryKeyMixin, Base):
    """Notification model for in-app and push notifications.

    Stores notification history and read status for each user.

    Inherits:
        - UUIDPrimaryKeyMixin: Provides UUID primary key (id)
        - Base: SQLAlchemy declarative base

    Indexes:
        - user_id (for fetching user notifications)
        - (user_id, is_read) composite (for unread count)
        - created_at (for sorting by recency)
    """

    __tablename__ = "notifications"

    # Foreign key
    user_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Notification details
    notification_type: Mapped[NotificationType] = mapped_column(
        SqlEnum(NotificationType, name="notification_type"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Additional data (JSON payload for navigation, etc.)
    data: Mapped[dict | None] = mapped_column(JSON)

    # Read status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default="func.now()",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user", "user_id"),
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_created", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Notification {self.id} {self.notification_type} for {self.user_id}>"


class DeviceToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Device token model for push notification delivery.

    Stores FCM (Firebase Cloud Messaging) tokens for each user device.

    Inherits:
        - UUIDPrimaryKeyMixin: Provides UUID primary key (id)
        - TimestampMixin: Provides created_at and updated_at
        - Base: SQLAlchemy declarative base

    Indexes:
        - user_id (for fetching user devices)
        - device_id (unique, for device identification)
        - fcm_token (for token lookup)
    """

    __tablename__ = "device_tokens"

    # Foreign key
    user_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Device details
    fcm_token: Mapped[str] = mapped_column(String(512), nullable=False)
    platform: Mapped[DevicePlatform] = mapped_column(
        SqlEnum(DevicePlatform, name="device_platform"),
        nullable=False,
    )
    device_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="device_tokens")

    __table_args__ = (
        Index("ix_device_tokens_user", "user_id"),
        Index("ix_device_tokens_fcm_token", "fcm_token"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<DeviceToken {self.id} {self.platform} for {self.user_id}>"
