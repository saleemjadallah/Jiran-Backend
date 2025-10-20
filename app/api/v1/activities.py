"""
Activity feed endpoints: Get activity feed from followed users, personal activity history
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.activity import Activity
from app.models.follow import Follow
from app.models.product import Product
from app.models.stream import Stream
from app.models.user import User
from app.schemas.activity import ActivityFeedResponse, ActivityResponse, PersonalActivityResponse

router = APIRouter(prefix="/activity", tags=["Activity"])


# === Activity Feed Endpoints ===


@router.get(
    "",
    response_model=ActivityFeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Get activity feed",
    description="Get activity feed from users that current user follows",
)
async def get_activity_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get activity feed for current user.

    - Shows activities from users that current user follows
    - Includes different activity types:
      - User went live
      - User posted new product
      - User sold a product
      - User received 5-star review
      - User achieved milestone
    - Sorted by created_at DESC (most recent first)
    """
    # Get list of users that current user follows
    following_result = await db.execute(
        select(Follow.following_id).where(Follow.follower_id == current_user.id)
    )
    following_ids = following_result.scalars().all()

    if not following_ids:
        # No one followed, return empty feed
        return ActivityFeedResponse(
            data=[],
            page=page,
            per_page=per_page,
            total=0,
            has_more=False,
        )

    # Build query for activities from followed users
    query = (
        select(Activity)
        .options(
            selectinload(Activity.user),
            selectinload(Activity.related_product),
            selectinload(Activity.related_stream),
            selectinload(Activity.related_user),
        )
        .where(Activity.user_id.in_(following_ids))
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Activity.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    activities = result.scalars().all()

    # Convert to response models with populated relationships
    activity_list = []
    for activity in activities:
        activity_dict = {
            "id": str(activity.id),
            "user_id": str(activity.user_id),
            "activity_type": activity.activity_type,
            "related_product_id": str(activity.related_product_id) if activity.related_product_id else None,
            "related_stream_id": str(activity.related_stream_id) if activity.related_stream_id else None,
            "related_user_id": str(activity.related_user_id) if activity.related_user_id else None,
            "meta_data": activity.meta_data,
            "created_at": activity.created_at,
        }

        # Add user info
        if activity.user:
            activity_dict["user"] = {
                "id": str(activity.user.id),
                "username": activity.user.username,
                "full_name": activity.user.full_name,
                "avatar_url": activity.user.avatar_url,
                "is_verified": activity.user.is_verified,
            }

        # Add related product info
        if activity.related_product:
            activity_dict["related_product"] = {
                "id": str(activity.related_product.id),
                "title": activity.related_product.title,
                "price": float(activity.related_product.price),
                "image_urls": activity.related_product.image_urls,
            }

        # Add related stream info
        if activity.related_stream:
            activity_dict["related_stream"] = {
                "id": str(activity.related_stream.id),
                "title": activity.related_stream.title,
                "thumbnail_url": activity.related_stream.thumbnail_url,
                "status": activity.related_stream.status,
            }

        # Add related user info (e.g., new follower)
        if activity.related_user:
            activity_dict["related_user"] = {
                "id": str(activity.related_user.id),
                "username": activity.related_user.username,
                "full_name": activity.related_user.full_name,
                "avatar_url": activity.related_user.avatar_url,
                "is_verified": activity.related_user.is_verified,
            }

        activity_list.append(ActivityResponse(**activity_dict))

    return ActivityFeedResponse(
        data=activity_list,
        page=page,
        per_page=per_page,
        total=total,
        has_more=(page * per_page) < total,
    )


@router.get(
    "/me",
    response_model=PersonalActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get personal activity history",
    description="Get current user's own activity history",
)
async def get_personal_activity(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get personal activity history for current user.

    - Shows all activities for current user
    - Includes:
      - Products listed
      - Products sold
      - Reviews received
      - New followers
      - Milestones achieved
      - Streams started/ended
    - Sorted by created_at DESC (most recent first)
    """
    # Build query for current user's activities
    query = (
        select(Activity)
        .options(
            selectinload(Activity.user),
            selectinload(Activity.related_product),
            selectinload(Activity.related_stream),
            selectinload(Activity.related_user),
        )
        .where(Activity.user_id == current_user.id)
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Activity.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    activities = result.scalars().all()

    # Convert to response models with populated relationships
    activity_list = []
    for activity in activities:
        activity_dict = {
            "id": str(activity.id),
            "user_id": str(activity.user_id),
            "activity_type": activity.activity_type,
            "related_product_id": str(activity.related_product_id) if activity.related_product_id else None,
            "related_stream_id": str(activity.related_stream_id) if activity.related_stream_id else None,
            "related_user_id": str(activity.related_user_id) if activity.related_user_id else None,
            "meta_data": activity.meta_data,
            "created_at": activity.created_at,
        }

        # Add user info
        if activity.user:
            activity_dict["user"] = {
                "id": str(activity.user.id),
                "username": activity.user.username,
                "full_name": activity.user.full_name,
                "avatar_url": activity.user.avatar_url,
                "is_verified": activity.user.is_verified,
            }

        # Add related product info
        if activity.related_product:
            activity_dict["related_product"] = {
                "id": str(activity.related_product.id),
                "title": activity.related_product.title,
                "price": float(activity.related_product.price),
                "image_urls": activity.related_product.image_urls,
            }

        # Add related stream info
        if activity.related_stream:
            activity_dict["related_stream"] = {
                "id": str(activity.related_stream.id),
                "title": activity.related_stream.title,
                "thumbnail_url": activity.related_stream.thumbnail_url,
                "status": activity.related_stream.status,
            }

        # Add related user info (e.g., new follower)
        if activity.related_user:
            activity_dict["related_user"] = {
                "id": str(activity.related_user.id),
                "username": activity.related_user.username,
                "full_name": activity.related_user.full_name,
                "avatar_url": activity.related_user.avatar_url,
                "is_verified": activity.related_user.is_verified,
            }

        activity_list.append(ActivityResponse(**activity_dict))

    return PersonalActivityResponse(
        data=activity_list,
        page=page,
        per_page=per_page,
        total=total,
        has_more=(page * per_page) < total,
    )
