from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import EmailStr, Field, model_validator

from app.models.product import ProductCategory
from app.models.user import UserRole
from app.schemas.base import ORMBaseModel


class UserLocation(ORMBaseModel):
    latitude: float = Field(..., ge=-90, le=90, examples=[25.2048])
    longitude: float = Field(..., ge=-180, le=180, examples=[55.2708])
    neighborhood: str | None = Field(default=None, examples=["Dubai Marina"])
    building_name: str | None = Field(default=None, examples=["Marina Heights Tower"])


class UserBase(ORMBaseModel):
    id: UUID = Field(..., examples=["c14f0a9d-3d1a-4c19-9a6e-9ce67817b34a"])
    username: str = Field(..., examples=["dubai_style"])
    full_name: str = Field(..., examples=["Layla Al Falasi"])
    role: UserRole = Field(default=UserRole.BUYER)
    avatar_url: str | None = Field(default=None, examples=["https://cdn.soukloop.com/avatars/layla.png"])
    bio: str | None = Field(default=None, max_length=280)
    location: UserLocation | None = None
    neighborhood: str | None = Field(default=None)
    building_name: str | None = Field(default=None)


class UserCreate(ORMBaseModel):
    email: EmailStr = Field(..., examples=["user@soukloop.com"])
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    phone: str = Field(..., min_length=8, max_length=20)
    full_name: str = Field(..., max_length=255)
    role: UserRole = UserRole.BUYER
    location: UserLocation | None = None


class UserUpdate(ORMBaseModel):
    full_name: str | None = Field(default=None)
    avatar_url: str | None = Field(default=None)
    bio: str | None = Field(default=None, max_length=280)
    username: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    location: UserLocation | None = None
    favorite_categories: list[ProductCategory] | None = Field(default=None)

    @model_validator(mode="after")
    def validate_non_empty(self) -> Self:
        if not any(getattr(self, field) is not None for field in ("full_name", "avatar_url", "bio", "username", "phone", "location", "favorite_categories")):
            raise ValueError("At least one field must be provided for update")
        return self


class UserStats(ORMBaseModel):
    followers_count: int = Field(default=0, ge=0)
    following_count: int = Field(default=0, ge=0)
    products_count: int = Field(default=0, ge=0)
    rating: float | None = Field(default=None, ge=0, le=5)


class UserResponse(UserBase):
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    is_verified: bool = Field(default=False)
    stats: UserStats | None = Field(default=None)


class UserDetailResponse(UserResponse):
    email: EmailStr = Field(...)
    phone: str = Field(...)
    is_active: bool = Field(default=True)
    stripe_customer_id: str | None = Field(default=None)
    stripe_connect_account_id: str | None = Field(default=None)

