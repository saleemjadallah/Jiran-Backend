"""
WebSocket Server Setup

Configures Socket.IO server and initializes connection manager.
"""

import socketio

from app.config import settings
from app.websocket.manager import get_connection_manager

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.CORS_ALLOWED_ORIGINS,
    logger=settings.DEBUG,
    engineio_logger=settings.DEBUG,
    message_queue=settings.SOCKET_IO_MESSAGE_QUEUE,
)

# Initialize connection manager
connection_manager = get_connection_manager(sio)

# Import event handlers (this registers them with @sio.event decorators)
# This must come AFTER sio is created and BEFORE socket_app
from app.websocket import messaging, offers, streams  # noqa: E402, F401

# Set manager in modules
messaging.set_manager(connection_manager)
offers.set_manager(connection_manager)
streams.set_manager(connection_manager)

# Create ASGI app
socket_app = socketio.ASGIApp(sio)

