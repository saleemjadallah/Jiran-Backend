"""Product model for marketplace listings.

This module defines the Product model with support for:
- Dual-feed architecture (Discover vs Community)
- 12 standard product categories aligned with Flutter frontend
- Geographic location with PostGIS (automatic GIST indexing)
- Media support (images, video, thumbnails)
- Engagement tracking (views, likes)
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID as UUIDType

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProductCategory(str, Enum):
    """Product category enumeration matching Flutter frontend categories.

    These 12 categories are standardized across the entire platform.
    See frontend/lib/core/constants/product_categories.dart for consistency.
    """

    TRADING_CARDS = "trading_cards"  # Pokémon, Yu-Gi-Oh!, Magic
    MENS_FASHION = "mens_fashion"  # Streetwear, apparel
    SNEAKERS = "sneakers"  # Limited editions & exclusives
    SPORTS_CARDS = "sports_cards"  # NBA, NFL, Soccer, Baseball
    COLLECTIBLES = "collectibles"  # Coins, money, rare items
    ELECTRONICS = "electronics"  # Gaming, audio, tech
    HOME_DECOR = "home_decor"  # Furniture, kitchen, home
    BEAUTY = "beauty"  # Cosmetics, skincare
    KIDS_BABY = "kids_baby"  # Toys, clothes, essentials
    FURNITURE = "furniture"  # Home furniture
    BOOKS = "books"  # Books, movies, media
    OTHER = "other"  # Miscellaneous


class ProductCondition(str, Enum):
    """Product condition enumeration."""

    NEW = "new"  # Brand new, unused
    LIKE_NEW = "like_new"  # Minimal use, excellent condition
    GOOD = "good"  # Some wear, fully functional
    FAIR = "fair"  # Visible wear, functional


class FeedType(str, Enum):
    """Feed type for dual-feed architecture.

    Discover: Professional sellers, higher fees (15% base), live streaming
    Community: Peer-to-peer, lower fees (5% base), local focus
    """

    DISCOVER = "discover"
    COMMUNITY = "community"


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Product model for marketplace listings.

    Inherits:
        - UUIDPrimaryKeyMixin: Provides UUID primary key (id)
        - TimestampMixin: Provides created_at and updated_at timestamps
        - Base: SQLAlchemy declarative base

    Indexes:
        - seller_id (indexed)
        - category + feed_type (composite index)
        - is_available (indexed)
        - location (GIST index, auto-created by GeoAlchemy2)

    Note:
        GeoAlchemy2 automatically creates a GIST spatial index on the 'location'
        column. Do not manually add it to __table_args__ to avoid duplicates.
    """

    __tablename__ = "products"
    __table_args__ = (Index("ix_products_category_feed", "category", "feed_type"),)

    # Seller relationship
    seller_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Product details
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())

    # Pricing
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    original_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="AED", nullable=False)

    # Classification
    category: Mapped[ProductCategory] = mapped_column(
        SqlEnum(ProductCategory, name="product_category"),
        default=ProductCategory.OTHER,
        nullable=False,
    )
    condition: Mapped[ProductCondition] = mapped_column(
        SqlEnum(ProductCondition, name="product_condition"),
        default=ProductCondition.GOOD,
        nullable=False,
    )
    feed_type: Mapped[FeedType] = mapped_column(
        SqlEnum(FeedType, name="feed_type"),
        default=FeedType.DISCOVER,
        nullable=False,
    )

    # Location (PostGIS with automatic GIST index)
    location: Mapped[str | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    neighborhood: Mapped[str | None] = mapped_column(String(255))

    # Availability and status
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Engagement metrics
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Media (JSONB for flexibility)
    image_urls: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(1024))
    video_thumbnail_url: Mapped[str | None] = mapped_column(String(1024))

    # Tags for search and categorization
    tags: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    seller: Mapped["User"] = relationship("User", back_populates="products")
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="product", cascade="all, delete")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="product", cascade="all, delete"
    )
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="product")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="product", cascade="all, delete")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Product {self.id} {self.title} ({self.feed_type.value})>"
