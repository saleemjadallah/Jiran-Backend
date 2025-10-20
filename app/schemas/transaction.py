from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.product import FeedType
from app.models.transaction import TransactionStatus
from app.schemas.base import ORMBaseModel


class FeeCalculation(ORMBaseModel):
    """Fee breakdown for a transaction."""

    amount: Decimal = Field(..., gt=0, description="Total transaction amount")
    currency: str = Field(default="AED", description="Currency code")
    platform_fee: Decimal = Field(..., ge=0, description="Platform fee amount")
    platform_fee_percentage: float = Field(..., ge=0, le=100, description="Platform fee percentage")
    seller_payout: Decimal = Field(..., ge=0, description="Amount seller receives")
    breakdown: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Detailed fee breakdown",
    )


class TransactionInitiate(ORMBaseModel):
    """Request to initiate a transaction."""

    product_id: UUID = Field(..., description="Product being purchased")
    payment_method_id: str | None = Field(default=None, description="Stripe payment method ID")
    offer_id: UUID | None = Field(default=None, description="Offer ID if buying via accepted offer")


class TransactionInitiateResponse(ORMBaseModel):
    """Response when initiating a transaction."""

    transaction_id: UUID = Field(..., description="Created transaction ID")
    client_secret: str = Field(..., description="Stripe client secret for payment confirmation")
    amount: Decimal = Field(..., description="Total amount to charge")
    platform_fee: Decimal = Field(..., description="Platform fee")
    seller_payout: Decimal = Field(..., description="Amount seller will receive")
    currency: str = Field(default="AED")


class TransactionConfirm(ORMBaseModel):
    """Request to confirm a completed payment."""

    pass  # No body needed, just POST to confirm endpoint


class TransactionRefundRequest(ORMBaseModel):
    """Request to refund a transaction."""

    reason: str = Field(..., min_length=1, max_length=500, description="Reason for refund")


class TransactionCreate(ORMBaseModel):
    """Internal schema for creating a transaction."""

    product_id: UUID = Field(...)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="AED", min_length=3, max_length=3)
    feed_type: FeedType = Field(...)
    payment_method: str = Field(..., examples=["card"])
    stripe_payment_intent_id: str | None = Field(default=None)
    fee_breakdown: FeeCalculation | None = None


class TransactionResponse(ORMBaseModel):
    """Full transaction response."""

    id: UUID = Field(...)
    buyer_id: UUID = Field(...)
    seller_id: UUID = Field(...)
    product_id: UUID | None = Field(default=None)
    amount: Decimal = Field(...)
    currency: str = Field(...)
    platform_fee: Decimal = Field(...)
    seller_payout: Decimal = Field(...)
    feed_type: FeedType = Field(...)
    status: TransactionStatus = Field(...)
    payment_method: str | None = Field(default=None)
    stripe_payment_intent_id: str | None = Field(default=None)
    stripe_charge_id: str | None = Field(default=None)
    stripe_transfer_id: str | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    fee_breakdown: FeeCalculation | None = Field(default=None)


class FeeCalculationRequest(ORMBaseModel):
    """Request to calculate fees for an amount."""

    amount: Decimal = Field(..., gt=0, description="Transaction amount")
    feed_type: FeedType = Field(..., description="Feed type (discover or community)")

