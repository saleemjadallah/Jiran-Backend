"""Admin log model for tracking all admin actions"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin, Base
from app.models.user import User


class AdminLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Admin action log for audit trail.
    Tracks all administrative actions for accountability and audit purposes.
    """

    __tablename__ = "admin_logs"

    # Admin who performed the action
    admin_user_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Action details
    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    # Values: 'user_suspended', 'user_unsuspended', 'product_removed',
    # 'stream_ended', 'verification_approved', 'verification_rejected',
    # 'report_resolved', 'transaction_refunded', etc.

    # Target of the action
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )
    # Values: 'user', 'product', 'stream', 'transaction', 'verification', 'report'

    target_id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True
    )

    # Change tracking
    old_values: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )

    new_values: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True
    )

    # Reason for action
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Request metadata
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True
    )

    # Relationships
    admin_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[admin_user_id],
        lazy="joined"
    )

    def __repr__(self):
        return (
            f"<AdminLog(id={self.id}, admin={self.admin_user_id}, "
            f"action={self.action_type}, target={self.target_type}:{self.target_id})>"
        )
