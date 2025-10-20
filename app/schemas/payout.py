from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.payout import PayoutStatus
from app.schemas.base import ORMBaseModel


class PayoutResponse(ORMBaseModel):
    """Payout response schema."""

    id: UUID = Field(..., description="Payout ID")
    seller_id: UUID = Field(..., description="Seller user ID")
    amount: Decimal = Field(..., description="Payout amount")
    currency: str = Field(..., description="Currency code")
    platform_fee_total: Decimal = Field(..., description="Total platform fees from transactions")
    transaction_count: int = Field(..., description="Number of transactions in payout")
    status: PayoutStatus = Field(..., description="Payout status")
    stripe_payout_id: str | None = Field(None, description="Stripe payout ID")
    bank_account_last4: str | None = Field(None, description="Last 4 digits of bank account")
    failure_reason: str | None = Field(None, description="Reason if payout failed")
    paid_at: datetime | None = Field(None, description="When payout was completed")
    created_at: datetime = Field(..., description="When payout was created")
    updated_at: datetime = Field(..., description="When payout was last updated")


class PayoutBalanceResponse(ORMBaseModel):
    """Seller balance response."""

    available_balance: Decimal = Field(..., description="Available for payout")
    pending_balance: Decimal = Field(..., description="Pending settlement")
    total_earnings: Decimal = Field(..., description="Total lifetime earnings")
    currency: str = Field(default="AED", description="Currency code")
    next_payout_date: datetime | None = Field(None, description="Next scheduled payout date")
    payout_schedule: str = Field(..., description="Payout schedule (weekly, instant, monthly)")


class PayoutRequestSchema(ORMBaseModel):
    """Request instant payout."""

    pass  # No body needed for instant payout request


class PayoutSettingsUpdate(ORMBaseModel):
    """Update payout settings."""

    payout_schedule: str = Field(..., description="Schedule: weekly, instant, or monthly")
    minimum_payout_amount: Decimal = Field(..., ge=50, description="Minimum amount for auto-payout (AED)")
