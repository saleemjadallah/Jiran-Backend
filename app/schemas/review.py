"""
Review schemas for request/response validation
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.review import ReviewType


# === Request Schemas ===

class ReviewCreate(BaseModel):
    """Create new review"""
    transaction_id: UUID
    product_id: Optional[UUID] = None
    seller_id: UUID
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    review_text: Optional[str] = Field(None, max_length=500, description="Review text (optional)")
    review_type: ReviewType = Field(..., description="Type of review (product or seller)")

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                "product_id": "650e8400-e29b-41d4-a716-446655440001",
                "seller_id": "750e8400-e29b-41d4-a716-446655440002",
                "rating": 5,
                "review_text": "Great quality and fast delivery! Exactly as described.",
                "review_type": "seller"
            }
        }


class ReviewUpdate(BaseModel):
    """Update existing review"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    review_text: Optional[str] = Field(None, max_length=500)

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v is not None and not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class SellerResponseCreate(BaseModel):
    """Seller response to review"""
    response_text: str = Field(..., min_length=1, max_length=300, description="Seller's response")

    class Config:
        json_schema_extra = {
            "example": {
                "response_text": "Thank you for your kind words! We're glad you're happy with your purchase."
            }
        }


# === Response Schemas ===

class ReviewerInfo(BaseModel):
    """Reviewer information (public)"""
    id: UUID
    username: str
    avatar_url: Optional[str]
    is_verified: bool

    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    """Review response"""
    id: UUID
    transaction_id: UUID
    product_id: Optional[UUID]
    seller_id: UUID
    reviewer_id: UUID
    review_type: ReviewType
    rating: int
    review_text: Optional[str]
    seller_response: Optional[str]
    helpful_count: int
    is_verified_purchase: bool
    responded_at: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Nested objects
    reviewer: Optional[ReviewerInfo] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "850e8400-e29b-41d4-a716-446655440003",
                "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                "product_id": "650e8400-e29b-41d4-a716-446655440001",
                "seller_id": "750e8400-e29b-41d4-a716-446655440002",
                "reviewer_id": "950e8400-e29b-41d4-a716-446655440004",
                "review_type": "seller",
                "rating": 5,
                "review_text": "Great quality and fast delivery!",
                "seller_response": "Thank you for your kind words!",
                "helpful_count": 12,
                "is_verified_purchase": True,
                "responded_at": "2025-10-18T15:00:00Z",
                "created_at": "2025-10-17T14:00:00Z",
                "updated_at": "2025-10-18T15:00:00Z",
                "reviewer": {
                    "id": "950e8400-e29b-41d4-a716-446655440004",
                    "username": "john_doe",
                    "avatar_url": "https://cdn.soukloop.com/avatars/john.jpg",
                    "is_verified": True
                }
            }
        }


class RatingBreakdown(BaseModel):
    """Rating breakdown by stars"""
    five_star: int = Field(0, alias="5")
    four_star: int = Field(0, alias="4")
    three_star: int = Field(0, alias="3")
    two_star: int = Field(0, alias="2")
    one_star: int = Field(0, alias="1")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "5": 89,
                "4": 28,
                "3": 7,
                "2": 3,
                "1": 1
            }
        }


class RatingSummaryResponse(BaseModel):
    """Rating summary for a seller"""
    average_rating: float
    total_reviews: int
    rating_breakdown: RatingBreakdown
    recent_reviews: list[ReviewResponse]

    class Config:
        json_schema_extra = {
            "example": {
                "average_rating": 4.7,
                "total_reviews": 128,
                "rating_breakdown": {
                    "5": 89,
                    "4": 28,
                    "3": 7,
                    "2": 3,
                    "1": 1
                },
                "recent_reviews": []
            }
        }


class ReviewListResponse(BaseModel):
    """Paginated review list response"""
    reviews: list[ReviewResponse]
    total: int
    page: int
    per_page: int
    has_more: bool

    class Config:
        json_schema_extra = {
            "example": {
                "reviews": [],
                "total": 45,
                "page": 1,
                "per_page": 20,
                "has_more": True
            }
        }
