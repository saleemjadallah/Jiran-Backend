"""
Block model for users blocking other users
"""
from uuid import UUID as UUIDType

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class Block(UUIDPrimaryKeyMixin, Base):
    """
    User blocking another user.

    When user A blocks user B:
    - B cannot message A
    - B cannot view A's products
    - B cannot interact with A's content
    """
    __tablename__ = "blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_blocker_blocked"),
        Index("ix_blocks_blocker_id", "blocker_id"),
        Index("ix_blocks_blocked_id", "blocked_id"),
    )

    # User who initiated the block
    blocker_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # User who is blocked
    blocked_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # When the block was created
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    blocker: Mapped["User"] = relationship(
        "User",
        foreign_keys=[blocker_id],
        back_populates="blocking",
    )
    blocked: Mapped["User"] = relationship(
        "User",
        foreign_keys=[blocked_id],
        back_populates="blocked_by",
    )
