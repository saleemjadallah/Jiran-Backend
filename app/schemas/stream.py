from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.product import ProductCategory
from app.models.stream import StreamStatus, StreamType
from app.schemas.base import ORMBaseModel
from app.schemas.user import UserResponse


class ProductTagPosition(ORMBaseModel):
    """Product tag position on video"""

    product_id: UUID = Field(..., examples=["7a6f65fa-2d4b-4f6f-a4b3-c9d5d8f92d51"])
    x: float = Field(..., ge=0.0, le=1.0, examples=[0.42], description="Normalized X coordinate (0-1)")
    y: float = Field(..., ge=0.0, le=1.0, examples=[0.63], description="Normalized Y coordinate (0-1)")
    timestamp_seconds: int | None = Field(None, description="When product appears in video")


class StreamViewer(ORMBaseModel):
    """Viewer information"""

    user_id: UUID = Field(...)
    username: str = Field(...)
    avatar_url: str | None = Field(default=None)
    joined_at: datetime = Field(...)


class StreamBase(ORMBaseModel):
    """Base stream schema"""

    title: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    category: str = Field(...)


class StreamCreate(ORMBaseModel):
    """
    Create stream schema (ENHANCED for Go Live flow)

    Used in Step 2: Product Selection of Go Live flow
    """

    title: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    category: str
    audience: Literal["everyone", "followers", "neighborhood"] = "everyone"
    estimated_duration: int = Field(30, ge=5, le=240, description="5 min to 4 hours")
    notify_followers: bool = True
    notify_neighborhood: bool = False
    enable_chat: bool = True
    enable_comments: bool = True
    record_stream: bool = True
    product_ids: list[str] = Field(default_factory=list, description="UUIDs of products to showcase")
    scheduled_at: datetime | None = None


class StreamUpdate(ORMBaseModel):
    """
    Update stream settings (Step 3: Stream Settings)
    """

    title: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    audience: Literal["everyone", "followers", "neighborhood"] | None = None
    estimated_duration: int | None = Field(None, ge=5, le=240)
    notify_followers: bool | None = None
    notify_neighborhood: bool | None = None
    enable_chat: bool | None = None
    enable_comments: bool | None = None
    record_stream: bool | None = None


class StreamResponse(ORMBaseModel):
    """Stream response with all details"""

    id: str
    user_id: str
    title: str
    description: str | None
    category: str
    status: StreamStatus
    stream_type: StreamType
    rtmp_url: str | None
    stream_key: str | None
    hls_url: str | None
    thumbnail_url: str | None
    viewer_count: int
    total_views: int
    duration_seconds: int | None
    started_at: datetime | None
    ended_at: datetime | None

    # Go Live fields
    audience: str
    estimated_duration: int | None
    notify_followers: bool
    notify_neighborhood: bool
    enable_chat: bool
    enable_comments: bool
    record_stream: bool
    vod_url: str | None

    # Analytics
    peak_viewers: int
    unique_viewers: int
    total_likes: int
    chat_messages_count: int
    average_watch_time: int | None

    created_at: datetime
    updated_at: datetime

    # Optional includes
    user: UserResponse | None = None


class GoLiveRequest(ORMBaseModel):
    """
    Go Live request (Step 5: After Countdown)
    """

    camera_ready: bool = Field(..., description="Camera setup complete")
    checklist_complete: bool = Field(..., description="Pre-live checklist verified")


class GoLiveResponse(ORMBaseModel):
    """
    Go Live response with RTMP credentials
    """

    stream_id: str
    status: str
    rtmp_url: str
    stream_key: str
    hls_url: str
    dash_url: str | None = None
    started_at: datetime
    notifications_sent: int  # Number of users notified


class StreamAnalytics(ORMBaseModel):
    """Comprehensive stream analytics"""

    stream_id: str
    basic_stats: dict
    engagement: dict
    products: list[dict]
    revenue: dict
    geography: dict

