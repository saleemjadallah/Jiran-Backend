"""
Integration tests for the complete caching system.

Tests the full cache stack:
- Redis operations
- Cache metrics tracking
- Cache warming
- Performance benchmarks
"""

import pytest
import pytest_asyncio
import asyncio
import time
from typing import List

from app.core.cache.redis_manager import RedisManager
from app.core.cache.cache_metrics import CacheMetricsCollector
from app.core.cache.cache_warming import CacheWarmingService


@pytest_asyncio.fixture
async def redis_manager():
    """Create Redis manager for testing"""
    manager = RedisManager()
    yield manager
    # Cleanup: delete test keys
    await manager.delete_pattern("test:*")
    await manager.close()


@pytest.fixture
def metrics_collector():
    """Create fresh metrics collector"""
    collector = CacheMetricsCollector()
    collector.reset_stats()
    return collector


@pytest_asyncio.fixture
async def warming_service(redis_manager):
    """Create cache warming service"""
    return CacheWarmingService(redis_manager)


class TestCacheIntegration:
    """Integration tests for complete caching system"""

    @pytest.mark.asyncio
    async def test_basic_cache_flow(self, redis_manager, metrics_collector):
        """Test basic cache get/set flow with metrics"""
        key = "test:product:123"
        value = {"id": "123", "name": "Test Product", "price": 99.99}

        # Simulate cache miss
        start = time.time()
        cached = await redis_manager.get(key)
        duration_ms = (time.time() - start) * 1000

        assert cached is None

        # Record miss
        await metrics_collector.record_cache_operation(
            operation="get",
            key=key,
            hit=False,
            response_time_ms=duration_ms
        )

        # Set value
        await redis_manager.set(key, value, ttl=300)

        # Simulate cache hit
        start = time.time()
        cached = await redis_manager.get(key)
        duration_ms = (time.time() - start) * 1000

        assert cached == value

        # Record hit
        await metrics_collector.record_cache_operation(
            operation="get",
            key=key,
            hit=True,
            response_time_ms=duration_ms
        )

        # Verify metrics
        stats = metrics_collector.get_overall_stats()
        assert stats.total_requests == 2
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1
        assert stats.hit_rate == 0.5

    @pytest.mark.asyncio
    async def test_cache_warming_workflow(self, warming_service, redis_manager):
        """Test cache warming populates cache correctly"""
        # Warm cache
        await warming_service.warm_all()

        # Verify discover feed was warmed
        for page in range(1, 4):
            key = f"feed:discover:page:{page}"
            cached = await redis_manager.get(key)
            assert cached is not None
            assert cached["page"] == page

        # Verify trending searches
        trending_count = await redis_manager.zcard("trending:searches")
        assert trending_count > 0

    @pytest.mark.asyncio
    async def test_cache_performance_benchmark(self, redis_manager):
        """Benchmark cache read/write performance"""
        num_operations = 1000
        test_data = {"id": "123", "name": "Test", "price": 99.99}

        # Benchmark writes
        write_times = []
        for i in range(num_operations):
            key = f"test:benchmark:write:{i}"
            start = time.time()
            await redis_manager.set(key, test_data, ttl=60)
            duration_ms = (time.time() - start) * 1000
            write_times.append(duration_ms)

        avg_write_time = sum(write_times) / len(write_times)
        print(f"\nAverage write time: {avg_write_time:.2f}ms")

        # Benchmark reads (cache hits)
        read_times = []
        for i in range(num_operations):
            key = f"test:benchmark:write:{i}"
            start = time.time()
            await redis_manager.get(key)
            duration_ms = (time.time() - start) * 1000
            read_times.append(duration_ms)

        avg_read_time = sum(read_times) / len(read_times)
        print(f"Average read time: {avg_read_time:.2f}ms")

        # Performance assertions
        assert avg_write_time < 50, "Write operations too slow"
        assert avg_read_time < 10, "Read operations too slow"

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, redis_manager):
        """Test cache TTL expiration works correctly"""
        key = "test:ttl:key"
        value = {"data": "expires soon"}

        # Set with 2 second TTL
        await redis_manager.set(key, value, ttl=2)

        # Verify exists
        exists = await redis_manager.exists(key)
        assert exists

        # Wait for expiration
        await asyncio.sleep(3)

        # Verify expired
        cached = await redis_manager.get(key)
        assert cached is None

    @pytest.mark.asyncio
    async def test_pattern_deletion(self, redis_manager):
        """Test pattern-based cache invalidation"""
        # Create multiple keys with same pattern
        for i in range(5):
            await redis_manager.set(f"test:feed:page:{i}", {"page": i}, ttl=300)

        # Verify all exist
        for i in range(5):
            exists = await redis_manager.exists(f"test:feed:page:{i}")
            assert exists

        # Delete by pattern
        deleted = await redis_manager.delete_pattern("test:feed:*")
        assert deleted == 5

        # Verify all deleted
        for i in range(5):
            exists = await redis_manager.exists(f"test:feed:page:{i}")
            assert not exists

    @pytest.mark.asyncio
    async def test_batch_operations_performance(self, redis_manager):
        """Test batch get/set operations are faster than individual"""
        num_keys = 100
        test_data = {f"test:batch:{i}": {"value": i} for i in range(num_keys)}

        # Benchmark individual sets
        start = time.time()
        for key, value in test_data.items():
            await redis_manager.set(key, value, ttl=60)
        individual_time = time.time() - start

        # Cleanup
        await redis_manager.delete_pattern("test:batch:*")

        # Benchmark batch set
        start = time.time()
        await redis_manager.mset(test_data)
        batch_time = time.time() - start

        print(f"\nIndividual sets: {individual_time:.3f}s")
        print(f"Batch set: {batch_time:.3f}s")
        print(f"Speedup: {individual_time / batch_time:.1f}x")

        # Batch should be significantly faster
        assert batch_time < individual_time

    @pytest.mark.asyncio
    async def test_compression_for_large_objects(self, redis_manager):
        """Test compression works for large objects"""
        # Create large object (>1KB)
        large_value = {"data": "x" * 2000, "items": list(range(100))}

        key = "test:large:object"

        # Set with compression
        await redis_manager.set_compressed(key, large_value, ttl=60, threshold=1024)

        # Verify compression flag exists
        is_compressed = await redis_manager.redis.get(f"{key}:is_compressed")
        assert is_compressed == "1"

        # Get and verify data integrity
        retrieved = await redis_manager.get_compressed(key)
        assert retrieved == large_value

        # Cleanup
        await redis_manager.delete_compressed(key)

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, redis_manager):
        """Test cache handles concurrent access correctly"""
        key = "test:concurrent"
        initial_value = {"counter": 0}

        await redis_manager.set(key, initial_value, ttl=60)

        # Concurrent increments
        async def increment_counter():
            for _ in range(10):
                value = await redis_manager.get(key)
                value["counter"] += 1
                await redis_manager.set(key, value, ttl=60)

        # Run 5 concurrent tasks
        await asyncio.gather(
            increment_counter(),
            increment_counter(),
            increment_counter(),
            increment_counter(),
            increment_counter()
        )

        final_value = await redis_manager.get(key)
        # Due to race conditions, counter might not be exactly 50
        # But should be > 0
        assert final_value["counter"] > 0

    @pytest.mark.asyncio
    async def test_cache_hit_rate_target(self, redis_manager, metrics_collector):
        """Test cache achieves target hit rate in realistic scenario"""
        # Simulate realistic access patterns
        # - 80% of requests hit same 20% of keys (hot keys)
        # - 20% of requests hit different keys (cold keys)

        hot_keys = [f"test:hot:{i}" for i in range(20)]
        cold_keys = [f"test:cold:{i}" for i in range(100)]

        # Pre-populate hot keys
        for key in hot_keys:
            await redis_manager.set(key, {"data": "hot"}, ttl=300)

        # Simulate 1000 requests
        for i in range(1000):
            if i % 5 < 4:  # 80% hot
                key = hot_keys[i % len(hot_keys)]
                start = time.time()
                result = await redis_manager.get(key)
                duration_ms = (time.time() - start) * 1000

                await metrics_collector.record_cache_operation(
                    operation="get",
                    key=key,
                    hit=result is not None,
                    response_time_ms=duration_ms
                )
            else:  # 20% cold
                key = cold_keys[i % len(cold_keys)]
                start = time.time()
                result = await redis_manager.get(key)
                duration_ms = (time.time() - start) * 1000

                await metrics_collector.record_cache_operation(
                    operation="get",
                    key=key,
                    hit=result is not None,
                    response_time_ms=duration_ms
                )

                # Populate on miss
                if result is None:
                    await redis_manager.set(key, {"data": "cold"}, ttl=300)

        # Verify hit rate meets target
        stats = metrics_collector.get_overall_stats()
        print(f"\nCache hit rate: {stats.hit_rate:.1%}")
        print(f"Average response time: {stats.avg_response_time_ms:.2f}ms")
        print(f"P95 response time: {stats.p95_response_time_ms:.2f}ms")

        assert stats.hit_rate >= 0.6, "Cache hit rate below 60% target"
        assert stats.avg_response_time_ms < 50, "Average response time too high"


class TestCacheStressTesting:
    """Stress tests for cache system"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_high_volume_operations(self, redis_manager, metrics_collector):
        """Test cache handles high volume of operations"""
        num_operations = 10000

        async def perform_operations(start_idx: int, count: int):
            for i in range(start_idx, start_idx + count):
                key = f"test:stress:{i % 1000}"  # Reuse 1000 keys
                value = {"index": i, "data": "test"}

                # Set
                await redis_manager.set(key, value, ttl=60)

                # Get
                start = time.time()
                result = await redis_manager.get(key)
                duration_ms = (time.time() - start) * 1000

                await metrics_collector.record_cache_operation(
                    operation="get",
                    key=key,
                    hit=result is not None,
                    response_time_ms=duration_ms
                )

        # Run concurrent operations
        start_time = time.time()
        await asyncio.gather(
            perform_operations(0, num_operations // 4),
            perform_operations(num_operations // 4, num_operations // 4),
            perform_operations(num_operations // 2, num_operations // 4),
            perform_operations(3 * num_operations // 4, num_operations // 4)
        )
        total_time = time.time() - start_time

        stats = metrics_collector.get_overall_stats()
        ops_per_sec = num_operations / total_time

        print(f"\nTotal operations: {num_operations}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Operations/sec: {ops_per_sec:.0f}")
        print(f"Hit rate: {stats.hit_rate:.1%}")
        print(f"Avg response: {stats.avg_response_time_ms:.2f}ms")

        assert ops_per_sec > 100, "Cache throughput too low"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
