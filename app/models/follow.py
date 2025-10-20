"""Follow model for social connections.

This module defines the Follow model for tracking user relationships:
- Follower/following connections
- Mutual follow detection
- Social graph for recommendations
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, UUIDType


class Follow(UUIDPrimaryKeyMixin, Base):
    """Follow model for social connections between users.

    Represents a one-way follow relationship from follower to following.

    Inherits:
        - UUIDPrimaryKeyMixin: Provides UUID primary key (id)
        - Base: SQLAlchemy declarative base

    Indexes:
        - (follower_id, following_id) unique constraint
        - follower_id (for getting who a user follows)
        - following_id (for getting a user's followers)

    Relationships:
        - follower: The user who is following
        - following: The user being followed
    """

    __tablename__ = "follows"

    # Foreign keys
    follower_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    following_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Timestamp (created_at only, no updates needed)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default="func.now()",
    )

    # Relationships
    follower: Mapped["User"] = relationship(
        "User",
        foreign_keys=[follower_id],
        back_populates="following_relationships",
    )
    following: Mapped["User"] = relationship(
        "User",
        foreign_keys=[following_id],
        back_populates="follower_relationships",
    )

    __table_args__ = (
        # Unique constraint: a user can follow another user only once
        UniqueConstraint("follower_id", "following_id", name="uq_follower_following"),
        # Index for finding who a user follows
        Index("ix_follows_follower", "follower_id"),
        # Index for finding a user's followers
        Index("ix_follows_following", "following_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Follow {self.follower_id} -> {self.following_id}>"
