"""
Review model for product and seller reviews
"""
from enum import Enum
from uuid import UUID as UUIDType

from sqlalchemy import Boolean, Enum as SqlEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReviewType(str, Enum):
    PRODUCT = "product"
    SELLER = "seller"


class Review(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        Index("ix_reviews_transaction_id", "transaction_id"),
        Index("ix_reviews_product_id", "product_id"),
        Index("ix_reviews_seller_id", "seller_id"),
        Index("ix_reviews_reviewer_id", "reviewer_id"),
        Index("ix_reviews_rating", "rating"),
    )

    # Foreign keys
    transaction_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    product_id: Mapped[UUIDType | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    seller_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Review details
    review_type: Mapped[ReviewType] = mapped_column(
        SqlEnum(ReviewType, name="review_type"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    review_text: Mapped[str | None] = mapped_column(Text())
    seller_response: Mapped[str | None] = mapped_column(Text())

    # Metadata
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=True)
    responded_at: Mapped[str | None] = mapped_column(String(100))  # datetime when seller responded

    # Relationships
    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="review")
    product: Mapped["Product | None"] = relationship("Product", back_populates="reviews")
    seller: Mapped["User"] = relationship("User", foreign_keys=[seller_id], back_populates="reviews_received")
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")
