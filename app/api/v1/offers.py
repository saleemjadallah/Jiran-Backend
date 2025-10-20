"""
Offers & Negotiation System API Endpoints

Implements offer submission and negotiation with real-time updates.

Endpoints:
    - POST /api/v1/offers - Create offer
    - PATCH /api/v1/offers/{id}/accept - Accept offer
    - PATCH /api/v1/offers/{id}/decline - Decline offer
    - PATCH /api/v1/offers/{id}/counter - Counter offer
    - GET /api/v1/offers - List offers
    - GET /api/v1/products/{id}/offers - Product offers
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_active_user, get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.offer import Offer, OfferStatus
from app.models.product import Product
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.offer import OfferCreate, OfferResponse, OfferUpdate

router = APIRouter(prefix="/offers", tags=["offers"])


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create offer",
)
async def create_offer(
    offer_data: OfferCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new offer on a product.

    Body:
    - product_id: Product UUID
    - offered_price: Decimal (must be > 0 and < original_price)
    - message: Optional message to seller

    Logic:
    - Validate product exists and is available
    - Validate offered_price > 0 and < original_price
    - Create offer in database with status 'pending'
    - Set expires_at to 24 hours from now
    - Create message in conversation with offer details
    - Emit WebSocket event 'offer:new' to seller
    - Send push notification to seller
    - Return created offer
    """
    # Validate product exists
    stmt = select(Product).where(Product.id == offer_data.product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Validate product is available
    if not product.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is no longer available",
        )

    # Validate price
    if offer_data.offered_price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer price must be greater than 0",
        )

    if offer_data.offered_price >= product.price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Offer price must be less than asking price ({product.price} {product.currency})",
        )

    # Check if conversation exists, if not create it
    stmt = select(Conversation).where(
        and_(
            Conversation.buyer_id == current_user.id,
            Conversation.seller_id == product.seller_id,
            Conversation.product_id == product.id,
        )
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        # Create conversation
        conversation = Conversation(
            buyer_id=current_user.id,
            seller_id=product.seller_id,
            product_id=product.id,
            last_message_at=datetime.now(timezone.utc),
        )
        db.add(conversation)
        await db.flush()

    # Create offer
    offer = Offer(
        conversation_id=conversation.id,
        product_id=product.id,
        buyer_id=current_user.id,
        seller_id=product.seller_id,
        offered_price=offer_data.offered_price,
        original_price=product.price,
        currency=product.currency,
        status=OfferStatus.PENDING,
        message=offer_data.message,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    db.add(offer)
    await db.flush()

    # Create message in conversation with offer details
    offer_message_data = {
        "offer_id": str(offer.id),
        "status": "pending",
        "offered_price": float(offer_data.offered_price),
        "currency": product.currency,
    }

    message = Message(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        message_type="offer",
        content=offer_data.message or f"Offered {product.currency} {offer_data.offered_price}",
        offer_data=offer_message_data,
        is_read=False,
    )

    db.add(message)
    await db.flush()

    # Update conversation
    conversation.last_message_id = message.id
    conversation.last_message_at = message.created_at
    conversation.unread_count_seller += 1

    await db.commit()
    await db.refresh(offer)

    # Load relationships
    stmt = (
        select(Offer)
        .where(Offer.id == offer.id)
        .options(
            selectinload(Offer.buyer),
            selectinload(Offer.seller),
            selectinload(Offer.product),
        )
    )
    result = await db.execute(stmt)
    offer = result.scalar_one()

    # TODO: Emit WebSocket event to seller
    # TODO: Send push notification to seller

    return {
        "success": True,
        "message": "Offer created successfully",
        "data": OfferResponse.model_validate(offer),
    }


@router.patch(
    "/{offer_id}/accept",
    response_model=dict,
    summary="Accept offer",
)
async def accept_offer(
    offer_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept an offer (seller only).

    Logic:
    - Validate offer not expired
    - Set status = 'accepted'
    - Mark product as sold
    - Create transaction record
    - Emit 'offer:updated' event
    - Notify buyer
    - Initiate payment flow
    """
    # Get offer
    stmt = (
        select(Offer)
        .where(Offer.id == offer_id)
        .options(
            selectinload(Offer.buyer),
            selectinload(Offer.seller),
            selectinload(Offer.product),
            selectinload(Offer.conversation),
        )
    )
    result = await db.execute(stmt)
    offer = result.scalar_one_or_none()

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found",
        )

    # Verify seller
    if offer.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can accept this offer",
        )

    # Check if expired
    if offer.expires_at < datetime.now(timezone.utc):
        offer.status = OfferStatus.EXPIRED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer has expired",
        )

    # Check status
    if offer.status != OfferStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot accept offer with status: {offer.status}",
        )

    # Accept offer
    offer.status = OfferStatus.ACCEPTED
    offer.responded_at = datetime.now(timezone.utc)

    # Mark product as sold
    product = offer.product
    product.is_available = False
    product.sold_at = datetime.now(timezone.utc)

    # Create transaction record
    # Calculate platform fee (same as products API)
    platform_fee_rate = 0.15 if product.feed_type == "discover" else 0.05
    platform_fee = max(offer.offered_price * Decimal(str(platform_fee_rate)), Decimal("5.0") if product.feed_type == "discover" else Decimal("2.0"))
    seller_payout = offer.offered_price - platform_fee

    transaction = Transaction(
        buyer_id=offer.buyer_id,
        seller_id=offer.seller_id,
        product_id=offer.product_id,
        amount=offer.offered_price,
        currency=offer.currency,
        platform_fee=platform_fee,
        seller_payout=seller_payout,
        feed_type=product.feed_type,
        status="pending",
    )

    db.add(transaction)

    # Add system message to conversation
    system_message = Message(
        conversation_id=offer.conversation_id,
        sender_id=current_user.id,
        message_type="system",
        content=f"Offer of {offer.currency} {offer.offered_price} accepted. Payment pending.",
        is_read=False,
    )

    db.add(system_message)

    await db.commit()
    await db.refresh(offer)

    # TODO: Emit WebSocket 'offer:updated' event
    # TODO: Notify buyer
    # TODO: Initiate Stripe payment flow

    return {
        "success": True,
        "message": "Offer accepted successfully",
        "data": {
            "offer": OfferResponse.model_validate(offer),
            "transaction_id": str(transaction.id),
            "payment_required": True,
        },
    }


@router.patch(
    "/{offer_id}/decline",
    response_model=dict,
    summary="Decline offer",
)
async def decline_offer(
    offer_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Decline an offer (seller only).

    Logic:
    - Set status = 'declined'
    - Add message to conversation
    - Emit 'offer:updated' event
    - Notify buyer
    """
    # Get offer
    stmt = (
        select(Offer)
        .where(Offer.id == offer_id)
        .options(
            selectinload(Offer.buyer),
            selectinload(Offer.seller),
            selectinload(Offer.product),
            selectinload(Offer.conversation),
        )
    )
    result = await db.execute(stmt)
    offer = result.scalar_one_or_none()

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found",
        )

    # Verify seller
    if offer.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can decline this offer",
        )

    # Check status
    if offer.status not in [OfferStatus.PENDING, OfferStatus.COUNTERED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot decline offer with status: {offer.status}",
        )

    # Decline offer
    offer.status = OfferStatus.DECLINED
    offer.responded_at = datetime.now(timezone.utc)

    # Add system message to conversation
    system_message = Message(
        conversation_id=offer.conversation_id,
        sender_id=current_user.id,
        message_type="system",
        content=f"Offer of {offer.currency} {offer.offered_price} declined.",
        is_read=False,
    )

    db.add(system_message)

    await db.commit()
    await db.refresh(offer)

    # TODO: Emit WebSocket 'offer:updated' event
    # TODO: Notify buyer

    return {
        "success": True,
        "message": "Offer declined",
        "data": OfferResponse.model_validate(offer),
    }


@router.patch(
    "/{offer_id}/counter",
    response_model=dict,
    summary="Counter offer",
)
async def counter_offer(
    offer_id: UUID,
    offer_update: OfferUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Counter an offer with a new price (seller only).

    Body:
    - counter_price: Decimal
    - message: Optional message

    Logic:
    - Validate counter price
    - Set status = 'countered'
    - Store counter_price
    - Emit 'offer:updated' event
    - Notify buyer
    - Reset expiry to 24 hours
    """
    # Get offer
    stmt = (
        select(Offer)
        .where(Offer.id == offer_id)
        .options(
            selectinload(Offer.buyer),
            selectinload(Offer.seller),
            selectinload(Offer.product),
            selectinload(Offer.conversation),
        )
    )
    result = await db.execute(stmt)
    offer = result.scalar_one_or_none()

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offer not found",
        )

    # Verify seller
    if offer.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the seller can counter this offer",
        )

    # Check status
    if offer.status != OfferStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot counter offer with status: {offer.status}",
        )

    # Validate counter price
    if not offer_update.counter_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="counter_price is required",
        )

    if offer_update.counter_price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Counter price must be greater than 0",
        )

    if offer_update.counter_price >= offer.original_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Counter price must be less than asking price ({offer.original_price} {offer.currency})",
        )

    # Update offer
    offer.status = OfferStatus.COUNTERED
    offer.counter_price = offer_update.counter_price
    offer.responded_at = datetime.now(timezone.utc)
    offer.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # Reset expiry

    if offer_update.message:
        offer.message = offer_update.message

    # Add message to conversation
    counter_message = Message(
        conversation_id=offer.conversation_id,
        sender_id=current_user.id,
        message_type="offer",
        content=offer_update.message or f"Counter offer: {offer.currency} {offer_update.counter_price}",
        offer_data={
            "offer_id": str(offer.id),
            "status": "countered",
            "offered_price": float(offer.offered_price),
            "counter_price": float(offer_update.counter_price),
            "currency": offer.currency,
        },
        is_read=False,
    )

    db.add(counter_message)

    # Update conversation
    offer.conversation.last_message_id = counter_message.id
    offer.conversation.last_message_at = counter_message.created_at
    offer.conversation.unread_count_buyer += 1

    await db.commit()
    await db.refresh(offer)

    # TODO: Emit WebSocket 'offer:updated' event
    # TODO: Notify buyer

    return {
        "success": True,
        "message": "Counter offer sent",
        "data": OfferResponse.model_validate(offer),
    }


@router.get(
    "",
    response_model=dict,
    summary="List offers",
)
async def list_offers(
    status: Optional[OfferStatus] = Query(None),
    as_buyer: bool = Query(False),
    as_seller: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all offers for current user.

    Query params:
    - status: pending, accepted, declined, expired, countered
    - as_buyer: Filter offers where user is buyer
    - as_seller: Filter offers where user is seller
    - page, per_page: Pagination

    Logic:
    - Get all offers for current user
    - Include product details
    - Include other party (buyer/seller) info
    - Sort by created_at DESC
    """
    # Build query
    conditions = []

    if as_buyer:
        conditions.append(Offer.buyer_id == current_user.id)
    if as_seller:
        conditions.append(Offer.seller_id == current_user.id)

    # If neither specified, show both
    if not as_buyer and not as_seller:
        conditions.append(
            or_(
                Offer.buyer_id == current_user.id,
                Offer.seller_id == current_user.id,
            )
        )

    stmt = (
        select(Offer)
        .where(and_(*conditions))
        .options(
            selectinload(Offer.buyer),
            selectinload(Offer.seller),
            selectinload(Offer.product),
            selectinload(Offer.conversation),
        )
    )

    # Filter by status
    if status:
        stmt = stmt.where(Offer.status == status)

    # Sort by created_at DESC
    stmt = stmt.order_by(desc(Offer.created_at))

    # Count total
    count_stmt = select(Offer.id).select_from(stmt.subquery())
    result = await db.execute(count_stmt)
    total = len(result.all())

    # Pagination
    offset = (page - 1) * per_page
    stmt = stmt.limit(per_page).offset(offset)

    result = await db.execute(stmt)
    offers = result.scalars().all()

    return {
        "success": True,
        "data": {
            "items": [OfferResponse.model_validate(offer) for offer in offers],
            "page": page,
            "per_page": per_page,
            "total": total,
            "has_more": (page * per_page) < total,
        },
    }


@router.get(
    "/products/{product_id}/offers",
    response_model=dict,
    summary="Get product offers",
)
async def get_product_offers(
    product_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all offers for a specific product (seller only).

    Logic:
    - Validate product exists
    - Verify current user is product owner
    - Return all offers with buyer info
    - Show offer history (counters, etc.)
    - Sort by created_at DESC
    """
    # Validate product
    stmt = select(Product).where(Product.id == product_id)
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Verify ownership
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the product owner can view offers",
        )

    # Get offers
    stmt = (
        select(Offer)
        .where(Offer.product_id == product_id)
        .options(
            selectinload(Offer.buyer),
            selectinload(Offer.seller),
            selectinload(Offer.product),
        )
        .order_by(desc(Offer.created_at))
    )

    result = await db.execute(stmt)
    offers = result.scalars().all()

    return {
        "success": True,
        "data": {
            "product_id": str(product_id),
            "product_title": product.title,
            "asking_price": float(product.price),
            "currency": product.currency,
            "offers": [OfferResponse.model_validate(offer) for offer in offers],
            "total_offers": len(offers),
        },
    }
