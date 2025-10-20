"""Feed Cache Service

Handles feed-specific caching logic for Discover and Community feeds.

Features:
- Cache discover feed (5 min TTL)
- Cache community feed (5 min TTL)
- Support for pagination
- Cache key generation with filters hash
- Cache invalidation on stream status changes
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from app.core.cache.redis_manager import RedisManager


class FeedCacheService:
    """Service for caching and managing feed data.

    Provides:
    - Discover feed caching (live streams, professional content)
    - Community feed caching (local peer-to-peer)
    - Pagination support
    - Filter-aware cache keys
    - Cache invalidation
    """

    # TTLs (in seconds)
    DISCOVER_FEED_TTL = 300  # 5 minutes
    COMMUNITY_FEED_TTL = 300  # 5 minutes

    def __init__(self, redis: RedisManager):
        """Initialize feed cache service.

        Args:
            redis: Redis manager instance
        """
        self.redis = redis

    # ========== Discover Feed ==========

    def _build_discover_cache_key(
        self,
        page: int,
        per_page: int,
        category: Optional[str] = None,
        sort: str = "live_first",
    ) -> str:
        """Build cache key for discover feed.

        Cache key format: "feed:discover:{filters_hash}:page:{page}:limit:{per_page}"

        Args:
            page: Page number
            per_page: Items per page
            category: Optional category filter
            sort: Sort order (live_first, recent, popular)

        Returns:
            Cache key string
        """
        # Build filters dict for hashing
        filters = {
            "category": category,
            "sort": sort,
        }

        # Create hash from filters
        filters_str = json.dumps(filters, sort_keys=True)
        filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:8]

        return f"feed:discover:{filters_hash}:page:{page}:limit:{per_page}"

    async def get_discover_feed(
        self,
        page: int,
        per_page: int,
        category: Optional[str] = None,
        sort: str = "live_first",
    ) -> Optional[Dict[str, Any]]:
        """Get discover feed from cache.

        Args:
            page: Page number
            per_page: Items per page
            category: Optional category filter
            sort: Sort order

        Returns:
            Cached feed data or None if not cached
        """
        cache_key = self._build_discover_cache_key(page, per_page, category, sort)
        return await self.redis.get(cache_key)

    async def set_discover_feed(
        self,
        page: int,
        per_page: int,
        data: Dict[str, Any],
        category: Optional[str] = None,
        sort: str = "live_first",
    ) -> None:
        """Cache discover feed data.

        Args:
            page: Page number
            per_page: Items per page
            data: Feed data to cache
            category: Optional category filter
            sort: Sort order
        """
        cache_key = self._build_discover_cache_key(page, per_page, category, sort)
        await self.redis.set(cache_key, data, ttl=self.DISCOVER_FEED_TTL)

    async def invalidate_discover_feed(self) -> int:
        """Invalidate all discover feed cache entries.

        Returns:
            Number of keys deleted
        """
        return await self.redis.delete_pattern("feed:discover:*")

    # ========== Community Feed ==========

    def _build_community_cache_key(
        self,
        page: int,
        per_page: int,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        category: Optional[str] = None,
        neighborhood: Optional[str] = None,
        sort: str = "nearest",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        condition: Optional[str] = None,
    ) -> str:
        """Build cache key for community feed.

        Cache key format: "feed:community:{location_hash}:{filters_hash}:page:{page}:limit:{per_page}"

        Args:
            page: Page number
            per_page: Items per page
            latitude: User latitude
            longitude: User longitude
            radius_km: Search radius in km
            category: Optional category filter
            neighborhood: Optional neighborhood filter
            sort: Sort order (nearest, recent, price_low, price_high)
            min_price: Minimum price filter
            max_price: Maximum price filter
            condition: Condition filter

        Returns:
            Cache key string
        """
        # Build location hash (rounded to 2 decimal places for cache hits in same area)
        location_key = f"{round(latitude, 2)}:{round(longitude, 2)}:{radius_km}"
        location_hash = hashlib.md5(location_key.encode()).hexdigest()[:8]

        # Build filters dict for hashing
        filters = {
            "category": category,
            "neighborhood": neighborhood,
            "sort": sort,
            "min_price": min_price,
            "max_price": max_price,
            "condition": condition,
        }

        # Create hash from filters
        filters_str = json.dumps(filters, sort_keys=True)
        filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:8]

        return f"feed:community:{location_hash}:{filters_hash}:page:{page}:limit:{per_page}"

    async def get_community_feed(
        self,
        page: int,
        per_page: int,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        category: Optional[str] = None,
        neighborhood: Optional[str] = None,
        sort: str = "nearest",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        condition: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get community feed from cache.

        Args:
            page: Page number
            per_page: Items per page
            latitude: User latitude
            longitude: User longitude
            radius_km: Search radius in km
            category: Optional category filter
            neighborhood: Optional neighborhood filter
            sort: Sort order
            min_price: Minimum price filter
            max_price: Maximum price filter
            condition: Condition filter

        Returns:
            Cached feed data or None if not cached
        """
        cache_key = self._build_community_cache_key(
            page,
            per_page,
            latitude,
            longitude,
            radius_km,
            category,
            neighborhood,
            sort,
            min_price,
            max_price,
            condition,
        )
        return await self.redis.get(cache_key)

    async def set_community_feed(
        self,
        page: int,
        per_page: int,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        category: Optional[str] = None,
        neighborhood: Optional[str] = None,
        sort: str = "nearest",
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        condition: Optional[str] = None,
    ) -> None:
        """Cache community feed data.

        Args:
            page: Page number
            per_page: Items per page
            data: Feed data to cache
            latitude: User latitude
            longitude: User longitude
            radius_km: Search radius in km
            category: Optional category filter
            neighborhood: Optional neighborhood filter
            sort: Sort order
            min_price: Minimum price filter
            max_price: Maximum price filter
            condition: Condition filter
        """
        cache_key = self._build_community_cache_key(
            page,
            per_page,
            latitude,
            longitude,
            radius_km,
            category,
            neighborhood,
            sort,
            min_price,
            max_price,
            condition,
        )
        await self.redis.set(cache_key, data, ttl=self.COMMUNITY_FEED_TTL)

    async def invalidate_community_feed(
        self,
        location_hash: Optional[str] = None,
    ) -> int:
        """Invalidate community feed cache entries.

        Args:
            location_hash: Optional specific location hash to invalidate.
                          If None, invalidates all community feeds.

        Returns:
            Number of keys deleted
        """
        if location_hash:
            return await self.redis.delete_pattern(
                f"feed:community:{location_hash}:*"
            )
        return await self.redis.delete_pattern("feed:community:*")

    # ========== Global Feed Invalidation ==========

    async def invalidate_all_feeds(self) -> int:
        """Invalidate all feed caches (discover + community).

        Used when stream status changes or product is created/updated/deleted.

        Returns:
            Total number of keys deleted
        """
        deleted = 0
        deleted += await self.invalidate_discover_feed()
        deleted += await self.invalidate_community_feed()
        return deleted

    # ========== Predictive Prefetching ==========

    async def prefetch_next_page(
        self,
        current_page: int,
        per_page: int,
        feed_fetcher: Any,
        feed_type: str = "discover",
        **kwargs,
    ) -> None:
        """Prefetch next page in background to improve UX.

        Call this when user loads a page to prefetch the next page.

        Args:
            current_page: Current page user is viewing
            per_page: Items per page
            feed_fetcher: Async function to fetch feed data
            feed_type: 'discover' or 'community'
            **kwargs: Additional arguments for feed fetcher (category, location, etc.)
        """
        next_page = current_page + 1

        # Build cache key for next page
        if feed_type == "discover":
            cache_key = self._build_discover_cache_key(
                next_page,
                per_page,
                kwargs.get("category"),
                kwargs.get("sort", "live_first"),
            )
        else:  # community
            cache_key = self._build_community_cache_key(
                next_page,
                per_page,
                kwargs["latitude"],
                kwargs["longitude"],
                kwargs.get("radius_km", 5.0),
                kwargs.get("category"),
                kwargs.get("neighborhood"),
                kwargs.get("sort", "nearest"),
                kwargs.get("min_price"),
                kwargs.get("max_price"),
                kwargs.get("condition"),
            )

        # Check if already cached
        cached = await self.redis.get(cache_key)
        if cached:
            # Already prefetched, no need to fetch again
            return

        # Fetch and cache next page in background (fire and forget)
        try:
            next_page_data = await feed_fetcher(page=next_page, per_page=per_page, **kwargs)

            if feed_type == "discover":
                await self.set_discover_feed(
                    next_page,
                    per_page,
                    next_page_data,
                    kwargs.get("category"),
                    kwargs.get("sort", "live_first"),
                )
            else:  # community
                await self.set_community_feed(
                    next_page,
                    per_page,
                    next_page_data,
                    kwargs["latitude"],
                    kwargs["longitude"],
                    kwargs.get("radius_km", 5.0),
                    kwargs.get("category"),
                    kwargs.get("neighborhood"),
                    kwargs.get("sort", "nearest"),
                    kwargs.get("min_price"),
                    kwargs.get("max_price"),
                    kwargs.get("condition"),
                )
        except Exception:
            # Silently fail - prefetching is optional
            pass

    async def warm_cache(
        self,
        pages: int,
        per_page: int,
        feed_fetcher: Any,
        feed_type: str = "discover",
        **kwargs,
    ) -> int:
        """Warm cache by prefetching multiple pages.

        Useful for initial cache population or after cache invalidation.

        Args:
            pages: Number of pages to prefetch
            per_page: Items per page
            feed_fetcher: Async function to fetch feed data
            feed_type: 'discover' or 'community'
            **kwargs: Additional arguments for feed fetcher

        Returns:
            Number of pages successfully cached
        """
        cached_count = 0

        for page in range(1, pages + 1):
            try:
                # Fetch page data
                page_data = await feed_fetcher(page=page, per_page=per_page, **kwargs)

                # Cache page
                if feed_type == "discover":
                    await self.set_discover_feed(
                        page,
                        per_page,
                        page_data,
                        kwargs.get("category"),
                        kwargs.get("sort", "live_first"),
                    )
                else:  # community
                    await self.set_community_feed(
                        page,
                        per_page,
                        page_data,
                        kwargs["latitude"],
                        kwargs["longitude"],
                        kwargs.get("radius_km", 5.0),
                        kwargs.get("category"),
                        kwargs.get("neighborhood"),
                        kwargs.get("sort", "nearest"),
                        kwargs.get("min_price"),
                        kwargs.get("max_price"),
                        kwargs.get("condition"),
                    )

                cached_count += 1

            except Exception:
                # Continue warming even if one page fails
                continue

        return cached_count

    # ========== Statistics ==========

    async def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache key counts
        """
        discover_keys = await self.redis.redis.keys("feed:discover:*")
        community_keys = await self.redis.redis.keys("feed:community:*")

        return {
            "discover_cache_entries": len(discover_keys),
            "community_cache_entries": len(community_keys),
            "total_feed_cache_entries": len(discover_keys) + len(community_keys),
        }
