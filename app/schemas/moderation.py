"""
Moderation schemas for reports and blocks
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.report import (
    ProductReportReason,
    ReportStatus,
    ReportType,
    ResolutionAction,
    UserReportReason,
)


# === Report Request Schemas ===

class ProductReportRequest(BaseModel):
    """Report a product"""
    reason: ProductReportReason
    description: Optional[str] = Field(None, max_length=1000)
    evidence_urls: Optional[List[str]] = Field(None, max_items=5)

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "fake_product",
                "description": "This product appears to be counterfeit based on the images",
                "evidence_urls": ["https://cdn.soukloop.com/evidence/img1.jpg"]
            }
        }


class UserReportRequest(BaseModel):
    """Report a user"""
    reason: UserReportReason
    description: Optional[str] = Field(None, max_length=1000)
    evidence_urls: Optional[List[str]] = Field(None, max_items=5)
    related_conversation_id: Optional[UUID] = None

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "harassment",
                "description": "User sent inappropriate messages in conversation",
                "related_conversation_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class ReportResolveRequest(BaseModel):
    """Admin resolve report"""
    action: ResolutionAction
    admin_notes: Optional[str] = Field(None, max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "action": "remove_content",
                "admin_notes": "Product violates community guidelines - removed"
            }
        }


class UserSuspendRequest(BaseModel):
    """Admin suspend user"""
    reason: str = Field(..., min_length=10, max_length=500)
    duration_days: Optional[int] = Field(None, ge=1, le=365, description="Duration in days, null for permanent")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Multiple violations of community guidelines",
                "duration_days": 30
            }
        }


# === Report Response Schemas ===

class ReportResponse(BaseModel):
    """Report response"""
    id: UUID
    reporter_id: UUID
    reported_user_id: Optional[UUID]
    reported_product_id: Optional[UUID]
    report_type: ReportType
    reason: str
    description: Optional[str]
    evidence_urls: Optional[List[str]]
    status: ReportStatus
    resolved_by: Optional[UUID]
    resolution_action: Optional[ResolutionAction]
    admin_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[str]

    class Config:
        from_attributes = True


class ReporterInfo(BaseModel):
    """Reporter information (for admin)"""
    id: UUID
    username: str
    email: str
    is_verified: bool


class ReportedItemInfo(BaseModel):
    """Information about reported item"""
    id: UUID
    title: Optional[str]  # For products
    username: Optional[str]  # For users
    email: Optional[str]  # For users


class ReportDetailResponse(BaseModel):
    """Detailed report for admin review"""
    id: UUID
    report_type: ReportType
    reason: str
    description: Optional[str]
    evidence_urls: Optional[List[str]]
    status: ReportStatus
    reporter: ReporterInfo
    reported_item: ReportedItemInfo
    resolution_action: Optional[ResolutionAction]
    admin_notes: Optional[str]
    created_at: datetime
    resolved_at: Optional[str]

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Paginated report list"""
    reports: List[ReportResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


# === Block Schemas ===

class BlockedUserResponse(BaseModel):
    """Blocked user information"""
    id: UUID
    username: str
    avatar_url: Optional[str]
    blocked_at: datetime

    class Config:
        from_attributes = True


class BlockListResponse(BaseModel):
    """List of blocked users"""
    blocked_users: List[BlockedUserResponse]
    total: int


class BlockActionResponse(BaseModel):
    """Response for block/unblock action"""
    user_id: UUID
    blocked: bool
    message: str
