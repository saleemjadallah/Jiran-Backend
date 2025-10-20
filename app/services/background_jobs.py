"""
Background Jobs

Handles periodic background tasks.

Jobs:
- cleanup_expired_offers - Expire old pending offers
- cleanup_stale_connections - Remove disconnected WebSocket sessions
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.offer import Offer, OfferStatus
from app.models.user import User

logger = logging.getLogger(__name__)


async def cleanup_expired_offers():
    """
    Find and expire pending offers that have passed their expiration time.

    Runs every hour to:
    - Find offers where expires_at < now() AND status = 'pending'
    - Set status = 'expired'
    - Notify buyers that offer expired
    - Clean up old expired offers (> 30 days)
    """
    async with async_session_maker() as db:
        try:
            # Find expired pending offers
            now = datetime.utcnow()

            stmt = (
                select(Offer)
                .where(
                    and_(
                        Offer.status == OfferStatus.PENDING,
                        Offer.expires_at < now,
                    )
                )
            )

            result = await db.execute(stmt)
            expired_offers = result.scalars().all()

            if not expired_offers:
                logger.info("No expired offers found")
                return

            # Update offers to expired status
            for offer in expired_offers:
                offer.status = OfferStatus.EXPIRED

                # TODO: Send notification to buyer
                logger.info(f"Offer {offer.id} expired, should notify buyer {offer.buyer_id}")

            await db.commit()

            logger.info(f"Expired {len(expired_offers)} offers")

            # Clean up very old expired offers (optional, to keep database clean)
            # Delete offers expired more than 30 days ago
            # Uncomment if you want automatic deletion
            """
            from datetime import timedelta
            thirty_days_ago = now - timedelta(days=30)

            delete_stmt = (
                delete(Offer)
                .where(
                    and_(
                        Offer.status == OfferStatus.EXPIRED,
                        Offer.expires_at < thirty_days_ago,
                    )
                )
            )

            result = await db.execute(delete_stmt)
            deleted_count = result.rowcount
            await db.commit()

            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old expired offers")
            """

        except Exception as e:
            logger.error(f"Error cleaning up expired offers: {e}")
            await db.rollback()


async def periodic_cleanup_expired_offers(interval: int = 3600):
    """
    Run cleanup_expired_offers periodically.

    Args:
        interval: Seconds between runs (default: 3600 = 1 hour)
    """
    while True:
        try:
            logger.info("Running expired offers cleanup...")
            await cleanup_expired_offers()
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

        await asyncio.sleep(interval)


async def start_background_jobs():
    """
    Start all background jobs.

    Call this from the FastAPI lifespan event.
    """
    logger.info("Starting background jobs...")

    # Start expired offers cleanup (every hour)
    asyncio.create_task(periodic_cleanup_expired_offers(interval=3600))

    # Add more background jobs here as needed
    logger.info("Background jobs started")


# Individual job functions for manual execution

async def notify_offer_expiration(offer: Offer, db: AsyncSession):
    """
    Send notification to buyer about expired offer.

    Args:
        offer: The expired offer
        db: Database session
    """
    # TODO: Implement push notification
    # TODO: Implement email notification
    # TODO: Send WebSocket event if user is online

    buyer_id = offer.buyer_id
    product_id = offer.product_id

    logger.info(
        f"Notifying buyer {buyer_id} about expired offer {offer.id} for product {product_id}"
    )

    # Placeholder for actual notification implementation
    # from app.services.notification_service import send_push_notification
    #
    # await send_push_notification(
    #     user_id=buyer_id,
    #     title="Offer Expired",
    #     body=f"Your offer on {product.title} has expired",
    #     data={
    #         "type": "offer_expired",
    #         "offer_id": str(offer.id),
    #         "product_id": str(product_id),
    #     },
    # )
