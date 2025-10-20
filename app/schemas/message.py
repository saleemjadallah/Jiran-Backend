from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.message import MessageType
from app.schemas.base import ORMBaseModel
from app.schemas.user import UserResponse


class ConversationCreate(ORMBaseModel):
    """Schema for creating a new conversation"""
    other_user_id: UUID = Field(..., description="ID of the other user in conversation")
    product_id: UUID | None = Field(None, description="Product ID if conversation is about a product")
    initial_message: str | None = Field(None, max_length=2000, description="Optional initial message to send")


class OfferMessageData(ORMBaseModel):
    offer_id: UUID = Field(...)
    status: str = Field(..., examples=["pending"])
    offered_price: Decimal = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)


class MessageCreate(ORMBaseModel):
    """Schema for creating a new message"""
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message: text, image, offer, system")
    content: str | None = Field(default=None, max_length=2000, description="Message content (required for text messages)")
    image_urls: list[str] | None = Field(default=None, description="Array of image URLs (required for image messages)")
    offer_data: OfferMessageData | None = Field(default=None, description="Offer data (required for offer messages)")


class MessageResponse(ORMBaseModel):
    id: UUID = Field(...)
    conversation_id: UUID = Field(...)
    message_type: MessageType = Field(...)
    content: str | None = Field(default=None)
    image_urls: list[str] | None = Field(default=None)
    offer_data: OfferMessageData | None = Field(default=None)
    is_read: bool = Field(default=False)
    read_at: datetime | None = Field(default=None)
    created_at: datetime = Field(...)
    sender: UserResponse


class ConversationResponse(ORMBaseModel):
    id: UUID = Field(...)
    buyer: UserResponse
    seller: UserResponse
    product_id: UUID | None = Field(default=None)
    last_message: MessageResponse | None = Field(default=None)
    last_message_at: datetime | None = Field(default=None)
    unread_count_buyer: int = Field(default=0, ge=0)
    unread_count_seller: int = Field(default=0, ge=0)
    is_archived_buyer: bool = Field(default=False)
    is_archived_seller: bool = Field(default=False)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
