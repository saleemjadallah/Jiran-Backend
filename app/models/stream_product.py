"""
StreamProduct Model

Junction table for many-to-many relationship between Streams and Products.

Includes product tag positioning (x, y coordinates for overlay) and
per-product analytics (clicks, views, inquiries, purchases).
"""

from uuid import UUID as UUIDType

from sqlalchemy import Float, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StreamProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Many-to-many relationship between Streams and Products.

    Tracks which products are showcased in a stream, with:
    - Tag positioning (x, y coordinates for video overlay)
    - Tag timestamp (when product appears in video)
    - Per-product analytics (clicks, views, inquiries, purchases)
    """

    __tablename__ = "stream_products"
    __table_args__ = (
        Index("ix_stream_products_stream", "stream_id"),
        Index("ix_stream_products_product", "product_id"),
    )

    stream_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("streams.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Product tag position (if tagged during stream)
    # Normalized coordinates (0-1) for responsive positioning
    x_position: Mapped[float | None] = mapped_column(Float)  # 0-1 normalized (horizontal)
    y_position: Mapped[float | None] = mapped_column(Float)  # 0-1 normalized (vertical)
    timestamp_seconds: Mapped[int | None] = mapped_column(Integer)  # When tagged in video

    # Analytics for this product in stream
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inquiries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    purchases: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    stream: Mapped["Stream"] = relationship("Stream", back_populates="stream_products")
    product: Mapped["Product"] = relationship("Product")
