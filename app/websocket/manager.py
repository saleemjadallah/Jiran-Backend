"""
WebSocket Connection Manager

Manages WebSocket connections, user sessions, and real-time messaging.

Features:
- User authentication via JWT
- Connection tracking in Redis
- Room management for conversations
- Broadcasting to rooms and users
- Online/offline status management
- Heartbeat/ping-pong for connection health
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID

import socketio
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.redis import get_redis
from app.database import async_session_maker

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and user sessions"""

    def __init__(self, sio: socketio.AsyncServer):
        self.sio = sio

        # In-memory connection tracking (for this process)
        # Format: {sid: user_id}
        self.connections: Dict[str, str] = {}

        # Format: {user_id: set(sid)}
        self.user_connections: Dict[str, Set[str]] = {}

        # Redis prefix for keys
        self.ONLINE_USERS_KEY = "ws:online_users"
        self.USER_SIDS_KEY_PREFIX = "ws:user:"  # ws:user:{user_id}
        self.SID_USER_KEY_PREFIX = "ws:sid:"  # ws:sid:{sid}
        self.HEARTBEAT_KEY_PREFIX = "ws:heartbeat:"  # ws:heartbeat:{sid}

    async def _get_redis(self):
        """Get Redis client"""
        return get_redis()

    async def _get_db(self) -> AsyncSession:
        """Get database session"""
        async with async_session_maker() as session:
            return session

    def _parse_jwt_token(self, token: str) -> Optional[dict]:
        """Parse and validate JWT token"""
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token[7:]

            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            return payload
        except Exception as e:
            logger.error(f"Failed to parse JWT token: {e}")
            return None

    async def authenticate_connection(
        self,
        sid: str,
        environ: dict,
    ) -> Optional[str]:
        """
        Authenticate WebSocket connection via JWT token.

        Returns user_id if authentication successful, None otherwise.
        """
        # Get token from query params or headers
        query_string = environ.get("QUERY_STRING", "")
        token = None

        # Try query params first: ?token=xxx
        if "token=" in query_string:
            for param in query_string.split("&"):
                if param.startswith("token="):
                    token = param.split("=", 1)[1]
                    break

        # Try Authorization header
        if not token:
            headers = dict(environ.get("HTTP_AUTHORIZATION", ""))
            token = headers.get("authorization")

        if not token:
            logger.warning(f"No token provided for connection {sid}")
            return None

        # Parse token
        payload = self._parse_jwt_token(token)
        if not payload:
            logger.warning(f"Invalid token for connection {sid}")
            return None

        user_id = payload.get("sub")
        if not user_id:
            logger.warning(f"No user_id in token for connection {sid}")
            return None

        return user_id

    async def connect(self, sid: str, environ: dict) -> bool:
        """
        Handle new WebSocket connection.

        Returns True if connection accepted, False otherwise.
        """
        # Authenticate user
        user_id = await self.authenticate_connection(sid, environ)

        if not user_id:
            logger.warning(f"Authentication failed for connection {sid}")
            return False

        # Store connection
        self.connections[sid] = user_id

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(sid)

        # Store in Redis
        redis = await self._get_redis()
        await redis.sadd(self.ONLINE_USERS_KEY, user_id)
        await redis.sadd(f"{self.USER_SIDS_KEY_PREFIX}{user_id}", sid)
        await redis.set(f"{self.SID_USER_KEY_PREFIX}{sid}", user_id, ex=86400)  # 24h TTL

        # Set heartbeat
        await self._update_heartbeat(sid)

        # Join user's personal room
        await self.sio.enter_room(sid, f"user:{user_id}")

        logger.info(f"User {user_id} connected via {sid}")

        # Emit user:online to user's contacts
        # TODO: Get user's contacts and emit to them

        return True

    async def disconnect(self, sid: str):
        """Handle WebSocket disconnection"""
        user_id = self.connections.get(sid)

        if not user_id:
            return

        # Remove from in-memory tracking
        if sid in self.connections:
            del self.connections[sid]

        if user_id in self.user_connections:
            self.user_connections[user_id].discard(sid)

            # If no more connections for this user, mark offline
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

                # Remove from Redis
                redis = await self._get_redis()
                await redis.srem(self.ONLINE_USERS_KEY, user_id)

                # Emit user:offline to contacts
                await self.sio.emit(
                    "user:offline",
                    {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()},
                    room=f"user:{user_id}",
                )

        # Clean up Redis
        redis = await self._get_redis()
        await redis.srem(f"{self.USER_SIDS_KEY_PREFIX}{user_id}", sid)
        await redis.delete(f"{self.SID_USER_KEY_PREFIX}{sid}")
        await redis.delete(f"{self.HEARTBEAT_KEY_PREFIX}{sid}")

        # Leave user's personal room
        await self.sio.leave_room(sid, f"user:{user_id}")

        logger.info(f"User {user_id} disconnected via {sid}")

    async def _update_heartbeat(self, sid: str):
        """Update connection heartbeat timestamp"""
        redis = await self._get_redis()
        await redis.set(
            f"{self.HEARTBEAT_KEY_PREFIX}{sid}",
            datetime.utcnow().isoformat(),
            ex=120,  # 2 minute TTL
        )

    async def join_conversation(self, sid: str, conversation_id: str):
        """Join a conversation room"""
        user_id = self.connections.get(sid)

        if not user_id:
            logger.warning(f"Cannot join conversation: no user_id for {sid}")
            return False

        # TODO: Validate user has access to this conversation

        room_name = f"conversation:{conversation_id}"
        await self.sio.enter_room(sid, room_name)

        logger.info(f"User {user_id} joined conversation {conversation_id}")
        return True

    async def leave_conversation(self, sid: str, conversation_id: str):
        """Leave a conversation room"""
        room_name = f"conversation:{conversation_id}"
        await self.sio.leave_room(sid, room_name)

        user_id = self.connections.get(sid)
        if user_id:
            logger.info(f"User {user_id} left conversation {conversation_id}")

    async def send_to_user(
        self,
        user_id: str,
        event: str,
        data: dict,
        skip_sid: Optional[str] = None,
    ):
        """
        Send event to a specific user (all their connections).

        Args:
            user_id: Target user ID
            event: Event name
            data: Event data
            skip_sid: Optional SID to skip (e.g., sender's connection)
        """
        room = f"user:{user_id}"
        await self.sio.emit(event, data, room=room, skip_sid=skip_sid)

    async def send_to_conversation(
        self,
        conversation_id: str,
        event: str,
        data: dict,
        skip_sid: Optional[str] = None,
    ):
        """
        Send event to all members of a conversation.

        Args:
            conversation_id: Conversation ID
            event: Event name
            data: Event data
            skip_sid: Optional SID to skip
        """
        room = f"conversation:{conversation_id}"
        await self.sio.emit(event, data, room=room, skip_sid=skip_sid)

    async def is_user_online(self, user_id: str) -> bool:
        """Check if a user is currently online"""
        redis = await self._get_redis()
        return await redis.sismember(self.ONLINE_USERS_KEY, user_id)

    async def get_online_users(self) -> List[str]:
        """Get list of all online user IDs"""
        redis = await self._get_redis()
        users = await redis.smembers(self.ONLINE_USERS_KEY)
        return list(users) if users else []

    async def get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        redis = await self._get_redis()
        return await redis.scard(f"{self.USER_SIDS_KEY_PREFIX}{user_id}")

    def get_user_from_sid(self, sid: str) -> Optional[str]:
        """Get user_id from session ID"""
        return self.connections.get(sid)

    async def broadcast_to_all(self, event: str, data: dict):
        """Broadcast event to all connected users"""
        await self.sio.emit(event, data)

    async def cleanup_stale_connections(self):
        """Clean up connections with expired heartbeats"""
        redis = await self._get_redis()

        # Get all heartbeat keys
        pattern = f"{self.HEARTBEAT_KEY_PREFIX}*"
        cursor = 0
        stale_sids = []

        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)

            for key in keys:
                # Check if heartbeat expired
                exists = await redis.exists(key)
                if not exists:
                    # Extract SID from key
                    sid = key.replace(self.HEARTBEAT_KEY_PREFIX, "")
                    stale_sids.append(sid)

            if cursor == 0:
                break

        # Disconnect stale connections
        for sid in stale_sids:
            await self.disconnect(sid)
            logger.warning(f"Cleaned up stale connection: {sid}")

    async def start_heartbeat_monitor(self, interval: int = 60):
        """Start background task to monitor connection health"""
        while True:
            await asyncio.sleep(interval)
            await self.cleanup_stale_connections()


# Global connection manager instance
manager: Optional[ConnectionManager] = None


def get_connection_manager(sio: socketio.AsyncServer) -> ConnectionManager:
    """Get or create connection manager instance"""
    global manager
    if manager is None:
        manager = ConnectionManager(sio)
    return manager
