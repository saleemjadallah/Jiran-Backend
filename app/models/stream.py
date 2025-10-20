from datetime import datetime
from enum import Enum
from uuid import UUID as UUIDType

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.product import ProductCategory


class StreamStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"


class StreamType(str, Enum):
    LIVE = "live"
    RECORDED = "recorded"


class Stream(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "streams"
    __table_args__ = (
        Index("ix_streams_user_id", "user_id"),
        Index("ix_streams_status", "status"),
        Index("ix_streams_category", "category"),
    )

    user_id: Mapped[UUIDType] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    category: Mapped[ProductCategory] = mapped_column(
        SqlEnum(ProductCategory, name="stream_category"),
        nullable=False,
    )
    status: Mapped[StreamStatus] = mapped_column(
        SqlEnum(StreamStatus, name="stream_status"),
        default=StreamStatus.SCHEDULED,
        nullable=False,
    )
    stream_type: Mapped[StreamType] = mapped_column(
        SqlEnum(StreamType, name="stream_type"),
        default=StreamType.LIVE,
        nullable=False,
    )
    rtmp_url: Mapped[str | None] = mapped_column(String(1024))
    stream_key: Mapped[str | None] = mapped_column(String(512))
    hls_url: Mapped[str | None] = mapped_column(String(1024))
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024))
    viewer_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Go Live flow fields (Phase 4)
    audience: Mapped[str] = mapped_column(
        String(20),
        default="everyone",
        nullable=False,
    )  # 'everyone', 'followers', 'neighborhood'

    estimated_duration: Mapped[int | None] = mapped_column(Integer)  # minutes

    notify_followers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_neighborhood: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    enable_chat: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_comments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    record_stream: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vod_url: Mapped[str | None] = mapped_column(String(1024))  # Video-on-demand URL

    # Analytics fields
    peak_viewers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_viewers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chat_messages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_watch_time: Mapped[int | None] = mapped_column(Integer)  # seconds

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="streams")
    stream_products: Mapped[list["StreamProduct"]] = relationship(
        "StreamProduct",
        back_populates="stream",
        cascade="all, delete-orphan",
    )
