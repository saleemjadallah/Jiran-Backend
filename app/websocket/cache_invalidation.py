"""WebSocket Event Handlers for Cache Invalidation

Handles cache invalidation triggers from WebSocket events:
- Stream status changes (live/ended)
- Product updates
- User profile updates
- Message/notification events

These events trigger cache invalidation across the application
to ensure real-time consistency between cached and fresh data.
"""

import logging
from typing import Optional

from app.core.cache.redis_manager import RedisManager
from app.core.redis import get_redis
from app.services.cache.feed_cache_service import FeedCacheService
from app.services.cache.realtime_cache_service import RealTimeCacheService
from app.websocket.manager import ConnectionManager
from app.websocket.server import sio

logger = logging.getLogger(__name__)

manager: Optional[ConnectionManager] = None


def set_manager(conn_manager: ConnectionManager):
    """Set the WebSocket connection manager.

    Args:
        conn_manager: Connection manager instance
    """
    global manager
    manager = conn_manager


async def _get_feed_cache_service() -> FeedCacheService:
    """Get FeedCacheService instance.

    Returns:
        FeedCacheService instance
    """
    redis = await get_redis()
    redis_manager = RedisManager(redis)
    return FeedCacheService(redis_manager)


async def _get_realtime_cache_service() -> RealTimeCacheService:
    """Get RealTimeCacheService instance.

    Returns:
        RealTimeCacheService instance
    """
    redis = await get_redis()
    redis_manager = RedisManager(redis)
    return RealTimeCacheService(redis_manager)


# ============================================================================
# STREAM STATUS CHANGE EVENTS
# ============================================================================


@sio.event
async def stream_status_changed(sid, data: dict):
    """Handle stream status change event.

    Triggered when:
    - Stream goes live (status: SCHEDULED → LIVE)
    - Stream ends (status: LIVE → ENDED)

    This invalidates all feed caches to ensure live badges and
    viewer counts are updated immediately.

    Data:
        stream_id: UUID of the stream
        old_status: Previous stream status
        new_status: New stream status
        timestamp: ISO timestamp of change

    Emits:
        - cache_invalidated: Confirmation event to sender
        - feed_refresh_required: Broadcast to all clients in feed rooms
    """
    stream_id = data.get("stream_id")
    old_status = data.get("old_status")
    new_status = data.get("new_status")

    logger.info(
        f"Stream {stream_id} status changed: {old_status} → {new_status}"
    )

    try:
        # Get feed cache service
        feed_cache = await _get_feed_cache_service()

        # Invalidate all feed caches
        deleted_count = await feed_cache.invalidate_all_feeds()

        logger.info(
            f"Invalidated {deleted_count} feed cache keys for stream {stream_id}"
        )

        # Emit confirmation to sender
        await sio.emit(
            "cache_invalidated",
            {
                "type": "stream_status",
                "stream_id": stream_id,
                "cache_keys_cleared": deleted_count,
                "timestamp": data.get("timestamp"),
            },
            room=sid,
        )

        # Broadcast to all clients that feeds need refresh
        await sio.emit(
            "feed_refresh_required",
            {
                "reason": "stream_status_changed",
                "stream_id": stream_id,
                "new_status": new_status,
            },
            room="discover_feed",  # Room for discover feed listeners
        )

        await sio.emit(
            "feed_refresh_required",
            {
                "reason": "stream_status_changed",
                "stream_id": stream_id,
                "new_status": new_status,
            },
            room="community_feed",  # Room for community feed listeners
        )

    except Exception as e:
        logger.error(f"Error invalidating feed cache: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to invalidate cache", "error": str(e)},
            room=sid,
        )


# ============================================================================
# PRODUCT UPDATE EVENTS
# ============================================================================


@sio.event
async def product_updated(sid, data: dict):
    """Handle product update event.

    Triggered when product is created, updated, or deleted.
    Invalidates feed caches to reflect changes.

    Data:
        product_id: UUID of the product
        action: "created" | "updated" | "deleted" | "sold"
        feed_type: "discover" | "community"

    Emits:
        - cache_invalidated: Confirmation event
        - feed_refresh_required: Broadcast to feed listeners
    """
    product_id = data.get("product_id")
    action = data.get("action")
    feed_type = data.get("feed_type", "both")

    logger.info(f"Product {product_id} {action}")

    try:
        feed_cache = await _get_feed_cache_service()

        # Invalidate relevant feed caches
        deleted_count = 0
        if feed_type == "discover" or feed_type == "both":
            deleted_count += await feed_cache.invalidate_discover_feed()
        if feed_type == "community" or feed_type == "both":
            deleted_count += await feed_cache.invalidate_community_feed()

        logger.info(
            f"Invalidated {deleted_count} feed cache keys for product {product_id}"
        )

        # Emit confirmation
        await sio.emit(
            "cache_invalidated",
            {
                "type": "product",
                "product_id": product_id,
                "action": action,
                "cache_keys_cleared": deleted_count,
            },
            room=sid,
        )

        # Broadcast feed refresh
        room = (
            f"{feed_type}_feed" if feed_type != "both" else "discover_feed"
        )
        await sio.emit(
            "feed_refresh_required",
            {
                "reason": f"product_{action}",
                "product_id": product_id,
            },
            room=room,
        )

        if feed_type == "both":
            await sio.emit(
                "feed_refresh_required",
                {
                    "reason": f"product_{action}",
                    "product_id": product_id,
                },
                room="community_feed",
            )

    except Exception as e:
        logger.error(f"Error invalidating product cache: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to invalidate cache", "error": str(e)},
            room=sid,
        )


# ============================================================================
# MANUAL CACHE CLEAR EVENTS
# ============================================================================


@sio.event
async def clear_feed_cache(sid, data: dict):
    """Manually clear feed caches.

    Admin/developer event to force cache refresh.

    Data:
        feed_type: "discover" | "community" | "all"
        reason: Optional reason for clearing

    Emits:
        - cache_cleared: Confirmation with count
    """
    if manager is None:
        await sio.emit("error", {"message": "Manager not initialized"}, room=sid)
        return

    # Check if user is admin (optional security check)
    # user_id = manager.get_user_from_sid(sid)
    # ... check admin role ...

    feed_type = data.get("feed_type", "all")
    reason = data.get("reason", "manual_clear")

    logger.warning(f"Manual cache clear requested: {feed_type} - {reason}")

    try:
        feed_cache = await _get_feed_cache_service()

        deleted_count = 0
        if feed_type == "discover":
            deleted_count = await feed_cache.invalidate_discover_feed()
        elif feed_type == "community":
            deleted_count = await feed_cache.invalidate_community_feed()
        else:  # "all"
            deleted_count = await feed_cache.invalidate_all_feeds()

        logger.info(f"Manually cleared {deleted_count} cache keys")

        await sio.emit(
            "cache_cleared",
            {
                "feed_type": feed_type,
                "cache_keys_cleared": deleted_count,
                "reason": reason,
            },
            room=sid,
        )

        # Broadcast to all feed listeners
        await sio.emit(
            "feed_refresh_required",
            {"reason": "manual_cache_clear"},
            room="discover_feed",
        )
        await sio.emit(
            "feed_refresh_required",
            {"reason": "manual_cache_clear"},
            room="community_feed",
        )

    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to clear cache", "error": str(e)},
            room=sid,
        )


# ============================================================================
# CACHE STATISTICS
# ============================================================================


@sio.event
async def get_cache_stats(sid, data: dict):
    """Get cache statistics.

    Returns current cache state for monitoring.

    Emits:
        - cache_stats: Cache key counts and metrics
    """
    try:
        feed_cache = await _get_feed_cache_service()
        stats = await feed_cache.get_cache_stats()

        await sio.emit(
            "cache_stats",
            {
                "discover_cache_entries": stats["discover_cache_entries"],
                "community_cache_entries": stats["community_cache_entries"],
                "total_feed_cache_entries": stats["total_feed_cache_entries"],
            },
            room=sid,
        )

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to get cache stats", "error": str(e)},
            room=sid,
        )


# ============================================================================
# REAL-TIME FEATURES - PHASE 4
# ============================================================================


# ========== Live Stream Viewer Events ==========


@sio.event
async def viewer_joined(sid, data: dict):
    """Handle viewer joining a live stream.

    Updates viewer count in Redis and broadcasts to all viewers.

    Data:
        stream_id: UUID of the live stream
        user_id: UUID of the viewer

    Emits:
        - viewer_count_updated: Broadcast new count to all stream viewers
    """
    stream_id = data.get("stream_id")
    user_id = data.get("user_id")

    if not stream_id or not user_id:
        await sio.emit("error", {"message": "Missing stream_id or user_id"}, room=sid)
        return

    try:
        realtime_cache = await _get_realtime_cache_service()

        # Add viewer to Redis sorted set
        viewer_count = await realtime_cache.add_viewer(stream_id, user_id)

        logger.info(f"Viewer {user_id} joined stream {stream_id}. Count: {viewer_count}")

        # Join the stream room for real-time updates
        await sio.enter_room(sid, f"stream:{stream_id}")

        # Broadcast updated count to all viewers in the stream
        await sio.emit(
            "viewer_count_updated",
            {
                "stream_id": stream_id,
                "count": viewer_count,
                "action": "joined",
            },
            room=f"stream:{stream_id}",
        )

    except Exception as e:
        logger.error(f"Error handling viewer join: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to join stream", "error": str(e)},
            room=sid,
        )


@sio.event
async def viewer_left(sid, data: dict):
    """Handle viewer leaving a live stream.

    Updates viewer count in Redis and broadcasts to remaining viewers.

    Data:
        stream_id: UUID of the live stream
        user_id: UUID of the viewer

    Emits:
        - viewer_count_updated: Broadcast new count to remaining viewers
    """
    stream_id = data.get("stream_id")
    user_id = data.get("user_id")

    if not stream_id or not user_id:
        await sio.emit("error", {"message": "Missing stream_id or user_id"}, room=sid)
        return

    try:
        realtime_cache = await _get_realtime_cache_service()

        # Remove viewer from Redis sorted set
        viewer_count = await realtime_cache.remove_viewer(stream_id, user_id)

        logger.info(f"Viewer {user_id} left stream {stream_id}. Count: {viewer_count}")

        # Leave the stream room
        await sio.leave_room(sid, f"stream:{stream_id}")

        # Broadcast updated count to remaining viewers
        await sio.emit(
            "viewer_count_updated",
            {
                "stream_id": stream_id,
                "count": viewer_count,
                "action": "left",
            },
            room=f"stream:{stream_id}",
        )

    except Exception as e:
        logger.error(f"Error handling viewer leave: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to leave stream", "error": str(e)},
            room=sid,
        )


@sio.event
async def get_viewer_count(sid, data: dict):
    """Get current viewer count for a stream.

    Data:
        stream_id: UUID of the live stream

    Emits:
        - viewer_count: Current count
    """
    stream_id = data.get("stream_id")

    if not stream_id:
        await sio.emit("error", {"message": "Missing stream_id"}, room=sid)
        return

    try:
        realtime_cache = await _get_realtime_cache_service()
        count = await realtime_cache.get_viewer_count(stream_id)

        await sio.emit(
            "viewer_count",
            {"stream_id": stream_id, "count": count},
            room=sid,
        )

    except Exception as e:
        logger.error(f"Error getting viewer count: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to get viewer count", "error": str(e)},
            room=sid,
        )


# ========== Typing Indicators ==========


@sio.event
async def typing_start(sid, data: dict):
    """Handle user starting to type in a conversation.

    Sets typing indicator with 3-second TTL and broadcasts to conversation.

    Data:
        conversation_id: UUID of the conversation
        user_id: UUID of the typing user

    Emits:
        - typing_status: Broadcast to other users in conversation
    """
    conversation_id = data.get("conversation_id")
    user_id = data.get("user_id")

    if not conversation_id or not user_id:
        await sio.emit("error", {"message": "Missing conversation_id or user_id"}, room=sid)
        return

    try:
        realtime_cache = await _get_realtime_cache_service()

        # Set typing indicator (3s TTL)
        await realtime_cache.set_typing(conversation_id, user_id)

        # Broadcast to conversation room (except sender)
        await sio.emit(
            "typing_status",
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "is_typing": True,
            },
            room=f"conversation:{conversation_id}",
            skip_sid=sid,  # Don't send back to sender
        )

        logger.debug(f"User {user_id} started typing in conversation {conversation_id}")

    except Exception as e:
        logger.error(f"Error setting typing indicator: {e}", exc_info=True)


@sio.event
async def typing_stop(sid, data: dict):
    """Handle user stopping typing in a conversation.

    Clears typing indicator and broadcasts to conversation.

    Data:
        conversation_id: UUID of the conversation
        user_id: UUID of the user

    Emits:
        - typing_status: Broadcast to other users in conversation
    """
    conversation_id = data.get("conversation_id")
    user_id = data.get("user_id")

    if not conversation_id or not user_id:
        return

    try:
        realtime_cache = await _get_realtime_cache_service()

        # Clear typing indicator
        await realtime_cache.clear_typing(conversation_id, user_id)

        # Broadcast to conversation room (except sender)
        await sio.emit(
            "typing_status",
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "is_typing": False,
            },
            room=f"conversation:{conversation_id}",
            skip_sid=sid,
        )

        logger.debug(f"User {user_id} stopped typing in conversation {conversation_id}")

    except Exception as e:
        logger.error(f"Error clearing typing indicator: {e}", exc_info=True)


# ========== Presence Status ==========


@sio.event
async def presence_update(sid, data: dict):
    """Handle user presence status update.

    Updates presence in Redis with 5-minute TTL.
    Should be refreshed every 30 seconds by active clients.

    Data:
        user_id: UUID of the user
        status: "online" | "away" | "offline"

    Emits:
        - presence_changed: Broadcast to user's contacts
    """
    user_id = data.get("user_id")
    status = data.get("status", "online")

    if not user_id:
        await sio.emit("error", {"message": "Missing user_id"}, room=sid)
        return

    try:
        realtime_cache = await _get_realtime_cache_service()

        # Update presence (5min TTL)
        await realtime_cache.set_presence(user_id, status)

        # Broadcast to user's contact list room
        await sio.emit(
            "presence_changed",
            {
                "user_id": user_id,
                "status": status,
            },
            room=f"user_contacts:{user_id}",
        )

        logger.debug(f"User {user_id} presence updated to {status}")

    except Exception as e:
        logger.error(f"Error updating presence: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to update presence", "error": str(e)},
            room=sid,
        )


@sio.event
async def get_presence(sid, data: dict):
    """Get presence status for one or more users.

    Data:
        user_ids: List of user UUIDs or single user_id

    Emits:
        - presence_status: Map of user_id to status
    """
    user_ids = data.get("user_ids")
    user_id = data.get("user_id")

    if not user_ids and not user_id:
        await sio.emit("error", {"message": "Missing user_ids or user_id"}, room=sid)
        return

    try:
        realtime_cache = await _get_realtime_cache_service()

        if user_id:
            # Single user
            status = await realtime_cache.get_presence(user_id)
            await sio.emit(
                "presence_status",
                {user_id: status},
                room=sid,
            )
        else:
            # Multiple users (batch)
            statuses = await realtime_cache.get_presence_batch(user_ids)
            await sio.emit(
                "presence_status",
                statuses,
                room=sid,
            )

    except Exception as e:
        logger.error(f"Error getting presence: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to get presence", "error": str(e)},
            room=sid,
        )


# ========== Unread Message Counters ==========


@sio.event
async def new_message(sid, data: dict):
    """Handle new message event.

    Increments unread counter and broadcasts to recipient.

    Data:
        conversation_id: UUID of the conversation
        sender_id: UUID of the sender
        recipient_id: UUID of the recipient
        message_id: UUID of the new message

    Emits:
        - unread_count_updated: To recipient
        - new_message_notification: To recipient
    """
    conversation_id = data.get("conversation_id")
    sender_id = data.get("sender_id")
    recipient_id = data.get("recipient_id")
    message_id = data.get("message_id")

    if not all([conversation_id, sender_id, recipient_id, message_id]):
        await sio.emit("error", {"message": "Missing required fields"}, room=sid)
        return

    try:
        realtime_cache = await _get_realtime_cache_service()

        # Increment unread counters
        conversation_count = await realtime_cache.increment_unread_count(
            recipient_id, conversation_id
        )
        total_count = await realtime_cache.increment_unread_count(recipient_id)

        logger.info(
            f"New message in conversation {conversation_id}. "
            f"Recipient {recipient_id} unread: {total_count}"
        )

        # Send unread count update to recipient
        await sio.emit(
            "unread_count_updated",
            {
                "conversation_id": conversation_id,
                "conversation_unread": conversation_count,
                "total_unread": total_count,
            },
            room=f"user:{recipient_id}",
        )

        # Send new message notification
        await sio.emit(
            "new_message_notification",
            {
                "conversation_id": conversation_id,
                "sender_id": sender_id,
                "message_id": message_id,
            },
            room=f"user:{recipient_id}",
        )

    except Exception as e:
        logger.error(f"Error handling new message: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to process message", "error": str(e)},
            room=sid,
        )


@sio.event
async def messages_read(sid, data: dict):
    """Handle messages read event.

    Resets unread counter for a conversation.

    Data:
        conversation_id: UUID of the conversation
        user_id: UUID of the user reading messages

    Emits:
        - unread_count_updated: To user
    """
    conversation_id = data.get("conversation_id")
    user_id = data.get("user_id")

    if not conversation_id or not user_id:
        await sio.emit("error", {"message": "Missing conversation_id or user_id"}, room=sid)
        return

    try:
        realtime_cache = await _get_realtime_cache_service()

        # Get current conversation unread count
        old_count = await realtime_cache.get_unread_count(user_id, conversation_id)

        # Reset conversation unread count
        await realtime_cache.reset_unread_count(user_id, conversation_id)

        # Decrement total unread count by the conversation count
        if old_count > 0:
            await realtime_cache.decrement_unread_count(user_id, amount=old_count)

        # Get updated total
        total_count = await realtime_cache.get_unread_count(user_id)

        logger.info(f"User {user_id} read messages in conversation {conversation_id}")

        # Send updated count to user
        await sio.emit(
            "unread_count_updated",
            {
                "conversation_id": conversation_id,
                "conversation_unread": 0,
                "total_unread": total_count,
            },
            room=f"user:{user_id}",
        )

    except Exception as e:
        logger.error(f"Error handling messages read: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to mark messages as read", "error": str(e)},
            room=sid,
        )


@sio.event
async def get_unread_count(sid, data: dict):
    """Get unread message count for user.

    Data:
        user_id: UUID of the user
        conversation_id: Optional specific conversation UUID

    Emits:
        - unread_count: Count data
    """
    user_id = data.get("user_id")
    conversation_id = data.get("conversation_id")

    if not user_id:
        await sio.emit("error", {"message": "Missing user_id"}, room=sid)
        return

    try:
        realtime_cache = await _get_realtime_cache_service()

        if conversation_id:
            # Get specific conversation count
            count = await realtime_cache.get_unread_count(user_id, conversation_id)
            await sio.emit(
                "unread_count",
                {
                    "conversation_id": conversation_id,
                    "count": count,
                },
                room=sid,
            )
        else:
            # Get total count
            total = await realtime_cache.get_unread_count(user_id)
            await sio.emit(
                "unread_count",
                {
                    "total_unread": total,
                },
                room=sid,
            )

    except Exception as e:
        logger.error(f"Error getting unread count: {e}", exc_info=True)
        await sio.emit(
            "error",
            {"message": "Failed to get unread count", "error": str(e)},
            room=sid,
        )
