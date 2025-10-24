from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import Field, PositiveInt, model_validator

from app.models.product import FeedType, ProductCategory, ProductCondition
from app.schemas.base import ORMBaseModel
from app.schemas.user import UserResponse


class ProductLocation(ORMBaseModel):
    latitude: float = Field(..., ge=-90, le=90, examples=[25.0808])
    longitude: float = Field(..., ge=-180, le=180, examples=[55.1398])
    neighborhood: str | None = Field(default=None, examples=["Dubai Marina"])
    building_name: str | None = Field(default=None, examples=["Marina Heights Tower"])


class ProductTag(ORMBaseModel):
    type: str = Field(..., examples=["urgency"], description="Tag category, e.g. lifestyle/urgency/event")
    value: str = Field(..., examples=["flash_sale"])
    label: str = Field(..., examples=["Flash Sale"])


class ProductBase(ORMBaseModel):
    id: UUID = Field(..., examples=["7a6f65fa-2d4b-4f6f-a4b3-c9d5d8f92d51"])
    title: str = Field(..., max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(..., ge=0, examples=[3500.0])
    original_price: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="AED", min_length=3, max_length=3)
    category: ProductCategory = Field(...)
    condition: ProductCondition = Field(...)
    feed_type: FeedType = Field(...)
    neighborhood: str | None = Field(default=None)
    is_available: bool = Field(default=True)
    view_count: int = Field(default=0, ge=0)
    like_count: int = Field(default=0, ge=0)
    image_urls: list[str] = Field(default_factory=list)
    video_url: str | None = Field(default=None)
    video_thumbnail_url: str | None = Field(default=None)
    tags: list[ProductTag] = Field(default_factory=list)
    sold_at: datetime | None = Field(default=None)


class ProductCreate(ORMBaseModel):
    title: str = Field(..., max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(..., gt=0)
    original_price: Decimal | None = Field(default=None, gt=0)
    currency: str = Field(default="AED", min_length=3, max_length=3)
    category: ProductCategory = Field(...)
    condition: ProductCondition = Field(default=ProductCondition.GOOD)
    feed_type: FeedType = Field(default=FeedType.COMMUNITY)
    location: ProductLocation | None = None  # Optional until Google Maps integration
    image_urls: list[str] = Field(default_factory=list)
    video_url: str | None = None
    video_thumbnail_url: str | None = None
    tags: list[ProductTag] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_media(self) -> Self:
        if not self.image_urls and not self.video_url:
            raise ValueError("At least one image or a video must be provided")
        return self


class ProductUpdate(ORMBaseModel):
    title: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, gt=0)
    original_price: Decimal | None = Field(default=None, gt=0)
    condition: ProductCondition | None = Field(default=None)
    feed_type: FeedType | None = Field(default=None)
    location: ProductLocation | None = None
    is_available: bool | None = Field(default=None)
    image_urls: list[str] | None = None
    video_url: str | None = None
    video_thumbnail_url: str | None = None
    tags: list[ProductTag] | None = None


class ProductResponse(ProductBase):
    seller: UserResponse
    location: ProductLocation | None = None
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)


class ProductDetailResponse(ProductResponse):
    related_products: list[UUID] = Field(default_factory=list)


class ProductFilter(ORMBaseModel):
    categories: list[ProductCategory] = Field(default_factory=list)
    feed_type: FeedType | None = Field(default=None)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    neighborhoods: list[str] = Field(default_factory=list)
    seller_ids: list[UUID] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    limit: PositiveInt = Field(default=20, le=100)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_price_range(self) -> Self:
        if self.min_price is not None and self.max_price is not None and self.max_price < self.min_price:
            raise ValueError("max_price must be greater than or equal to min_price")
        return self
