"""Background job to cleanup old cache entries.

Runs daily at 3 AM to remove stale cache entries and orphaned keys.
"""

import logging

from app.core.cache.redis_manager import get_redis_manager

logger = logging.getLogger(__name__)


async def cleanup_old_cache_job() -> None:
    """Clean up old and orphaned cache entries.

    This job runs daily to:
    - Remove expired keys
    - Clean up orphaned compressed cache entries
    - Report cache statistics
    """
    try:
        redis = get_redis_manager()

        # Get initial stats
        initial_keys = await redis.redis.dbsize()
        logger.info(f"Cache cleanup started. Total keys: {initial_keys}")

        # Clean up orphaned compressed entries
        # (entries where :compressed exists but :is_compressed doesn't)
        orphaned_count = 0

        # Get all compressed keys
        compressed_keys = await redis.redis.keys("*:compressed")

        for compressed_key in compressed_keys:
            # Get base key
            base_key = compressed_key.rsplit(":compressed", 1)[0]
            is_compressed_key = f"{base_key}:is_compressed"

            # Check if is_compressed flag exists
            exists = await redis.exists(is_compressed_key)

            if not exists:
                # Orphaned compressed entry, delete it
                await redis.delete(compressed_key)
                orphaned_count += 1

        # Get final stats
        final_keys = await redis.redis.dbsize()
        deleted_keys = initial_keys - final_keys

        logger.info(
            f"Cache cleanup completed. "
            f"Deleted {deleted_keys} expired keys, "
            f"{orphaned_count} orphaned compressed entries. "
            f"Final total: {final_keys} keys"
        )

        # Get memory stats
        info = await redis.redis.info()
        memory_mb = round(int(info.get("used_memory", 0)) / (1024 * 1024), 2)
        logger.info(f"Redis memory usage: {memory_mb} MB")

    except Exception as e:
        logger.error(f"Error in cleanup_old_cache_job: {e}", exc_info=True)
