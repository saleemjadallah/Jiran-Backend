from redis.asyncio import Redis, from_url

from app.config import settings


# Redis client (lazy initialization to avoid startup errors)
redis_client: Redis | None = None


async def get_redis() -> Redis:
    """Get Redis client with lazy initialization.

    Returns None-safe Redis client for optional caching.
    For Railway deployment without Redis, endpoints should handle None gracefully.
    """
    global redis_client

    if redis_client is None:
        try:
            # Try to connect to Redis
            redis_client = from_url(str(settings.REDIS_URL), decode_responses=True)
            # Test connection
            await redis_client.ping()
        except Exception:
            # Redis not available - return None for graceful degradation
            return None

    return redis_client

