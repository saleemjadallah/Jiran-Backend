"""
Social features endpoints: Follow/Unfollow, Followers, Following, Relationships
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.activity import Activity, ActivityType
from app.models.block import Block
from app.models.follow import Follow
from app.models.notification import NotificationType
from app.models.user import User
from app.schemas.base import APIResponse
from app.schemas.follow import (
    FollowerListResponse,
    FollowerResponse,
    FollowingListResponse,
    FollowingResponse,
    FollowResponse,
    RelationshipData,
    UserProfileSummary,
    UserRelationshipResponse,
)
from app.services.notification_service import notification_service

router = APIRouter(prefix="/users", tags=["Social"])


# === Follow/Unfollow Endpoints ===


@router.post(
    "/{user_id}/follow",
    response_model=FollowResponse,
    status_code=status.HTTP_200_OK,
    summary="Follow user",
    description="Follow a user to see their content in your feed",
)
async def follow_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Follow a user.

    - Increments follower_count for followed user
    - Increments following_count for current user
    - Sends notification to followed user
    - Creates activity record
    """
    # Cannot follow yourself
    if str(user_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself",
        )

    # Check if user exists
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if already following
    existing = await db.execute(
        select(Follow).where(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        return FollowResponse(
            success=True,
            message="Already following this user",
            following=True,
        )

    # Create follow relationship
    follow = Follow(
        follower_id=current_user.id,
        following_id=user_id,
    )
    db.add(follow)

    # Update counts
    target_user.follower_count += 1
    current_user.following_count += 1

    await db.commit()

    # Create activity for the followed user
    activity = Activity(
        user_id=target_user.id,
        activity_type=ActivityType.NEW_FOLLOWER,
        related_user_id=current_user.id,
        meta_data={"follower_username": current_user.username},
    )
    db.add(activity)
    await db.commit()

    # Send notification
    await notification_service.send_notification(
        db=db,
        user_id=str(target_user.id),
        notification_type=NotificationType.NEW_FOLLOWER,
        title="New Follower",
        body=f"{current_user.username} started following you",
        data={
            "type": "new_follower",
            "follower_id": str(current_user.id),
            "follower_username": current_user.username,
        },
    )

    return FollowResponse(
        success=True,
        message="Successfully followed user",
        following=True,
    )


@router.delete(
    "/{user_id}/follow",
    response_model=FollowResponse,
    status_code=status.HTTP_200_OK,
    summary="Unfollow user",
    description="Unfollow a user",
)
async def unfollow_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unfollow a user.

    - Decrements follower_count for followed user
    - Decrements following_count for current user
    - Deletes follow relationship
    """
    # Find follow relationship
    result = await db.execute(
        select(Follow).where(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id,
        )
    )
    follow = result.scalar_one_or_none()

    if not follow:
        return FollowResponse(
            success=True,
            message="Not following this user",
            following=False,
        )

    # Get target user to decrement count
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()

    if target_user:
        target_user.follower_count -= 1

    current_user.following_count -= 1

    # Delete follow relationship
    await db.delete(follow)
    await db.commit()

    return FollowResponse(
        success=True,
        message="Successfully unfollowed user",
        following=False,
    )


# === Followers/Following List Endpoints ===


@router.get(
    "/{user_id}/followers",
    response_model=FollowerListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user followers",
    description="Get list of users following this user",
)
async def get_followers(
    user_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get followers for a user.

    - Returns paginated list of followers
    - Includes mutual follow indicator
    - Supports search by username
    """
    # Build base query
    query = (
        select(Follow, User)
        .join(User, Follow.follower_id == User.id)
        .where(Follow.following_id == user_id)
    )

    # Add search filter if provided
    if search:
        query = query.where(User.username.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Follow.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    followers = result.all()

    # Check mutual follows (if current user also follows each follower)
    follower_ids = [f[1].id for f in followers]
    mutual_result = await db.execute(
        select(Follow.following_id).where(
            Follow.follower_id == current_user.id, Follow.following_id.in_(follower_ids)
        )
    )
    mutual_follows = set(mutual_result.scalars().all())

    # Build response
    follower_list = [
        FollowerResponse(
            user=UserProfileSummary.model_validate(follower_user),
            followed_at=follow.created_at,
            is_mutual=follower_user.id in mutual_follows,
        )
        for follow, follower_user in followers
    ]

    return FollowerListResponse(
        data=follower_list,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(page * per_page) < total,
    )


@router.get(
    "/{user_id}/following",
    response_model=FollowingListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get users being followed",
    description="Get list of users that this user is following",
)
async def get_following(
    user_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get users that a user is following.

    - Returns paginated list of following
    - Includes follow-back indicator
    - Supports search by username
    """
    # Build base query
    query = (
        select(Follow, User)
        .join(User, Follow.following_id == User.id)
        .where(Follow.follower_id == user_id)
    )

    # Add search filter if provided
    if search:
        query = query.where(User.username.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Follow.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    following = result.all()

    # Check if each followed user follows back
    following_ids = [f[1].id for f in following]
    follows_back_result = await db.execute(
        select(Follow.follower_id).where(
            Follow.following_id == user_id, Follow.follower_id.in_(following_ids)
        )
    )
    follows_back = set(follows_back_result.scalars().all())

    # Build response
    following_list = [
        FollowingResponse(
            user=UserProfileSummary.model_validate(following_user),
            followed_at=follow.created_at,
            follows_back=following_user.id in follows_back,
        )
        for follow, following_user in following
    ]

    return FollowingListResponse(
        data=following_list,
        total=total,
        page=page,
        per_page=per_page,
        has_more=(page * per_page) < total,
    )


# === Relationship Endpoint ===


@router.get(
    "/{user_id}/relationship",
    response_model=UserRelationshipResponse,
    status_code=status.HTTP_200_OK,
    summary="Get relationship with user",
    description="Check relationship status between current user and target user",
)
async def get_relationship(
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get relationship between current user and target user.

    Returns:
    - following: Current user follows target
    - followed_by: Target follows current user
    - blocked: Current user blocked target
    - blocked_by: Target blocked current user
    - can_message: Whether current user can message target
    """
    # Check if following
    following_result = await db.execute(
        select(Follow).where(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id,
        )
    )
    following = following_result.scalar_one_or_none() is not None

    # Check if followed by
    followed_by_result = await db.execute(
        select(Follow).where(
            Follow.follower_id == user_id,
            Follow.following_id == current_user.id,
        )
    )
    followed_by = followed_by_result.scalar_one_or_none() is not None

    # Check if blocked
    blocked_result = await db.execute(
        select(Block).where(
            Block.blocker_id == current_user.id,
            Block.blocked_id == user_id,
        )
    )
    blocked = blocked_result.scalar_one_or_none() is not None

    # Check if blocked by
    blocked_by_result = await db.execute(
        select(Block).where(
            Block.blocker_id == user_id,
            Block.blocked_id == current_user.id,
        )
    )
    blocked_by = blocked_by_result.scalar_one_or_none() is not None

    # Can message if not blocked
    can_message = not blocked and not blocked_by

    relationship_data = RelationshipData(
        following=following,
        followed_by=followed_by,
        blocked=blocked,
        blocked_by=blocked_by,
        can_message=can_message,
    )

    return UserRelationshipResponse(data=relationship_data.model_dump())
