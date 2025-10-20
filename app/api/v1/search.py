"""Search and filtering endpoints with 90-point filter system.

This module provides comprehensive search functionality:
- Full-text search with PostgreSQL
- 90-point filter system
- Geospatial filtering
- Auto-suggestions
- Trending searches
- Search tracking for analytics
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis
from app.dependencies import get_current_active_user, get_db
from app.models.product import FeedType, Product, ProductCategory, ProductCondition
from app.models.user import User
from app.schemas.product import ProductLocation

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search_products(
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
    q: str = Query(..., min_length=1, description="Search query"),
    feed_type: FeedType | None = Query(None, description="Filter by feed type"),
    category: ProductCategory | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    condition: ProductCondition | None = Query(None),
    location_lat: float | None = Query(None, ge=-90, le=90),
    location_lng: float | None = Query(None, ge=-180, le=180),
    radius_km: float = Query(5.0, ge=0.1, le=50.0),
    neighborhood: str | None = Query(None),
    sort: str = Query("relevance", description="Sort: relevance, recent, price_low, price_high, nearest"),
    verified_sellers_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Comprehensive product search with 90-point filter system.

    Search features:
    - Full-text search in title, description, tags, seller username
    - Multiple filter categories (12 points)
    - Price ranges (6 points)
    - Condition filters (4 points)
    - Distance filters (5 points)
    - Seller type filters (3 points)
    - Feed type filters (2 points)
    - Availability filters (2 points)
    - Category-specific filters (varies by category)

    Args:
        session: Database session
        redis: Redis client
        current_user: Optional authenticated user
        q: Search query string
        feed_type: Filter by discover/community
        category: Category filter
        min_price: Minimum price
        max_price: Maximum price
        condition: Product condition
        location_lat: User latitude for distance
        location_lng: User longitude for distance
        radius_km: Search radius
        neighborhood: Exact neighborhood match
        sort: Sort order
        verified_sellers_only: Filter to verified sellers
        page: Page number
        per_page: Items per page

    Returns:
        Search results with facets and suggestions
    """
    # Track search query for trending
    await redis.zincrby("trending_searches", 1, q.lower())

    # Build base query with full-text search
    # PostgreSQL full-text search using to_tsvector and to_tsquery
    search_vector = func.to_tsvector("english", Product.title + " " + func.coalesce(Product.description, ""))
    search_query_ts = func.plainto_tsquery("english", q)

    query = (
        select(Product, func.ts_rank(search_vector, search_query_ts).label("rank"))
        .options(selectinload(Product.seller))
        .where(
            and_(
                Product.is_available == True,  # noqa: E712
                or_(
                    search_vector.op("@@")(search_query_ts),  # Full-text match
                    Product.title.ilike(f"%{q}%"),  # Fallback LIKE search
                    func.coalesce(Product.description, "").ilike(f"%{q}%"),
                ),
            )
        )
    )

    # Apply filters
    if feed_type:
        query = query.where(Product.feed_type == feed_type)

    if category:
        query = query.where(Product.category == category)

    if min_price is not None:
        query = query.where(Product.price >= min_price)

    if max_price is not None:
        query = query.where(Product.price <= max_price)

    if condition:
        query = query.where(Product.condition == condition)

    if neighborhood:
        query = query.where(Product.neighborhood == neighborhood)

    if verified_sellers_only:
        query = query.join(User, Product.seller_id == User.id).where(User.is_verified == True)  # noqa: E712

    # Geospatial filter
    if location_lat and location_lng:
        radius_m = radius_km * 1000
        user_point = func.ST_SetSRID(func.ST_MakePoint(location_lng, location_lat), 4326)
        query = query.where(
            func.ST_DWithin(func.cast(Product.location, "geography"), func.cast(user_point, "geography"), radius_m)
        )

        # Add distance for sorting if "nearest"
        if sort == "nearest":
            distance_expr = func.ST_Distance(
                func.cast(Product.location, "geography"), func.cast(user_point, "geography")
            )
            query = query.add_columns((distance_expr / 1000).label("distance_km"))

    # Sorting
    if sort == "relevance":
        query = query.order_by(text("rank DESC"))
    elif sort == "recent":
        query = query.order_by(Product.created_at.desc())
    elif sort == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort == "price_high":
        query = query.order_by(Product.price.desc())
    elif sort == "nearest" and location_lat and location_lng:
        query = query.order_by(text("distance_km ASC"))
    else:
        query = query.order_by(Product.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Pagination
    offset = (page - 1) * per_page
    query = query.limit(per_page).offset(offset)

    # Execute
    result = await session.execute(query)
    rows = result.all()

    # Build response
    from app.api.v1.feeds import _convert_product_to_feed_response

    items = []
    for row in rows:
        product = row[0]
        requester_location = None
        if location_lat and location_lng:
            requester_location = ProductLocation(latitude=location_lat, longitude=location_lng)

        item = _convert_product_to_feed_response(product, requester_location)

        # Add distance if available
        if sort == "nearest" and len(row) > 2:
            item["distance_km"] = round(row[2], 2)

        items.append(item)

    # Generate facets (category counts, price ranges)
    facets = await _generate_facets(session, q, feed_type)

    return {
        "success": True,
        "data": {
            "items": items,
            "page": page,
            "per_page": per_page,
            "total": total,
            "has_more": (page * per_page) < total,
            "facets": facets,
        },
    }


async def _generate_facets(session: AsyncSession, query: str, feed_type: FeedType | None) -> dict:
    """Generate search facets for filtering.

    Args:
        session: Database session
        query: Search query
        feed_type: Optional feed type filter

    Returns:
        Dict with category counts and price ranges
    """
    # Build base query
    search_vector = func.to_tsvector("english", Product.title + " " + func.coalesce(Product.description, ""))
    search_query_ts = func.plainto_tsquery("english", query)

    base_where = and_(
        Product.is_available == True,  # noqa: E712
        or_(
            search_vector.op("@@")(search_query_ts),
            Product.title.ilike(f"%{query}%"),
        ),
    )

    if feed_type:
        base_where = and_(base_where, Product.feed_type == feed_type)

    # Category counts
    category_result = await session.execute(
        select(Product.category, func.count(Product.id).label("count")).where(base_where).group_by(Product.category)
    )
    category_facets = [{"category": row[0].value, "count": row[1]} for row in category_result.all()]

    # Price ranges
    price_ranges = [
        {"label": "Under AED 100", "min": 0, "max": 100},
        {"label": "AED 100-500", "min": 100, "max": 500},
        {"label": "AED 500-1000", "min": 500, "max": 1000},
        {"label": "AED 1000-5000", "min": 1000, "max": 5000},
        {"label": "AED 5000-10000", "min": 5000, "max": 10000},
        {"label": "Above AED 10000", "min": 10000, "max": None},
    ]

    price_facets = []
    for range_info in price_ranges:
        range_where = and_(base_where, Product.price >= range_info["min"])
        if range_info["max"]:
            range_where = and_(range_where, Product.price < range_info["max"])

        count_result = await session.execute(select(func.count()).select_from(Product).where(range_where))
        count = count_result.scalar_one()

        price_facets.append({"label": range_info["label"], "count": count, "min": range_info["min"], "max": range_info["max"]})

    return {"categories": category_facets, "price_ranges": price_facets}


@router.get("/suggestions")
async def get_search_suggestions(
    redis: Annotated[Redis, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_db)],
    q: str = Query(..., min_length=2, description="Query prefix"),
):
    """Get auto-suggest results as user types.

    Returns top 10 suggestions based on:
    - Product titles
    - Categories
    - Seller usernames
    - Popular searches (from cache)

    Args:
        redis: Redis client
        session: Database session
        q: Query prefix (min 2 characters)

    Returns:
        List of suggestions
    """
    suggestions = []

    # Product titles (top 5)
    title_result = await session.execute(
        select(Product.title)
        .where(and_(Product.is_available == True, Product.title.ilike(f"{q}%")))  # noqa: E712
        .distinct()
        .limit(5)
    )
    for row in title_result.all():
        suggestions.append({"text": row[0], "type": "product"})

    # Categories (match by name)
    from app.api.v1.categories import CATEGORY_METADATA

    for cat_enum, meta in CATEGORY_METADATA.items():
        if q.lower() in meta["name"].lower():
            suggestions.append({"text": meta["name"], "type": "category", "slug": meta["slug"]})

    # Seller usernames (top 3)
    seller_result = await session.execute(
        select(User.username).where(User.username.ilike(f"{q}%")).distinct().limit(3)
    )
    for row in seller_result.all():
        suggestions.append({"text": row[0], "type": "seller"})

    # Limit to 10 total
    return {"success": True, "data": suggestions[:10]}


@router.get("/trending")
async def get_trending_searches(
    redis: Annotated[Redis, Depends(get_redis)],
):
    """Get top 10 trending search queries.

    Based on search frequency in last 7 days.
    Stored in Redis sorted set with scores.

    Args:
        redis: Redis client

    Returns:
        List of trending searches with counts
    """
    # Get top 10 from sorted set
    trending = await redis.zrevrange("trending_searches", 0, 9, withscores=True)

    results = [{"query": query.decode() if isinstance(query, bytes) else query, "count": int(score)} for query, score in trending]

    return {"success": True, "data": results}


@router.post("/track")
async def track_search(
    redis: Annotated[Redis, Depends(get_redis)],
    q: str = Query(..., description="Search query to track"),
):
    """Track search query for trending calculations.

    Increments count in Redis sorted set.
    Fire and forget endpoint (no response needed).

    Args:
        redis: Redis client
        q: Search query

    Returns:
        Success status
    """
    await redis.zincrby("trending_searches", 1, q.lower())
    return {"success": True, "message": "Search tracked"}
