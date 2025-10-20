from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID as UUIDType

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OfferStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    COUNTERED = "countered"


class Offer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "offers"
    __table_args__ = (
        Index("ix_offers_conversation", "conversation_id"),
        Index("ix_offers_product", "product_id"),
        Index("ix_offers_status", "status"),
    )

    conversation_id: Mapped[UUIDType] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[UUIDType] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    buyer_id: Mapped[UUIDType] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller_id: Mapped[UUIDType] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    offered_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    original_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="AED", nullable=False)
    status: Mapped[OfferStatus] = mapped_column(
        SqlEnum(OfferStatus, name="offer_status"),
        default=OfferStatus.PENDING,
        nullable=False,
    )
    counter_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    message: Mapped[str | None] = mapped_column(Text())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="offers")
    product: Mapped["Product"] = relationship("Product", back_populates="offers")
    buyer: Mapped["User"] = relationship("User", foreign_keys=[buyer_id], back_populates="offers_made")
    seller: Mapped["User"] = relationship("User", foreign_keys=[seller_id], back_populates="offers_received")
