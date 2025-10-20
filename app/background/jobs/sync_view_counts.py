"""Background job to sync view counts from Redis to database.

Runs every 5 seconds to batch-sync view counts.
"""

import logging

from app.core.cache.redis_manager import get_redis_manager
from app.core.database import get_async_session
from app.services.cache.view_count_service import ViewCountService

logger = logging.getLogger(__name__)


async def sync_view_counts_job() -> None:
    """Sync buffered view counts from Redis to PostgreSQL.

    This job runs every 5 seconds to prevent overwhelming the database
    with individual view increments.
    """
    try:
        # Get dependencies
        redis = get_redis_manager()
        async with get_async_session() as db:
            # Create service
            service = ViewCountService(redis=redis, db=db)

            # Sync to database
            stats = await service.sync_to_database()

            if stats["total_views"] > 0:
                logger.info(
                    f"View count sync: {stats['products_synced']} products, "
                    f"{stats['streams_synced']} streams, "
                    f"{stats['total_views']} total views synced"
                )

    except Exception as e:
        logger.error(f"Error in sync_view_counts_job: {e}", exc_info=True)
