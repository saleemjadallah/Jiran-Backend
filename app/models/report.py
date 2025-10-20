"""
Report model for content and user moderation
"""
from enum import Enum
from uuid import UUID as UUIDType

from sqlalchemy import Enum as SqlEnum, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReportType(str, Enum):
    PRODUCT = "product"
    USER = "user"


class ProductReportReason(str, Enum):
    PROHIBITED_ITEM = "prohibited_item"
    FAKE_PRODUCT = "fake_product"
    OFFENSIVE_CONTENT = "offensive_content"
    SCAM = "scam"
    WRONG_CATEGORY = "wrong_category"
    MISLEADING_DESCRIPTION = "misleading_description"
    OTHER = "other"


class UserReportReason(str, Enum):
    HARASSMENT = "harassment"
    SPAM = "spam"
    FAKE_ACCOUNT = "fake_account"
    FRAUD = "fraud"
    INAPPROPRIATE_BEHAVIOR = "inappropriate_behavior"
    OTHER = "other"


class ReportStatus(str, Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ResolutionAction(str, Enum):
    REMOVE_CONTENT = "remove_content"
    SUSPEND_USER = "suspend_user"
    WARN_USER = "warn_user"
    NO_ACTION = "no_action"


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_reporter_id", "reporter_id"),
        Index("ix_reports_reported_user_id", "reported_user_id"),
        Index("ix_reports_reported_product_id", "reported_product_id"),
        Index("ix_reports_status", "status"),
        Index("ix_reports_type", "report_type"),
    )

    # Reporter
    reporter_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Reported entities (one of these will be set)
    reported_user_id: Mapped[UUIDType | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    reported_product_id: Mapped[UUIDType | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )

    # Report details
    report_type: Mapped[ReportType] = mapped_column(
        SqlEnum(ReportType, name="report_type"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(100), nullable=False)  # Stores enum value as string
    description: Mapped[str | None] = mapped_column(Text())
    evidence_urls: Mapped[list | None] = mapped_column(JSON)  # Array of image URLs

    # Status
    status: Mapped[ReportStatus] = mapped_column(
        SqlEnum(ReportStatus, name="report_status"),
        default=ReportStatus.PENDING,
        nullable=False,
    )

    # Resolution (admin action)
    resolved_by: Mapped[UUIDType | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolution_action: Mapped[ResolutionAction | None] = mapped_column(
        SqlEnum(ResolutionAction, name="resolution_action")
    )
    admin_notes: Mapped[str | None] = mapped_column(Text())
    resolved_at: Mapped[str | None] = mapped_column(String(100))  # ISO datetime string

    # Relationships
    reporter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[reporter_id],
        back_populates="reports_filed",
    )
    reported_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[reported_user_id],
        back_populates="reports_against",
    )
    reported_product: Mapped["Product | None"] = relationship(
        "Product",
        foreign_keys=[reported_product_id],
    )
    resolver: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[resolved_by],
    )
