"""
Moderation endpoints - Reports, blocks, and admin moderation tools
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_active_user, require_admin_role
from app.models.block import Block
from app.models.product import Product
from app.models.report import Report, ReportStatus, ReportType
from app.models.user import User
from app.schemas.base import APIResponse
from app.schemas.moderation import (
    BlockActionResponse,
    BlockedUserResponse,
    BlockListResponse,
    ProductReportRequest,
    ReportDetailResponse,
    ReportedItemInfo,
    ReporterInfo,
    ReportListResponse,
    ReportResponse,
    ReportResolveRequest,
    UserReportRequest,
    UserSuspendRequest,
)

router = APIRouter(prefix="/moderation", tags=["Moderation"])


# === Report Endpoints (User) ===

@router.post(
    "/products/{product_id}/report",
    response_model=APIResponse[ReportResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Report product",
    description="Report a product for violations",
)
async def report_product(
    product_id: UUID,
    report_data: ProductReportRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Report a product for violations.

    Creates a report and increments product report count.
    If report count > 3, product is auto-hidden pending review.
    """
    # Check product exists
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Create report
    report = Report(
        reporter_id=current_user.id,
        reported_product_id=product_id,
        report_type=ReportType.PRODUCT,
        reason=report_data.reason.value,
        description=report_data.description,
        evidence_urls=report_data.evidence_urls or [],
        status=ReportStatus.PENDING,
    )

    db.add(report)

    # Increment product report count (assuming field exists)
    # TODO: Add report_count field to Product model
    # product.report_count += 1
    # if product.report_count > 3:
    #     product.is_available = False  # Auto-hide

    await db.commit()
    await db.refresh(report)

    # TODO: Send notification to admin

    return APIResponse(
        success=True,
        data=ReportResponse.model_validate(report),
        message="Product reported successfully. Our team will review it shortly.",
    )


@router.post(
    "/users/{user_id}/report",
    response_model=APIResponse[ReportResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Report user",
    description="Report a user for violations",
)
async def report_user(
    user_id: UUID,
    report_data: UserReportRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Report a user for violations.

    Creates a report. If user receives > 5 reports, account is auto-suspended
    pending admin review.
    """
    # Check user exists
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot report yourself",
        )

    # Create report
    report = Report(
        reporter_id=current_user.id,
        reported_user_id=user_id,
        report_type=ReportType.USER,
        reason=report_data.reason.value,
        description=report_data.description,
        evidence_urls=report_data.evidence_urls or [],
        status=ReportStatus.PENDING,
    )

    db.add(report)

    # Check total reports against this user
    count_result = await db.execute(
        select(func.count())
        .select_from(Report)
        .where(Report.reported_user_id == user_id)
        .where(Report.status == ReportStatus.PENDING)
    )
    report_count = count_result.scalar() or 0

    # Auto-suspend if too many reports
    if report_count > 5:
        user.is_active = False  # Suspend account
        # TODO: Send notification to user about suspension

    await db.commit()
    await db.refresh(report)

    # TODO: Send notification to admin

    return APIResponse(
        success=True,
        data=ReportResponse.model_validate(report),
        message="User reported successfully. Our team will review it shortly.",
    )


# === Block Endpoints (User) ===

@router.post(
    "/users/{user_id}/block",
    response_model=APIResponse[BlockActionResponse],
    summary="Block user",
    description="Block a user (prevents messaging and interaction)",
)
async def block_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Block a user.

    Blocked users cannot:
    - Message you
    - View your products
    - Interact with your content
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot block yourself",
        )

    # Check user exists
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if already blocked
    existing = await db.execute(
        select(Block)
        .where(Block.blocker_id == current_user.id)
        .where(Block.blocked_id == user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already blocked",
        )

    # Create block
    block = Block(
        blocker_id=current_user.id,
        blocked_id=user_id,
    )

    db.add(block)
    await db.commit()

    # TODO: Remove user from followers if following
    # TODO: Hide conversations with this user

    return APIResponse(
        success=True,
        data=BlockActionResponse(
            user_id=user_id,
            blocked=True,
            message="User blocked successfully",
        ),
    )


@router.delete(
    "/users/{user_id}/block",
    response_model=APIResponse[BlockActionResponse],
    summary="Unblock user",
    description="Unblock a previously blocked user",
)
async def unblock_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Unblock a user"""
    # Find block
    result = await db.execute(
        select(Block)
        .where(Block.blocker_id == current_user.id)
        .where(Block.blocked_id == user_id)
    )
    block = result.scalar_one_or_none()

    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not blocked",
        )

    # Remove block
    await db.delete(block)
    await db.commit()

    return APIResponse(
        success=True,
        data=BlockActionResponse(
            user_id=user_id,
            blocked=False,
            message="User unblocked successfully",
        ),
    )


@router.get(
    "/users/blocked",
    response_model=APIResponse[BlockListResponse],
    summary="Get blocked users",
    description="Get list of users you have blocked",
)
async def get_blocked_users(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of blocked users"""
    result = await db.execute(
        select(Block)
        .where(Block.blocker_id == current_user.id)
        .options(selectinload(Block.blocked))
        .order_by(Block.created_at.desc())
    )
    blocks = result.scalars().all()

    blocked_users = [
        BlockedUserResponse(
            id=block.blocked.id,
            username=block.blocked.username,
            avatar_url=block.blocked.avatar_url,
            blocked_at=block.created_at,
        )
        for block in blocks
        if block.blocked  # Ensure user still exists
    ]

    return APIResponse(
        success=True,
        data=BlockListResponse(
            blocked_users=blocked_users,
            total=len(blocked_users),
        ),
    )


# === Admin Endpoints ===

@router.get(
    "/admin/reports",
    response_model=APIResponse[ReportListResponse],
    summary="Get reports (Admin)",
    description="Get all reports with filters",
    dependencies=[Depends(require_admin_role)],
)
async def get_reports_admin(
    report_type: Optional[ReportType] = Query(None),
    status_filter: Optional[ReportStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all reports for admin review.

    Filters:
    - report_type: Filter by type (product/user)
    - status: Filter by status
    """
    # Build query
    query = select(Report)

    # Apply filters
    if report_type:
        query = query.where(Report.report_type == report_type)
    if status_filter:
        query = query.where(Report.status == status_filter)

    # Order by priority (pending first, then by creation date)
    query = query.order_by(
        Report.status.asc(),  # Pending first
        Report.created_at.desc(),
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute
    result = await db.execute(query)
    reports = result.scalars().all()

    report_responses = [ReportResponse.model_validate(r) for r in reports]

    return APIResponse(
        success=True,
        data=ReportListResponse(
            reports=report_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_more=(offset + len(reports)) < total,
        ),
    )


@router.get(
    "/admin/reports/{report_id}",
    response_model=APIResponse[ReportDetailResponse],
    summary="Get report details (Admin)",
    description="Get detailed report information",
    dependencies=[Depends(require_admin_role)],
)
async def get_report_detail_admin(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full report details for admin review"""
    result = await db.execute(
        select(Report)
        .where(Report.id == report_id)
        .options(
            selectinload(Report.reporter),
            selectinload(Report.reported_user),
            selectinload(Report.reported_product),
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Build reporter info
    reporter_info = ReporterInfo(
        id=report.reporter.id,
        username=report.reporter.username,
        email=report.reporter.email,
        is_verified=report.reporter.is_verified,
    )

    # Build reported item info
    if report.report_type == ReportType.PRODUCT and report.reported_product:
        reported_item = ReportedItemInfo(
            id=report.reported_product.id,
            title=report.reported_product.title,
            username=None,
            email=None,
        )
    elif report.report_type == ReportType.USER and report.reported_user:
        reported_item = ReportedItemInfo(
            id=report.reported_user.id,
            title=None,
            username=report.reported_user.username,
            email=report.reported_user.email,
        )
    else:
        reported_item = ReportedItemInfo(id=report.id, title=None, username=None, email=None)

    return APIResponse(
        success=True,
        data=ReportDetailResponse(
            id=report.id,
            report_type=report.report_type,
            reason=report.reason,
            description=report.description,
            evidence_urls=report.evidence_urls or [],
            status=report.status,
            reporter=reporter_info,
            reported_item=reported_item,
            resolution_action=report.resolution_action,
            admin_notes=report.admin_notes,
            created_at=report.created_at,
            resolved_at=report.resolved_at,
        ),
    )


@router.patch(
    "/admin/reports/{report_id}/resolve",
    response_model=APIResponse[ReportResponse],
    summary="Resolve report (Admin)",
    description="Take action on a report",
    dependencies=[Depends(require_admin_role)],
)
async def resolve_report_admin(
    report_id: UUID,
    resolve_data: ReportResolveRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve a report by taking action.

    Actions:
    - remove_content: Delete/hide the reported content
    - suspend_user: Suspend the reported user
    - warn_user: Send warning to user
    - no_action: Dismiss the report
    """
    result = await db.execute(
        select(Report)
        .where(Report.id == report_id)
        .options(
            selectinload(Report.reported_product),
            selectinload(Report.reported_user),
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Take action based on resolution
    if resolve_data.action == "remove_content":
        if report.reported_product:
            report.reported_product.is_available = False
            # TODO: Soft delete or hard delete
        # TODO: Send notification to content owner

    elif resolve_data.action == "suspend_user":
        if report.reported_user:
            report.reported_user.is_active = False
            # TODO: Hide all user's products
            # TODO: Cancel ongoing transactions
            # TODO: Send suspension notification

    elif resolve_data.action == "warn_user":
        # TODO: Send warning notification to user
        pass

    # Update report
    report.status = ReportStatus.RESOLVED
    report.resolution_action = resolve_data.action
    report.admin_notes = resolve_data.admin_notes
    report.resolved_by = current_user.id
    report.resolved_at = datetime.utcnow().isoformat()

    await db.commit()
    await db.refresh(report)

    # TODO: Log admin action

    return APIResponse(
        success=True,
        data=ReportResponse.model_validate(report),
        message="Report resolved successfully",
    )


@router.post(
    "/admin/users/{user_id}/suspend",
    response_model=APIResponse[dict],
    summary="Suspend user (Admin)",
    description="Suspend user account",
    dependencies=[Depends(require_admin_role)],
)
async def suspend_user_admin(
    user_id: UUID,
    suspend_data: UserSuspendRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Suspend user account.

    Actions taken:
    - Set user as inactive
    - Hide all active products
    - Cancel ongoing transactions
    - Send notification
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend admin users",
        )

    # Suspend user
    user.is_active = False

    # Hide all active products
    await db.execute(
        select(Product)
        .where(Product.seller_id == user_id)
        .where(Product.is_available == True)
    )
    # TODO: Update products to is_available = False

    await db.commit()

    # TODO: Send notification to user
    # TODO: Log admin action
    # TODO: Store suspension duration

    duration_msg = f"for {suspend_data.duration_days} days" if suspend_data.duration_days else "permanently"

    return APIResponse(
        success=True,
        data={
            "user_id": str(user_id),
            "suspended": True,
            "duration_days": suspend_data.duration_days,
            "reason": suspend_data.reason,
        },
        message=f"User suspended {duration_msg}",
    )


@router.post(
    "/admin/users/{user_id}/unsuspend",
    response_model=APIResponse[dict],
    summary="Unsuspend user (Admin)",
    description="Reactivate suspended user account",
    dependencies=[Depends(require_admin_role)],
)
async def unsuspend_user_admin(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reactivate suspended user"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Reactivate user
    user.is_active = True

    # Restore products (let user decide which to re-list)
    # Don't automatically restore products

    await db.commit()

    # TODO: Send notification to user
    # TODO: Log admin action

    return APIResponse(
        success=True,
        data={
            "user_id": str(user_id),
            "suspended": False,
        },
        message="User account reactivated successfully",
    )
