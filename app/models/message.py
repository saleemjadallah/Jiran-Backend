from datetime import datetime
from enum import Enum
from uuid import UUID as UUIDType

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    OFFER = "offer"
    SYSTEM = "system"


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation", "conversation_id"),
        Index("ix_messages_sender", "sender_id"),
    )

    conversation_id: Mapped[UUIDType] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[UUIDType] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_type: Mapped[MessageType] = mapped_column(
        SqlEnum(MessageType, name="message_type"),
        default=MessageType.TEXT,
        nullable=False,
    )
    content: Mapped[str | None] = mapped_column(Text())
    image_urls: Mapped[list[str] | None] = mapped_column(JSONB)
    offer_data: Mapped[dict | None] = mapped_column(JSONB)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
        foreign_keys=[conversation_id]
    )
    sender: Mapped["User"] = relationship("User")
