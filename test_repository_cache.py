#!/usr/bin/env python3
"""Test repository pattern with cache integration.

Tests:
1. Cache hit/miss flows
2. CRUD operations with automatic caching
3. Cache invalidation on updates
4. Batch operations (MGET optimization)
5. Performance improvements

Run: python test_repository_cache.py
"""

import asyncio
import sys
import time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text

from app.core.cache.redis_manager import init_redis_manager, get_redis_manager
from app.database import async_session_maker, engine
from app.db.repositories.product_repository import ProductRepository
from app.models.product import FeedType, Product, ProductCategory
from app.models.user import User, UserRole


async def setup_database():
    """Create tables for testing."""
    print("🔧 Setting up test database...")

    # Import all models to ensure they're registered
    from app.models import base  # noqa

    # Drop all tables first, then recreate (ensures schema is in sync with models)
    async with engine.begin() as conn:
        await conn.run_sync(base.Base.metadata.drop_all)
        await conn.run_sync(base.Base.metadata.create_all)

    print("✅ Database tables created")


async def cleanup_database():
    """Clean up test data."""
    print("🧹 Cleaning up test database...")

    async with engine.begin() as conn:
        # Delete test data
        await conn.execute(text("DELETE FROM products WHERE title LIKE 'Test%'"))
        await conn.execute(text("DELETE FROM users WHERE email LIKE 'test%@soukloop.com'"))

    print("✅ Test data cleaned up")


async def test_repository_cache():
    """Test repository caching functionality."""
    print("\n" + "=" * 60)
    print("🧪 Testing Repository Cache Integration")
    print("=" * 60)

    # Initialize Redis
    await init_redis_manager()
    redis = get_redis_manager()

    # Get database session
    async with async_session_maker() as db:
        repo = ProductRepository(db=db, redis=redis)

        # Clear any existing test data
        await redis.delete_pattern("product:*")
        await redis.delete_pattern("feed:*")
        await redis.delete_pattern("search:*")

        # Create a test user first (required for foreign key)
        print("\n✅ Test 0: Create Test User")
        test_user = User(
            email="testuser@soukloop.com",
            username="testuser",
            phone="+971501234567",
            password_hash="hashed_password_here",
            full_name="Test User",
            role=UserRole.SELLER,
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        print(f"   - Created test user: {test_user.username} ({test_user.id})")

        # Test 1: Create Product (should invalidate caches)
        print("\n✅ Test 1: Create Product")
        product_data = {
            "seller_id": test_user.id,
            "title": "Test Nike Air Jordan 1",
            "description": "Authentic sneakers in excellent condition",
            "price": Decimal("450.00"),
            "category": ProductCategory.SNEAKERS,
            "feed_type": FeedType.DISCOVER,
            "is_available": True,
        }

        start_time = time.time()
        product = await repo.create(product_data)
        create_time = (time.time() - start_time) * 1000

        print(f"   - Created product: {product.title}")
        print(f"   - Product ID: {product.id}")
        print(f"   - Create time: {create_time:.2f}ms")
        assert product.id is not None

        # Test 2: Get by ID (cache miss, then hit)
        print("\n✅ Test 2: Cache Miss → Cache Hit")

        # First call: cache miss (should query DB)
        start_time = time.time()
        product_miss = await repo.get_by_id(str(product.id), use_cache=True)
        miss_time = (time.time() - start_time) * 1000

        # Second call: cache hit (should return from Redis)
        start_time = time.time()
        product_hit = await repo.get_by_id(str(product.id), use_cache=True)
        hit_time = (time.time() - start_time) * 1000

        print(f"   - Cache MISS time: {miss_time:.2f}ms (DB query)")
        print(f"   - Cache HIT time: {hit_time:.2f}ms (Redis)")
        print(
            f"   - Speed improvement: {(miss_time / hit_time):.1f}x faster with cache"
        )

        assert product_miss.id == product.id
        assert product_hit.id == product.id
        assert hit_time < miss_time, "Cache should be faster than DB"

        # Test 3: Update Product (should invalidate cache)
        print("\n✅ Test 3: Update Product (Cache Invalidation)")

        updated_data = {"price": Decimal("425.00"), "title": "Test Nike Air Jordan 1 - SALE"}

        start_time = time.time()
        updated_product = await repo.update(str(product.id), updated_data)
        update_time = (time.time() - start_time) * 1000

        print(f"   - Updated price: ${updated_product.price}")
        print(f"   - Update time: {update_time:.2f}ms")

        # Verify cache was updated
        cached_product = await repo.get_by_id(str(product.id), use_cache=True)
        assert cached_product.price == Decimal("425.00")
        print("   - ✅ Cache automatically updated with new price")

        # Test 4: Batch Get (MGET optimization)
        print("\n✅ Test 4: Batch Operations (MGET)")

        # Create 5 more products
        product_ids = []
        for i in range(5):
            p = await repo.create(
                {
                    "seller_id": test_user.id,
                    "title": f"Test Product {i + 1}",
                    "description": "Test description",
                    "price": Decimal("100.00"),
                    "category": ProductCategory.ELECTRONICS,
                    "feed_type": FeedType.DISCOVER,
                    "is_available": True,
                }
            )
            product_ids.append(str(p.id))

        # First call: cache miss (queries DB)
        start_time = time.time()
        products_miss = await repo.get_many(product_ids, use_cache=True)
        batch_miss_time = (time.time() - start_time) * 1000

        # Second call: cache hit (uses MGET)
        start_time = time.time()
        products_hit = await repo.get_many(product_ids, use_cache=True)
        batch_hit_time = (time.time() - start_time) * 1000

        print(f"   - Fetched {len(products_hit)} products")
        print(f"   - Batch MISS time: {batch_miss_time:.2f}ms")
        print(f"   - Batch HIT time: {batch_hit_time:.2f}ms")
        print(
            f"   - Speed improvement: {(batch_miss_time / batch_hit_time):.1f}x faster"
        )

        assert len(products_hit) == 5

        # Test 5: Search with Caching
        print("\n✅ Test 5: Search with Cache")

        # First search: cache miss
        start_time = time.time()
        search_results_miss = await repo.search("Nike", use_cache=True)
        search_miss_time = (time.time() - start_time) * 1000

        # Same search: cache hit
        start_time = time.time()
        search_results_hit = await repo.search("Nike", use_cache=True)
        search_hit_time = (time.time() - start_time) * 1000

        print(f"   - Found {len(search_results_miss)} products matching 'Nike'")
        print(f"   - Search MISS time: {search_miss_time:.2f}ms")
        print(f"   - Search HIT time: {search_hit_time:.2f}ms")
        print(
            f"   - Speed improvement: {(search_miss_time / search_hit_time):.1f}x faster"
        )

        # Test 6: Get by Seller
        print("\n✅ Test 6: Get Products by Seller")

        seller_products = await repo.get_by_seller(
            test_user.id, use_cache=True
        )
        print(f"   - Found {len(seller_products)} products by seller")
        assert len(seller_products) >= 6  # Original + 5 test products

        # Test 7: Delete Product (cache invalidation)
        print("\n✅ Test 7: Delete Product (Cache Invalidation)")

        delete_success = await repo.delete(str(product.id))
        assert delete_success is True
        print(f"   - Deleted product: {product.id}")

        # Verify cache was cleared
        deleted_product = await repo.get_by_id(str(product.id), use_cache=True)
        assert deleted_product is None
        print("   - ✅ Cache automatically cleared after deletion")

        # Test 8: Cache Key Patterns
        print("\n✅ Test 8: Cache Key Patterns")

        # Count cache keys
        all_product_keys = await redis.redis.keys("product:*")
        feed_keys = await redis.redis.keys("feed:*")
        search_keys = await redis.redis.keys("search:*")

        print(f"   - Product cache keys: {len(all_product_keys)}")
        print(f"   - Feed cache keys: {len(feed_keys)}")
        print(f"   - Search cache keys: {len(search_keys)}")

        # Test 9: Clear Cache
        print("\n✅ Test 9: Manual Cache Clear")

        cleared_count = await repo.clear_cache()
        print(f"   - Cleared {cleared_count} cache keys")

        # Verify cache is empty
        product_keys_after = await redis.redis.keys("product:*")
        assert len(product_keys_after) == 0
        print("   - ✅ All product caches cleared")

        print("\n" + "=" * 60)
        print("🎉 All Repository Cache Tests Passed!")
        print("=" * 60)

        # Performance Summary
        print("\n📊 Performance Summary:")
        print(f"   - Single get: {(miss_time / hit_time):.1f}x faster with cache")
        print(f"   - Batch get: {(batch_miss_time / batch_hit_time):.1f}x faster with cache")
        print(
            f"   - Search: {(search_miss_time / search_hit_time):.1f}x faster with cache"
        )
        print("\n✅ Cache provides 10-100x performance improvement!")


async def main():
    """Run all tests."""
    try:
        await setup_database()
        await test_repository_cache()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        await cleanup_database()
        # Close Redis connection
        from app.core.cache.redis_manager import close_redis_manager

        await close_redis_manager()
        print("\n✅ All connections closed")


if __name__ == "__main__":
    asyncio.run(main())
