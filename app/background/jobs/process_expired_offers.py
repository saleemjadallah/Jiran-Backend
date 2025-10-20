"""Background job to process expired offers.

Runs every 1 minute to mark expired offers and send notifications.
"""

import logging

from app.core.cache.redis_manager import get_redis_manager
from app.core.database import get_async_session
from app.services.cache.offer_cache_service import OfferCacheService

logger = logging.getLogger(__name__)


async def process_expired_offers_job() -> None:
    """Process expired offers and mark them in the database.

    This job runs every 1 minute to check for offers that have expired
    and updates their status in the database.
    """
    try:
        # Get dependencies
        redis = get_redis_manager()
        async with get_async_session() as db:
            # Create service
            service = OfferCacheService(redis=redis, db=db)

            # Process expired offers
            stats = await service.process_expired_offers()

            if stats["processed"] > 0:
                logger.info(
                    f"Offer expiration: {stats['processed']} offers processed, "
                    f"{stats['database_updated']} updated, "
                    f"{stats['errors']} errors"
                )

            # Also cleanup orphaned entries once per hour
            # (only run if current minute is 0)
            from datetime import datetime

            if datetime.now().minute == 0:
                orphaned = await service.cleanup_orphaned_entries()
                if orphaned > 0:
                    logger.info(f"Cleaned up {orphaned} orphaned offer entries")

    except Exception as e:
        logger.error(f"Error in process_expired_offers_job: {e}", exc_info=True)
