"""User model for authentication and profiles.

This module defines the User model with support for:
- Email/phone/username authentication
- Role-based access (buyer, seller, both, admin)
- Geographic location with PostGIS (automatic GIST indexing)
- Stripe payment integration
- Identity verification status
"""
from datetime import datetime
from enum import Enum

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, Enum):
    """User role enumeration for access control."""

    BUYER = "buyer"
    SELLER = "seller"
    BOTH = "both"
    ADMIN = "admin"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User model for authentication and profile management.

    Inherits:
        - UUIDPrimaryKeyMixin: Provides UUID primary key (id)
        - TimestampMixin: Provides created_at and updated_at timestamps
        - Base: SQLAlchemy declarative base

    Indexes:
        - email (unique, indexed)
        - username (unique, indexed)
        - phone (unique, indexed)
        - location (GIST index, auto-created by GeoAlchemy2)

    Note:
        GeoAlchemy2 automatically creates a GIST spatial index on the 'location'
        column. Do not manually add it to __table_args__ to avoid duplicates.
    """

    __tablename__ = "users"

    # Authentication fields (unique + indexed)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile information
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    bio: Mapped[str | None] = mapped_column(Text())

    # Role and status
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role"), default=UserRole.BUYER, nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Location (PostGIS with automatic GIST index)
    location: Mapped[str | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326))
    neighborhood: Mapped[str | None] = mapped_column(String(255))
    building_name: Mapped[str | None] = mapped_column(String(255))

    # Activity tracking
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Payment integration
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_connect_account_id: Mapped[str | None] = mapped_column(String(255))

    # Social counts
    follower_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    following_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="seller",
        cascade="all, delete-orphan",
    )
    streams: Mapped[list["Stream"]] = relationship(
        "Stream",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    conversations_as_buyer: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="buyer",
        foreign_keys="Conversation.buyer_id",
        cascade="all, delete",
    )
    conversations_as_seller: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="seller",
        foreign_keys="Conversation.seller_id",
        cascade="all, delete",
    )
    offers_made: Mapped[list["Offer"]] = relationship(
        "Offer",
        back_populates="buyer",
        foreign_keys="Offer.buyer_id",
    )
    offers_received: Mapped[list["Offer"]] = relationship(
        "Offer",
        back_populates="seller",
        foreign_keys="Offer.seller_id",
    )
    transactions_bought: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="buyer",
        foreign_keys="Transaction.buyer_id",
    )
    transactions_sold: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="seller",
        foreign_keys="Transaction.seller_id",
    )
    payouts: Mapped[list["Payout"]] = relationship(
        "Payout",
        back_populates="seller",
        foreign_keys="Payout.seller_id",
    )
    verification: Mapped["Verification"] = relationship(
        "Verification",
        back_populates="user",
        foreign_keys="Verification.user_id",
        cascade="all, delete-orphan",
        uselist=False,
    )
    # Follow relationships
    follower_relationships: Mapped[list["Follow"]] = relationship(
        "Follow",
        foreign_keys="Follow.following_id",
        back_populates="following",
        cascade="all, delete-orphan",
    )
    following_relationships: Mapped[list["Follow"]] = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan",
    )
    # Notification relationships
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    device_tokens: Mapped[list["DeviceToken"]] = relationship(
        "DeviceToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    # Activity relationships
    activities: Mapped[list["Activity"]] = relationship(
        "Activity",
        foreign_keys="Activity.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.id} {self.email}>"
