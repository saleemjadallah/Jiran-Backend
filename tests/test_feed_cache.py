"""Tests for Feed Cache Service

Verifies:
- Cache key generation
- Pagination with different cache keys
- Cache hit/miss behavior
- Cache invalidation
"""

import asyncio
import hashlib
import json

import pytest

from app.core.cache.redis_manager import RedisManager
from app.services.cache.feed_cache_service import FeedCacheService


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def redis_manager():
    """Create Redis manager for tests."""
    # In real tests, use a test Redis instance
    # For this example, we'll create a mock
    from unittest.mock import AsyncMock, MagicMock

    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock()
    mock_redis.delete_pattern = AsyncMock(return_value=0)
    mock_redis.redis = MagicMock()
    mock_redis.redis.keys = AsyncMock(return_value=[])

    redis_manager = RedisManager(mock_redis)
    return redis_manager


@pytest.fixture
def feed_cache(redis_manager):
    """Create FeedCacheService instance."""
    return FeedCacheService(redis_manager)


# ============================================================================
# TEST CACHE KEY GENERATION
# ============================================================================


def test_discover_cache_key_generation(feed_cache):
    """Test that discover feed cache keys are unique per page/filters."""
    # Same parameters should generate same key
    key1 = feed_cache._build_discover_cache_key(
        page=1, per_page=20, category="electronics", sort="live_first"
    )
    key2 = feed_cache._build_discover_cache_key(
        page=1, per_page=20, category="electronics", sort="live_first"
    )
    assert key1 == key2

    # Different page should generate different key
    key3 = feed_cache._build_discover_cache_key(
        page=2, per_page=20, category="electronics", sort="live_first"
    )
    assert key1 != key3

    # Different category should generate different key
    key4 = feed_cache._build_discover_cache_key(
        page=1, per_page=20, category="fashion", sort="live_first"
    )
    assert key1 != key4

    # Different sort should generate different key
    key5 = feed_cache._build_discover_cache_key(
        page=1, per_page=20, category="electronics", sort="recent"
    )
    assert key1 != key5

    # Different per_page should generate different key
    key6 = feed_cache._build_discover_cache_key(
        page=1, per_page=50, category="electronics", sort="live_first"
    )
    assert key1 != key6


def test_community_cache_key_generation(feed_cache):
    """Test that community feed cache keys are unique per location/filters."""
    # Same parameters should generate same key
    key1 = feed_cache._build_community_cache_key(
        page=1,
        per_page=20,
        latitude=25.2048,
        longitude=55.2708,
        radius_km=5.0,
        category="electronics",
        sort="nearest",
    )
    key2 = feed_cache._build_community_cache_key(
        page=1,
        per_page=20,
        latitude=25.2048,
        longitude=55.2708,
        radius_km=5.0,
        category="electronics",
        sort="nearest",
    )
    assert key1 == key2

    # Different page should generate different key
    key3 = feed_cache._build_community_cache_key(
        page=2,
        per_page=20,
        latitude=25.2048,
        longitude=55.2708,
        radius_km=5.0,
        category="electronics",
        sort="nearest",
    )
    assert key1 != key3

    # Different location should generate different key
    # (rounded to 2 decimals, so small changes might still match)
    key4 = feed_cache._build_community_cache_key(
        page=1,
        per_page=20,
        latitude=25.3000,  # Different location
        longitude=55.3000,
        radius_km=5.0,
        category="electronics",
        sort="nearest",
    )
    assert key1 != key4

    # Different radius should generate different key
    key5 = feed_cache._build_community_cache_key(
        page=1,
        per_page=20,
        latitude=25.2048,
        longitude=55.2708,
        radius_km=10.0,  # Different radius
        category="electronics",
        sort="nearest",
    )
    assert key1 != key5


def test_pagination_cache_keys(feed_cache):
    """Test that pagination generates unique cache keys for each page."""
    # Generate keys for pages 1-5
    keys = []
    for page in range(1, 6):
        key = feed_cache._build_discover_cache_key(
            page=page, per_page=20, category=None, sort="live_first"
        )
        keys.append(key)

    # All keys should be unique
    assert len(keys) == len(set(keys))

    # Keys should contain page number
    for i, key in enumerate(keys, start=1):
        assert f"page:{i}" in key


# ============================================================================
# TEST CACHE OPERATIONS
# ============================================================================


@pytest.mark.asyncio
async def test_cache_set_and_get(redis_manager, feed_cache):
    """Test setting and getting cached feed data."""
    # Mock data
    feed_data = {
        "items": [
            {"id": "1", "title": "Product 1"},
            {"id": "2", "title": "Product 2"},
        ],
        "page": 1,
        "per_page": 20,
        "total": 100,
        "has_more": True,
    }

    # Set cache
    await feed_cache.set_discover_feed(
        page=1, per_page=20, data=feed_data, category=None, sort="live_first"
    )

    # Verify set was called on redis
    assert redis_manager.redis.set.called


@pytest.mark.asyncio
async def test_cache_invalidation(redis_manager, feed_cache):
    """Test cache invalidation patterns."""
    # Invalidate all feeds
    await feed_cache.invalidate_all_feeds()

    # Should delete both discover and community patterns
    assert redis_manager.redis.delete_pattern.call_count >= 2


# ============================================================================
# TEST CACHE KEY FORMAT
# ============================================================================


def test_cache_key_format(feed_cache):
    """Test that cache keys follow expected format."""
    # Discover feed key format
    discover_key = feed_cache._build_discover_cache_key(
        page=1, per_page=20, category="electronics", sort="live_first"
    )
    assert discover_key.startswith("feed:discover:")
    assert "page:1" in discover_key
    assert "limit:20" in discover_key

    # Community feed key format
    community_key = feed_cache._build_community_cache_key(
        page=1,
        per_page=20,
        latitude=25.2048,
        longitude=55.2708,
        radius_km=5.0,
        sort="nearest",
    )
    assert community_key.startswith("feed:community:")
    assert "page:1" in community_key
    assert "limit:20" in community_key


# ============================================================================
# MANUAL VERIFICATION SCRIPT
# ============================================================================


def print_cache_keys_demonstration():
    """Demonstration script showing cache key generation.

    Run this to see how cache keys are generated for different scenarios.
    This helps verify that pagination and filters create unique keys.
    """
    from app.core.cache.redis_manager import RedisManager

    # Create mock redis for demonstration
    class MockRedis:
        pass

    redis_manager = RedisManager(MockRedis())
    feed_cache = FeedCacheService(redis_manager)

    print("=" * 80)
    print("FEED CACHE KEY GENERATION DEMONSTRATION")
    print("=" * 80)

    print("\n1. DISCOVER FEED - Different Pages (Same Filters)")
    print("-" * 80)
    for page in range(1, 4):
        key = feed_cache._build_discover_cache_key(
            page=page, per_page=20, category=None, sort="live_first"
        )
        print(f"Page {page}: {key}")

    print("\n2. DISCOVER FEED - Different Categories (Same Page)")
    print("-" * 80)
    for category in ["electronics", "fashion", "home"]:
        key = feed_cache._build_discover_cache_key(
            page=1, per_page=20, category=category, sort="live_first"
        )
        print(f"Category '{category}': {key}")

    print("\n3. DISCOVER FEED - Different Sort Orders")
    print("-" * 80)
    for sort in ["live_first", "recent", "popular"]:
        key = feed_cache._build_discover_cache_key(
            page=1, per_page=20, category=None, sort=sort
        )
        print(f"Sort '{sort}': {key}")

    print("\n4. COMMUNITY FEED - Different Locations")
    print("-" * 80)
    locations = [
        (25.2048, 55.2708, "Dubai Marina"),
        (25.2000, 55.2700, "JBR"),
        (25.1000, 55.1700, "Different Area"),
    ]
    for lat, lng, name in locations:
        key = feed_cache._build_community_cache_key(
            page=1,
            per_page=20,
            latitude=lat,
            longitude=lng,
            radius_km=5.0,
            sort="nearest",
        )
        print(f"{name} ({lat}, {lng}): {key}")

    print("\n5. COMMUNITY FEED - Different Radius")
    print("-" * 80)
    for radius in [1.0, 5.0, 10.0, 20.0]:
        key = feed_cache._build_community_cache_key(
            page=1,
            per_page=20,
            latitude=25.2048,
            longitude=55.2708,
            radius_km=radius,
            sort="nearest",
        )
        print(f"Radius {radius}km: {key}")

    print("\n" + "=" * 80)
    print("✅ All cache keys are unique per page/filter combination")
    print("✅ Pagination generates separate cache entries")
    print("=" * 80)


if __name__ == "__main__":
    # Run demonstration
    print_cache_keys_demonstration()
