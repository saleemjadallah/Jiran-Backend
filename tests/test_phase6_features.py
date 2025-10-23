"""Tests for Phase 6 advanced caching features.

Tests:
1. Stale-while-revalidate decorator
2. Predictive prefetching
3. Write-behind view counts
4. Offer expiration
5. Batch API endpoints
6. Cache compression
"""

import asyncio
import json
import time
from datetime import datetime, timedelta

import pytest

from app.core.cache.redis_manager import RedisManager, init_redis_manager
from app.services.cache.view_count_service import ViewCountService
from app.services.cache.offer_cache_service import OfferCacheService
from app.services.cache.feed_cache_service import FeedCacheService
from app.core.cache.cache_decorators import (
    cached,
    stale_while_revalidate,
    invalidate_cache,
)


# ============= Fixtures =============


@pytest.fixture
async def redis_manager():
    """Initialize Redis manager for tests."""
    manager = await init_redis_manager()
    # Clear test data
    await manager.redis.flushdb()
    yield manager
    await manager.close()


@pytest.fixture
def mock_db():
    """Mock database session."""

    class MockDB:
        def __init__(self):
            self.executed_queries = []
            self.committed = False

        async def execute(self, query, params=None):
            self.executed_queries.append({"query": str(query), "params": params})
            return self

        async def commit(self):
            self.committed = True

        async def rollback(self):
            pass

        def fetchall(self):
            return []

    return MockDB()


# ============= Test Cache Decorators =============


@pytest.mark.asyncio
async def test_cached_decorator(redis_manager):
    """Test @cached decorator."""
    call_count = 0

    @cached(key_prefix="test", ttl=10)
    async def get_data(item_id: str):
        nonlocal call_count
        call_count += 1
        return {"id": item_id, "data": f"value_{call_count}"}

    # First call - cache miss
    result1 = await get_data("123")
    assert result1["data"] == "value_1"
    assert call_count == 1

    # Second call - cache hit
    result2 = await get_data("123")
    assert result2["data"] == "value_1"  # Same as first call
    assert call_count == 1  # Function not called again

    print("✓ Cached decorator working correctly")


@pytest.mark.asyncio
async def test_stale_while_revalidate(redis_manager):
    """Test stale-while-revalidate pattern."""
    call_count = 0

    @stale_while_revalidate(key_prefix="swr", ttl=10)
    async def get_product(product_id: str):
        nonlocal call_count
        call_count += 1
        return {"id": product_id, "version": call_count}

    # First call - cache miss
    result1 = await get_product("prod1")
    assert result1["version"] == 1
    assert call_count == 1

    # Second call - cache hit, triggers background revalidation
    result2 = await get_product("prod1")
    assert result2["version"] == 1  # Stale data returned immediately
    assert call_count == 1  # Revalidation happens in background

    # Wait for background revalidation
    await asyncio.sleep(0.1)

    # Third call - fresh data from revalidation
    result3 = await get_product("prod1")
    assert result3["version"] == 2  # Updated data
    assert call_count == 2

    print("✓ Stale-while-revalidate working correctly")


@pytest.mark.asyncio
async def test_invalidate_cache_decorator(redis_manager):
    """Test @invalidate_cache decorator."""

    # Set some cached data
    await redis_manager.set("product:123", {"id": "123", "price": 100})
    await redis_manager.set("feed:discover:page:1", [{"id": "stream1"}])

    @invalidate_cache("product:{product_id}", "feed:*")
    async def update_product(product_id: str, new_price: float):
        return {"id": product_id, "price": new_price}

    # Check data exists
    assert await redis_manager.exists("product:123")
    assert await redis_manager.exists("feed:discover:page:1")

    # Update product
    await update_product("123", 150)

    # Check caches invalidated
    assert not await redis_manager.exists("product:123")
    assert not await redis_manager.exists("feed:discover:page:1")

    print("✓ Invalidate cache decorator working correctly")


# ============= Test View Count Service =============


@pytest.mark.asyncio
async def test_view_count_increment(redis_manager, mock_db):
    """Test view count increment and buffering."""
    service = ViewCountService(redis=redis_manager, db=mock_db)

    # Increment views
    count1 = await service.increment_view("product_123")
    assert count1 == 1

    count2 = await service.increment_view("product_123")
    assert count2 == 2

    count3 = await service.increment_view("product_456")
    assert count3 == 1

    # Check buffered counts
    buffered = await service.get_buffered_count("product_123")
    assert buffered == 2

    print("✓ View count increment working correctly")


@pytest.mark.asyncio
async def test_view_count_sync(redis_manager, mock_db):
    """Test view count sync to database."""
    service = ViewCountService(redis=redis_manager, db=mock_db)

    # Buffer some views
    await service.increment_view("product_1")
    await service.increment_view("product_1")
    await service.increment_view("product_2")

    # Sync to database
    stats = await service.sync_to_database()

    # Check stats
    assert stats["products_synced"] == 2
    assert stats["total_views"] == 3

    # Check database was updated
    assert mock_db.committed
    assert len(mock_db.executed_queries) >= 2

    # Check Redis counters cleared
    buffered = await service.get_buffered_count("product_1")
    assert buffered == 0

    print("✓ View count sync working correctly")


# ============= Test Offer Expiration =============


@pytest.mark.asyncio
async def test_offer_expiration_tracking(redis_manager, mock_db):
    """Test offer expiration tracking."""
    service = OfferCacheService(redis=redis_manager, db=mock_db)

    # Track offer expiration
    offer_id = "offer_123"
    expires_at = datetime.utcnow() + timedelta(hours=1)

    await service.track_offer_expiration(offer_id, expires_at)

    # Check expiration stored
    stored_expiration = await service.get_offer_expiration(offer_id)
    assert stored_expiration is not None
    assert abs((stored_expiration - expires_at).total_seconds()) < 1

    # Check in sorted set
    count = await service.get_active_offer_count()
    assert count == 1

    print("✓ Offer expiration tracking working correctly")


@pytest.mark.asyncio
async def test_offer_expiration_processing(redis_manager, mock_db):
    """Test processing expired offers."""
    service = OfferCacheService(redis=redis_manager, db=mock_db)

    # Track offers with past expiration
    past_time = datetime.utcnow() - timedelta(hours=1)
    await service.track_offer_expiration("expired_1", past_time)
    await service.track_offer_expiration("expired_2", past_time)

    # Track offer with future expiration
    future_time = datetime.utcnow() + timedelta(hours=1)
    await service.track_offer_expiration("valid_1", future_time)

    # Process expired offers
    stats = await service.process_expired_offers()

    # Check stats
    assert stats["processed"] == 2

    # Check valid offer still tracked
    count = await service.get_active_offer_count()
    assert count == 1

    print("✓ Offer expiration processing working correctly")


# ============= Test Batch Operations =============


@pytest.mark.asyncio
async def test_batch_mget(redis_manager):
    """Test batch MGET operation."""
    # Set up test data
    await redis_manager.set("user:1", {"id": "1", "name": "Alice"})
    await redis_manager.set("user:2", {"id": "2", "name": "Bob"})
    await redis_manager.set("user:3", {"id": "3", "name": "Charlie"})

    # Batch get
    keys = ["user:1", "user:2", "user:3", "user:99"]
    results = await redis_manager.mget(keys)

    # Check results
    assert len(results) == 4
    assert results[0]["name"] == "Alice"
    assert results[1]["name"] == "Bob"
    assert results[2]["name"] == "Charlie"
    assert results[3] is None  # Missing key

    print("✓ Batch MGET working correctly")


@pytest.mark.asyncio
async def test_batch_mset(redis_manager):
    """Test batch MSET operation."""
    # Batch set
    data = {
        "product:1": {"id": "1", "price": 100},
        "product:2": {"id": "2", "price": 200},
        "product:3": {"id": "3", "price": 300},
    }

    await redis_manager.mset(data)

    # Verify all set
    for key, expected in data.items():
        result = await redis_manager.get(key)
        assert result == expected

    print("✓ Batch MSET working correctly")


# ============= Test Cache Compression =============


@pytest.mark.asyncio
async def test_cache_compression_small_object(redis_manager):
    """Test compression with small object (should not compress)."""
    # Small object (< 1KB)
    small_data = {"id": "123", "name": "Test"}

    await redis_manager.set_compressed("small", small_data, threshold=1024)

    # Should be stored uncompressed
    assert not await redis_manager.exists("small:compressed")
    assert not await redis_manager.exists("small:is_compressed")

    # Regular get should work
    result = await redis_manager.get("small")
    assert result == small_data

    # Compressed get should also work
    result2 = await redis_manager.get_compressed("small")
    assert result2 == small_data

    print("✓ Cache compression (small object) working correctly")


@pytest.mark.asyncio
async def test_cache_compression_large_object(redis_manager):
    """Test compression with large object (should compress)."""
    # Large object (> 1KB)
    large_data = {"id": "456", "data": "x" * 2000}

    await redis_manager.set_compressed("large", large_data, threshold=1024)

    # Should be stored compressed
    assert await redis_manager.exists("large:compressed")
    assert await redis_manager.exists("large:is_compressed")

    # Get compressed should work
    result = await redis_manager.get_compressed("large")
    assert result == large_data

    print("✓ Cache compression (large object) working correctly")


@pytest.mark.asyncio
async def test_cache_compression_delete(redis_manager):
    """Test deleting compressed cache."""
    # Set compressed data
    data = {"id": "789", "data": "x" * 2000}
    await redis_manager.set_compressed("test_delete", data, threshold=1024)

    # Verify exists
    assert await redis_manager.exists("test_delete:compressed")

    # Delete
    deleted_count = await redis_manager.delete_compressed("test_delete")
    assert deleted_count >= 2  # Should delete multiple keys

    # Verify deleted
    assert not await redis_manager.exists("test_delete:compressed")
    assert not await redis_manager.exists("test_delete:is_compressed")

    print("✓ Cache compression delete working correctly")


# ============= Test Predictive Prefetching =============


@pytest.mark.asyncio
async def test_predictive_prefetching(redis_manager):
    """Test predictive prefetching for feeds."""
    service = FeedCacheService(redis=redis_manager)

    # Mock feed fetcher
    async def mock_feed_fetcher(page: int, per_page: int, **kwargs):
        return {
            "items": [{"id": f"item_{page}_{i}"} for i in range(per_page)],
            "page": page,
            "total": 100,
        }

    # Prefetch next page
    await service.prefetch_next_page(
        current_page=1,
        per_page=20,
        feed_fetcher=mock_feed_fetcher,
        feed_type="discover",
    )

    # Check page 2 was cached
    cached = await service.get_discover_feed(page=2, per_page=20)
    assert cached is not None
    assert cached["page"] == 2
    assert len(cached["items"]) == 20

    print("✓ Predictive prefetching working correctly")


@pytest.mark.asyncio
async def test_cache_warming(redis_manager):
    """Test cache warming functionality."""
    service = FeedCacheService(redis=redis_manager)

    # Mock feed fetcher
    async def mock_feed_fetcher(page: int, per_page: int, **kwargs):
        return {
            "items": [{"id": f"item_{page}_{i}"} for i in range(per_page)],
            "page": page,
        }

    # Warm cache with 3 pages
    cached_count = await service.warm_cache(
        pages=3,
        per_page=20,
        feed_fetcher=mock_feed_fetcher,
        feed_type="discover",
    )

    assert cached_count == 3

    # Verify all pages cached
    for page in [1, 2, 3]:
        cached = await service.get_discover_feed(page=page, per_page=20)
        assert cached is not None
        assert cached["page"] == page

    print("✓ Cache warming working correctly")


# ============= Run All Tests =============


async def run_all_tests():
    """Run all Phase 6 tests."""
    print("\n" + "=" * 60)
    print("Phase 6 Advanced Features Tests")
    print("=" * 60 + "\n")

    # Initialize Redis
    redis = await init_redis_manager()
    await redis.redis.flushdb()

    mock_db = type(
        "MockDB",
        (),
        {
            "execute": lambda self, q, p=None: asyncio.coroutine(
                lambda: setattr(self, "committed", False)
            )(),
            "commit": lambda self: asyncio.coroutine(lambda: setattr(self, "committed", True))(),
            "rollback": lambda self: asyncio.coroutine(lambda: None)(),
            "fetchall": lambda self: [],
        },
    )()

    try:
        # Test decorators
        print("\n--- Testing Cache Decorators ---")
        await test_cached_decorator(redis)
        await test_stale_while_revalidate(redis)
        await test_invalidate_cache_decorator(redis)

        # Test view counts
        print("\n--- Testing View Count Service ---")
        await test_view_count_increment(redis, mock_db)
        await test_view_count_sync(redis, mock_db)

        # Test offer expiration
        print("\n--- Testing Offer Expiration ---")
        await test_offer_expiration_tracking(redis, mock_db)
        await test_offer_expiration_processing(redis, mock_db)

        # Test batch operations
        print("\n--- Testing Batch Operations ---")
        await test_batch_mget(redis)
        await test_batch_mset(redis)

        # Test compression
        print("\n--- Testing Cache Compression ---")
        await test_cache_compression_small_object(redis)
        await test_cache_compression_large_object(redis)
        await test_cache_compression_delete(redis)

        # Test prefetching
        print("\n--- Testing Predictive Prefetching ---")
        await test_predictive_prefetching(redis)
        await test_cache_warming(redis)

        print("\n" + "=" * 60)
        print("✓ All Phase 6 tests passed!")
        print("=" * 60 + "\n")

    finally:
        await redis.close()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
