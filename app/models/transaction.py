from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID as UUIDType

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.product import FeedType


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_buyer", "buyer_id"),
        Index("ix_transactions_seller", "seller_id"),
        Index("ix_transactions_product", "product_id"),
        Index("ix_transactions_status", "status"),
    )

    buyer_id: Mapped[UUIDType] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller_id: Mapped[UUIDType] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[UUIDType | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="AED", nullable=False)
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    seller_payout: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    feed_type: Mapped[FeedType] = mapped_column(SqlEnum(FeedType, name="transaction_feed_type"), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        SqlEnum(TransactionStatus, name="transaction_status"),
        default=TransactionStatus.PENDING,
        nullable=False,
    )
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255))
    stripe_charge_id: Mapped[str | None] = mapped_column(String(255))
    stripe_transfer_id: Mapped[str | None] = mapped_column(String(255))
    payment_method: Mapped[str | None] = mapped_column(String(50))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    buyer: Mapped["User"] = relationship("User", foreign_keys=[buyer_id], back_populates="transactions_bought")
    seller: Mapped["User"] = relationship("User", foreign_keys=[seller_id], back_populates="transactions_sold")
    product: Mapped["Product | None"] = relationship("Product", back_populates="transactions")
