"""Category management endpoints with live stream counts.

This module provides the 12 standard categories for Souk Loop:
1. Trading Card Games
2. Men's Fashion
3. Sneakers & Streetwear
4. Sports Cards
5. Collectibles (Coins & Money)
6. Electronics
7. Home & Decor
8. Beauty & Cosmetics
9. Kids & Baby
10. Furniture
11. Books & Media
12. Other

Each category includes:
- Total product counts
- Live stream counts
- Active listings counts
- Category metadata (icon, color)
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis
from app.dependencies import get_current_active_user, get_db
from app.models.product import FeedType, Product, ProductCategory
from app.models.stream import Stream, StreamStatus
from app.models.user import User
from app.schemas.product import ProductResponse

router = APIRouter(prefix="/categories", tags=["categories"])

# Category metadata (aligned with frontend product_categories.dart)
CATEGORY_METADATA = {
    ProductCategory.TRADING_CARDS: {
        "slug": "trading_cards",
        "name": "Trading Card Games",
        "description": "Pokémon, Yu-Gi-Oh!, Magic: The Gathering",
        "icon": "🎴",
        "color": "#9333EA",  # Purple
        "secondary_color": "#EC4899",  # Pink
    },
    ProductCategory.MENS_FASHION: {
        "slug": "mens_fashion",
        "name": "Men's Fashion",
        "description": "Streetwear, sneakers, apparel",
        "icon": "👔",
        "color": "#0D9488",  # Teal
        "secondary_color": "#8B5CF6",  # Purple
    },
    ProductCategory.SNEAKERS: {
        "slug": "sneakers",
        "name": "Sneakers & Streetwear",
        "description": "Limited editions & exclusives",
        "icon": "👟",
        "color": "#D4A745",  # Gold
        "secondary_color": "#EC4899",  # Pink
    },
    ProductCategory.SPORTS_CARDS: {
        "slug": "sports_cards",
        "name": "Sports Cards",
        "description": "NBA, NFL, Soccer, Baseball collectibles",
        "icon": "🏀",
        "color": "#DC2626",  # Red
        "secondary_color": "#D4A745",  # Gold
    },
    ProductCategory.COLLECTIBLES: {
        "slug": "collectibles",
        "name": "Collectibles",
        "description": "Coins, money, rare items",
        "icon": "💎",
        "color": "#F59E0B",  # Warning Gold
        "secondary_color": "#0D9488",  # Teal
    },
    ProductCategory.ELECTRONICS: {
        "slug": "electronics",
        "name": "Electronics",
        "description": "Gaming, audio, tech",
        "icon": "🎧",
        "color": "#0D9488",  # Teal
        "secondary_color": "#D4A745",  # Gold
    },
    ProductCategory.HOME_DECOR: {
        "slug": "home_decor",
        "name": "Home & Decor",
        "description": "Furniture, kitchen, home essentials",
        "icon": "🏠",
        "color": "#F59E0B",  # Warning Gold
        "secondary_color": "#DC2626",  # Red
    },
    ProductCategory.BEAUTY: {
        "slug": "beauty",
        "name": "Beauty & Cosmetics",
        "description": "Skincare, makeup, beauty products",
        "icon": "💄",
        "color": "#EC4899",  # Pink
        "secondary_color": "#D4A745",  # Gold
    },
    ProductCategory.KIDS_BABY: {
        "slug": "kids_baby",
        "name": "Kids & Baby",
        "description": "Toys, clothes, essentials",
        "icon": "🍼",
        "color": "#8B5CF6",  # Purple
        "secondary_color": "#F59E0B",  # Warning Gold
    },
    ProductCategory.FURNITURE: {
        "slug": "furniture",
        "name": "Furniture",
        "description": "Home furniture",
        "icon": "🛋️",
        "color": "#0D9488",  # Teal
        "secondary_color": "#8B5CF6",  # Purple
    },
    ProductCategory.BOOKS: {
        "slug": "books",
        "name": "Books & Media",
        "description": "Books, movies, collectibles",
        "icon": "📚",
        "color": "#8B5CF6",  # Purple
        "secondary_color": "#0D9488",  # Teal
    },
    ProductCategory.OTHER: {
        "slug": "other",
        "name": "Other",
        "description": "Miscellaneous items",
        "icon": "📦",
        "color": "#6B7280",  # Gray
        "secondary_color": "#9CA3AF",  # Light Gray
    },
}


async def _get_category_counts(session: AsyncSession, category: ProductCategory) -> dict:
    """Get counts for a specific category.

    Args:
        session: Database session
        category: ProductCategory enum

    Returns:
        Dict with total_products, live_streams_count, active_listings_count
    """
    # Total products in category
    total_result = await session.execute(
        select(func.count()).select_from(Product).where(Product.category == category)
    )
    total_products = total_result.scalar_one()

    # Active (available) listings
    active_result = await session.execute(
        select(func.count())
        .select_from(Product)
        .where(and_(Product.category == category, Product.is_available == True))  # noqa: E712
    )
    active_listings = active_result.scalar_one()

    # Live streams count (currently live)
    # Join Stream with Product to get category
    live_result = await session.execute(
        select(func.count())
        .select_from(Stream)
        .join(Product, Stream.user_id == Product.seller_id)
        .where(and_(Stream.status == StreamStatus.LIVE, Product.category == category))
    )
    live_streams = live_result.scalar_one()

    return {
        "total_products": total_products,
        "live_streams_count": live_streams,
        "active_listings_count": active_listings,
    }


@router.get("")
async def get_all_categories(
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    """Get all 12 categories with counts and metadata.

    Returns categories with:
    - Total products count
    - Live streams count (currently live)
    - Active listings count
    - Category metadata (name, icon, colors)

    Results are cached in Redis with 5-minute TTL.

    Args:
        session: Database session
        redis: Redis client

    Returns:
        List of all categories with counts and metadata
    """
    # Try to get from cache
    cache_key = "categories:all"
    cached = await redis.get(cache_key)
    if cached:
        import json

        return {"success": True, "data": json.loads(cached)}

    # Build category list
    categories = []
    for category_enum in ProductCategory:
        metadata = CATEGORY_METADATA[category_enum]
        counts = await _get_category_counts(session, category_enum)

        categories.append(
            {
                "slug": metadata["slug"],
                "name": metadata["name"],
                "description": metadata["description"],
                "icon": metadata["icon"],
                "color": metadata["color"],
                "secondary_color": metadata["secondary_color"],
                "total_products": counts["total_products"],
                "live_streams_count": counts["live_streams_count"],
                "active_listings_count": counts["active_listings_count"],
                "badge_count": counts["live_streams_count"],  # Badge shows live count
            }
        )

    # Cache for 5 minutes
    import json

    await redis.setex(cache_key, 300, json.dumps(categories))

    return {"success": True, "data": categories}


@router.get("/{category_slug}")
async def get_category(
    category_slug: str,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Get single category details.

    Includes:
    - Category metadata
    - Product counts
    - Top sellers in category
    - Trending products

    Args:
        category_slug: Category slug (e.g., "trading_cards")
        session: Database session

    Returns:
        Category details with top sellers and trending products

    Raises:
        HTTPException 404: If category not found
    """
    # Find category by slug
    category_enum = None
    for cat, meta in CATEGORY_METADATA.items():
        if meta["slug"] == category_slug:
            category_enum = cat
            break

    if not category_enum:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    metadata = CATEGORY_METADATA[category_enum]
    counts = await _get_category_counts(session, category_enum)

    # Get top sellers (most products in category)
    top_sellers_result = await session.execute(
        select(Product.seller_id, func.count(Product.id).label("product_count"))
        .where(and_(Product.category == category_enum, Product.is_available == True))  # noqa: E712
        .group_by(Product.seller_id)
        .order_by(func.count(Product.id).desc())
        .limit(5)
    )
    top_sellers = [{"seller_id": str(row[0]), "product_count": row[1]} for row in top_sellers_result.all()]

    # Get trending products (most viewed recently)
    trending_result = await session.execute(
        select(Product.id)
        .where(and_(Product.category == category_enum, Product.is_available == True))  # noqa: E712
        .order_by(Product.view_count.desc(), Product.created_at.desc())
        .limit(10)
    )
    trending_products = [str(row[0]) for row in trending_result.all()]

    return {
        "success": True,
        "data": {
            "slug": metadata["slug"],
            "name": metadata["name"],
            "description": metadata["description"],
            "icon": metadata["icon"],
            "color": metadata["color"],
            "secondary_color": metadata["secondary_color"],
            "total_products": counts["total_products"],
            "live_streams_count": counts["live_streams_count"],
            "active_listings_count": counts["active_listings_count"],
            "top_sellers": top_sellers,
            "trending_products": trending_products,
        },
    }


@router.get("/{category_slug}/streams")
async def get_category_streams(
    category_slug: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Get all live and recorded streams for category.

    Shows live streams first, then recorded streams sorted by views.

    Args:
        category_slug: Category slug
        session: Database session
        page: Page number
        per_page: Items per page

    Returns:
        Paginated list of streams for category

    Raises:
        HTTPException 404: If category not found
    """
    # Find category
    category_enum = None
    for cat, meta in CATEGORY_METADATA.items():
        if meta["slug"] == category_slug:
            category_enum = cat
            break

    if not category_enum:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Query streams with category filter
    # Note: Streams don't have category directly, need to join through user's products
    query = (
        select(Stream)
        .options(selectinload(Stream.user))
        .join(Product, Stream.user_id == Product.seller_id)
        .where(Product.category == category_enum)
        .order_by(
            (Stream.status == StreamStatus.LIVE).desc(),  # Live first
            Stream.total_views.desc(),
        )
        .distinct()
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Pagination
    offset = (page - 1) * per_page
    query = query.limit(per_page).offset(offset)

    result = await session.execute(query)
    streams = result.scalars().all()

    # Convert to response (simplified, full schema in Phase 4)
    items = [
        {
            "id": str(stream.id),
            "title": stream.title,
            "status": stream.status.value,
            "thumbnail_url": stream.thumbnail_url,
            "viewer_count": stream.viewer_count if stream.status == StreamStatus.LIVE else None,
            "total_views": stream.total_views,
            "created_at": stream.created_at,
        }
        for stream in streams
    ]

    return {
        "success": True,
        "data": {
            "items": items,
            "page": page,
            "per_page": per_page,
            "total": total,
            "has_more": (page * per_page) < total,
        },
    }


@router.get("/{category_slug}/products")
async def get_category_products(
    category_slug: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort: str = Query("recent", description="Sort: recent, popular, price_low, price_high"),
    feed_type: FeedType | None = Query(None),
):
    """Get all products for category.

    Supports filtering by feed_type and sorting.

    Args:
        category_slug: Category slug
        session: Database session
        page: Page number
        per_page: Items per page
        sort: Sort order
        feed_type: Optional feed type filter

    Returns:
        Paginated list of products in category

    Raises:
        HTTPException 404: If category not found
    """
    # Find category
    category_enum = None
    for cat, meta in CATEGORY_METADATA.items():
        if meta["slug"] == category_slug:
            category_enum = cat
            break

    if not category_enum:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Build query
    query = (
        select(Product)
        .options(selectinload(Product.seller))
        .where(and_(Product.category == category_enum, Product.is_available == True))  # noqa: E712
    )

    # Feed type filter
    if feed_type:
        query = query.where(Product.feed_type == feed_type)

    # Sort
    if sort == "recent":
        query = query.order_by(Product.created_at.desc())
    elif sort == "popular":
        query = query.order_by(Product.view_count.desc(), Product.like_count.desc())
    elif sort == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort == "price_high":
        query = query.order_by(Product.price.desc())

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Pagination
    offset = (page - 1) * per_page
    query = query.limit(per_page).offset(offset)

    result = await session.execute(query)
    products = result.scalars().all()

    # Convert to response (using existing conversion logic)
    from app.api.v1.feeds import _convert_product_to_feed_response

    items = [_convert_product_to_feed_response(p) for p in products]

    return {
        "success": True,
        "data": {
            "items": items,
            "page": page,
            "per_page": per_page,
            "total": total,
            "has_more": (page * per_page) < total,
        },
    }
