"""
Cache warming service for preloading frequently accessed data.

Implements strategies to populate cache with hot data before requests arrive,
improving cache hit rates and reducing database load.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio
import logging

from app.core.cache.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class CacheWarmingService:
    """
    Service for warming cache with frequently accessed data.

    Strategies:
    - Warm popular feeds on startup
    - Warm trending searches
    - Warm popular categories
    - Warm active seller profiles
    """

    def __init__(self, redis: RedisManager):
        self.redis = redis
        self._warming_in_progress = False

    async def warm_all(self):
        """Warm all cache types"""
        if self._warming_in_progress:
            logger.warning("Cache warming already in progress, skipping")
            return

        self._warming_in_progress = True
        start_time = datetime.now(timezone.utc)

        try:
            logger.info("Starting cache warming...")

            # Run warming tasks in parallel
            await asyncio.gather(
                self.warm_discover_feed(),
                self.warm_trending_searches(),
                self.warm_popular_categories(),
                self.warm_active_sellers(),
                return_exceptions=True
            )

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(f"Cache warming completed in {duration:.2f}s")

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
        finally:
            self._warming_in_progress = False

    async def warm_discover_feed(self):
        """Warm discover feed (first 3 pages)"""
        try:
            logger.info("Warming discover feed...")

            # TODO: Replace with actual database query
            # For now, we'll just set placeholders
            for page in range(1, 4):
                cache_key = f"feed:discover:page:{page}"

                # Check if already cached
                exists = await self.redis.exists(cache_key)
                if exists:
                    logger.debug(f"Feed page {page} already cached")
                    continue

                # In production, fetch from database:
                # streams = await stream_repository.get_discover_feed(page=page)

                # For now, create placeholder
                placeholder = {
                    "page": page,
                    "streams": [],
                    "warmed_at": datetime.now(timezone.utc).isoformat()
                }

                await self.redis.set(cache_key, placeholder, ttl=300)  # 5 min
                logger.debug(f"Warmed feed page {page}")

            logger.info("Discover feed warming complete")

        except Exception as e:
            logger.error(f"Failed to warm discover feed: {e}")

    async def warm_trending_searches(self):
        """Warm trending search queries"""
        try:
            logger.info("Warming trending searches...")

            # Common search queries to pre-cache
            trending_queries = [
                "nike shoes",
                "iphone",
                "macbook",
                "sneakers",
                "fashion"
            ]

            for query in trending_queries:
                cache_key = f"trending:search:{query}"

                exists = await self.redis.exists(cache_key)
                if exists:
                    continue

                # Increment search count in trending sorted set
                await self.redis.zincrby("trending:searches", 1.0, query)

            logger.info("Trending searches warming complete")

        except Exception as e:
            logger.error(f"Failed to warm trending searches: {e}")

    async def warm_popular_categories(self):
        """Warm popular category data"""
        try:
            logger.info("Warming popular categories...")

            # Top categories to pre-cache
            popular_categories = [
                "trading_card_games",
                "mens_fashion",
                "sneakers_streetwear",
                "sports_cards",
                "electronics"
            ]

            for category_id in popular_categories:
                cache_key = f"category:{category_id}:products"

                exists = await self.redis.exists(cache_key)
                if exists:
                    continue

                # Add to popular categories sorted set
                await self.redis.zincrby("popular:categories", 1.0, category_id)

                # Cache empty placeholder (will be populated on first real request)
                placeholder = {
                    "category_id": category_id,
                    "products": [],
                    "warmed_at": datetime.now(timezone.utc).isoformat()
                }

                await self.redis.set(cache_key, placeholder, ttl=600)  # 10 min

            logger.info("Popular categories warming complete")

        except Exception as e:
            logger.error(f"Failed to warm popular categories: {e}")

    async def warm_active_sellers(self):
        """Warm active seller profiles"""
        try:
            logger.info("Warming active seller profiles...")

            # In production, query for sellers with active streams
            # For now, just log
            logger.info("Active sellers warming complete (placeholder)")

        except Exception as e:
            logger.error(f"Failed to warm active sellers: {e}")

    async def warm_specific_key(
        self,
        key: str,
        data: Any,
        ttl: int = 300
    ):
        """Warm a specific cache key"""
        try:
            await self.redis.set(key, data, ttl=ttl)
            logger.debug(f"Warmed cache key: {key}")
        except Exception as e:
            logger.error(f"Failed to warm key {key}: {e}")

    async def warm_batch(
        self,
        keys_data: Dict[str, Any],
        ttl: int = 300
    ):
        """Warm multiple cache keys in batch"""
        try:
            # Use mset for batch operation
            await self.redis.mset(keys_data)

            # Set TTLs individually (mset doesn't support TTL)
            for key in keys_data.keys():
                await self.redis.expire(key, ttl)

            logger.info(f"Warmed {len(keys_data)} cache keys in batch")

        except Exception as e:
            logger.error(f"Failed to warm batch: {e}")


# Global cache warming service instance
_warming_service: Optional[CacheWarmingService] = None


def get_cache_warming_service() -> CacheWarmingService:
    """Get global cache warming service instance"""
    if _warming_service is None:
        raise RuntimeError("Cache warming service not initialized")
    return _warming_service


def init_cache_warming_service(redis: RedisManager) -> CacheWarmingService:
    """Initialize global cache warming service"""
    global _warming_service
    _warming_service = CacheWarmingService(redis)
    return _warming_service
