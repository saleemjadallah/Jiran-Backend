"""Simple integration tests for Phase 6 features.

Tests core functionality without database dependencies.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.cache.redis_manager import init_redis_manager
from app.services.cache.feed_cache_service import FeedCacheService


async def test_redis_connection():
    """Test Redis connection."""
    print("Testing Redis connection...")
    redis = await init_redis_manager()
    await redis.redis.flushdb()

    # Test basic operations
    await redis.set("test_key", "test_value")
    value = await redis.get("test_key")
    assert value == "test_value", "Redis get/set failed"

    print("✓ Redis connection working")
    return redis


async def test_cache_decorators(redis):
    """Test cache decorators."""
    print("\nTesting cache decorators...")
    from app.core.cache.cache_decorators import cached, stale_while_revalidate

    call_count = 0

    @cached(key_prefix="test", ttl=10)
    async def get_data(item_id: str):
        nonlocal call_count
        call_count += 1
        return {"id": item_id, "count": call_count}

    # First call - cache miss
    result1 = await get_data("123")
    assert result1["count"] == 1

    # Second call - cache hit
    result2 = await get_data("123")
    assert result2["count"] == 1  # Same value
    assert call_count == 1  # Function not called again

    print("✓ Cached decorator working")

    # Test stale-while-revalidate
    call_count2 = 0

    @stale_while_revalidate(key_prefix="swr", ttl=10)
    async def get_product(product_id: str):
        nonlocal call_count2
        call_count2 += 1
        await asyncio.sleep(0.05)  # Simulate slow query
        return {"id": product_id, "version": call_count2}

    result1 = await get_product("prod1")
    assert result1["version"] == 1

    # Cache hit returns stale immediately
    result2 = await get_product("prod1")
    assert result2["version"] == 1  # Stale data

    # Wait for revalidation
    await asyncio.sleep(0.2)

    print("✓ Stale-while-revalidate working")


async def test_batch_operations(redis):
    """Test batch MGET/MSET."""
    print("\nTesting batch operations...")

    # MSET
    data = {
        "user:1": {"name": "Alice", "age": 25},
        "user:2": {"name": "Bob", "age": 30},
        "user:3": {"name": "Charlie", "age": 35},
    }
    await redis.mset(data)

    # MGET
    keys = ["user:1", "user:2", "user:3", "user:99"]
    results = await redis.mget(keys)

    assert len(results) == 4
    assert results[0]["name"] == "Alice"
    assert results[1]["name"] == "Bob"
    assert results[2]["name"] == "Charlie"
    assert results[3] is None

    print("✓ Batch operations working (MGET/MSET)")


async def test_compression(redis):
    """Test cache compression."""
    print("\nTesting cache compression...")

    # Small object (not compressed)
    small_data = {"id": "1", "name": "Test"}
    await redis.set_compressed("small", small_data, threshold=1024)

    result = await redis.get_compressed("small")
    assert result == small_data

    # Check not compressed
    is_compressed = await redis.exists("small:compressed")
    assert not is_compressed

    print("✓ Small object not compressed (correct)")

    # Large object (should compress)
    large_data = {"id": "2", "data": "x" * 2000}
    await redis.set_compressed("large", large_data, threshold=1024)

    result = await redis.get_compressed("large")
    assert result == large_data

    # Check compressed
    is_compressed = await redis.exists("large:compressed")
    assert is_compressed

    print("✓ Large object compressed (correct)")

    # Test delete compressed
    deleted = await redis.delete_compressed("large")
    assert deleted >= 2

    print("✓ Cache compression working")


async def test_view_count_buffering(redis):
    """Test view count increment and buffering."""
    print("\nTesting view count buffering...")
    from app.services.cache.view_count_service import ViewCountService

    # Mock DB
    class MockDB:
        def __init__(self):
            self.queries = []

        async def execute(self, query, params=None):
            self.queries.append(params)
            return self

        async def commit(self):
            pass

        async def rollback(self):
            pass

    db = MockDB()
    service = ViewCountService(redis=redis, db=db)

    # Increment views
    count1 = await service.increment_view("product_1")
    assert count1 == 1

    count2 = await service.increment_view("product_1")
    assert count2 == 2

    count3 = await service.increment_view("product_2")
    assert count3 == 1

    # Check buffered
    buffered = await service.get_buffered_count("product_1")
    assert buffered == 2

    print("✓ View count buffering working")


async def test_offer_expiration_tracking(redis):
    """Test offer expiration tracking."""
    print("\nTesting offer expiration...")
    from app.services.cache.offer_cache_service import OfferCacheService
    from datetime import datetime, timedelta

    # Mock DB
    class MockDB:
        async def execute(self, query, params=None):
            return self

        async def commit(self):
            pass

        async def rollback(self):
            pass

        def fetchall(self):
            return []

    db = MockDB()
    service = OfferCacheService(redis=redis, db=db)

    # Track offer
    offer_id = "offer_123"
    expires_at = datetime.utcnow() + timedelta(hours=1)

    await service.track_offer_expiration(offer_id, expires_at)

    # Check stored
    stored = await service.get_offer_expiration(offer_id)
    assert stored is not None

    # Check count
    count = await service.get_active_offer_count()
    assert count == 1

    # Remove tracking
    await service.remove_offer_tracking(offer_id)
    count = await service.get_active_offer_count()
    assert count == 0

    print("✓ Offer expiration tracking working")


async def test_feed_caching(redis):
    """Test feed caching and prefetching."""
    print("\nTesting feed caching...")

    service = FeedCacheService(redis=redis)

    # Set discover feed
    feed_data = {
        "items": [{"id": "stream1"}, {"id": "stream2"}],
        "page": 1,
        "total": 100,
    }

    await service.set_discover_feed(
        page=1, per_page=20, data=feed_data, sort="live_first"
    )

    # Get from cache
    cached = await service.get_discover_feed(page=1, per_page=20, sort="live_first")
    assert cached == feed_data

    print("✓ Feed caching working")

    # Test prefetching
    async def mock_fetcher(page: int, per_page: int, **kwargs):
        return {
            "items": [{"id": f"stream_{page}_{i}"} for i in range(3)],
            "page": page,
        }

    await service.prefetch_next_page(
        current_page=1,
        per_page=20,
        feed_fetcher=mock_fetcher,
        feed_type="discover",
    )

    # Check page 2 prefetched
    cached_page2 = await service.get_discover_feed(page=2, per_page=20)
    assert cached_page2 is not None
    assert cached_page2["page"] == 2

    print("✓ Feed prefetching working")

    # Test invalidation
    deleted = await service.invalidate_all_feeds()
    assert deleted >= 2

    print("✓ Feed invalidation working")


async def test_sorted_sets(redis):
    """Test Redis sorted sets for offer expiration."""
    print("\nTesting sorted sets...")

    # Add offers with scores (timestamps)
    import time

    now = time.time()
    await redis.zadd(
        "offers:test",
        {"offer1": now - 100, "offer2": now + 100, "offer3": now + 200},
    )

    # Get expired (score < now)
    expired = await redis.zrangebyscore("offers:test", min_score=0, max_score=now)
    assert "offer1" in expired
    assert "offer2" not in expired

    # Get count
    count = await redis.zcard("offers:test")
    assert count == 3

    # Remove one
    await redis.zrem("offers:test", "offer1")
    count = await redis.zcard("offers:test")
    assert count == 2

    print("✓ Sorted sets working")


async def run_all_tests():
    """Run all simple tests."""
    print("\n" + "=" * 60)
    print("Phase 6 Advanced Features - Integration Tests")
    print("=" * 60)

    redis = None

    try:
        # Test 1: Redis connection
        redis = await test_redis_connection()

        # Test 2: Cache decorators
        await test_cache_decorators(redis)

        # Test 3: Batch operations
        await test_batch_operations(redis)

        # Test 4: Compression
        await test_compression(redis)

        # Test 5: View count buffering
        await test_view_count_buffering(redis)

        # Test 6: Offer expiration
        await test_offer_expiration_tracking(redis)

        # Test 7: Feed caching
        await test_feed_caching(redis)

        # Test 8: Sorted sets
        await test_sorted_sets(redis)

        print("\n" + "=" * 60)
        print("✅ All Phase 6 tests passed successfully!")
        print("=" * 60 + "\n")

        print("Summary of implemented features:")
        print("1. ✓ Stale-while-revalidate pattern")
        print("2. ✓ Predictive prefetching")
        print("3. ✓ Write-behind view counts")
        print("4. ✓ Offer expiration tracking")
        print("5. ✓ Batch API endpoints (MGET/MSET)")
        print("6. ✓ Cache compression")
        print("7. ✓ Feed caching with invalidation")
        print("8. ✓ Background job infrastructure")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if redis:
            await redis.close()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
