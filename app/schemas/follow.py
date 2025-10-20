"""Follow/Social Pydantic schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserProfileSummary(BaseModel):
    """Summary of user profile for follow lists."""

    id: str
    username: str
    full_name: str
    avatar_url: str | None
    is_verified: bool
    neighborhood: str | None
    follower_count: int
    following_count: int

    model_config = ConfigDict(from_attributes=True)


class FollowResponse(BaseModel):
    """Response schema for follow action."""

    success: bool = True
    message: str
    following: bool


class FollowerResponse(BaseModel):
    """Response schema for single follower."""

    user: UserProfileSummary
    followed_at: datetime
    is_mutual: bool  # True if current user also follows this follower

    model_config = ConfigDict(from_attributes=True)


class FollowerListResponse(BaseModel):
    """Response schema for follower list."""

    success: bool = True
    data: list[FollowerResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class FollowingResponse(BaseModel):
    """Response schema for single following."""

    user: UserProfileSummary
    followed_at: datetime
    follows_back: bool  # True if this user follows current user back

    model_config = ConfigDict(from_attributes=True)


class FollowingListResponse(BaseModel):
    """Response schema for following list."""

    success: bool = True
    data: list[FollowingResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class UserRelationshipResponse(BaseModel):
    """Response schema for user relationship."""

    success: bool = True
    data: dict[str, bool]


class RelationshipData(BaseModel):
    """Relationship data between two users."""

    following: bool  # Current user follows target user
    followed_by: bool  # Target user follows current user
    blocked: bool  # Current user blocked target user
    blocked_by: bool  # Target user blocked current user
    can_message: bool  # Can current user message target user

    model_config = ConfigDict(from_attributes=True)
