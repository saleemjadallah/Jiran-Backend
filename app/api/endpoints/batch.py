"""Batch API endpoints for efficient multi-item fetching.

Prevents N+1 queries by allowing clients to fetch multiple items in a single request.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.redis_manager import RedisManager, get_redis_manager
from app.dependencies import get_db
from app.models.product import Product
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["batch"])


# ============= Request/Response Models =============


class BatchUserRequest(BaseModel):
    """Request model for batch user fetching."""

    user_ids: List[str] = Field(
        ..., min_items=1, max_items=100, description="List of user IDs to fetch"
    )


class UserBatchResponse(BaseModel):
    """Single user in batch response."""

    id: str
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_verified: bool
    rating: Optional[float]
    follower_count: int


class BatchProductRequest(BaseModel):
    """Request model for batch product fetching."""

    product_ids: List[str] = Field(
        ..., min_items=1, max_items=100, description="List of product IDs to fetch"
    )


class ProductBatchResponse(BaseModel):
    """Single product in batch response."""

    id: str
    title: str
    price: float
    thumbnail_url: Optional[str]
    seller_id: str
    status: str
    category: str
    views: int
    is_live: bool


# ============= Batch Endpoints =============


@router.post("/users", response_model=List[UserBatchResponse])
async def get_users_batch(
    request: BatchUserRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisManager = Depends(get_redis_manager),
) -> List[UserBatchResponse]:
    """Fetch multiple users in a single request.

    Uses Redis MGET for efficient caching.

    Args:
        request: Batch request with user IDs
        db: Database session
        redis: Redis manager

    Returns:
        List of user data

    Example:
        POST /api/v1/batch/users
        {
            "user_ids": ["user1", "user2", "user3"]
        }
    """
    user_ids = request.user_ids

    # Build cache keys
    cache_keys = [f"user:profile:{user_id}" for user_id in user_ids]

    # Batch fetch from Redis
    cached_users = await redis.mget(cache_keys)

    # Track cache hits and misses
    users: List[UserBatchResponse] = []
    missing_ids: List[str] = []
    cache_hits = 0

    for user_id, cached in zip(user_ids, cached_users):
        if cached:
            try:
                users.append(UserBatchResponse(**cached))
                cache_hits += 1
            except Exception as e:
                logger.warning(f"Failed to deserialize cached user {user_id}: {e}")
                missing_ids.append(user_id)
        else:
            missing_ids.append(user_id)

    logger.info(
        f"Batch users: {cache_hits} cache hits, {len(missing_ids)} misses"
    )

    # Fetch missing users from database
    if missing_ids:
        result = await db.execute(
            select(User).filter(User.id.in_(missing_ids))
        )
        db_users = result.scalars().all()

        # Backfill cache and add to results
        for user in db_users:
            user_data = UserBatchResponse(
                id=str(user.id),
                username=user.username,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                is_verified=user.is_verified,
                rating=user.rating,
                follower_count=user.follower_count or 0,
            )
            users.append(user_data)

            # Cache for future requests
            cache_key = f"user:profile:{user.id}"
            await redis.set(cache_key, user_data.dict(), ttl=3600)  # 1 hour

    return users


@router.post("/products", response_model=List[ProductBatchResponse])
async def get_products_batch(
    request: BatchProductRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisManager = Depends(get_redis_manager),
) -> List[ProductBatchResponse]:
    """Fetch multiple products in a single request.

    Uses Redis MGET for efficient caching.

    Args:
        request: Batch request with product IDs
        db: Database session
        redis: Redis manager

    Returns:
        List of product data

    Example:
        POST /api/v1/batch/products
        {
            "product_ids": ["prod1", "prod2", "prod3"]
        }
    """
    product_ids = request.product_ids

    # Build cache keys
    cache_keys = [f"product:{product_id}" for product_id in product_ids]

    # Batch fetch from Redis
    cached_products = await redis.mget(cache_keys)

    # Track cache hits and misses
    products: List[ProductBatchResponse] = []
    missing_ids: List[str] = []
    cache_hits = 0

    for product_id, cached in zip(product_ids, cached_products):
        if cached:
            try:
                products.append(ProductBatchResponse(**cached))
                cache_hits += 1
            except Exception as e:
                logger.warning(
                    f"Failed to deserialize cached product {product_id}: {e}"
                )
                missing_ids.append(product_id)
        else:
            missing_ids.append(product_id)

    logger.info(
        f"Batch products: {cache_hits} cache hits, {len(missing_ids)} misses"
    )

    # Fetch missing products from database
    if missing_ids:
        result = await db.execute(
            select(Product).filter(Product.id.in_(missing_ids))
        )
        db_products = result.scalars().all()

        # Backfill cache and add to results
        for product in db_products:
            product_data = ProductBatchResponse(
                id=str(product.id),
                title=product.title,
                price=float(product.price),
                thumbnail_url=product.thumbnail_url,
                seller_id=str(product.seller_id),
                status=product.status,
                category=product.category,
                views=product.views or 0,
                is_live=product.is_live or False,
            )
            products.append(product_data)

            # Cache for future requests
            cache_key = f"product:{product.id}"
            await redis.set(cache_key, product_data.dict(), ttl=900)  # 15 min

    return products


@router.get("/cache-stats")
async def get_cache_stats(
    redis: RedisManager = Depends(get_redis_manager),
) -> Dict[str, any]:
    """Get cache statistics and health info.

    Returns:
        Cache statistics including memory usage, hit rates, etc.
    """
    try:
        # Get Redis info
        info = await redis.redis.info()

        stats = {
            "redis_version": info.get("redis_version"),
            "memory_used_mb": round(
                int(info.get("used_memory", 0)) / (1024 * 1024), 2
            ),
            "memory_peak_mb": round(
                int(info.get("used_memory_peak", 0)) / (1024 * 1024), 2
            ),
            "connected_clients": info.get("connected_clients"),
            "total_keys": await redis.redis.dbsize(),
            "hit_rate": round(
                float(info.get("keyspace_hits", 0))
                / (
                    float(info.get("keyspace_hits", 0))
                    + float(info.get("keyspace_misses", 1))
                )
                * 100,
                2,
            ),
        }

        return stats

    except Exception as e:
        logger.error(f"Error fetching cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch cache statistics",
        )
