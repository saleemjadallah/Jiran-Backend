"""
Test cache monitoring endpoints

Run this with the server running:
python3 -m pytest tests/test_monitoring_endpoints.py -v -s
"""

import pytest
import httpx
import asyncio


# Configure this based on your server
BASE_URL = "http://localhost:8000/api/v1"


@pytest.mark.asyncio
async def test_cache_health_endpoint():
    """Test cache health endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/cache/health")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "status" in data
        assert "hit_rate" in data
        assert "avg_response_time_ms" in data
        assert "p95_response_time_ms" in data
        assert "total_requests" in data
        assert "warnings" in data
        assert "timestamp" in data

        print("\n✅ Cache Health:")
        print(f"   Status: {data['status']}")
        print(f"   Hit Rate: {data['hit_rate']:.1%}")
        print(f"   Avg Response: {data['avg_response_time_ms']:.2f}ms")
        print(f"   P95 Response: {data['p95_response_time_ms']:.2f}ms")
        print(f"   Total Requests: {data['total_requests']}")
        print(f"   Warnings: {data['warnings']}")


@pytest.mark.asyncio
async def test_cache_stats_endpoint():
    """Test cache statistics endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/cache/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "total_requests" in data
        assert "cache_hits" in data
        assert "cache_misses" in data
        assert "hit_rate" in data
        assert "miss_rate" in data

        print("\n✅ Cache Statistics:")
        print(f"   Total Requests: {data['total_requests']}")
        print(f"   Hits: {data['cache_hits']}")
        print(f"   Misses: {data['cache_misses']}")
        print(f"   Hit Rate: {data['hit_rate']:.1%}")
        print(f"   Miss Rate: {data['miss_rate']:.1%}")


@pytest.mark.asyncio
async def test_pattern_stats_endpoint():
    """Test pattern statistics endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/cache/stats/patterns")

        assert response.status_code == 200
        data = response.json()

        print("\n✅ Pattern Statistics:")
        for pattern, stats in data.items():
            print(f"\n   Pattern: {pattern}")
            print(f"   - Requests: {stats['total_requests']}")
            print(f"   - Hit Rate: {stats['hit_rate']:.1%}")
            print(f"   - Avg Response: {stats['avg_response_time_ms']:.2f}ms")


@pytest.mark.asyncio
async def test_top_patterns_endpoint():
    """Test top patterns endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/cache/stats/top-patterns?limit=5")

        assert response.status_code == 200
        data = response.json()

        print("\n✅ Top 5 Cache Patterns:")
        for i, pattern_data in enumerate(data, 1):
            print(f"\n   {i}. {pattern_data['pattern']}")
            print(f"      Requests: {pattern_data['total_requests']}")
            print(f"      Hit Rate: {pattern_data['hit_rate']:.1%}")


@pytest.mark.asyncio
async def test_redis_info_endpoint():
    """Test Redis info endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/cache/info")

        assert response.status_code == 200
        data = response.json()

        print("\n✅ Redis Server Info:")
        print(f"   Version: {data.get('redis_version')}")
        print(f"   Memory: {data.get('used_memory_human')}")
        print(f"   Clients: {data.get('connected_clients')}")
        print(f"   Total Keys: {data.get('total_keys')}")
        print(f"   Hit Rate: {data.get('hit_rate', 0):.1%}")


@pytest.mark.asyncio
async def test_cache_warm_endpoint():
    """Test cache warming endpoint"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{BASE_URL}/cache/warm")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        print("\n✅ Cache Warming:")
        print(f"   {data['message']}")


if __name__ == "__main__":
    # Run with: python3 tests/test_monitoring_endpoints.py
    print("\n" + "="*60)
    print("Testing Cache Monitoring Endpoints")
    print("="*60)
    print("\nMake sure the server is running on http://localhost:8000")
    print("\nStarting tests...\n")

    pytest.main([__file__, "-v", "-s"])
