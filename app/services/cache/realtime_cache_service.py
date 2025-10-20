"""Real-Time Cache Service

Handles real-time features using Redis:
- Viewer count tracking (sorted sets)
- Typing indicators (3s TTL)
- Presence status (5min TTL)
- Unread message counters

Phase 4: Real-Time Features Implementation
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Set

from app.core.cache.redis_manager import RedisManager


class RealTimeCacheService:
    """Service for real-time features using Redis.

    Features:
    - Live stream viewer tracking with sorted sets
    - Typing indicators with automatic expiration
    - User presence status (online/offline/away)
    - Unread message counters
    """

    # TTLs (in seconds)
    TYPING_INDICATOR_TTL = 3       # 3 seconds
    PRESENCE_STATUS_TTL = 300      # 5 minutes

    # Presence status values
    STATUS_ONLINE = "online"
    STATUS_AWAY = "away"
    STATUS_OFFLINE = "offline"

    def __init__(self, redis: RedisManager):
        """Initialize real-time cache service.

        Args:
            redis: Redis manager instance
        """
        self.redis = redis

    # ========== Viewer Count Tracking ==========

    async def add_viewer(self, stream_id: str, user_id: str) -> int:
        """Add viewer to live stream.

        Uses Redis sorted set with join timestamp as score.

        Args:
            stream_id: Live stream ID
            user_id: User ID joining the stream

        Returns:
            Current viewer count
        """
        key = f"live:stream:{stream_id}:viewers"
        timestamp = time.time()

        # Add user to sorted set (score = join timestamp)
        await self.redis.zadd(key, {user_id: timestamp})

        # Get updated count
        return await self.redis.zcard(key)

    async def remove_viewer(self, stream_id: str, user_id: str) -> int:
        """Remove viewer from live stream.

        Args:
            stream_id: Live stream ID
            user_id: User ID leaving the stream

        Returns:
            Current viewer count
        """
        key = f"live:stream:{stream_id}:viewers"

        # Remove user from sorted set
        await self.redis.zrem(key, user_id)

        # Get updated count
        return await self.redis.zcard(key)

    async def get_viewer_count(self, stream_id: str) -> int:
        """Get current viewer count for stream.

        Args:
            stream_id: Live stream ID

        Returns:
            Number of viewers
        """
        key = f"live:stream:{stream_id}:viewers"
        return await self.redis.zcard(key)

    async def get_viewers(self, stream_id: str) -> List[str]:
        """Get list of viewer user IDs.

        Args:
            stream_id: Live stream ID

        Returns:
            List of user IDs currently watching
        """
        key = f"live:stream:{stream_id}:viewers"
        # Get all members (sorted by join time)
        return await self.redis.zrange(key, 0, -1)

    async def is_viewing(self, stream_id: str, user_id: str) -> bool:
        """Check if user is currently viewing stream.

        Args:
            stream_id: Live stream ID
            user_id: User ID to check

        Returns:
            True if user is viewing
        """
        key = f"live:stream:{stream_id}:viewers"
        # Check if user is in sorted set
        score = await self.redis.redis.zscore(key, user_id)
        return score is not None

    async def clear_viewers(self, stream_id: str) -> None:
        """Clear all viewers when stream ends.

        Args:
            stream_id: Live stream ID
        """
        key = f"live:stream:{stream_id}:viewers"
        await self.redis.delete(key)

    # ========== Typing Indicators ==========

    async def set_typing(self, conversation_id: str, user_id: str) -> None:
        """Set typing indicator for user in conversation.

        Automatically expires after 3 seconds.

        Args:
            conversation_id: Conversation ID
            user_id: User who is typing
        """
        key = f"typing:{conversation_id}:{user_id}"
        timestamp = datetime.utcnow().isoformat()

        # Set with 3-second TTL
        await self.redis.set(key, timestamp, ttl=self.TYPING_INDICATOR_TTL)

    async def clear_typing(self, conversation_id: str, user_id: str) -> None:
        """Clear typing indicator for user.

        Args:
            conversation_id: Conversation ID
            user_id: User who stopped typing
        """
        key = f"typing:{conversation_id}:{user_id}"
        await self.redis.delete(key)

    async def get_typing_users(self, conversation_id: str) -> List[str]:
        """Get list of users currently typing in conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of user IDs currently typing
        """
        # Use pattern to find all typing indicators for this conversation
        pattern = f"typing:{conversation_id}:*"
        keys = await self.redis.redis.keys(pattern)

        # Extract user IDs from keys
        typing_users = []
        for key in keys:
            # Key format: "typing:{conversation_id}:{user_id}"
            parts = key.split(":")
            if len(parts) == 3:
                user_id = parts[2]
                typing_users.append(user_id)

        return typing_users

    async def is_typing(self, conversation_id: str, user_id: str) -> bool:
        """Check if user is currently typing.

        Args:
            conversation_id: Conversation ID
            user_id: User ID to check

        Returns:
            True if user is typing
        """
        key = f"typing:{conversation_id}:{user_id}"
        return await self.redis.exists(key)

    # ========== Presence Status ==========

    async def set_presence(
        self,
        user_id: str,
        status: str = STATUS_ONLINE
    ) -> None:
        """Set user presence status.

        Automatically expires after 5 minutes unless refreshed.
        Should be refreshed every 30 seconds by active clients.

        Args:
            user_id: User ID
            status: Status value (online, away, offline)
        """
        key = f"presence:{user_id}"

        # Validate status
        valid_statuses = {self.STATUS_ONLINE, self.STATUS_AWAY, self.STATUS_OFFLINE}
        if status not in valid_statuses:
            status = self.STATUS_ONLINE

        # Set with 5-minute TTL
        await self.redis.set(key, status, ttl=self.PRESENCE_STATUS_TTL)

    async def get_presence(self, user_id: str) -> str:
        """Get user presence status.

        Args:
            user_id: User ID

        Returns:
            Presence status (online, away, offline, or offline if not found)
        """
        key = f"presence:{user_id}"
        status = await self.redis.get(key)

        # If no status found, user is offline
        if status is None:
            return self.STATUS_OFFLINE

        return status

    async def get_presence_batch(self, user_ids: List[str]) -> Dict[str, str]:
        """Get presence status for multiple users.

        Args:
            user_ids: List of user IDs

        Returns:
            Dictionary of user_id: status
        """
        if not user_ids:
            return {}

        # Build cache keys
        keys = [f"presence:{user_id}" for user_id in user_ids]

        # Batch fetch
        statuses = await self.redis.mget(keys)

        # Map results
        result = {}
        for user_id, status in zip(user_ids, statuses):
            result[user_id] = status if status else self.STATUS_OFFLINE

        return result

    async def set_offline(self, user_id: str) -> None:
        """Set user as offline (delete presence key).

        Args:
            user_id: User ID
        """
        key = f"presence:{user_id}"
        await self.redis.delete(key)

    async def is_online(self, user_id: str) -> bool:
        """Check if user is online.

        Args:
            user_id: User ID

        Returns:
            True if user is online
        """
        status = await self.get_presence(user_id)
        return status == self.STATUS_ONLINE

    # ========== Unread Message Counters ==========

    async def increment_unread_count(
        self,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> int:
        """Increment unread message count.

        Args:
            user_id: User ID
            conversation_id: Optional specific conversation ID

        Returns:
            New unread count
        """
        if conversation_id:
            # Conversation-specific unread count
            key = f"unread:{user_id}:conversation:{conversation_id}"
        else:
            # Total unread messages
            key = f"unread:{user_id}:messages"

        return await self.redis.increment(key)

    async def decrement_unread_count(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        amount: int = 1
    ) -> int:
        """Decrement unread message count.

        Args:
            user_id: User ID
            conversation_id: Optional specific conversation ID
            amount: Amount to decrement by

        Returns:
            New unread count (won't go below 0)
        """
        if conversation_id:
            key = f"unread:{user_id}:conversation:{conversation_id}"
        else:
            key = f"unread:{user_id}:messages"

        # Decrement
        new_count = await self.redis.decrement(key, amount)

        # Ensure it doesn't go negative
        if new_count < 0:
            await self.redis.set(key, 0)
            return 0

        return new_count

    async def get_unread_count(
        self,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> int:
        """Get unread message count.

        Args:
            user_id: User ID
            conversation_id: Optional specific conversation ID

        Returns:
            Unread message count
        """
        if conversation_id:
            key = f"unread:{user_id}:conversation:{conversation_id}"
        else:
            key = f"unread:{user_id}:messages"

        count = await self.redis.get(key)
        return int(count) if count else 0

    async def reset_unread_count(
        self,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> None:
        """Reset unread message count to zero.

        Args:
            user_id: User ID
            conversation_id: Optional specific conversation ID
        """
        if conversation_id:
            key = f"unread:{user_id}:conversation:{conversation_id}"
        else:
            key = f"unread:{user_id}:messages"

        await self.redis.set(key, 0)

    async def get_all_conversation_unread_counts(self, user_id: str) -> Dict[str, int]:
        """Get unread counts for all conversations.

        Args:
            user_id: User ID

        Returns:
            Dictionary of conversation_id: unread_count
        """
        pattern = f"unread:{user_id}:conversation:*"
        keys = await self.redis.redis.keys(pattern)

        if not keys:
            return {}

        # Batch fetch counts
        counts = await self.redis.mget(keys)

        # Map to conversation IDs
        result = {}
        for key, count in zip(keys, counts):
            # Extract conversation ID from key
            # Key format: "unread:{user_id}:conversation:{conversation_id}"
            parts = key.split(":")
            if len(parts) == 4:
                conversation_id = parts[3]
                result[conversation_id] = int(count) if count else 0

        return result

    # ========== Unread Notification Counters ==========

    async def increment_notification_count(self, user_id: str) -> int:
        """Increment unread notification count.

        Args:
            user_id: User ID

        Returns:
            New notification count
        """
        key = f"unread:{user_id}:notifications"
        return await self.redis.increment(key)

    async def get_notification_count(self, user_id: str) -> int:
        """Get unread notification count.

        Args:
            user_id: User ID

        Returns:
            Unread notification count
        """
        key = f"unread:{user_id}:notifications"
        count = await self.redis.get(key)
        return int(count) if count else 0

    async def reset_notification_count(self, user_id: str) -> None:
        """Reset unread notification count to zero.

        Args:
            user_id: User ID
        """
        key = f"unread:{user_id}:notifications"
        await self.redis.set(key, 0)

    # ========== Active Streams by Location ==========

    async def add_active_stream(self, neighborhood: str, stream_id: str) -> None:
        """Add stream to active streams for a neighborhood.

        Args:
            neighborhood: Neighborhood name
            stream_id: Live stream ID
        """
        key = f"live:active:location:{neighborhood}"
        await self.redis.sadd(key, stream_id)

    async def remove_active_stream(self, neighborhood: str, stream_id: str) -> None:
        """Remove stream from active streams.

        Args:
            neighborhood: Neighborhood name
            stream_id: Live stream ID
        """
        key = f"live:active:location:{neighborhood}"
        await self.redis.srem(key, stream_id)

    async def get_active_streams(self, neighborhood: str) -> Set[str]:
        """Get all active stream IDs for a neighborhood.

        Args:
            neighborhood: Neighborhood name

        Returns:
            Set of active stream IDs
        """
        key = f"live:active:location:{neighborhood}"
        return await self.redis.smembers(key)

    async def get_active_stream_count(self, neighborhood: str) -> int:
        """Get count of active streams in neighborhood.

        Args:
            neighborhood: Neighborhood name

        Returns:
            Number of active streams
        """
        key = f"live:active:location:{neighborhood}"
        return await self.redis.scard(key)
