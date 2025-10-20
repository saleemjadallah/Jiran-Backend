"""Activity Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.activity import ActivityType


class ActivityBase(BaseModel):
    """Base activity schema with common fields."""

    activity_type: ActivityType
    meta_data: dict[str, Any] | None = None


class ActivityResponse(BaseModel):
    """Response schema for single activity."""

    id: str
    user_id: str
    activity_type: ActivityType
    related_product_id: str | None
    related_stream_id: str | None
    related_user_id: str | None
    meta_data: dict[str, Any] | None
    created_at: datetime

    # Populated from joins
    user: dict[str, Any] | None = None
    related_product: dict[str, Any] | None = None
    related_stream: dict[str, Any] | None = None
    related_user: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class ActivityFeedResponse(BaseModel):
    """Response schema for activity feed."""

    success: bool = True
    data: list[ActivityResponse]
    page: int
    per_page: int
    total: int
    has_more: bool


class PersonalActivityResponse(BaseModel):
    """Response schema for personal activity history."""

    success: bool = True
    data: list[ActivityResponse]
    page: int
    per_page: int
    total: int
    has_more: bool
