"""
Cache monitoring and metrics endpoints.

Provides real-time cache performance metrics, health checks,
and administrative controls.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.cache.cache_metrics import get_metrics_collector
from app.core.cache.cache_warming import get_cache_warming_service
from app.core.cache.redis_manager import get_redis_manager


router = APIRouter(prefix="/cache", tags=["cache-monitoring"])


class CacheHealthResponse(BaseModel):
    """Cache health check response"""
    status: str
    hit_rate: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    total_requests: int
    warnings: list[str]
    timestamp: str


class CacheStatsResponse(BaseModel):
    """Cache statistics response"""
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    miss_rate: float
    avg_response_time_ms: float
    p50_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float


class PatternStatsResponse(BaseModel):
    """Pattern-specific cache statistics"""
    pattern: str
    stats: CacheStatsResponse


@router.get("/health", response_model=CacheHealthResponse)
async def get_cache_health():
    """
    Get cache health status.

    Returns overall health with warnings for:
    - Low hit rate (<50%)
    - High avg response time (>50ms)
    - High p95 response time (>100ms)
    """
    try:
        metrics = get_metrics_collector()
        health = metrics.get_health_status()

        return CacheHealthResponse(**health)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache health: {str(e)}")


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get overall cache statistics.

    Includes:
    - Total requests, hits, misses
    - Hit/miss rates
    - Response time percentiles (p50, p95, p99)
    """
    try:
        metrics = get_metrics_collector()
        stats = metrics.get_overall_stats()

        return CacheStatsResponse(
            total_requests=stats.total_requests,
            cache_hits=stats.cache_hits,
            cache_misses=stats.cache_misses,
            hit_rate=stats.hit_rate,
            miss_rate=stats.miss_rate,
            avg_response_time_ms=stats.avg_response_time_ms,
            p50_response_time_ms=stats.p50_response_time_ms,
            p95_response_time_ms=stats.p95_response_time_ms,
            p99_response_time_ms=stats.p99_response_time_ms
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.get("/stats/patterns")
async def get_pattern_stats(
    pattern: Optional[str] = Query(None, description="Specific pattern to query (e.g., 'feed:*')")
):
    """
    Get cache statistics by key pattern.

    Query parameters:
    - pattern: Specific pattern to filter (optional)

    Returns stats for all patterns or a specific pattern.
    """
    try:
        metrics = get_metrics_collector()
        pattern_stats = metrics.get_pattern_stats(pattern)

        return {
            pattern: {
                "total_requests": stats.total_requests,
                "cache_hits": stats.cache_hits,
                "cache_misses": stats.cache_misses,
                "hit_rate": stats.hit_rate,
                "avg_response_time_ms": stats.avg_response_time_ms,
                "p95_response_time_ms": stats.p95_response_time_ms
            }
            for pattern, stats in pattern_stats.items()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pattern stats: {str(e)}")


@router.get("/stats/endpoints")
async def get_endpoint_stats(
    endpoint: Optional[str] = Query(None, description="Specific endpoint to query")
):
    """
    Get cache statistics by API endpoint.

    Query parameters:
    - endpoint: Specific endpoint to filter (optional)

    Returns stats for all endpoints or a specific endpoint.
    """
    try:
        metrics = get_metrics_collector()
        endpoint_stats = metrics.get_endpoint_stats(endpoint)

        return {
            ep: {
                "total_requests": stats.total_requests,
                "cache_hits": stats.cache_hits,
                "cache_misses": stats.cache_misses,
                "hit_rate": stats.hit_rate,
                "avg_response_time_ms": stats.avg_response_time_ms
            }
            for ep, stats in endpoint_stats.items()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get endpoint stats: {str(e)}")


@router.get("/stats/top-patterns")
async def get_top_patterns(
    limit: int = Query(10, ge=1, le=50, description="Number of top patterns to return")
):
    """
    Get top cache patterns by request count.

    Useful for identifying hottest cache keys.
    """
    try:
        metrics = get_metrics_collector()
        top_patterns = metrics.get_top_patterns(limit=limit)

        return [
            {
                "pattern": pattern,
                "total_requests": stats.total_requests,
                "hit_rate": stats.hit_rate,
                "avg_response_time_ms": stats.avg_response_time_ms
            }
            for pattern, stats in top_patterns
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get top patterns: {str(e)}")


@router.get("/stats/low-performers")
async def get_low_performers(
    threshold: float = Query(0.5, ge=0, le=1, description="Hit rate threshold"),
    limit: int = Query(10, ge=1, le=50, description="Number of patterns to return")
):
    """
    Get cache patterns with low hit rates.

    Identifies patterns that need optimization:
    - Consider increasing TTL
    - Check if data is cacheable
    - Review invalidation logic

    Query parameters:
    - threshold: Hit rate threshold (default: 0.5 = 50%)
    - limit: Max patterns to return
    """
    try:
        metrics = get_metrics_collector()
        low_performers = metrics.get_low_hit_rate_patterns(threshold=threshold, limit=limit)

        return [
            {
                "pattern": pattern,
                "hit_rate": stats.hit_rate,
                "total_requests": stats.total_requests,
                "recommendation": _get_optimization_recommendation(pattern, stats)
            }
            for pattern, stats in low_performers
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get low performers: {str(e)}")


@router.post("/warm")
async def warm_cache():
    """
    Manually trigger cache warming.

    Warms:
    - Discover feed (first 3 pages)
    - Trending searches
    - Popular categories
    - Active seller profiles
    """
    try:
        warming_service = get_cache_warming_service()
        await warming_service.warm_all()

        return {
            "status": "success",
            "message": "Cache warming triggered successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to warm cache: {str(e)}")


@router.post("/reset-metrics")
async def reset_metrics():
    """
    Reset cache metrics.

    WARNING: This clears all collected metrics data.
    Use for testing or after configuration changes.
    """
    try:
        metrics = get_metrics_collector()
        metrics.reset_stats()

        return {
            "status": "success",
            "message": "Cache metrics reset successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset metrics: {str(e)}")


@router.get("/info")
async def get_redis_info():
    """
    Get Redis server information.

    Returns:
    - Redis version
    - Memory usage
    - Connected clients
    - Total keys
    """
    try:
        redis = get_redis_manager()

        # Get Redis INFO
        info = await redis.redis.info()

        return {
            "redis_version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_keys": sum(info.get(f"db{i}", {}).get("keys", 0) for i in range(16)),
            "uptime_in_seconds": info.get("uptime_in_seconds"),
            "hit_rate": info.get("keyspace_hits", 0) / max(
                info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1
            )
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Redis info: {str(e)}")


def _get_optimization_recommendation(pattern: str, stats) -> str:
    """Generate optimization recommendation for low-performing pattern"""
    if "feed:" in pattern:
        return "Consider increasing TTL for feed data (currently 5 min, try 10 min)"
    elif "search:" in pattern:
        return "Search results may be too varied. Consider broader cache keys or longer TTL"
    elif "product:" in pattern:
        return "Product data changes frequently. Review invalidation logic"
    elif "user:" in pattern:
        return "User profiles rarely change. Consider longer TTL (1+ hours)"
    else:
        return "Review data access patterns and cache key structure"
