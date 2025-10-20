"""
Verification endpoints - Emirates ID and Trade License verification system
"""
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_active_user, require_admin_role
from app.models.user import User
from app.models.verification import Verification, VerificationStatus, VerificationType
from app.schemas.base import APIResponse
from app.schemas.verification import (
    BusinessVerificationRequest,
    VerificationAdminDetailResponse,
    VerificationAdminListItem,
    VerificationApproveRequest,
    VerificationCardDetails,
    VerificationCardResponse,
    VerificationRejectRequest,
    VerificationStatusResponse,
    VerificationSubmitRequest,
    VerificationSubmitResponse,
)
from app.utils.encryption import decrypt_emirates_id, encrypt_emirates_id

router = APIRouter(prefix="/verification", tags=["Verification"])


# === User Endpoints ===

@router.post(
    "/submit",
    response_model=APIResponse[VerificationSubmitResponse],
    status_code=status.HTTP_200_OK,
    summary="Submit verification request",
    description="Submit Emirates ID and/or Trade License for verification",
)
async def submit_verification(
    request: VerificationSubmitRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit verification documents for review.

    - Uploads documents to secure storage
    - Encrypts Emirates ID number
    - Creates verification request with pending status
    - Sends notification to admin for review
    """
    # Check if user already has a verification
    existing = await db.execute(
        select(Verification).where(Verification.user_id == current_user.id)
    )
    existing_verification = existing.scalar_one_or_none()

    if existing_verification:
        if existing_verification.status == VerificationStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already verified",
            )
        elif existing_verification.status == VerificationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification request is already pending review",
            )

    # Encrypt Emirates ID number if provided
    encrypted_emirates_id = None
    if request.emirates_id_number:
        encrypted_emirates_id = encrypt_emirates_id(request.emirates_id_number)

    # Create or update verification
    if existing_verification:
        # Update existing (for re-submission after rejection)
        existing_verification.verification_type = request.verification_type
        existing_verification.status = VerificationStatus.PENDING
        existing_verification.emirates_id_number = encrypted_emirates_id
        existing_verification.emirates_id_front_image_url = request.emirates_id_front_image
        existing_verification.emirates_id_back_image_url = request.emirates_id_back_image
        existing_verification.trade_license_number = request.trade_license_number
        existing_verification.trade_license_document_url = request.trade_license_document
        existing_verification.submitted_at = datetime.utcnow()
        existing_verification.reviewed_at = None
        existing_verification.reviewed_by = None
        existing_verification.rejection_reason = None
        verification = existing_verification
    else:
        # Create new verification
        verification = Verification(
            user_id=current_user.id,
            verification_type=request.verification_type,
            status=VerificationStatus.PENDING,
            emirates_id_number=encrypted_emirates_id,
            emirates_id_front_image_url=request.emirates_id_front_image,
            emirates_id_back_image_url=request.emirates_id_back_image,
            trade_license_number=request.trade_license_number,
            trade_license_document_url=request.trade_license_document,
        )
        db.add(verification)

    await db.commit()
    await db.refresh(verification)

    # TODO: Send notification to admin for review
    # TODO: Send confirmation email to user

    return APIResponse(
        success=True,
        data=VerificationSubmitResponse(
            verification_id=verification.id,
            status=verification.status,
            estimated_review_time="24 hours",
            submitted_at=verification.submitted_at,
        ),
        message="Verification submitted successfully. We'll review your documents within 24 hours.",
    )


@router.get(
    "/status",
    response_model=APIResponse[VerificationStatusResponse],
    summary="Get verification status",
    description="Get current user's verification status",
)
async def get_verification_status(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get verification status for current user.

    Returns verification details without sensitive information.
    """
    result = await db.execute(
        select(Verification).where(Verification.user_id == current_user.id)
    )
    verification = result.scalar_one_or_none()

    if not verification:
        return APIResponse(
            success=True,
            data=VerificationStatusResponse(
                is_verified=False,
                status=VerificationStatus.PENDING,
                verification_type=None,
                submitted_at=None,
                reviewed_at=None,
                rejection_reason=None,
            ),
            message="No verification submitted yet",
        )

    return APIResponse(
        success=True,
        data=VerificationStatusResponse(
            is_verified=verification.status == VerificationStatus.APPROVED,
            status=verification.status,
            verification_type=verification.verification_type,
            submitted_at=verification.submitted_at,
            reviewed_at=verification.reviewed_at,
            rejection_reason=verification.rejection_reason,
        ),
    )


@router.get(
    "/{user_id}",
    response_model=APIResponse[VerificationCardResponse],
    summary="Get verification card",
    description="Get Airbnb-style verification card for any user (public endpoint)",
)
async def get_verification_card(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get verification card for any user.

    This is a public endpoint that returns verification information
    without sensitive data for display in user profiles.
    """
    # Get user with verification
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.verification))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Determine trust message based on role
    trust_message = "Member of the Souk Loop community"
    if user.verification and user.verification.status == VerificationStatus.APPROVED:
        if user.role == "seller":
            trust_message = "Trust is the cornerstone of Souk Loop's community, and identity verification is part of how we build it."
        elif user.role == "buyer":
            trust_message = "Verified buyers help create a trusted marketplace where everyone can shop with confidence."
        elif user.role == "both":
            trust_message = "Trusted member of our community, verified to both buy and sell with confidence."

    # Get user stats (placeholder - replace with actual queries)
    # TODO: Calculate actual stats from transactions and reviews
    details = VerificationCardDetails(
        completed_transactions=0,  # TODO: Count from transactions table
        rating=user.rating if hasattr(user, 'rating') else None,
        review_count=0,  # TODO: Count from reviews table
        badges=[],  # TODO: Calculate badges based on user performance
        neighborhood=user.neighborhood,
        joined_date=user.created_at,
    )

    verified_since = None
    verification_type = None
    if user.verification and user.verification.status == VerificationStatus.APPROVED:
        verified_since = user.verification.reviewed_at
        verification_type = user.verification.verification_type

    return APIResponse(
        success=True,
        data=VerificationCardResponse(
            user_id=user.id,
            name=user.full_name,
            avatar_url=user.avatar_url,
            verified_since=verified_since,
            is_verified=user.is_verified,
            verification_type=verification_type,
            trust_message=trust_message,
            details=details,
        ),
    )


@router.post(
    "/submit-business",
    response_model=APIResponse[VerificationSubmitResponse],
    status_code=status.HTTP_200_OK,
    summary="Submit business verification",
    description="Submit trade license for business verification",
)
async def submit_business_verification(
    request: BusinessVerificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit business/trade license verification.

    For sellers who want to verify their business.
    """
    # Check existing verification
    existing = await db.execute(
        select(Verification).where(Verification.user_id == current_user.id)
    )
    existing_verification = existing.scalar_one_or_none()

    if existing_verification and existing_verification.status == VerificationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified",
        )

    # Create or update
    if existing_verification:
        existing_verification.verification_type = VerificationType.TRADE_LICENSE
        existing_verification.status = VerificationStatus.PENDING
        existing_verification.trade_license_number = request.trade_license_number
        existing_verification.trade_license_document_url = request.trade_license_document
        existing_verification.submitted_at = datetime.utcnow()
        verification = existing_verification
    else:
        verification = Verification(
            user_id=current_user.id,
            verification_type=VerificationType.TRADE_LICENSE,
            status=VerificationStatus.PENDING,
            trade_license_number=request.trade_license_number,
            trade_license_document_url=request.trade_license_document,
        )
        db.add(verification)

    await db.commit()
    await db.refresh(verification)

    # TODO: Verify with Dubai Economy Department API if available
    # TODO: Send notification to admin

    return APIResponse(
        success=True,
        data=VerificationSubmitResponse(
            verification_id=verification.id,
            status=verification.status,
            estimated_review_time="24 hours",
            submitted_at=verification.submitted_at,
        ),
        message="Business verification submitted successfully",
    )


# === Admin Endpoints ===

@router.get(
    "/admin/pending",
    response_model=APIResponse[List[VerificationAdminListItem]],
    summary="Get pending verifications (Admin)",
    description="Get all pending verification requests for review",
    dependencies=[Depends(require_admin_role)],
)
async def get_pending_verifications(
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Get pending verifications for admin review.

    Admin only endpoint.
    """
    offset = (page - 1) * per_page

    result = await db.execute(
        select(Verification)
        .where(Verification.status == VerificationStatus.PENDING)
        .options(selectinload(Verification.user))
        .order_by(Verification.submitted_at.asc())
        .offset(offset)
        .limit(per_page)
    )
    verifications = result.scalars().all()

    items = [
        VerificationAdminListItem(
            verification_id=v.id,
            user_id=v.user_id,
            user_name=v.user.full_name,
            user_email=v.user.email,
            verification_type=v.verification_type,
            status=v.status,
            submitted_at=v.submitted_at,
            emirates_id_front_image_url=v.emirates_id_front_image_url,
            emirates_id_back_image_url=v.emirates_id_back_image_url,
            trade_license_document_url=v.trade_license_document_url,
        )
        for v in verifications
    ]

    return APIResponse(
        success=True,
        data=items,
        message=f"Found {len(items)} pending verifications",
    )


@router.get(
    "/admin/{verification_id}",
    response_model=APIResponse[VerificationAdminDetailResponse],
    summary="Get verification details (Admin)",
    description="Get detailed verification for admin review",
    dependencies=[Depends(require_admin_role)],
)
async def get_verification_details_admin(
    verification_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full verification details including sensitive data.

    Admin only endpoint.
    """
    result = await db.execute(
        select(Verification)
        .where(Verification.id == verification_id)
        .options(selectinload(Verification.user))
    )
    verification = result.scalar_one_or_none()

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found",
        )

    # Decrypt Emirates ID for admin review
    decrypted_emirates_id = None
    if verification.emirates_id_number:
        try:
            decrypted_emirates_id = decrypt_emirates_id(verification.emirates_id_number)
        except Exception:
            decrypted_emirates_id = "[Decryption Failed]"

    return APIResponse(
        success=True,
        data=VerificationAdminDetailResponse(
            verification_id=verification.id,
            user_id=verification.user_id,
            user_name=verification.user.full_name,
            user_email=verification.user.email,
            user_phone=verification.user.phone,
            verification_type=verification.verification_type,
            status=verification.status,
            emirates_id_number=decrypted_emirates_id,
            emirates_id_front_image_url=verification.emirates_id_front_image_url,
            emirates_id_back_image_url=verification.emirates_id_back_image_url,
            trade_license_number=verification.trade_license_number,
            trade_license_document_url=verification.trade_license_document_url,
            submitted_at=verification.submitted_at,
            reviewed_at=verification.reviewed_at,
            reviewed_by=verification.reviewed_by,
            rejection_reason=verification.rejection_reason,
        ),
    )


@router.patch(
    "/admin/{verification_id}/approve",
    response_model=APIResponse[VerificationStatusResponse],
    summary="Approve verification (Admin)",
    description="Approve a verification request",
    dependencies=[Depends(require_admin_role)],
)
async def approve_verification(
    verification_id: UUID,
    request: VerificationApproveRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Approve verification request.

    Admin only endpoint.
    """
    result = await db.execute(
        select(Verification)
        .where(Verification.id == verification_id)
        .options(selectinload(Verification.user))
    )
    verification = result.scalar_one_or_none()

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found",
        )

    if verification.status == VerificationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification is already approved",
        )

    # Approve verification
    verification.status = VerificationStatus.APPROVED
    verification.reviewed_at = datetime.utcnow()
    verification.reviewed_by = current_user.id

    # Update user verification status
    verification.user.is_verified = True

    await db.commit()
    await db.refresh(verification)

    # TODO: Send notification to user about approval
    # TODO: Add verification badge to user

    return APIResponse(
        success=True,
        data=VerificationStatusResponse(
            is_verified=True,
            status=verification.status,
            verification_type=verification.verification_type,
            submitted_at=verification.submitted_at,
            reviewed_at=verification.reviewed_at,
            rejection_reason=None,
        ),
        message="Verification approved successfully",
    )


@router.patch(
    "/admin/{verification_id}/reject",
    response_model=APIResponse[VerificationStatusResponse],
    summary="Reject verification (Admin)",
    description="Reject a verification request with reason",
    dependencies=[Depends(require_admin_role)],
)
async def reject_verification(
    verification_id: UUID,
    request: VerificationRejectRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reject verification request.

    Admin only endpoint. User can resubmit after rejection.
    """
    result = await db.execute(
        select(Verification)
        .where(Verification.id == verification_id)
        .options(selectinload(Verification.user))
    )
    verification = result.scalar_one_or_none()

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found",
        )

    # Reject verification
    verification.status = VerificationStatus.REJECTED
    verification.reviewed_at = datetime.utcnow()
    verification.reviewed_by = current_user.id
    verification.rejection_reason = request.reason

    # Keep user as unverified
    verification.user.is_verified = False

    await db.commit()
    await db.refresh(verification)

    # TODO: Send notification to user with rejection reason
    # TODO: Allow user to resubmit

    return APIResponse(
        success=True,
        data=VerificationStatusResponse(
            is_verified=False,
            status=verification.status,
            verification_type=verification.verification_type,
            submitted_at=verification.submitted_at,
            reviewed_at=verification.reviewed_at,
            rejection_reason=verification.rejection_reason,
        ),
        message="Verification rejected",
    )
