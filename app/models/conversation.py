"""Conversation model for peer-to-peer messaging.

This module defines the Conversation model with support for:
- Direct messaging between buyers and sellers
- Product-specific conversations
- Unread message tracking per user
- Archive functionality per user
- Circular dependency resolution with Message model
"""
from datetime import datetime
from uuid import UUID as UUIDType

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Conversation model for direct messaging between users.

    Inherits:
        - UUIDPrimaryKeyMixin: Provides UUID primary key (id)
        - TimestampMixin: Provides created_at and updated_at timestamps
        - Base: SQLAlchemy declarative base

    Indexes:
        - buyer_id + seller_id (composite index)
        - product_id (indexed)

    Circular Dependency Resolution:
        This model has a circular dependency with Message:
        - Conversation references Message.last_message_id
        - Message references Conversation.conversation_id

        Resolution:
        - last_message_id uses `use_alter=True` to defer FK creation
        - last_message relationship uses `post_update=True`
        - This allows both tables to be created without FK conflicts
    """

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_buyer_seller", "buyer_id", "seller_id"),
        Index("ix_conversations_product", "product_id"),
    )

    # Participants
    buyer_id: Mapped[UUIDType] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller_id: Mapped[UUIDType] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Optional product context
    product_id: Mapped[UUIDType | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))

    # Last message tracking (circular dependency with Message)
    last_message_id: Mapped[UUIDType | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL", use_alter=True, name="fk_conversations_last_message")
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Unread counts per user
    unread_count_buyer: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unread_count_seller: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Archive status per user
    is_archived_buyer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived_seller: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    buyer: Mapped["User"] = relationship(
        "User",
        back_populates="conversations_as_buyer",
        foreign_keys=[buyer_id],
    )
    seller: Mapped["User"] = relationship(
        "User",
        back_populates="conversations_as_seller",
        foreign_keys=[seller_id],
    )
    product: Mapped["Product | None"] = relationship("Product", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        foreign_keys="Message.conversation_id",
        cascade="all, delete-orphan",
    )
    last_message: Mapped["Message | None"] = relationship(
        "Message",
        foreign_keys=[last_message_id],
        post_update=True,  # Required for circular dependency
    )
    offers: Mapped[list["Offer"]] = relationship(
        "Offer",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Conversation {self.id} buyer={self.buyer_id} seller={self.seller_id}>"
