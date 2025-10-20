"""Stream Repository with cache integration."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.redis_manager import RedisManager
from app.db.repositories.base_repository import BaseRepository
from app.models.stream import Stream, StreamStatus


class StreamRepository(BaseRepository[Stream]):
    """Repository for Stream model with caching.

    Provides:
    - Standard CRUD operations with cache
    - Stream-specific queries
    - Feed cache invalidation on status changes
    """

    def __init__(self, db: AsyncSession, redis: RedisManager):
        """Initialize stream repository.

        Args:
            db: Database session
            redis: Redis manager for caching
        """
        super().__init__(
            db=db,
            redis=redis,
            model=Stream,
            cache_prefix="stream",
            default_ttl=600,  # 10 minutes
        )

    async def get_live_streams(
        self, offset: int = 0, limit: int = 20
    ) -> List[Stream]:
        """Get all currently live streams.

        Args:
            offset: Pagination offset
            limit: Page size

        Returns:
            List of live Stream instances
        """
        # Build cache key
        cache_key = f"stream:live:offset:{offset}:limit:{limit}"

        # Check cache
        cached = await self.redis.get(cache_key)
        if cached:
            return [self._deserialize(item) for item in cached]

        # Query database
        result = await self.db.execute(
            select(Stream)
            .where(Stream.status == StreamStatus.LIVE)
            .order_by(Stream.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        streams = list(result.scalars().all())

        # Cache for 1 minute (live streams change frequently)
        serialized = [self._serialize(s) for s in streams]
        await self.redis.set(cache_key, serialized, ttl=60)

        return streams

    async def get_stream_by_user(
        self, user_id: str, status: Optional[StreamStatus] = None
    ) -> List[Stream]:
        """Get streams by user ID.

        Args:
            user_id: User ID
            status: Optional status filter

        Returns:
            List of Stream instances
        """
        # Build cache key
        cache_key = f"stream:user:{user_id}:status:{status}"

        # Check cache
        cached = await self.redis.get(cache_key)
        if cached:
            return [self._deserialize(item) for item in cached]

        # Build query
        query = select(Stream).where(Stream.user_id == user_id)
        if status:
            query = query.where(Stream.status == status)
        query = query.order_by(Stream.created_at.desc())

        # Execute
        result = await self.db.execute(query)
        streams = list(result.scalars().all())

        # Cache for 5 minutes
        serialized = [self._serialize(s) for s in streams]
        await self.redis.set(cache_key, serialized, ttl=300)

        return streams

    async def _invalidate_related_caches(self, entity: Stream) -> None:
        """Invalidate stream-related caches.

        Invalidates:
        - Stream-specific cache
        - Live streams list
        - User's streams
        - **IMPORTANT: All feed caches** (when stream status changes)

        Args:
            entity: Stream instance
        """
        # Invalidate specific stream
        await self.redis.delete(f"stream:{entity.id}")

        # Invalidate live streams list
        await self.redis.delete_pattern("stream:live:*")

        # Invalidate user's streams
        await self.redis.delete_pattern(f"stream:user:{entity.user_id}:*")

        # ========== CRITICAL: Invalidate ALL feed caches ==========
        # When a stream goes live or ends, feeds need to refresh
        # to show updated live badges and viewer counts
        await self.redis.delete_pattern("feed:*")

        # Also invalidate list caches
        await self.redis.delete_pattern("stream:list:*")
