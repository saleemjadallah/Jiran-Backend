"""Activity model for tracking user actions and feed.

This module defines the Activity model for:
- User activity feed (for followers)
- Personal activity history
- Achievement tracking
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, UUIDType


class ActivityType(str, Enum):
    """Types of activities that can be tracked."""

    # Streaming
    WENT_LIVE = "went_live"
    STREAM_ENDED = "stream_ended"

    # Products
    NEW_PRODUCT = "new_product"
    PRODUCT_SOLD = "product_sold"

    # Social
    NEW_FOLLOWER = "new_follower"
    REVIEW_RECEIVED = "review_received"

    # Achievements
    MILESTONE = "milestone"


class Activity(UUIDPrimaryKeyMixin, Base):
    """Activity model for tracking user actions.

    Stores activities for generating user feeds and tracking history.

    Inherits:
        - UUIDPrimaryKeyMixin: Provides UUID primary key (id)
        - Base: SQLAlchemy declarative base

    Indexes:
        - user_id (for fetching user activities)
        - created_at (for sorting by recency)
        - (user_id, created_at) composite (for efficient feed queries)
    """

    __tablename__ = "activities"

    # Foreign key
    user_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Activity type
    activity_type: Mapped[ActivityType] = mapped_column(
        SqlEnum(ActivityType, name="activity_type"),
        nullable=False,
    )

    # Related entities (optional foreign keys)
    related_product_id: Mapped[UUIDType | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
    )
    related_stream_id: Mapped[UUIDType | None] = mapped_column(
        ForeignKey("streams.id", ondelete="SET NULL"),
    )
    related_user_id: Mapped[UUIDType | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Additional metadata (JSON)
    # Can store: milestone details, achievement badges, custom messages, etc.
    # Note: Using 'meta_data' instead of 'metadata' (reserved word in SQLAlchemy)
    meta_data: Mapped[dict | None] = mapped_column(JSON)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default="func.now()",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="activities")
    related_product: Mapped["Product"] = relationship(
        "Product",
        foreign_keys=[related_product_id],
    )
    related_stream: Mapped["Stream"] = relationship(
        "Stream",
        foreign_keys=[related_stream_id],
    )
    related_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[related_user_id],
    )

    __table_args__ = (
        Index("ix_activities_user", "user_id"),
        Index("ix_activities_created", "created_at"),
        Index("ix_activities_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Activity {self.id} {self.activity_type} by {self.user_id}>"
