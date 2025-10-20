"""
Verification schemas for request/response validation
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.verification import VerificationStatus, VerificationType


# === Request Schemas ===

class VerificationSubmitRequest(BaseModel):
    """Submit verification request"""
    verification_type: VerificationType = Field(..., description="Type of verification")
    emirates_id_number: Optional[str] = Field(None, description="Emirates ID number")
    emirates_id_front_image: Optional[str] = Field(None, description="Front image URL")
    emirates_id_back_image: Optional[str] = Field(None, description="Back image URL")
    trade_license_number: Optional[str] = Field(None, description="Trade license number")
    trade_license_document: Optional[str] = Field(None, description="Trade license document URL")

    class Config:
        json_schema_extra = {
            "example": {
                "verification_type": "emirates_id",
                "emirates_id_number": "784-1234-5678901-2",
                "emirates_id_front_image": "https://cdn.soukloop.com/verification/emirate_front.jpg",
                "emirates_id_back_image": "https://cdn.soukloop.com/verification/emirate_back.jpg"
            }
        }


class BusinessVerificationRequest(BaseModel):
    """Submit business verification request"""
    business_name: str = Field(..., min_length=2, max_length=200)
    trade_license_number: str = Field(..., min_length=3, max_length=100)
    trade_license_document: str = Field(..., description="Trade license document URL")
    business_latitude: float = Field(..., ge=-90, le=90)
    business_longitude: float = Field(..., ge=-180, le=180)

    class Config:
        json_schema_extra = {
            "example": {
                "business_name": "Dubai Tech Solutions LLC",
                "trade_license_number": "CN-1234567",
                "trade_license_document": "https://cdn.soukloop.com/verification/license.pdf",
                "business_latitude": 25.2048,
                "business_longitude": 55.2708
            }
        }


class VerificationApproveRequest(BaseModel):
    """Admin approval request"""
    admin_notes: Optional[str] = Field(None, max_length=1000)


class VerificationRejectRequest(BaseModel):
    """Admin rejection request"""
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for rejection")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Provided Emirates ID image is blurry and unreadable. Please re-submit with a clear photo."
            }
        }


# === Response Schemas ===

class VerificationStatusResponse(BaseModel):
    """Current user's verification status"""
    is_verified: bool
    status: VerificationStatus
    verification_type: Optional[VerificationType]
    submitted_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]

    class Config:
        from_attributes = True


class VerificationSubmitResponse(BaseModel):
    """Response after submitting verification"""
    verification_id: UUID
    status: VerificationStatus
    estimated_review_time: str
    submitted_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "verification_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "estimated_review_time": "24 hours",
                "submitted_at": "2025-10-18T14:00:00Z"
            }
        }


class VerificationCardDetails(BaseModel):
    """Detailed verification information (for card modal)"""
    completed_transactions: int
    rating: Optional[float]
    review_count: int
    badges: List[str]
    neighborhood: Optional[str]
    joined_date: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "completed_transactions": 47,
                "rating": 4.8,
                "review_count": 32,
                "badges": ["power_seller", "top_rated", "quick_responder"],
                "neighborhood": "Dubai Marina",
                "joined_date": "2024-01-10T00:00:00Z"
            }
        }


class VerificationCardResponse(BaseModel):
    """Airbnb-style verification card response (public)"""
    user_id: UUID
    name: str
    avatar_url: Optional[str]
    verified_since: Optional[datetime]
    is_verified: bool
    verification_type: Optional[VerificationType]
    trust_message: str
    details: Optional[VerificationCardDetails]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Ahmed Hassan",
                "avatar_url": "https://cdn.soukloop.com/avatars/user_123.jpg",
                "verified_since": "2024-06-15T00:00:00Z",
                "is_verified": True,
                "verification_type": "both",
                "trust_message": "Trust is the cornerstone of Souk Loop's community, and identity verification is part of how we build it.",
                "details": {
                    "completed_transactions": 47,
                    "rating": 4.8,
                    "review_count": 32,
                    "badges": ["power_seller", "top_rated", "quick_responder"],
                    "neighborhood": "Dubai Marina",
                    "joined_date": "2024-01-10T00:00:00Z"
                }
            }
        }


class VerificationAdminListItem(BaseModel):
    """Verification item for admin list"""
    verification_id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    verification_type: VerificationType
    status: VerificationStatus
    submitted_at: datetime
    emirates_id_front_image_url: Optional[str]
    emirates_id_back_image_url: Optional[str]
    trade_license_document_url: Optional[str]

    class Config:
        from_attributes = True


class VerificationAdminDetailResponse(BaseModel):
    """Detailed verification for admin review"""
    verification_id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    user_phone: Optional[str]
    verification_type: VerificationType
    status: VerificationStatus
    emirates_id_number: Optional[str]  # Decrypted for admin
    emirates_id_front_image_url: Optional[str]
    emirates_id_back_image_url: Optional[str]
    trade_license_number: Optional[str]
    trade_license_document_url: Optional[str]
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[UUID]
    rejection_reason: Optional[str]

    class Config:
        from_attributes = True
