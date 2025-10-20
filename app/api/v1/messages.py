"""
Messaging System API Endpoints

Implements real-time messaging and conversations for Souk Loop.

Endpoints:
    - POST /api/v1/conversations - Create conversation
    - GET /api/v1/conversations - List conversations
    - GET /api/v1/conversations/{id} - Get conversation details
    - POST /api/v1/conversations/{id}/messages - Send message
    - GET /api/v1/conversations/{id}/messages - Get messages
    - PATCH /api/v1/conversations/{id}/read - Mark as read
    - DELETE /api/v1/conversations/{id} - Archive conversation
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_active_user, get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.product import Product
from app.models.user import User
from app.schemas.message import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)

router = APIRouter(prefix="/conversations", tags=["messages"])


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create conversation",
)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new conversation between two users.

    Logic:
    - Check if conversation already exists between users for this product
    - If exists, return existing conversation
    - If not, create new conversation
    - Send initial message if provided
    - Return conversation with messages
    """
    other_user_id = conversation_data.other_user_id
    product_id = conversation_data.product_id
    initial_message = conversation_data.initial_message

    # Validate other user exists
    stmt = select(User).where(User.id == other_user_id)
    result = await db.execute(stmt)
    other_user = result.scalar_one_or_none()

    if not other_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # If product_id provided, validate it exists
    product = None
    if product_id:
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

    # Determine buyer and seller roles
    if product:
        # If product exists, current user is buyer, product seller is seller
        buyer_id = current_user.id
        seller_id = product.seller_id
    else:
        # No product, just general conversation
        # Assign arbitrarily based on who initiated
        buyer_id = current_user.id
        seller_id = other_user_id

    # Check if conversation already exists
    stmt = (
        select(Conversation)
        .where(
            and_(
                Conversation.buyer_id == buyer_id,
                Conversation.seller_id == seller_id,
                or_(
                    Conversation.product_id == product_id,
                    Conversation.product_id.is_(None),
                ) if product_id else Conversation.product_id.is_(None),
            )
        )
        .options(
            selectinload(Conversation.buyer),
            selectinload(Conversation.seller),
            selectinload(Conversation.product),
        )
    )
    result = await db.execute(stmt)
    existing_conversation = result.scalar_one_or_none()

    if existing_conversation:
        # Return existing conversation
        return {
            "success": True,
            "message": "Conversation already exists",
            "data": ConversationResponse.model_validate(existing_conversation),
        }

    # Create new conversation
    new_conversation = Conversation(
        buyer_id=buyer_id,
        seller_id=seller_id,
        product_id=product_id,
        last_message_at=datetime.utcnow(),
    )

    db.add(new_conversation)
    await db.flush()  # Get conversation ID

    # Send initial message if provided
    if initial_message:
        message = Message(
            conversation_id=new_conversation.id,
            sender_id=current_user.id,
            message_type="text",
            content=initial_message,
            is_read=False,
        )
        db.add(message)
        await db.flush()

        # Update conversation last_message_id
        new_conversation.last_message_id = message.id
        new_conversation.last_message_at = message.created_at

        # Increment unread count for recipient
        if current_user.id == buyer_id:
            new_conversation.unread_count_seller = 1
        else:
            new_conversation.unread_count_buyer = 1

    await db.commit()
    await db.refresh(new_conversation)

    # Load relationships
    stmt = (
        select(Conversation)
        .where(Conversation.id == new_conversation.id)
        .options(
            selectinload(Conversation.buyer),
            selectinload(Conversation.seller),
            selectinload(Conversation.product),
        )
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one()

    return {
        "success": True,
        "message": "Conversation created successfully",
        "data": ConversationResponse.model_validate(conversation),
    }


@router.get(
    "",
    response_model=dict,
    summary="List conversations",
)
async def list_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    filter_type: str = Query("all", regex="^(all|unread|archived)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all conversations for current user.

    Query params:
    - page: Page number (default 1)
    - per_page: Items per page (default 20, max 100)
    - filter: all, unread, archived

    Logic:
    - Get all conversations where user is buyer or seller
    - Include unread_count
    - Include last_message preview
    - Sort by last_message_at DESC
    - Support pagination
    """
    # Base query
    stmt = (
        select(Conversation)
        .where(
            or_(
                Conversation.buyer_id == current_user.id,
                Conversation.seller_id == current_user.id,
            )
        )
        .options(
            selectinload(Conversation.buyer),
            selectinload(Conversation.seller),
            selectinload(Conversation.product),
            selectinload(Conversation.last_message),
        )
    )

    # Apply filters
    if filter_type == "unread":
        stmt = stmt.where(
            or_(
                and_(
                    Conversation.buyer_id == current_user.id,
                    Conversation.unread_count_buyer > 0,
                ),
                and_(
                    Conversation.seller_id == current_user.id,
                    Conversation.unread_count_seller > 0,
                ),
            )
        )
    elif filter_type == "archived":
        stmt = stmt.where(
            or_(
                and_(
                    Conversation.buyer_id == current_user.id,
                    Conversation.is_archived_buyer == True,
                ),
                and_(
                    Conversation.seller_id == current_user.id,
                    Conversation.is_archived_seller == True,
                ),
            )
        )
    else:  # all
        # Exclude archived
        stmt = stmt.where(
            and_(
                or_(
                    Conversation.buyer_id != current_user.id,
                    Conversation.is_archived_buyer == False,
                ),
                or_(
                    Conversation.seller_id != current_user.id,
                    Conversation.is_archived_seller == False,
                ),
            )
        )

    # Sort by last_message_at DESC
    stmt = stmt.order_by(desc(Conversation.last_message_at))

    # Count total
    count_stmt = select(Conversation.id).select_from(stmt.subquery())
    result = await db.execute(count_stmt)
    total = len(result.all())

    # Pagination
    offset = (page - 1) * per_page
    stmt = stmt.limit(per_page).offset(offset)

    result = await db.execute(stmt)
    conversations = result.scalars().all()

    return {
        "success": True,
        "data": {
            "items": [
                ConversationResponse.model_validate(conv) for conv in conversations
            ],
            "page": page,
            "per_page": per_page,
            "total": total,
            "has_more": (page * per_page) < total,
        },
    }


@router.get(
    "/{conversation_id}",
    response_model=dict,
    summary="Get conversation details",
)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get single conversation details with messages.

    Logic:
    - Get conversation details
    - Include other user info
    - Include product info if applicable
    - Mark messages as read for current user
    """
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.buyer),
            selectinload(Conversation.seller),
            selectinload(Conversation.product),
        )
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Verify user has access
    if current_user.id not in [conversation.buyer_id, conversation.seller_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation",
        )

    # Mark messages as read
    is_buyer = current_user.id == conversation.buyer_id

    if is_buyer and conversation.unread_count_buyer > 0:
        # Mark unread messages as read
        update_stmt = (
            Message.__table__.update()
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.sender_id != current_user.id,
                    Message.is_read == False,
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await db.execute(update_stmt)

        # Reset unread count
        conversation.unread_count_buyer = 0

    elif not is_buyer and conversation.unread_count_seller > 0:
        # Mark unread messages as read
        update_stmt = (
            Message.__table__.update()
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.sender_id != current_user.id,
                    Message.is_read == False,
                )
            )
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await db.execute(update_stmt)

        # Reset unread count
        conversation.unread_count_seller = 0

    await db.commit()
    await db.refresh(conversation)

    return {
        "success": True,
        "data": ConversationResponse.model_validate(conversation),
    }


@router.post(
    "/{conversation_id}/messages",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Send message",
)
async def send_message(
    conversation_id: UUID,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message in a conversation.

    Body:
    - message_type: text, image, offer
    - content: Message content (for text)
    - image_urls: Array of image URLs (for image messages)
    - offer_data: Offer details (for offer messages)

    Logic:
    - Create message in database
    - Emit WebSocket event to other user (real-time delivery)
    - Update conversation.last_message_at
    - Increment unread_count for recipient
    - Send push notification to recipient if offline
    - Return created message
    """
    # Validate conversation exists
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Verify user has access
    if current_user.id not in [conversation.buyer_id, conversation.seller_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation",
        )

    # Validate message data
    if message_data.message_type == "text" and not message_data.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text messages must have content",
        )

    if message_data.message_type == "image" and not message_data.image_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image messages must have image_urls",
        )

    if message_data.message_type == "offer" and not message_data.offer_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offer messages must have offer_data",
        )

    # Create message
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        message_type=message_data.message_type,
        content=message_data.content,
        image_urls=message_data.image_urls,
        offer_data=message_data.offer_data,
        is_read=False,
    )

    db.add(message)
    await db.flush()

    # Update conversation
    conversation.last_message_id = message.id
    conversation.last_message_at = message.created_at

    # Increment unread count for recipient
    is_buyer = current_user.id == conversation.buyer_id
    if is_buyer:
        conversation.unread_count_seller += 1
    else:
        conversation.unread_count_buyer += 1

    await db.commit()
    await db.refresh(message)

    # Load sender relationship
    stmt = (
        select(Message)
        .where(Message.id == message.id)
        .options(selectinload(Message.sender))
    )
    result = await db.execute(stmt)
    message = result.scalar_one()

    # TODO: Emit WebSocket event to other user
    # TODO: Send push notification if recipient offline

    return {
        "success": True,
        "message": "Message sent successfully",
        "data": MessageResponse.model_validate(message),
    }


@router.get(
    "/{conversation_id}/messages",
    response_model=dict,
    summary="Get messages",
)
async def get_messages(
    conversation_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    before_message_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get messages for a conversation.

    Query params:
    - page: Page number
    - per_page: Messages per page (default 50, max 100)
    - before_message_id: Cursor pagination (load messages before this ID)

    Logic:
    - Get messages for conversation
    - Sort by created_at DESC (newest first)
    - Support cursor-based pagination for smooth infinite scroll
    - Return messages with sender info
    """
    # Validate conversation exists
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Verify user has access
    if current_user.id not in [conversation.buyer_id, conversation.seller_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation",
        )

    # Build query
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .options(selectinload(Message.sender))
    )

    # Cursor pagination (if before_message_id provided)
    if before_message_id:
        # Get the timestamp of the cursor message
        cursor_stmt = select(Message.created_at).where(Message.id == before_message_id)
        result = await db.execute(cursor_stmt)
        cursor_time = result.scalar_one_or_none()

        if cursor_time:
            stmt = stmt.where(Message.created_at < cursor_time)

    # Sort by created_at DESC
    stmt = stmt.order_by(desc(Message.created_at))

    # Count total
    count_stmt = (
        select(Message.id)
        .where(Message.conversation_id == conversation_id)
    )
    result = await db.execute(count_stmt)
    total = len(result.all())

    # Pagination
    offset = (page - 1) * per_page if not before_message_id else 0
    stmt = stmt.limit(per_page).offset(offset)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    return {
        "success": True,
        "data": {
            "items": [MessageResponse.model_validate(msg) for msg in messages],
            "page": page,
            "per_page": per_page,
            "total": total,
            "has_more": len(messages) == per_page,
        },
    }


@router.patch(
    "/{conversation_id}/read",
    response_model=dict,
    summary="Mark conversation as read",
)
async def mark_conversation_read(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark all messages in conversation as read.

    Logic:
    - Set is_read = true for unread messages
    - Reset unread_count to 0
    - Emit read receipt via WebSocket
    """
    # Validate conversation exists
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Verify user has access
    if current_user.id not in [conversation.buyer_id, conversation.seller_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation",
        )

    # Mark messages as read
    is_buyer = current_user.id == conversation.buyer_id

    update_stmt = (
        Message.__table__.update()
        .where(
            and_(
                Message.conversation_id == conversation_id,
                Message.sender_id != current_user.id,
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

    # TODO: Emit read receipt via WebSocket

    return {
        "success": True,
        "message": "Conversation marked as read",
    }


@router.delete(
    "/{conversation_id}",
    response_model=dict,
    summary="Archive conversation",
)
async def archive_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Archive conversation (soft delete).

    Logic:
    - Set is_archived = true for current user
    - Don't actually delete (other user may still need it)
    - Remove from user's conversation list
    """
    # Validate conversation exists
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # Verify user has access
    if current_user.id not in [conversation.buyer_id, conversation.seller_id]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this conversation",
        )

    # Archive for current user only
    is_buyer = current_user.id == conversation.buyer_id

    if is_buyer:
        conversation.is_archived_buyer = True
    else:
        conversation.is_archived_seller = True

    await db.commit()

    return {
        "success": True,
        "message": "Conversation archived successfully",
    }
