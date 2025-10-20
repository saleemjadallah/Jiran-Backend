"""
Reviews & Ratings endpoints
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.review import Review, ReviewType
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.schemas.base import APIResponse
from app.schemas.review import (
    RatingBreakdown,
    RatingSummaryResponse,
    ReviewCreate,
    ReviewerInfo,
    ReviewListResponse,
    ReviewResponse,
    ReviewUpdate,
    SellerResponseCreate,
)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


# === User Endpoints ===

@router.post(
    "",
    response_model=APIResponse[ReviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create review",
    description="Create a review for a product or seller after completed transaction",
)
async def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a review for a completed transaction.

    Requirements:
    - User must have completed the transaction
    - User hasn't already reviewed this transaction
    - Transaction must be completed
    """
    # Validate transaction exists and is completed
    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == review_data.transaction_id)
        .where(Transaction.buyer_id == current_user.id)
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or you don't have permission",
        )

    if transaction.status != TransactionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only review completed transactions",
        )

    # Check if already reviewed
    existing = await db.execute(
        select(Review).where(Review.transaction_id == review_data.transaction_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this transaction",
        )

    # Create review
    review = Review(
        transaction_id=review_data.transaction_id,
        product_id=review_data.product_id,
        seller_id=review_data.seller_id,
        reviewer_id=current_user.id,
        review_type=review_data.review_type,
        rating=review_data.rating,
        review_text=review_data.review_text,
        is_verified_purchase=True,
    )

    db.add(review)
    await db.commit()
    await db.refresh(review)

    # Update seller's average rating
    await _update_seller_rating(review_data.seller_id, db)

    # TODO: Send notification to seller
    # TODO: Update product rating if product review

    return APIResponse(
        success=True,
        data=ReviewResponse.model_validate(review),
        message="Review submitted successfully",
    )


@router.get(
    "",
    response_model=APIResponse[ReviewListResponse],
    summary="Get reviews",
    description="Get reviews with filters (for seller, product, or all)",
)
async def get_reviews(
    user_id: Optional[UUID] = Query(None, description="Filter by seller ID"),
    product_id: Optional[UUID] = Query(None, description="Filter by product ID"),
    rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by rating"),
    sort: str = Query("recent", regex="^(recent|highest|lowest)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get reviews with various filters.

    Sort options:
    - recent: Most recent first
    - highest: Highest rating first
    - lowest: Lowest rating first
    """
    # Build query
    query = select(Review).options(selectinload(Review.reviewer))

    # Apply filters
    if user_id:
        query = query.where(Review.seller_id == user_id)
    if product_id:
        query = query.where(Review.product_id == product_id)
    if rating:
        query = query.where(Review.rating == rating)

    # Apply sorting
    if sort == "recent":
        query = query.order_by(Review.created_at.desc())
    elif sort == "highest":
        query = query.order_by(Review.rating.desc(), Review.created_at.desc())
    elif sort == "lowest":
        query = query.order_by(Review.rating.asc(), Review.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    # Execute query
    result = await db.execute(query)
    reviews = result.scalars().all()

    # Build response
    review_responses = []
    for review in reviews:
        reviewer_info = None
        if review.reviewer:
            reviewer_info = ReviewerInfo(
                id=review.reviewer.id,
                username=review.reviewer.username,
                avatar_url=review.reviewer.avatar_url,
                is_verified=review.reviewer.is_verified,
            )

        review_response = ReviewResponse.model_validate(review)
        review_response.reviewer = reviewer_info
        review_responses.append(review_response)

    return APIResponse(
        success=True,
        data=ReviewListResponse(
            reviews=review_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_more=(offset + len(reviews)) < total,
        ),
    )


@router.get(
    "/{review_id}",
    response_model=APIResponse[ReviewResponse],
    summary="Get single review",
    description="Get detailed review information",
)
async def get_review(
    review_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get single review by ID"""
    result = await db.execute(
        select(Review)
        .where(Review.id == review_id)
        .options(selectinload(Review.reviewer))
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # Build reviewer info
    reviewer_info = None
    if review.reviewer:
        reviewer_info = ReviewerInfo(
            id=review.reviewer.id,
            username=review.reviewer.username,
            avatar_url=review.reviewer.avatar_url,
            is_verified=review.reviewer.is_verified,
        )

    review_response = ReviewResponse.model_validate(review)
    review_response.reviewer = reviewer_info

    return APIResponse(
        success=True,
        data=review_response,
    )


@router.patch(
    "/{review_id}",
    response_model=APIResponse[ReviewResponse],
    summary="Update review",
    description="Update review (only within 7 days of creation)",
)
async def update_review(
    review_id: UUID,
    update_data: ReviewUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update review.

    Can only update within 7 days of creation and only by the review author.
    """
    result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # Check ownership
    if review.reviewer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own reviews",
        )

    # Check if within 7 days
    if datetime.utcnow() - review.created_at > timedelta(days=7):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update reviews within 7 days of creation",
        )

    # Update fields
    if update_data.rating is not None:
        review.rating = update_data.rating
    if update_data.review_text is not None:
        review.review_text = update_data.review_text

    await db.commit()
    await db.refresh(review)

    # Recalculate seller rating
    await _update_seller_rating(review.seller_id, db)

    return APIResponse(
        success=True,
        data=ReviewResponse.model_validate(review),
        message="Review updated successfully",
    )


@router.delete(
    "/{review_id}",
    response_model=APIResponse[dict],
    summary="Delete review",
    description="Delete review (soft delete)",
)
async def delete_review(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete review.

    Only the author or admin can delete.
    """
    result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # Check permission (owner or admin)
    if review.reviewer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this review",
        )

    seller_id = review.seller_id

    # Delete review
    await db.delete(review)
    await db.commit()

    # Recalculate seller rating
    await _update_seller_rating(seller_id, db)

    return APIResponse(
        success=True,
        data={"deleted": True},
        message="Review deleted successfully",
    )


@router.post(
    "/{review_id}/response",
    response_model=APIResponse[ReviewResponse],
    summary="Respond to review (Seller)",
    description="Seller can respond to reviews on their products",
)
async def respond_to_review(
    review_id: UUID,
    response_data: SellerResponseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Seller response to review.

    Only the seller who received the review can respond.
    """
    result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # Check if current user is the seller
    if review.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can respond to their reviews",
        )

    # Add response
    review.seller_response = response_data.response_text
    review.responded_at = datetime.utcnow().isoformat()

    await db.commit()
    await db.refresh(review)

    # TODO: Send notification to reviewer

    return APIResponse(
        success=True,
        data=ReviewResponse.model_validate(review),
        message="Response added successfully",
    )


@router.post(
    "/{review_id}/helpful",
    response_model=APIResponse[dict],
    summary="Mark review as helpful",
    description="Mark a review as helpful (upvote)",
)
async def mark_helpful(
    review_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark review as helpful.

    Increments helpful count. TODO: Track users who marked to prevent duplicates.
    """
    result = await db.execute(
        select(Review).where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # TODO: Check if user already marked this review as helpful
    # For now, just increment

    review.helpful_count += 1
    await db.commit()

    return APIResponse(
        success=True,
        data={"helpful_count": review.helpful_count},
        message="Marked as helpful",
    )


@router.get(
    "/users/{user_id}/rating-summary",
    response_model=APIResponse[RatingSummaryResponse],
    summary="Get user rating summary",
    description="Get rating breakdown and statistics for a seller",
)
async def get_rating_summary(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get rating summary for a seller.

    Includes:
    - Average rating
    - Total reviews
    - Breakdown by star rating
    - Recent reviews
    """
    # Get all reviews for seller
    result = await db.execute(
        select(Review).where(Review.seller_id == user_id)
    )
    reviews = result.scalars().all()

    if not reviews:
        return APIResponse(
            success=True,
            data=RatingSummaryResponse(
                average_rating=0.0,
                total_reviews=0,
                rating_breakdown=RatingBreakdown(
                    five_star=0,
                    four_star=0,
                    three_star=0,
                    two_star=0,
                    one_star=0,
                ),
                recent_reviews=[],
            ),
        )

    # Calculate stats
    total_reviews = len(reviews)
    average_rating = sum(r.rating for r in reviews) / total_reviews

    # Build breakdown
    breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for review in reviews:
        breakdown[review.rating] += 1

    # Get recent reviews (last 3)
    recent = sorted(reviews, key=lambda r: r.created_at, reverse=True)[:3]
    recent_responses = [ReviewResponse.model_validate(r) for r in recent]

    return APIResponse(
        success=True,
        data=RatingSummaryResponse(
            average_rating=round(average_rating, 1),
            total_reviews=total_reviews,
            rating_breakdown=RatingBreakdown(
                five_star=breakdown[5],
                four_star=breakdown[4],
                three_star=breakdown[3],
                two_star=breakdown[2],
                one_star=breakdown[1],
            ),
            recent_reviews=recent_responses,
        ),
    )


# === Helper Functions ===

async def _update_seller_rating(seller_id: UUID, db: AsyncSession):
    """Update seller's average rating based on all their reviews"""
    result = await db.execute(
        select(func.avg(Review.rating)).where(Review.seller_id == seller_id)
    )
    avg_rating = result.scalar()

    if avg_rating is not None:
        # Update user's rating
        user_result = await db.execute(
            select(User).where(User.id == seller_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            user.rating = float(avg_rating)
            await db.commit()
