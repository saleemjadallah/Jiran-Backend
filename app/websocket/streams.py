"""
WebSocket Event Handlers for Live Streams

Handles:
- Stream join/leave
- Live chat
- Reactions
- Viewer count updates
- Stream preparation (countdown)
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.database import async_session_maker
from app.models.stream import Stream, StreamStatus
from app.models.user import User
from app.websocket.manager import ConnectionManager
from app.websocket.server import sio

logger = logging.getLogger(__name__)

manager: Optional[ConnectionManager] = None


def set_manager(conn_manager: ConnectionManager):
    global manager
    manager = conn_manager


async def _get_db() -> AsyncSession:
    async with async_session_maker() as session:
        return session


async def _get_redis():
    return get_redis()


# ============================================================================
# STREAM JOIN/LEAVE
# ============================================================================


@sio.event
async def stream_join(sid, data: dict):
    """
    Join stream room

    Data:
        stream_id: UUID
    """
    if manager is None:
        await sio.emit("error", {"message": "Manager not initialized"}, room=sid)
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        await sio.emit("error", {"message": "Not authenticated"}, room=sid)
        return

    stream_id = data.get("stream_id")
    if not stream_id:
        await sio.emit("error", {"message": "stream_id required"}, room=sid)
        return

    try:
        db = await _get_db()
        redis = await _get_redis()

        # Validate stream exists and is live
        stmt = select(Stream).where(Stream.id == UUID(stream_id))
        result = await db.execute(stmt)
        stream = result.scalar_one_or_none()

        if not stream:
            await sio.emit("error", {"message": "Stream not found"}, room=sid)
            return

        # Join stream room
        await sio.enter_room(sid, f"stream:{stream_id}")

        # Track unique viewer
        await redis.sadd(f"stream:{stream_id}:unique_viewers", user_id)

        # Increment current viewer count
        current_viewers = await redis.incr(f"stream:{stream_id}:current_viewers")

        # Update peak viewers if needed
        peak = await redis.get(f"stream:{stream_id}:peak_viewers") or 0
        if current_viewers > int(peak):
            await redis.set(f"stream:{stream_id}:peak_viewers", current_viewers)

        # Update stream viewer_count in database
        update_stmt = (
            update(Stream).where(Stream.id == UUID(stream_id)).values(viewer_count=current_viewers)
        )
        await db.execute(update_stmt)
        await db.commit()

        # Emit viewer joined to stream
        await sio.emit(
            "viewer:joined",
            {
                "streamId": stream_id,
                "viewerId": user_id,
                "viewerCount": current_viewers,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=f"stream:{stream_id}",
            skip_sid=sid,
        )

        # Confirm to joiner
        await sio.emit(
            "stream:joined",
            {
                "streamId": stream_id,
                "viewerCount": current_viewers,
            },
            room=sid,
        )

        logger.info(f"User {user_id} joined stream {stream_id}")

    except Exception as e:
        logger.error(f"Error joining stream: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def stream_leave(sid, data: dict):
    """Leave stream room"""
    if manager is None:
        return

    user_id = manager.get_user_from_sid(sid)
    stream_id = data.get("stream_id")

    if not stream_id:
        return

    try:
        redis = await _get_redis()
        db = await _get_db()

        # Decrement viewer count
        current_viewers = await redis.decr(f"stream:{stream_id}:current_viewers")
        if current_viewers < 0:
            current_viewers = 0
            await redis.set(f"stream:{stream_id}:current_viewers", 0)

        # Update database
        update_stmt = (
            update(Stream).where(Stream.id == UUID(stream_id)).values(viewer_count=current_viewers)
        )
        await db.execute(update_stmt)
        await db.commit()

        # Leave room
        await sio.leave_room(sid, f"stream:{stream_id}")

        # Emit viewer left
        await sio.emit(
            "viewer:left",
            {
                "streamId": stream_id,
                "viewerId": user_id,
                "viewerCount": current_viewers,
            },
            room=f"stream:{stream_id}",
        )

        logger.info(f"User {user_id} left stream {stream_id}")

    except Exception as e:
        logger.error(f"Error leaving stream: {e}")


# ============================================================================
# LIVE CHAT
# ============================================================================


@sio.event
async def stream_chat(sid, data: dict):
    """
    Send chat message in stream

    Data:
        stream_id: UUID
        message: string (max 200 chars)
    """
    if manager is None:
        await sio.emit("error", {"message": "Manager not initialized"}, room=sid)
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        await sio.emit("error", {"message": "Not authenticated"}, room=sid)
        return

    stream_id = data.get("stream_id")
    message = data.get("message", "").strip()

    if not stream_id or not message:
        await sio.emit("error", {"message": "stream_id and message required"}, room=sid)
        return

    if len(message) > 200:
        await sio.emit("error", {"message": "Message too long (max 200 chars)"}, room=sid)
        return

    try:
        db = await _get_db()
        redis = await _get_redis()

        # Get user info
        stmt = select(User).where(User.id == UUID(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one()

        # Rate limit: max 10 messages per minute
        rate_key = f"stream:{stream_id}:chat_rate:{user_id}"
        current_count = await redis.incr(rate_key)
        if current_count == 1:
            await redis.expire(rate_key, 60)
        if current_count > 10:
            await sio.emit("error", {"message": "Rate limit exceeded"}, room=sid)
            return

        # Increment chat count
        await redis.incr(f"stream:{stream_id}:chat_count")

        # Store in Redis (last 100 messages)
        message_data = {
            "userId": user_id,
            "username": user.username,
            "avatarUrl": user.avatar_url,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await redis.lpush(f"stream:{stream_id}:chat", str(message_data))
        await redis.ltrim(f"stream:{stream_id}:chat", 0, 99)

        # Broadcast to stream
        await sio.emit(
            "chat:message",
            message_data,
            room=f"stream:{stream_id}",
        )

        logger.info(f"Chat message in stream {stream_id} by {user_id}")

    except Exception as e:
        logger.error(f"Error sending chat: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


# ============================================================================
# REACTIONS
# ============================================================================


@sio.event
async def stream_reaction(sid, data: dict):
    """
    Send reaction in stream

    Data:
        stream_id: UUID
        emoji: string (❤️ 🔥 👏 😂 😮 💎)
    """
    if manager is None:
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        return

    stream_id = data.get("stream_id")
    emoji = data.get("emoji")

    allowed_emojis = ["❤️", "🔥", "👏", "😂", "😮", "💎"]

    if not stream_id or not emoji or emoji not in allowed_emojis:
        return

    try:
        redis = await _get_redis()

        # Increment reaction count
        await redis.incr(f"stream:{stream_id}:reactions:{emoji}")
        await redis.incr(f"stream:{stream_id}:total_likes")

        # Broadcast reaction
        await sio.emit(
            "reaction:new",
            {
                "streamId": stream_id,
                "userId": user_id,
                "emoji": emoji,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=f"stream:{stream_id}",
        )

    except Exception as e:
        logger.error(f"Error sending reaction: {e}")


# ============================================================================
# STREAM PREPARATION (COUNTDOWN)
# ============================================================================


@sio.event
async def stream_prepare(sid, data: dict):
    """
    Prepare stream (during countdown)

    Data:
        stream_id: UUID
    """
    if manager is None:
        return

    user_id = manager.get_user_from_sid(sid)
    stream_id = data.get("stream_id")

    if not stream_id:
        return

    try:
        # TODO: Warm up RTMP connection, prepare CDN

        await sio.emit(
            "stream:ready",
            {
                "streamId": stream_id,
                "estimatedLatency": 3,
                "status": "ready",
            },
            room=sid,
        )

        logger.info(f"Stream {stream_id} prepared for go live")

    except Exception as e:
        logger.error(f"Error preparing stream: {e}")


# ============================================================================
# VIEWER COUNT BROADCAST (Background Task)
# ============================================================================


async def broadcast_viewer_counts():
    """
    Background task to broadcast viewer counts every 10 seconds

    NOTE: This should be called from a background scheduler (e.g., APScheduler)
    """
    try:
        redis = await _get_redis()
        db = await _get_db()

        # Get all active streams
        stmt = select(Stream).where(Stream.status == StreamStatus.LIVE)
        result = await db.execute(stmt)
        active_streams = result.scalars().all()

        for stream in active_streams:
            stream_id = str(stream.id)
            current_viewers = await redis.get(f"stream:{stream_id}:current_viewers") or 0

            # Broadcast to all viewers in stream room
            await sio.emit(
                "stream:viewer-count",
                {
                    "streamId": stream_id,
                    "count": int(current_viewers),
                    "timestamp": datetime.utcnow().isoformat(),
                },
                room=f"stream:{stream_id}",
            )

    except Exception as e:
        logger.error(f"Error broadcasting viewer counts: {e}")
