"""Dual-feed endpoints for Discover and Community feeds.

This module provides the dual-feed architecture:
- Discover Feed: Professional sellers, live streams, video content
- Community Feed: Peer-to-peer local sales, location-based
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape
from sqlalchemy import and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_active_user, get_db, get_feed_cache_service
from app.models.product import FeedType, Product, ProductCategory
from app.models.stream import Stream, StreamStatus
from app.models.user import User
from app.schemas.product import ProductLocation, ProductResponse
from app.services.cache.feed_cache_service import FeedCacheService
from app.utils.geospatial import calculate_distance, get_distance_label

router = APIRouter(prefix="/feeds", tags=["feeds"])


def _convert_product_to_feed_response(
    product: Product, requester_location: ProductLocation | None = None
) -> dict:
    """Convert Product to feed response with seller and distance info.

    Args:
        product: Product model
        requester_location: Optional requester location for distance

    Returns:
        Product data dict with seller info and distance
    """
    # Convert location
    location_data = None
    distance_km = None
    distance_label = None

    if product.location:
        point = to_shape(product.location)
        location_data = {
            "latitude": point.y,
            "longitude": point.x,
            "neighborhood": product.neighborhood,
            "building_name": None,
        }

        # Calculate distance if requester location provided
        if requester_location:
            distance_km = calculate_distance(
                requester_location.latitude,
                requester_location.longitude,
                point.y,
                point.x,
            )
            distance_label = get_distance_label(distance_km)
            location_data["distance_km"] = round(distance_km, 2)
            location_data["distance_label"] = distance_label

    return {
        "id": str(product.id),
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "original_price": product.original_price,
        "currency": product.currency,
        "category": product.category,
        "condition": product.condition,
        "feed_type": product.feed_type,
        "neighborhood": product.neighborhood,
        "is_available": product.is_available,
        "view_count": product.view_count,
        "like_count": product.like_count,
        "image_urls": product.image_urls,
        "video_url": product.video_url,
        "video_thumbnail_url": product.video_thumbnail_url,
        "tags": product.tags,
        "sold_at": product.sold_at,
        "seller": {
            "id": str(product.seller.id),
            "username": product.seller.username,
            "full_name": product.seller.full_name,
            "avatar_url": product.seller.avatar_url,
            "is_verified": product.seller.is_verified,
            "neighborhood": product.seller.neighborhood,
            "rating": 0.0,  # TODO: Calculate from reviews (Phase 6)
        },
        "location": location_data,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


@router.get("/discover")
async def get_discover_feed(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: User | None = None,  # Made optional without dependency
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    category: ProductCategory | None = Query(None, description="Filter by category"),
    sort: str = Query("live_first", description="Sort order: live_first, recent, popular"),
    latitude: float | None = Query(None, ge=-90, le=90, description="User latitude"),
    longitude: float | None = Query(None, ge=-180, le=180, description="User longitude"),
):
    """Get Discover feed with live streams and professional content.

    Discover feed features:
    - Live streams shown first (status = 'live')
    - Recorded videos with streams
    - Professional seller content
    - Sorted by: live first, then by created_at DESC
    - Includes seller info with verification badges
    - Distance calculation from user location

    Args:
        session: Database session
        current_user: Optional authenticated user
        page: Page number (1-indexed)
        per_page: Items per page (max 100)
        category: Optional category filter
        sort: Sort order
        latitude: User latitude for distance
        longitude: User longitude for distance

    Returns:
        Paginated discover feed with items, pagination info
    """
    # ========== Query Database (Cache disabled for now) ==========

    # Get user location
    requester_location = None
    if latitude and longitude:
        requester_location = ProductLocation(latitude=latitude, longitude=longitude)
    elif current_user and current_user.location:
        user_point = to_shape(current_user.location)
        requester_location = ProductLocation(latitude=user_point.y, longitude=user_point.x)

    # Build query for Discover feed
    query = (
        select(Product)
        .options(selectinload(Product.seller))
        .where(and_(Product.feed_type == FeedType.DISCOVER, Product.is_available == True))  # noqa: E712
    )

    # Apply category filter
    if category:
        query = query.where(Product.category == category)

    # Check for live streams (from Stream table)
    # The feed should show BOTH:
    # 1. Products from products table (recorded videos, photos)
    # 2. Live streams from streams table (actual live broadcasts)
    live_stream_ids = []
    try:
        live_streams_query = (
            select(Stream.id)
            .where(Stream.status == StreamStatus.LIVE)
        )
        live_stream_result = await session.execute(live_streams_query)
        live_stream_ids = [row[0] for row in live_stream_result.all()]
    except Exception:
        # Streams table doesn't exist yet or other error - skip live check
        pass

    # Sort query - prioritize live streams if any exist
    if sort == "live_first":
        if live_stream_ids:
            # Show live streams first, then all other products by created_at
            query = query.order_by(
                Product.id.in_(live_stream_ids).desc(),  # Live streams first
                Product.created_at.desc(),  # Then newest products
            )
        else:
            # No live streams, show all products by created_at
            query = query.order_by(Product.created_at.desc())
    elif sort == "recent":
        query = query.order_by(Product.created_at.desc())
    elif sort == "popular":
        query = query.order_by(Product.view_count.desc(), Product.like_count.desc())

    # Calculate total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.limit(per_page).offset(offset)

    # Execute query
    result = await session.execute(query)
    products = result.scalars().all()

    # Convert to response format
    items = []
    for product in products:
        item = _convert_product_to_feed_response(product, requester_location)

        # Check if live
        is_live = str(product.id) in [str(sid) for sid in live_stream_ids]
        item["is_live"] = is_live

        # Get viewer count if live
        if is_live:
            stream_result = await session.execute(select(Stream).where(Stream.id == product.id))
            stream = stream_result.scalar_one_or_none()
            if stream:
                item["viewer_count"] = stream.viewer_count

        items.append(item)

    # ========== Build Response ==========
    response_data = {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "has_more": (page * per_page) < total,
    }

    return {
        "success": True,
        "data": response_data,
    }


@router.get("/community")
async def get_community_feed(
    session: Annotated[AsyncSession, Depends(get_db)],
    feed_cache: Annotated[FeedCacheService, Depends(get_feed_cache_service)],
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: ProductCategory | None = Query(None),
    neighborhood: str | None = Query(None, description="Filter by neighborhood"),
    latitude: float = Query(..., ge=-90, le=90, description="User latitude (required)"),
    longitude: float = Query(..., ge=-180, le=180, description="User longitude (required)"),
    radius_km: float = Query(5.0, ge=0.1, le=50.0, description="Search radius in km"),
    sort: str = Query("nearest", description="Sort: nearest, recent, price_low, price_high"),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    condition: str | None = Query(None),
):
    """Get Community feed with local peer-to-peer sales.

    Community feed features:
    - Location-based filtering (required latitude/longitude)
    - Peer-to-peer local transactions
    - Distance badges (Same building, Walking distance, etc.)
    - Seller trust indicators
    - Default sort by nearest

    Args:
        session: Database session
        current_user: Optional authenticated user
        page: Page number
        per_page: Items per page
        category: Category filter
        neighborhood: Neighborhood filter
        latitude: User latitude (required)
        longitude: User longitude (required)
        radius_km: Search radius (default 5km, max 50km)
        sort: Sort order
        min_price: Minimum price filter
        max_price: Maximum price filter
        condition: Condition filter

    Returns:
        Paginated community feed with distance labels
    """
    # ========== Check Cache First ==========
    category_str = category.value if category else None
    cached_feed = await feed_cache.get_community_feed(
        page=page,
        per_page=per_page,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        category=category_str,
        neighborhood=neighborhood,
        sort=sort,
        min_price=min_price,
        max_price=max_price,
        condition=condition,
    )

    if cached_feed:
        # Cache hit - return immediately
        return {
            "success": True,
            "data": cached_feed,
            "cached": True,  # Debug flag
        }

    # ========== Cache Miss - Query Database ==========

    requester_location = ProductLocation(latitude=latitude, longitude=longitude)

    # Convert km to meters
    radius_m = radius_km * 1000

    # Build base query with spatial filter
    # Using proper Geography type from geoalchemy2 instead of string cast
    distance_expr = func.ST_Distance(
        cast(Product.location, Geography),
        cast(func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326), Geography),
    )

    query = (
        select(Product, (distance_expr / 1000).label("distance_km"))
        .options(selectinload(Product.seller))
        .where(
            and_(
                Product.feed_type == FeedType.COMMUNITY,
                Product.is_available == True,  # noqa: E712
                func.ST_DWithin(
                    cast(Product.location, Geography),
                    cast(func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326), Geography),
                    radius_m,
                ),
            )
        )
    )

    # Apply filters
    if category:
        query = query.where(Product.category == category)
    if neighborhood:
        query = query.where(Product.neighborhood == neighborhood)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    if condition:
        query = query.where(Product.condition == condition)

    # Sort
    if sort == "nearest":
        query = query.order_by(distance_expr)
    elif sort == "recent":
        query = query.order_by(Product.created_at.desc())
    elif sort == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort == "price_high":
        query = query.order_by(Product.price.desc())

    # Execute query to get all results (then we'll paginate in Python)
    # Note: We fetch all results due to SQLAlchemy caching issues with geography casts
    # For production, consider using raw SQL or limiting radius to keep result set manageable
    result = await session.execute(query)
    all_rows = result.all()
    total = len(all_rows)

    # Apply pagination in Python
    offset = (page - 1) * per_page
    paginated_rows = all_rows[offset : offset + per_page]

    # Build response with distance labels
    items = []
    for product, distance_km in paginated_rows:
        item = _convert_product_to_feed_response(product, requester_location)
        item["distance_km"] = round(distance_km, 2)
        item["distance_label"] = get_distance_label(distance_km)
        items.append(item)

    # ========== Build Response ==========
    response_data = {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "has_more": (page * per_page) < total,
    }

    # ========== Cache Response (5 min TTL) ==========
    await feed_cache.set_community_feed(
        page=page,
        per_page=per_page,
        data=response_data,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        category=category_str,
        neighborhood=neighborhood,
        sort=sort,
        min_price=min_price,
        max_price=max_price,
        condition=condition,
    )

    return {
        "success": True,
        "data": response_data,
        "cached": False,  # Debug flag
    }


@router.get("/following")
async def get_following_feed(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Get feed from users that current user follows.

    Shows products and streams from followed users.
    Combines both Discover and Community content.
    Sorted by created_at DESC.

    Args:
        session: Database session
        current_user: Authenticated user (required)
        page: Page number
        per_page: Items per page

    Returns:
        Paginated feed of followed users' content
    """
    # TODO: Implement follow system (Phase 7)
    # For now, return empty feed
    # This will be implemented in Phase 7 when Follow model is created

    return {
        "success": True,
        "data": {
            "items": [],
            "page": page,
            "per_page": per_page,
            "total": 0,
            "has_more": False,
        },
        "message": "Follow system not yet implemented (Phase 7)",
    }
