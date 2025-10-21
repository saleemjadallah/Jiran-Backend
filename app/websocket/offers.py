"""
WebSocket Event Handlers for Offers

Implements real-time offer updates and scrolling offers feed.

Events:
- offer:create - Create offer from live stream
- offer:respond - Accept/decline/counter offer
- offer:subscribe - Subscribe to product offer feed
- offer:unsubscribe - Unsubscribe from product offer feed
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.database import async_session_maker
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.offer import Offer, OfferStatus
from app.models.product import Product
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
# OFFER CREATION (from live streams or Community videos)
# ============================================================================


@sio.event('offer:create')
async def offer_create(sid, data: dict):
    """
    Create offer in real-time (from live stream or video).

    Data:
        product_id: UUID
        offered_price: Decimal
        message: Optional message

    Logic:
    - Create offer
    - Emit to seller real-time
    - Show in scrolling offers feed on Community videos
    """
    if manager is None:
        await sio.emit("error", {"message": "Manager not initialized"}, room=sid)
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        await sio.emit("error", {"message": "Not authenticated"}, room=sid)
        return

    try:
        product_id = data.get("product_id")
        offered_price = data.get("offered_price")
        message = data.get("message")

        if not product_id or not offered_price:
            await sio.emit(
                "error",
                {"message": "product_id and offered_price required"},
                room=sid,
            )
            return

        # Validate product
        db = await _get_db()
        stmt = select(Product).where(Product.id == UUID(product_id))
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            await sio.emit("error", {"message": "Product not found"}, room=sid)
            return

        if not product.is_available:
            await sio.emit("error", {"message": "Product not available"}, room=sid)
            return

        # Validate price
        offered_price_decimal = Decimal(str(offered_price))

        if offered_price_decimal <= 0:
            await sio.emit("error", {"message": "Price must be > 0"}, room=sid)
            return

        if offered_price_decimal >= product.price:
            await sio.emit(
                "error",
                {"message": f"Price must be < {product.price} {product.currency}"},
                room=sid,
            )
            return

        # Get or create conversation
        stmt = select(Conversation).where(
            and_(
                Conversation.buyer_id == UUID(user_id),
                Conversation.seller_id == product.seller_id,
                Conversation.product_id == UUID(product_id),
            )
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                buyer_id=UUID(user_id),
                seller_id=product.seller_id,
                product_id=UUID(product_id),
                last_message_at=datetime.utcnow(),
            )
            db.add(conversation)
            await db.flush()

        # Create offer
        offer = Offer(
            conversation_id=conversation.id,
            product_id=UUID(product_id),
            buyer_id=UUID(user_id),
            seller_id=product.seller_id,
            offered_price=offered_price_decimal,
            original_price=product.price,
            currency=product.currency,
            status=OfferStatus.PENDING,
            message=message,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )

        db.add(offer)
        await db.flush()

        # Get buyer info for display
        stmt = select(User).where(User.id == UUID(user_id))
        result = await db.execute(stmt)
        buyer = result.scalar_one()

        # Create offer message
        offer_message = Message(
            conversation_id=conversation.id,
            sender_id=UUID(user_id),
            message_type="offer",
            content=message or f"Offered {product.currency} {offered_price_decimal}",
            offer_data={
                "offer_id": str(offer.id),
                "status": "pending",
                "offered_price": float(offered_price_decimal),
                "currency": product.currency,
            },
            is_read=False,
        )

        db.add(offer_message)

        # Update conversation
        conversation.last_message_id = offer_message.id
        conversation.last_message_at = offer_message.created_at
        conversation.unread_count_seller += 1

        await db.commit()

        # Prepare offer data for real-time display
        offer_display_data = {
            "offer_id": str(offer.id),
            "product_id": product_id,
            "buyer_id": user_id,
            "buyer_username": buyer.username,
            "buyer_avatar": buyer.avatar_url,
            "offered_price": float(offered_price_decimal),
            "currency": product.currency,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "time_ago": "now",
        }

        # Emit to seller
        seller_id = str(product.seller_id)
        await manager.send_to_user(
            seller_id,
            "offer:new",
            offer_display_data,
        )

        # Add to scrolling offers feed in Redis (for Community videos)
        # Store last 20 offers for this product
        redis = await _get_redis()
        offer_feed_key = f"offers:product:{product_id}"

        await redis.lpush(offer_feed_key, str(offer_display_data))
        await redis.ltrim(offer_feed_key, 0, 19)  # Keep only last 20
        await redis.expire(offer_feed_key, 3600)  # 1 hour TTL

        # Broadcast to anyone watching this product (e.g., in live stream)
        await sio.emit(
            "offer:feed:new",
            offer_display_data,
            room=f"product:{product_id}",
        )

        # Confirm to buyer
        await sio.emit(
            "offer:created",
            {
                "success": True,
                "offer_id": str(offer.id),
                "data": offer_display_data,
            },
            room=sid,
        )

        logger.info(f"Offer created by {user_id} for product {product_id}")

    except Exception as e:
        logger.error(f"Error creating offer: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


# ============================================================================
# OFFER RESPONSE (accept/decline/counter)
# ============================================================================


@sio.event('offer:respond')
async def offer_respond(sid, data: dict):
    """
    Respond to an offer (accept/decline/counter).

    Data:
        offer_id: UUID
        action: accept, decline, counter
        counter_price: Decimal (if action = counter)
        message: Optional message

    Logic:
    - Accept/decline/counter offer
    - Emit to buyer real-time
    - Update offer feed
    """
    if manager is None:
        await sio.emit("error", {"message": "Manager not initialized"}, room=sid)
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        await sio.emit("error", {"message": "Not authenticated"}, room=sid)
        return

    try:
        offer_id = data.get("offer_id")
        action = data.get("action")  # accept, decline, counter

        if not offer_id or not action:
            await sio.emit(
                "error",
                {"message": "offer_id and action required"},
                room=sid,
            )
            return

        # Get offer
        db = await _get_db()
        stmt = select(Offer).where(Offer.id == UUID(offer_id))
        result = await db.execute(stmt)
        offer = result.scalar_one_or_none()

        if not offer:
            await sio.emit("error", {"message": "Offer not found"}, room=sid)
            return

        # Verify seller
        if str(offer.seller_id) != user_id:
            await sio.emit("error", {"message": "Only seller can respond"}, room=sid)
            return

        # Process action
        if action == "accept":
            offer.status = OfferStatus.ACCEPTED
            offer.responded_at = datetime.utcnow()

            # Mark product as sold
            stmt = select(Product).where(Product.id == offer.product_id)
            result = await db.execute(stmt)
            product = result.scalar_one()

            product.is_available = False
            product.sold_at = datetime.utcnow()

            response_message = "Offer accepted"

        elif action == "decline":
            offer.status = OfferStatus.DECLINED
            offer.responded_at = datetime.utcnow()

            response_message = "Offer declined"

        elif action == "counter":
            counter_price = data.get("counter_price")

            if not counter_price:
                await sio.emit(
                    "error",
                    {"message": "counter_price required for counter action"},
                    room=sid,
                )
                return

            counter_price_decimal = Decimal(str(counter_price))

            if counter_price_decimal <= 0 or counter_price_decimal >= offer.original_price:
                await sio.emit(
                    "error",
                    {"message": f"Counter price must be between 0 and {offer.original_price}"},
                    room=sid,
                )
                return

            offer.status = OfferStatus.COUNTERED
            offer.counter_price = counter_price_decimal
            offer.responded_at = datetime.utcnow()
            offer.expires_at = datetime.utcnow() + timedelta(hours=24)

            response_message = f"Counter offer: {offer.currency} {counter_price_decimal}"

        else:
            await sio.emit("error", {"message": "Invalid action"}, room=sid)
            return

        await db.commit()

        # Prepare response data
        offer_update_data = {
            "offer_id": offer_id,
            "status": offer.status.value,
            "action": action,
            "counter_price": float(offer.counter_price) if offer.counter_price else None,
            "message": data.get("message", response_message),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Emit to buyer
        buyer_id = str(offer.buyer_id)
        await manager.send_to_user(
            buyer_id,
            "offer:updated",
            offer_update_data,
        )

        # Confirm to seller
        await sio.emit(
            "offer:responded",
            {
                "success": True,
                "data": offer_update_data,
            },
            room=sid,
        )

        logger.info(f"Offer {offer_id} {action}ed by {user_id}")

    except Exception as e:
        logger.error(f"Error responding to offer: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


# ============================================================================
# SCROLLING OFFERS FEED (for Community videos)
# ============================================================================


@sio.event('offer:feed:subscribe')
async def offer_feed_subscribe(sid, data: dict):
    """
    Subscribe to product offer feed.

    Data:
        product_id: UUID

    Allows user to see real-time scrolling offers on a product.
    """
    if manager is None:
        return

    product_id = data.get("product_id")
    if not product_id:
        return

    # Join product room
    await sio.enter_room(sid, f"product:{product_id}")

    # Send recent offers from Redis
    try:
        redis = await _get_redis()
        offer_feed_key = f"offers:product:{product_id}"

        recent_offers = await redis.lrange(offer_feed_key, 0, 19)

        if recent_offers:
            await sio.emit(
                "offer:feed:history",
                {
                    "product_id": product_id,
                    "offers": recent_offers,
                },
                room=sid,
            )

        logger.info(f"User subscribed to offer feed for product {product_id}")

    except Exception as e:
        logger.error(f"Error subscribing to offer feed: {e}")


@sio.event('offer:feed:unsubscribe')
async def offer_feed_unsubscribe(sid, data: dict):
    """
    Unsubscribe from product offer feed.

    Data:
        product_id: UUID
    """
    if manager is None:
        return

    product_id = data.get("product_id")
    if not product_id:
        return

    # Leave product room
    await sio.leave_room(sid, f"product:{product_id}")

    logger.info(f"User unsubscribed from offer feed for product {product_id}")
