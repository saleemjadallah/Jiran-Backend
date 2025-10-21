"""
WebSocket Event Handlers for Messaging

Implements real-time messaging features using Socket.IO.

Events:
- Connection/Disconnect
- Conversation join/leave
- Message send
- Typing indicators
- Read receipts
- User online/offline status
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.database import async_session_maker
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.websocket.manager import ConnectionManager
from app.websocket.server import sio

logger = logging.getLogger(__name__)


# Connection Manager instance
manager: Optional[ConnectionManager] = None


def set_manager(conn_manager: ConnectionManager):
    """Set the connection manager instance"""
    global manager
    manager = conn_manager


async def _get_db() -> AsyncSession:
    """Get database session"""
    async with async_session_maker() as session:
        return session


async def _get_redis():
    """Get Redis client"""
    return get_redis()


# ============================================================================
# CONNECTION EVENTS
# ============================================================================


@sio.event
async def connect(sid, environ):
    """
    Handle client connection.

    - Authenticate user via JWT token
    - Add user to online_users set in Redis
    - Join user's personal room (for 1-to-1 messaging)
    - Emit 'user:online' to user's contacts
    """
    if manager is None:
        logger.error("Connection manager not initialized")
        return False

    # Authenticate and connect
    success = await manager.connect(sid, environ)

    if not success:
        logger.warning(f"Connection rejected for {sid}")
        return False

    user_id = manager.get_user_from_sid(sid)

    # Emit connected event to client
    await sio.emit(
        "connected",
        {
            "success": True,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
        room=sid,
    )

    logger.info(f"User {user_id} connected successfully via {sid}")
    return True


@sio.event
async def disconnect(sid):
    """
    Handle client disconnection.

    - Remove user from online_users
    - Leave all rooms
    - Emit 'user:offline' to contacts
    """
    if manager is None:
        logger.error("Connection manager not initialized")
        return

    user_id = manager.get_user_from_sid(sid)
    await manager.disconnect(sid)

    if user_id:
        logger.info(f"User {user_id} disconnected via {sid}")


# ============================================================================
# CONVERSATION EVENTS
# ============================================================================


@sio.on('conversation:join')
async def conversation_join(sid, data: dict):
    """
    Join a conversation room.

    Data:
        conversation_id: UUID of conversation

    - Validate user has access to conversation
    - Join conversation room
    - Mark messages as read
    - Emit read receipts
    """
    if manager is None:
        await sio.emit("error", {"message": "Manager not initialized"}, room=sid)
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        await sio.emit("error", {"message": "Not authenticated"}, room=sid)
        return

    conversation_id = data.get("conversation_id")
    if not conversation_id:
        await sio.emit("error", {"message": "conversation_id required"}, room=sid)
        return

    try:
        # Validate conversation access
        db = await _get_db()
        stmt = select(Conversation).where(Conversation.id == UUID(conversation_id))
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            await sio.emit("error", {"message": "Conversation not found"}, room=sid)
            return

        # Check user has access
        if user_id not in [str(conversation.buyer_id), str(conversation.seller_id)]:
            await sio.emit("error", {"message": "Access denied"}, room=sid)
            return

        # Join room
        await manager.join_conversation(sid, conversation_id)

        # Mark messages as read
        is_buyer = user_id == str(conversation.buyer_id)
        update_stmt = (
            Message.__table__.update()
            .where(
                and_(
                    Message.conversation_id == UUID(conversation_id),
                    Message.sender_id != UUID(user_id),
                    Message.is_read == False,
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await db.execute(update_stmt)

        # Reset unread count
        if is_buyer:
            conversation.unread_count_buyer = 0
        else:
            conversation.unread_count_seller = 0

        await db.commit()

        # Emit joined confirmation
        await sio.emit(
            "conversation:joined",
            {
                "conversation_id": conversation_id,
                "success": True,
            },
            room=sid,
        )

        # Emit read receipts to other party
        other_user_id = str(conversation.seller_id if is_buyer else conversation.buyer_id)
        await manager.send_to_user(
            other_user_id,
            "messages:read",
            {
                "conversation_id": conversation_id,
                "read_by": user_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        logger.info(f"User {user_id} joined conversation {conversation_id}")

    except Exception as e:
        logger.error(f"Error joining conversation: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.on('conversation:leave')
async def conversation_leave(sid, data: dict):
    """
    Leave a conversation room.

    Data:
        conversation_id: UUID of conversation
    """
    if manager is None:
        return

    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return

    await manager.leave_conversation(sid, conversation_id)

    await sio.emit(
        "conversation:left",
        {"conversation_id": conversation_id, "success": True},
        room=sid,
    )


# ============================================================================
# MESSAGING EVENTS
# ============================================================================


@sio.on('message:send')
async def message_send(sid, data: dict):
    """
    Send a message in a conversation.

    Data:
        conversation_id: UUID
        message_type: text, image, offer
        content: Message content (for text)
        image_urls: Array (for images)
        offer_data: Object (for offers)

    - Validate message
    - Save to database
    - Emit 'message:new' to recipient
    - Update conversation last_message_at
    - Send push notification if recipient offline
    """
    if manager is None:
        await sio.emit("error", {"message": "Manager not initialized"}, room=sid)
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        await sio.emit("error", {"message": "Not authenticated"}, room=sid)
        return

    try:
        conversation_id = data.get("conversation_id")
        # Accept both 'message_type' (backend convention) and 'type' (frontend sends)
        message_type = data.get("message_type") or data.get("type", "text")
        content = data.get("content")
        image_urls = data.get("image_urls")
        offer_data = data.get("offer_data")

        if not conversation_id:
            await sio.emit("error", {"message": "conversation_id required"}, room=sid)
            return

        # Validate conversation
        db = await _get_db()
        stmt = select(Conversation).where(Conversation.id == UUID(conversation_id))
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            await sio.emit("error", {"message": "Conversation not found"}, room=sid)
            return

        # Check access
        if user_id not in [str(conversation.buyer_id), str(conversation.seller_id)]:
            await sio.emit("error", {"message": "Access denied"}, room=sid)
            return

        # Create message
        message = Message(
            conversation_id=UUID(conversation_id),
            sender_id=UUID(user_id),
            message_type=message_type,
            content=content,
            image_urls=image_urls,
            offer_data=offer_data,
            is_read=False,
        )

        db.add(message)
        await db.flush()

        # Update conversation
        conversation.last_message_id = message.id
        conversation.last_message_at = message.created_at

        # Increment unread count for recipient
        is_buyer = user_id == str(conversation.buyer_id)
        if is_buyer:
            conversation.unread_count_seller += 1
            recipient_id = str(conversation.seller_id)
        else:
            conversation.unread_count_buyer += 1
            recipient_id = str(conversation.buyer_id)

        await db.commit()

        # Emit message to conversation room
        message_data = {
            "id": str(message.id),
            "conversation_id": conversation_id,
            "sender_id": user_id,
            "message_type": message_type,
            "content": content,
            "image_urls": image_urls,
            "offer_data": offer_data,
            "created_at": message.created_at.isoformat(),
        }

        await manager.send_to_conversation(
            conversation_id,
            "message:received",
            message_data,
            skip_sid=sid,  # Don't send back to sender
        )

        # Send to recipient directly
        await manager.send_to_user(
            recipient_id,
            "message:received",
            message_data,
        )

        # Emit delivery confirmation to sender
        await sio.emit(
            "message:delivered",
            {
                "id": str(message.id),
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=sid,
        )

        # TODO: Send push notification if recipient offline
        is_online = await manager.is_user_online(recipient_id)
        if not is_online:
            # Send push notification
            logger.info(f"TODO: Send push notification to {recipient_id}")

        logger.info(f"Message sent in conversation {conversation_id} by {user_id}")

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


# ============================================================================
# TYPING INDICATORS
# ============================================================================


@sio.on('typing:start')
async def typing_start(sid, data: dict):
    """
    User started typing.

    Data:
        conversation_id: UUID

    - Emit 'typing:active' to other user
    - Set Redis key with 5-second expiry
    """
    if manager is None:
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        return

    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return

    try:
        # Store typing status in Redis (5 second TTL)
        redis = await _get_redis()
        typing_key = f"typing:{conversation_id}:{user_id}"
        await redis.set(typing_key, "1", ex=5)

        # Emit to conversation
        await manager.send_to_conversation(
            conversation_id,
            "typing:active",
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "isTyping": True,
                "timestamp": datetime.utcnow().isoformat(),
            },
            skip_sid=sid,
        )

    except Exception as e:
        logger.error(f"Error handling typing start: {e}")


@sio.on('typing:stop')
async def typing_stop(sid, data: dict):
    """
    User stopped typing.

    Data:
        conversation_id: UUID

    - Emit 'typing:inactive' to other user
    - Delete Redis key
    """
    if manager is None:
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        return

    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return

    try:
        # Remove typing status from Redis
        redis = await _get_redis()
        typing_key = f"typing:{conversation_id}:{user_id}"
        await redis.delete(typing_key)

        # Emit to conversation
        await manager.send_to_conversation(
            conversation_id,
            "typing:inactive",
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "isTyping": False,
                "timestamp": datetime.utcnow().isoformat(),
            },
            skip_sid=sid,
        )

    except Exception as e:
        logger.error(f"Error handling typing stop: {e}")


# ============================================================================
# READ RECEIPTS
# ============================================================================


@sio.on('message:read')
async def message_read(sid, data: dict):
    """
    Mark message as read.

    Data:
        message_id: UUID

    - Mark message as read in database
    - Emit 'message:read' to sender
    """
    if manager is None:
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        return

    message_id = data.get("message_id")
    if not message_id:
        return

    try:
        db = await _get_db()

        # Get message
        stmt = select(Message).where(Message.id == UUID(message_id))
        result = await db.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            await sio.emit("error", {"message": "Message not found"}, room=sid)
            return

        # Update read status
        message.is_read = True
        message.read_at = datetime.utcnow()
        await db.commit()

        # Emit to sender
        sender_id = str(message.sender_id)
        await manager.send_to_user(
            sender_id,
            "message:read",
            {
                "message_id": message_id,
                "read_by": user_id,
                "read_at": message.read_at.isoformat(),
            },
        )

        logger.info(f"Message {message_id} marked as read by {user_id}")

    except Exception as e:
        logger.error(f"Error marking message as read: {e}")


# ============================================================================
# HEARTBEAT
# ============================================================================


@sio.on('heartbeat')
async def heartbeat(sid, data: dict):
    """
    Client heartbeat ping.

    Maintains connection health status.
    """
    if manager is None:
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        return

    try:
        # Update heartbeat timestamp
        redis = await _get_redis()
        heartbeat_key = f"ws:heartbeat:{sid}"
        await redis.set(heartbeat_key, datetime.utcnow().isoformat(), ex=120)

        # Respond with pong
        await sio.emit(
            "pong",
            {"timestamp": datetime.utcnow().isoformat()},
            room=sid,
        )

    except Exception as e:
        logger.error(f"Error handling heartbeat: {e}")
