from datetime import datetime
from enum import Enum
from uuid import UUID as UUIDType

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VerificationType(str, Enum):
    EMIRATES_ID = "emirates_id"
    TRADE_LICENSE = "trade_license"
    BOTH = "both"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Verification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "verifications"
    __table_args__ = (
        Index("ix_verifications_user_id", "user_id"),
        Index("ix_verifications_status", "status"),
    )

    user_id: Mapped[UUIDType] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    verification_type: Mapped[VerificationType] = mapped_column(
        SqlEnum(VerificationType, name="verification_type"),
        nullable=False,
    )
    status: Mapped[VerificationStatus] = mapped_column(
        SqlEnum(VerificationStatus, name="verification_status"),
        default=VerificationStatus.PENDING,
        nullable=False,
    )
    emirates_id_number: Mapped[str | None] = mapped_column(String(128))
    emirates_id_front_image_url: Mapped[str | None] = mapped_column(String(1024))
    emirates_id_back_image_url: Mapped[str | None] = mapped_column(String(1024))
    trade_license_number: Mapped[str | None] = mapped_column(String(128))
    trade_license_document_url: Mapped[str | None] = mapped_column(String(1024))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUIDType | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    rejection_reason: Mapped[str | None] = mapped_column(Text())

    user: Mapped["User"] = relationship("User", back_populates="verification", foreign_keys=[user_id])
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by])
