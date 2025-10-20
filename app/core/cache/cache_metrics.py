"""
Cache metrics tracking and monitoring system.

Tracks cache hits, misses, response times, and provides analytics
for cache performance optimization.
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio
import time


@dataclass
class CacheMetric:
    """Individual cache operation metric"""
    timestamp: datetime
    operation: str  # get, set, delete
    key_pattern: str  # e.g., "feed:*", "product:*"
    hit: bool
    response_time_ms: float
    size_bytes: Optional[int] = None


@dataclass
class CacheStats:
    """Aggregated cache statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_response_time_ms: float = 0
    avg_response_time_ms: float = 0
    hit_rate: float = 0
    miss_rate: float = 0
    p50_response_time_ms: float = 0
    p95_response_time_ms: float = 0
    p99_response_time_ms: float = 0
    total_size_bytes: int = 0
    avg_size_bytes: float = 0


@dataclass
class EndpointCacheStats:
    """Cache statistics per API endpoint"""
    endpoint: str
    stats: CacheStats
    last_updated: datetime = field(default_factory=datetime.utcnow)


class CacheMetricsCollector:
    """
    Collects and aggregates cache metrics for monitoring and optimization.

    Features:
    - Real-time hit/miss tracking
    - Response time percentiles
    - Per-endpoint statistics
    - Pattern-based analytics
    - Configurable retention period
    """

    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self._metrics: List[CacheMetric] = []
        self._endpoint_stats: Dict[str, CacheStats] = defaultdict(CacheStats)
        self._pattern_stats: Dict[str, CacheStats] = defaultdict(CacheStats)
        self._lock = asyncio.Lock()

        # Counters for quick access
        self._total_hits = 0
        self._total_misses = 0
        self._total_requests = 0

    async def record_cache_operation(
        self,
        operation: str,
        key: str,
        hit: bool,
        response_time_ms: float,
        endpoint: Optional[str] = None,
        size_bytes: Optional[int] = None
    ):
        """Record a cache operation"""
        async with self._lock:
            # Extract pattern from key (e.g., "feed:discover:page:1" -> "feed:*")
            pattern = self._extract_pattern(key)

            # Create metric
            metric = CacheMetric(
                timestamp=datetime.now(timezone.utc),
                operation=operation,
                key_pattern=pattern,
                hit=hit,
                response_time_ms=response_time_ms,
                size_bytes=size_bytes
            )

            # Store metric
            self._metrics.append(metric)

            # Update counters
            self._total_requests += 1
            if hit:
                self._total_hits += 1
            else:
                self._total_misses += 1

            # Update pattern stats
            self._update_stats(self._pattern_stats[pattern], metric)

            # Update endpoint stats if provided
            if endpoint:
                self._update_stats(self._endpoint_stats[endpoint], metric)

            # Cleanup old metrics (async)
            if len(self._metrics) % 1000 == 0:
                asyncio.create_task(self._cleanup_old_metrics())

    def _extract_pattern(self, key: str) -> str:
        """Extract cache key pattern (first two segments)"""
        parts = key.split(":")
        if len(parts) >= 2:
            return f"{parts[0]}:{parts[1]}:*"
        elif len(parts) == 1:
            return f"{parts[0]}:*"
        return "*"

    def _update_stats(self, stats: CacheStats, metric: CacheMetric):
        """Update statistics with new metric"""
        stats.total_requests += 1

        if metric.hit:
            stats.cache_hits += 1
        else:
            stats.cache_misses += 1

        stats.total_response_time_ms += metric.response_time_ms
        stats.avg_response_time_ms = stats.total_response_time_ms / stats.total_requests

        stats.hit_rate = stats.cache_hits / stats.total_requests if stats.total_requests > 0 else 0
        stats.miss_rate = stats.cache_misses / stats.total_requests if stats.total_requests > 0 else 0

        if metric.size_bytes:
            stats.total_size_bytes += metric.size_bytes
            stats.avg_size_bytes = stats.total_size_bytes / stats.total_requests

    async def _cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        async with self._lock:
            self._metrics = [m for m in self._metrics if m.timestamp > cutoff]

    def get_overall_stats(self) -> CacheStats:
        """Get overall cache statistics"""
        if not self._metrics:
            return CacheStats()

        # Calculate percentiles from recent metrics
        response_times = [m.response_time_ms for m in self._metrics[-10000:]]  # Last 10k
        response_times.sort()

        total = len(response_times)

        stats = CacheStats(
            total_requests=self._total_requests,
            cache_hits=self._total_hits,
            cache_misses=self._total_misses,
            hit_rate=self._total_hits / self._total_requests if self._total_requests > 0 else 0,
            miss_rate=self._total_misses / self._total_requests if self._total_requests > 0 else 0,
        )

        if response_times:
            stats.avg_response_time_ms = sum(response_times) / total
            stats.p50_response_time_ms = response_times[int(total * 0.5)]
            stats.p95_response_time_ms = response_times[int(total * 0.95)] if total > 20 else response_times[-1]
            stats.p99_response_time_ms = response_times[int(total * 0.99)] if total > 100 else response_times[-1]

        return stats

    def get_endpoint_stats(self, endpoint: Optional[str] = None) -> Dict[str, CacheStats]:
        """Get statistics per endpoint"""
        if endpoint:
            return {endpoint: self._endpoint_stats.get(endpoint, CacheStats())}
        return dict(self._endpoint_stats)

    def get_pattern_stats(self, pattern: Optional[str] = None) -> Dict[str, CacheStats]:
        """Get statistics per key pattern"""
        if pattern:
            return {pattern: self._pattern_stats.get(pattern, CacheStats())}
        return dict(self._pattern_stats)

    def get_top_patterns(self, limit: int = 10) -> List[tuple[str, CacheStats]]:
        """Get top cache patterns by request count"""
        patterns = sorted(
            self._pattern_stats.items(),
            key=lambda x: x[1].total_requests,
            reverse=True
        )
        return patterns[:limit]

    def get_low_hit_rate_patterns(self, threshold: float = 0.5, limit: int = 10) -> List[tuple[str, CacheStats]]:
        """Get patterns with low hit rates (candidates for optimization)"""
        low_performers = [
            (pattern, stats)
            for pattern, stats in self._pattern_stats.items()
            if stats.hit_rate < threshold and stats.total_requests > 10
        ]

        return sorted(low_performers, key=lambda x: x[1].hit_rate)[:limit]

    def get_health_status(self) -> Dict:
        """Get cache health status for monitoring"""
        overall = self.get_overall_stats()

        # Health thresholds
        health_status = "healthy"
        warnings = []

        if overall.hit_rate < 0.5:
            health_status = "degraded"
            warnings.append(f"Low hit rate: {overall.hit_rate:.1%} (target: >50%)")

        if overall.avg_response_time_ms > 50:
            health_status = "degraded"
            warnings.append(f"High avg response time: {overall.avg_response_time_ms:.2f}ms (target: <50ms)")

        if overall.p95_response_time_ms > 100:
            if health_status != "degraded":
                health_status = "warning"
            warnings.append(f"High p95 response time: {overall.p95_response_time_ms:.2f}ms (target: <100ms)")

        return {
            "status": health_status,
            "hit_rate": overall.hit_rate,
            "avg_response_time_ms": overall.avg_response_time_ms,
            "p95_response_time_ms": overall.p95_response_time_ms,
            "total_requests": overall.total_requests,
            "warnings": warnings,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def reset_stats(self):
        """Reset all statistics"""
        self._metrics.clear()
        self._endpoint_stats.clear()
        self._pattern_stats.clear()
        self._total_hits = 0
        self._total_misses = 0
        self._total_requests = 0


# Global metrics collector instance
_metrics_collector = CacheMetricsCollector()


def get_metrics_collector() -> CacheMetricsCollector:
    """Get the global metrics collector instance"""
    return _metrics_collector
