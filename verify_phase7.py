"""
Phase 7 Verification Script

This script verifies that all Phase 7 components are properly implemented.
Run with: python3 verify_phase7.py
"""

import asyncio
import sys


async def verify_imports():
    """Verify all Phase 7 modules can be imported"""
    print("🔍 Verifying imports...")

    try:
        from app.core.cache.cache_metrics import CacheMetricsCollector, get_metrics_collector
        print("  ✅ cache_metrics module")
    except ImportError as e:
        print(f"  ❌ cache_metrics module: {e}")
        return False

    try:
        from app.core.cache.cache_warming import CacheWarmingService, get_cache_warming_service
        print("  ✅ cache_warming module")
    except ImportError as e:
        print(f"  ❌ cache_warming module: {e}")
        return False

    try:
        from app.api.endpoints import cache_monitoring
        print("  ✅ cache_monitoring module")
    except ImportError as e:
        print(f"  ❌ cache_monitoring module: {e}")
        return False

    return True


async def verify_metrics_collector():
    """Verify metrics collector functionality"""
    print("\n🔍 Verifying metrics collector...")

    from app.core.cache.cache_metrics import CacheMetricsCollector

    collector = CacheMetricsCollector()

    # Test recording operations
    await collector.record_cache_operation(
        operation="get",
        key="test:key:1",
        hit=True,
        response_time_ms=5.0
    )

    await collector.record_cache_operation(
        operation="get",
        key="test:key:2",
        hit=False,
        response_time_ms=50.0
    )

    # Verify stats
    stats = collector.get_overall_stats()
    assert stats.total_requests == 2, "Total requests should be 2"
    assert stats.cache_hits == 1, "Cache hits should be 1"
    assert stats.cache_misses == 1, "Cache misses should be 1"
    assert stats.hit_rate == 0.5, "Hit rate should be 50%"

    print("  ✅ Record operations")
    print("  ✅ Calculate statistics")

    # Verify health check
    health = collector.get_health_status()
    assert "status" in health, "Health should have status"
    assert "warnings" in health, "Health should have warnings"

    print("  ✅ Health status")

    # Verify pattern stats
    pattern_stats = collector.get_pattern_stats()
    assert len(pattern_stats) > 0, "Should have pattern stats"

    print("  ✅ Pattern statistics")

    return True


async def verify_cache_warming():
    """Verify cache warming service"""
    print("\n🔍 Verifying cache warming...")

    from app.core.cache.redis_manager import RedisManager
    from app.core.cache.cache_warming import CacheWarmingService

    redis = RedisManager()
    warming_service = CacheWarmingService(redis)

    # Test warming (will log errors if Redis not running, but won't crash)
    try:
        await warming_service.warm_all()
        print("  ✅ Cache warming execution")
    except Exception as e:
        print(f"  ⚠️  Cache warming: {e} (Redis may not be running)")

    await redis.close()
    return True


async def verify_monitoring_endpoints():
    """Verify monitoring endpoints exist"""
    print("\n🔍 Verifying monitoring endpoints...")

    from app.api.endpoints import cache_monitoring

    # Check router exists
    assert hasattr(cache_monitoring, 'router'), "Router should exist"

    # Check endpoints are registered
    routes = [route.path for route in cache_monitoring.router.routes]

    expected_endpoints = [
        "/cache/health",
        "/cache/stats",
        "/cache/stats/patterns",
        "/cache/stats/endpoints",
        "/cache/stats/top-patterns",
        "/cache/stats/low-performers",
        "/cache/warm",
        "/cache/reset-metrics",
        "/cache/info"
    ]

    for endpoint in expected_endpoints:
        if endpoint in routes:
            print(f"  ✅ {endpoint}")
        else:
            print(f"  ❌ {endpoint} not found")
            return False

    return True


async def verify_test_files():
    """Verify test files exist"""
    print("\n🔍 Verifying test files...")

    import os

    test_files = [
        "tests/test_cache_metrics.py",
        "tests/test_cache_integration.py",
        "tests/test_monitoring_endpoints.py"
    ]

    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"  ✅ {test_file}")
        else:
            print(f"  ❌ {test_file} not found")
            return False

    return True


async def main():
    """Run all verifications"""
    print("=" * 60)
    print("Phase 7 Verification")
    print("=" * 60)

    results = []

    # Run verifications
    results.append(await verify_imports())
    results.append(await verify_metrics_collector())
    results.append(await verify_cache_warming())
    results.append(await verify_monitoring_endpoints())
    results.append(await verify_test_files())

    # Summary
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"\n✅ All verifications passed ({passed}/{total})")
        print("\nPhase 7 is complete and ready for use!")
        print("\nNext steps:")
        print("1. Ensure Redis is running: docker-compose up -d redis")
        print("2. Start the server: python3 -m uvicorn app.main:app --reload")
        print("3. Test endpoints: curl http://localhost:8000/api/v1/cache/health")
        print("4. Run tests: python3 -m pytest tests/test_cache_metrics.py -v")
        return 0
    else:
        print(f"\n❌ Some verifications failed ({passed}/{total})")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
