from redis.asyncio import Redis, from_url

from app.config import settings


# Convert Pydantic Url object to string for Redis
redis_client: Redis = from_url(str(settings.REDIS_URL), decode_responses=True)


async def get_redis() -> Redis:
    return redis_client

