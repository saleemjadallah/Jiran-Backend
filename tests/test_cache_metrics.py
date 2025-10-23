"""
Comprehensive tests for cache metrics system.

Tests:
- Metrics collection and aggregation
- Hit/miss tracking
- Response time percentiles
- Pattern-based statistics
- Health checks
"""

import pytest
import asyncio
from datetime import datetime

from app.core.cache.cache_metrics import (
    CacheMetricsCollector,
    CacheMetric,
    CacheStats
)


class TestCacheMetrics:
    """Test cache metrics collection and reporting"""

    @pytest.fixture
    def metrics_collector(self):
        """Create fresh metrics collector for each test"""
        return CacheMetricsCollector(retention_hours=1)

    @pytest.mark.asyncio
    async def test_record_cache_hit(self, metrics_collector):
        """Test recording cache hit"""
        await metrics_collector.record_cache_operation(
            operation="get",
            key="feed:discover:page:1",
            hit=True,
            response_time_ms=5.2,
            endpoint="/api/feeds/discover"
        )

        stats = metrics_collector.get_overall_stats()
        assert stats.total_requests == 1
        assert stats.cache_hits == 1
        assert stats.cache_misses == 0
        assert stats.hit_rate == 1.0

    @pytest.mark.asyncio
    async def test_record_cache_miss(self, metrics_collector):
        """Test recording cache miss"""
        await metrics_collector.record_cache_operation(
            operation="get",
            key="product:123",
            hit=False,
            response_time_ms=45.8
        )

        stats = metrics_collector.get_overall_stats()
        assert stats.total_requests == 1
        assert stats.cache_hits == 0
        assert stats.cache_misses == 1
        assert stats.miss_rate == 1.0

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self, metrics_collector):
        """Test hit rate calculation with mixed results"""
        # Record 7 hits and 3 misses
        for i in range(7):
            await metrics_collector.record_cache_operation(
                operation="get",
                key=f"feed:discover:page:{i}",
                hit=True,
                response_time_ms=10.0
            )

        for i in range(3):
            await metrics_collector.record_cache_operation(
                operation="get",
                key=f"product:{i}",
                hit=False,
                response_time_ms=50.0
            )

        stats = metrics_collector.get_overall_stats()
        assert stats.total_requests == 10
        assert stats.cache_hits == 7
        assert stats.cache_misses == 3
        assert stats.hit_rate == 0.7
        assert stats.miss_rate == 0.3

    @pytest.mark.asyncio
    async def test_response_time_percentiles(self, metrics_collector):
        """Test response time percentile calculations"""
        # Record 100 operations with varying response times
        for i in range(100):
            await metrics_collector.record_cache_operation(
                operation="get",
                key=f"key:{i}",
                hit=True,
                response_time_ms=float(i)  # 0-99ms
            )

        stats = metrics_collector.get_overall_stats()
        assert stats.avg_response_time_ms == pytest.approx(49.5, rel=1)
        assert stats.p50_response_time_ms == pytest.approx(50, abs=5)
        assert stats.p95_response_time_ms == pytest.approx(95, abs=5)
        assert stats.p99_response_time_ms == pytest.approx(99, abs=5)

    @pytest.mark.asyncio
    async def test_pattern_extraction(self, metrics_collector):
        """Test cache key pattern extraction"""
        await metrics_collector.record_cache_operation(
            operation="get",
            key="feed:discover:page:1",
            hit=True,
            response_time_ms=10.0
        )

        await metrics_collector.record_cache_operation(
            operation="get",
            key="feed:discover:page:2",
            hit=True,
            response_time_ms=12.0
        )

        pattern_stats = metrics_collector.get_pattern_stats("feed:discover:*")
        assert "feed:discover:*" in pattern_stats
        assert pattern_stats["feed:discover:*"].total_requests == 2

    @pytest.mark.asyncio
    async def test_endpoint_stats(self, metrics_collector):
        """Test per-endpoint statistics"""
        # Record operations for different endpoints
        await metrics_collector.record_cache_operation(
            operation="get",
            key="feed:discover:page:1",
            hit=True,
            response_time_ms=10.0,
            endpoint="/api/feeds/discover"
        )

        await metrics_collector.record_cache_operation(
            operation="get",
            key="product:123",
            hit=False,
            response_time_ms=50.0,
            endpoint="/api/products/123"
        )

        endpoint_stats = metrics_collector.get_endpoint_stats("/api/feeds/discover")
        assert "/api/feeds/discover" in endpoint_stats
        assert endpoint_stats["/api/feeds/discover"].hit_rate == 1.0

    @pytest.mark.asyncio
    async def test_top_patterns(self, metrics_collector):
        """Test top patterns by request count"""
        # Create patterns with different request counts
        for i in range(10):
            await metrics_collector.record_cache_operation(
                operation="get",
                key="feed:discover:page:1",
                hit=True,
                response_time_ms=10.0
            )

        for i in range(5):
            await metrics_collector.record_cache_operation(
                operation="get",
                key="product:123",
                hit=True,
                response_time_ms=15.0
            )

        top_patterns = metrics_collector.get_top_patterns(limit=2)
        assert len(top_patterns) == 2
        assert top_patterns[0][0] == "feed:discover:*"  # Most requests
        assert top_patterns[0][1].total_requests == 10

    @pytest.mark.asyncio
    async def test_low_hit_rate_patterns(self, metrics_collector):
        """Test identification of low-performing patterns"""
        # Pattern with good hit rate
        for i in range(10):
            await metrics_collector.record_cache_operation(
                operation="get",
                key="feed:discover:page:1",
                hit=True,
                response_time_ms=10.0
            )

        # Pattern with poor hit rate - use same search pattern to group them
        for i in range(15):
            await metrics_collector.record_cache_operation(
                operation="get",
                key="search:results:some_query",
                hit=i < 5,  # Only 33% hit rate
                response_time_ms=20.0
            )

        low_performers = metrics_collector.get_low_hit_rate_patterns(threshold=0.5)
        assert len(low_performers) > 0
        assert any("search:" in pattern for pattern, _ in low_performers)

    @pytest.mark.asyncio
    async def test_health_status_healthy(self, metrics_collector):
        """Test health status when cache is performing well"""
        # Record good performance
        for i in range(100):
            await metrics_collector.record_cache_operation(
                operation="get",
                key=f"feed:page:{i}",
                hit=True,  # 100% hit rate
                response_time_ms=10.0  # Fast responses
            )

        health = metrics_collector.get_health_status()
        assert health["status"] == "healthy"
        assert health["hit_rate"] >= 0.8
        assert health["avg_response_time_ms"] < 50
        assert len(health["warnings"]) == 0

    @pytest.mark.asyncio
    async def test_health_status_degraded(self, metrics_collector):
        """Test health status when cache is degraded"""
        # Record poor performance
        for i in range(100):
            await metrics_collector.record_cache_operation(
                operation="get",
                key=f"key:{i}",
                hit=i < 30,  # 30% hit rate
                response_time_ms=80.0  # Slow responses
            )

        health = metrics_collector.get_health_status()
        assert health["status"] == "degraded"
        assert len(health["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_reset_stats(self, metrics_collector):
        """Test resetting statistics"""
        # Record some operations
        await metrics_collector.record_cache_operation(
            operation="get",
            key="test:key",
            hit=True,
            response_time_ms=10.0
        )

        # Reset
        metrics_collector.reset_stats()

        # Verify reset
        stats = metrics_collector.get_overall_stats()
        assert stats.total_requests == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, metrics_collector):
        """Test thread-safety with concurrent operations"""
        async def record_operations(count: int):
            for i in range(count):
                await metrics_collector.record_cache_operation(
                    operation="get",
                    key=f"key:{i}",
                    hit=True,
                    response_time_ms=10.0
                )

        # Run concurrent operations
        await asyncio.gather(
            record_operations(50),
            record_operations(50),
            record_operations(50)
        )

        stats = metrics_collector.get_overall_stats()
        assert stats.total_requests == 150


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
