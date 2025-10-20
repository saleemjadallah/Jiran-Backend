from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID as UUIDType

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"


class Payout(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payouts"
    __table_args__ = (
        Index("ix_payouts_seller", "seller_id"),
        Index("ix_payouts_status", "status"),
        Index("ix_payouts_paid_at", "paid_at"),
    )

    seller_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="AED", nullable=False)
    platform_fee_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total platform fees from included transactions"
    )
    transaction_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of transactions in this payout"
    )
    status: Mapped[PayoutStatus] = mapped_column(
        SqlEnum(PayoutStatus, name="payout_status"),
        default=PayoutStatus.PENDING,
        nullable=False
    )
    stripe_payout_id: Mapped[str | None] = mapped_column(String(255))
    stripe_transfer_id: Mapped[str | None] = mapped_column(String(255))
    bank_account_last4: Mapped[str | None] = mapped_column(String(4))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    seller: Mapped["User"] = relationship("User", back_populates="payouts")
