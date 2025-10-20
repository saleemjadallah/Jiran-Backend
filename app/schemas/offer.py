from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.offer import OfferStatus
from app.schemas.base import ORMBaseModel


class OfferCreate(ORMBaseModel):
    product_id: UUID = Field(...)
    offered_price: Decimal = Field(..., gt=0)
    message: str | None = Field(default=None, max_length=500)


class OfferUpdate(ORMBaseModel):
    status: OfferStatus = Field(...)
    counter_price: Decimal | None = Field(default=None, gt=0)
    message: str | None = Field(default=None, max_length=500)


class OfferResponse(ORMBaseModel):
    id: UUID = Field(...)
    conversation_id: UUID = Field(...)
    product_id: UUID = Field(...)
    buyer_id: UUID = Field(...)
    seller_id: UUID = Field(...)
    offered_price: Decimal = Field(...)
    original_price: Decimal = Field(...)
    counter_price: Decimal | None = Field(default=None)
    currency: str = Field(...)
    status: OfferStatus = Field(...)
    message: str | None = Field(default=None)
    expires_at: datetime = Field(...)
    responded_at: datetime | None = Field(default=None)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)

