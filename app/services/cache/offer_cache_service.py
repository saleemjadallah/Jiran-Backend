"""Offer expiration service with Redis-based tracking.

Manages offer expiration using Redis sorted sets for efficient time-based queries.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class OfferCacheService:
    """Manage offer expiration with Redis sorted sets.

    Flow:
    1. When offer is created → Add to Redis sorted set with expiration timestamp
    2. Background job runs every minute
    3. Query sorted set for expired offers
    4. Update database to mark as expired
    5. Remove from sorted set
    6. Broadcast WebSocket events to affected users
    """

    EXPIRING_OFFERS_KEY = "offers:expiring"
    OFFER_EXPIRATION_PREFIX = "offer:expires_at:"

    def __init__(self, redis: RedisManager, db: AsyncSession):
        """Initialize offer cache service.

        Args:
            redis: Redis manager instance
            db: Database session
        """
        self.redis = redis
        self.db = db

    async def track_offer_expiration(
        self, offer_id: str, expires_at: datetime
    ) -> None:
        """Track offer expiration in Redis.

        Args:
            offer_id: Offer ID
            expires_at: Expiration datetime
        """
        # Add to sorted set with expiration timestamp as score
        timestamp = expires_at.timestamp()
        await self.redis.zadd(
            self.EXPIRING_OFFERS_KEY, {offer_id: timestamp}, ttl=None
        )

        # Also set individual expiration key for quick lookup
        ttl_seconds = int((expires_at - datetime.utcnow()).total_seconds())
        if ttl_seconds > 0:
            await self.redis.set(
                f"{self.OFFER_EXPIRATION_PREFIX}{offer_id}",
                expires_at.isoformat(),
                ttl=ttl_seconds,
            )

        logger.debug(f"Tracking offer {offer_id} expiration at {expires_at}")

    async def get_offer_expiration(self, offer_id: str) -> Optional[datetime]:
        """Get offer expiration time from Redis.

        Args:
            offer_id: Offer ID

        Returns:
            Expiration datetime or None if not found
        """
        key = f"{self.OFFER_EXPIRATION_PREFIX}{offer_id}"
        expires_at_str = await self.redis.get(key)

        if expires_at_str:
            return datetime.fromisoformat(expires_at_str)
        return None

    async def remove_offer_tracking(self, offer_id: str) -> None:
        """Remove offer from expiration tracking.

        Call this when offer is accepted, declined, or cancelled.

        Args:
            offer_id: Offer ID
        """
        # Remove from sorted set
        await self.redis.zrem(self.EXPIRING_OFFERS_KEY, offer_id)

        # Remove expiration key
        key = f"{self.OFFER_EXPIRATION_PREFIX}{offer_id}"
        await self.redis.delete(key)

        logger.debug(f"Removed offer {offer_id} from expiration tracking")

    async def get_expiring_soon(
        self, within_minutes: int = 5
    ) -> List[Dict[str, any]]:
        """Get offers expiring within specified minutes.

        Useful for sending reminder notifications.

        Args:
            within_minutes: Time window in minutes

        Returns:
            List of offer IDs and expiration times
        """
        current_time = time.time()
        future_time = current_time + (within_minutes * 60)

        # Get offers expiring in time window
        offer_ids = await self.redis.zrangebyscore(
            self.EXPIRING_OFFERS_KEY, min_score=current_time, max_score=future_time
        )

        results = []
        for offer_id in offer_ids:
            # Get expiration time
            expires_at = await self.get_offer_expiration(offer_id)
            if expires_at:
                results.append({"offer_id": offer_id, "expires_at": expires_at})

        return results

    async def process_expired_offers(self) -> Dict[str, int]:
        """Process all expired offers.

        This should be called by a background job every 1 minute.

        Returns:
            Statistics about processed offers
        """
        current_timestamp = time.time()

        # Get offers that have expired (score < current_timestamp)
        expired_offer_ids = await self.redis.zrangebyscore(
            self.EXPIRING_OFFERS_KEY, min_score=0, max_score=current_timestamp
        )

        if not expired_offer_ids:
            return {
                "processed": 0,
                "database_updated": 0,
                "errors": 0,
            }

        logger.info(f"Processing {len(expired_offer_ids)} expired offers")

        # Update database
        updated_count = 0
        error_count = 0

        try:
            # Update all expired offers in database
            result = await self.db.execute(
                text(
                    """
                    UPDATE offers
                    SET status = 'expired',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ANY(:ids)
                      AND status = 'pending'
                    RETURNING id
                    """
                ),
                {"ids": expired_offer_ids},
            )

            updated_rows = result.fetchall()
            updated_count = len(updated_rows)

            await self.db.commit()

            # Remove from Redis sorted set
            if updated_count > 0:
                await self.redis.zrem(self.EXPIRING_OFFERS_KEY, *expired_offer_ids)

                # Remove individual expiration keys
                for offer_id in expired_offer_ids:
                    key = f"{self.OFFER_EXPIRATION_PREFIX}{offer_id}"
                    await self.redis.delete(key)

            logger.info(f"Marked {updated_count} offers as expired")

            return {
                "processed": len(expired_offer_ids),
                "database_updated": updated_count,
                "errors": error_count,
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing expired offers: {e}")
            error_count = len(expired_offer_ids)

            return {
                "processed": len(expired_offer_ids),
                "database_updated": updated_count,
                "errors": error_count,
            }

    async def extend_offer_expiration(
        self, offer_id: str, extend_by_hours: int = 24
    ) -> datetime:
        """Extend offer expiration time.

        Args:
            offer_id: Offer ID
            extend_by_hours: Hours to extend by (default: 24)

        Returns:
            New expiration datetime
        """
        # Get current expiration
        current_expiration = await self.get_offer_expiration(offer_id)

        if not current_expiration:
            raise ValueError(f"Offer {offer_id} not found in expiration tracking")

        # Calculate new expiration
        new_expiration = current_expiration + timedelta(hours=extend_by_hours)

        # Update tracking
        await self.track_offer_expiration(offer_id, new_expiration)

        # Update database
        await self.db.execute(
            text(
                """
                UPDATE offers
                SET expires_at = :expires_at,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {"id": offer_id, "expires_at": new_expiration},
        )
        await self.db.commit()

        logger.info(
            f"Extended offer {offer_id} expiration to {new_expiration}"
        )

        return new_expiration

    async def get_active_offer_count(self) -> int:
        """Get count of offers being tracked for expiration.

        Returns:
            Number of active tracked offers
        """
        count = await self.redis.zcard(self.EXPIRING_OFFERS_KEY)
        return count

    async def cleanup_orphaned_entries(self) -> int:
        """Remove orphaned entries from expiration tracking.

        This checks for offers in Redis that no longer exist or are already expired
        in the database.

        Returns:
            Number of entries cleaned up
        """
        # Get all tracked offer IDs
        all_offer_ids = await self.redis.zrange(
            self.EXPIRING_OFFERS_KEY, start=0, end=-1
        )

        if not all_offer_ids:
            return 0

        # Check which offers still exist and are pending in database
        result = await self.db.execute(
            text(
                """
                SELECT id FROM offers
                WHERE id = ANY(:ids)
                  AND status = 'pending'
                """
            ),
            {"ids": all_offer_ids},
        )

        valid_ids = {str(row[0]) for row in result.fetchall()}

        # Find orphaned entries
        orphaned_ids = [oid for oid in all_offer_ids if oid not in valid_ids]

        if orphaned_ids:
            # Remove orphaned entries
            await self.redis.zrem(self.EXPIRING_OFFERS_KEY, *orphaned_ids)

            for offer_id in orphaned_ids:
                key = f"{self.OFFER_EXPIRATION_PREFIX}{offer_id}"
                await self.redis.delete(key)

            logger.info(f"Cleaned up {len(orphaned_ids)} orphaned offer entries")

        return len(orphaned_ids)
