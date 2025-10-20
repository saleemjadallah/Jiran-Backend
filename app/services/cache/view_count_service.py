"""View count service with write-behind pattern.

Buffers view counts in Redis and syncs to database in batches.
Reduces database load for high-frequency view tracking.
"""

import logging
from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class ViewCountService:
    """Write-behind pattern for view counts.

    Flow:
    1. User views product → Increment Redis counter
    2. Background job runs every 5s
    3. Batch sync counters to DB
    4. Clear Redis counters

    This prevents overwhelming the database with individual view updates.
    """

    def __init__(self, redis: RedisManager, db: AsyncSession):
        """Initialize view count service.

        Args:
            redis: Redis manager instance
            db: Database session
        """
        self.redis = redis
        self.db = db

    async def increment_view(self, product_id: str) -> int:
        """Increment view count in Redis (fast operation).

        Args:
            product_id: Product ID to increment views for

        Returns:
            New view count in Redis
        """
        key = f"views:{product_id}"
        count = await self.redis.increment(key)

        logger.debug(f"Incremented view count for product {product_id}: {count}")
        return count

    async def increment_stream_view(self, stream_id: str) -> int:
        """Increment live stream view count in Redis.

        Args:
            stream_id: Stream ID to increment views for

        Returns:
            New view count in Redis
        """
        key = f"stream_views:{stream_id}"
        count = await self.redis.increment(key)

        logger.debug(f"Incremented stream view count for {stream_id}: {count}")
        return count

    async def get_buffered_count(self, product_id: str) -> int:
        """Get buffered view count from Redis (not yet synced to DB).

        Args:
            product_id: Product ID

        Returns:
            Buffered count (0 if no buffered views)
        """
        key = f"views:{product_id}"
        count = await self.redis.get(key)
        return int(count) if count else 0

    async def sync_to_database(self) -> Dict[str, int]:
        """Sync Redis view counters to database.

        This should be called by a background job every 5-10 seconds.

        Returns:
            Dictionary with sync statistics
        """
        stats = {
            "products_synced": 0,
            "streams_synced": 0,
            "total_views": 0,
            "errors": 0,
        }

        # Sync product views
        try:
            product_stats = await self._sync_product_views()
            stats["products_synced"] = product_stats["count"]
            stats["total_views"] += product_stats["total_views"]
        except Exception as e:
            logger.error(f"Error syncing product views: {e}")
            stats["errors"] += 1

        # Sync stream views
        try:
            stream_stats = await self._sync_stream_views()
            stats["streams_synced"] = stream_stats["count"]
            stats["total_views"] += stream_stats["total_views"]
        except Exception as e:
            logger.error(f"Error syncing stream views: {e}")
            stats["errors"] += 1

        return stats

    async def _sync_product_views(self) -> Dict[str, int]:
        """Sync product view counts to database.

        Returns:
            Statistics about the sync operation
        """
        # Get all product view counter keys
        keys = await self.redis.redis.keys("views:*")

        if not keys:
            return {"count": 0, "total_views": 0}

        updates: List[Dict[str, any]] = []
        total_views = 0

        # Collect all counts
        for key in keys:
            product_id = key.split(":", 1)[1]
            count = await self.redis.get(key)

            if count and int(count) > 0:
                updates.append({"id": product_id, "increment": int(count)})
                total_views += int(count)

        if not updates:
            return {"count": 0, "total_views": 0}

        # Batch update database
        try:
            # Use a single transaction
            for update in updates:
                await self.db.execute(
                    text(
                        """
                        UPDATE products
                        SET views = views + :increment,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                        """
                    ),
                    update,
                )

            await self.db.commit()

            # Clear Redis counters after successful sync
            await self.redis.delete(*keys)

            logger.info(
                f"Synced {len(updates)} product view counts ({total_views} total views)"
            )

            return {"count": len(updates), "total_views": total_views}

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to sync product views: {e}")
            raise

    async def _sync_stream_views(self) -> Dict[str, int]:
        """Sync live stream view counts to database.

        Returns:
            Statistics about the sync operation
        """
        # Get all stream view counter keys
        keys = await self.redis.redis.keys("stream_views:*")

        if not keys:
            return {"count": 0, "total_views": 0}

        updates: List[Dict[str, any]] = []
        total_views = 0

        # Collect all counts
        for key in keys:
            stream_id = key.split(":", 1)[1]
            count = await self.redis.get(key)

            if count and int(count) > 0:
                updates.append({"id": stream_id, "increment": int(count)})
                total_views += int(count)

        if not updates:
            return {"count": 0, "total_views": 0}

        # Batch update database
        try:
            # Use a single transaction
            for update in updates:
                await self.db.execute(
                    text(
                        """
                        UPDATE live_streams
                        SET views = views + :increment,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                        """
                    ),
                    update,
                )

            await self.db.commit()

            # Clear Redis counters after successful sync
            await self.redis.delete(*keys)

            logger.info(
                f"Synced {len(updates)} stream view counts ({total_views} total views)"
            )

            return {"count": len(updates), "total_views": total_views}

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to sync stream views: {e}")
            raise

    async def force_sync(self, product_id: str) -> None:
        """Force immediate sync of a specific product's view count.

        Use this when you need immediate accuracy (e.g., before displaying stats).

        Args:
            product_id: Product ID to sync
        """
        key = f"views:{product_id}"
        count = await self.redis.get(key)

        if count and int(count) > 0:
            await self.db.execute(
                text(
                    """
                    UPDATE products
                    SET views = views + :increment,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """
                ),
                {"id": product_id, "increment": int(count)},
            )
            await self.db.commit()
            await self.redis.delete(key)

            logger.info(f"Force synced {count} views for product {product_id}")
