#!/usr/bin/env python3
"""Test Redis connection and RedisManager operations.

Run this script to verify Redis is working correctly:
    python test_redis.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.cache.redis_manager import RedisManager
from app.core.cache.cache_keys import CacheKeys


async def test_redis():
    """Test Redis connection and basic operations."""
    print("🔍 Testing Redis Connection...\n")

    # Initialize Redis manager
    redis = RedisManager()

    try:
        # Test 1: String Operations
        print("✅ Test 1: String Operations")
        await redis.set("test:string", "Hello Redis!", ttl=60)
        value = await redis.get("test:string")
        assert value == "Hello Redis!", f"Expected 'Hello Redis!', got {value}"
        print(f"   - Set & Get: '{value}'")

        # Test 2: JSON Serialization
        print("\n✅ Test 2: JSON Serialization")
        test_data = {"name": "Souk Loop", "version": "1.0", "active": True}
        await redis.set("test:json", test_data, ttl=60)
        retrieved = await redis.get("test:json")
        assert retrieved == test_data, f"Expected {test_data}, got {retrieved}"
        print(f"   - Stored: {test_data}")
        print(f"   - Retrieved: {retrieved}")

        # Test 3: Counter Operations
        print("\n✅ Test 3: Counter Operations")
        await redis.set("test:counter", "0")
        count1 = await redis.increment("test:counter")
        count2 = await redis.increment("test:counter", 5)
        count3 = await redis.decrement("test:counter", 2)
        print(f"   - After increment: {count1}")
        print(f"   - After increment by 5: {count2}")
        print(f"   - After decrement by 2: {count3}")
        assert count3 == 4, f"Expected 4, got {count3}"

        # Test 4: Hash Operations
        print("\n✅ Test 4: Hash Operations")
        user_data = {
            "username": "ali_seller",
            "email": "ali@soukloop.com",
            "verified": True,
        }
        await redis.hmset("test:user:123", user_data, ttl=60)
        retrieved_user = await redis.hgetall("test:user:123")
        print(f"   - Stored user: {retrieved_user}")
        assert retrieved_user["username"] == "ali_seller"

        # Test 5: Set Operations
        print("\n✅ Test 5: Set Operations")
        await redis.sadd("test:tags", "fashion", "sneakers", "limited")
        tags = await redis.smembers("test:tags")
        is_member = await redis.sismember("test:tags", "sneakers")
        print(f"   - Tags: {tags}")
        print(f"   - Is 'sneakers' in tags: {is_member}")
        assert is_member == True or is_member == 1  # Redis returns 1 for True

        # Test 6: Sorted Set Operations
        print("\n✅ Test 6: Sorted Set (Leaderboard)")
        await redis.zadd(
            "test:trending",
            {"nike shoes": 150, "adidas sneakers": 120, "jordans": 200},
            ttl=60,
        )
        top_searches = await redis.zrevrange("test:trending", 0, 2)
        print(f"   - Top searches: {top_searches}")
        assert top_searches[0] == "jordans", "Highest score should be first"

        # Test 7: List Operations
        print("\n✅ Test 7: List Operations")
        await redis.rpush("test:feed", "item1", "item2", "item3")
        feed_items = await redis.lrange("test:feed", 0, -1)
        print(f"   - Feed items: {feed_items}")
        assert len(feed_items) == 3

        # Test 8: TTL Operations
        print("\n✅ Test 8: TTL Operations")
        await redis.set("test:ttl", "expires soon", ttl=10)
        ttl = await redis.ttl("test:ttl")
        print(f"   - Key expires in: {ttl} seconds")
        assert ttl > 0 and ttl <= 10

        # Test 9: Batch Operations
        print("\n✅ Test 9: Batch Operations (MGET/MSET)")
        await redis.mset(
            {"test:batch:1": "value1", "test:batch:2": "value2", "test:batch:3": "value3"}
        )
        batch_values = await redis.mget(["test:batch:1", "test:batch:2", "test:batch:3"])
        print(f"   - Batch get: {batch_values}")
        assert len(batch_values) == 3

        # Test 10: Pattern Deletion
        print("\n✅ Test 10: Pattern Deletion")
        await redis.set("test:delete:1", "val1")
        await redis.set("test:delete:2", "val2")
        await redis.set("test:delete:3", "val3")
        deleted = await redis.delete_pattern("test:delete:*")
        print(f"   - Deleted {deleted} keys matching 'test:delete:*'")
        assert deleted == 3

        # Test 11: Cache Keys Integration
        print("\n✅ Test 11: CacheKeys Integration")
        product_key = CacheKeys.product("prod_123")
        feed_key = CacheKeys.discover_feed(1)
        user_key = CacheKeys.user_profile("user_456")
        print(f"   - Product key: {product_key}")
        print(f"   - Feed key: {feed_key}")
        print(f"   - User key: {user_key}")
        assert product_key == "product:prod_123"
        assert feed_key == "feed:discover:page:1"

        # Test 12: Real-Time Features Keys
        print("\n✅ Test 12: Real-Time Features")
        stream_key = CacheKeys.stream_viewers("stream_789")
        await redis.zadd(stream_key, {"user_1": 1000.0, "user_2": 1001.0})
        viewer_count = await redis.zcard(stream_key)
        print(f"   - Stream viewer count: {viewer_count}")
        assert viewer_count == 2

        # Cleanup: Delete all test keys
        print("\n🧹 Cleaning up test keys...")
        await redis.delete_pattern("test:*")

        print("\n" + "=" * 50)
        print("🎉 All Redis tests passed successfully!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
    finally:
        # Close connection
        await redis.close()
        print("\n✅ Redis connection closed")


if __name__ == "__main__":
    asyncio.run(test_redis())
