import logging

from redis.asyncio import Redis, from_url

from app.config import settings


# Redis client (lazy initialization to avoid startup errors)
redis_client: Redis | None = None
logger = logging.getLogger(__name__)


async def get_redis() -> Redis:
    """Get Redis client with lazy initialization.

    Returns None-safe Redis client for optional caching.
    For Railway deployment without Redis, endpoints should handle None gracefully.
    """
    global redis_client

    if redis_client is None:
        try:
            client = from_url(str(settings.REDIS_URL), decode_responses=True)
            await client.ping()
            redis_client = client
        except Exception as exc:
            logger.warning(
                "Redis connection unavailable; continuing without cache",
                extra={"redis_url": str(settings.REDIS_URL), "error": str(exc)},
            )
            redis_client = None
            return None

    return redis_client
