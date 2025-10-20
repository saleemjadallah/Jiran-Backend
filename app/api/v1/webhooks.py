"""Stripe webhook handlers.

This module handles Stripe webhook events for:
- Payment intent status updates
- Transfer status updates
- Payout status updates
- Account updates for Connect accounts
"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.payout import Payout, PayoutStatus
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.base import SuccessResponse
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    stripe_signature: Annotated[str, Header(alias="Stripe-Signature")],
) -> SuccessResponse[dict]:
    """Handle Stripe webhook events.

    Args:
        request: FastAPI request object
        session: Database session
        stripe_signature: Stripe webhook signature header

    Returns:
        Success response

    Raises:
        HTTPException: If signature verification fails
    """
    # Get raw body
    payload = await request.body()

    # Verify webhook signature
    try:
        event = await PaymentService.verify_webhook_signature(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        ) from exc

    # Handle different event types
    event_type = event["type"]
    event_data = event["data"]["object"]

    if event_type == "payment_intent.succeeded":
        await handle_payment_intent_succeeded(event_data, session)
    elif event_type == "payment_intent.payment_failed":
        await handle_payment_intent_failed(event_data, session)
    elif event_type == "transfer.created":
        await handle_transfer_created(event_data, session)
    elif event_type == "transfer.failed":
        await handle_transfer_failed(event_data, session)
    elif event_type == "payout.paid":
        await handle_payout_paid(event_data, session)
    elif event_type == "payout.failed":
        await handle_payout_failed(event_data, session)
    elif event_type == "account.updated":
        await handle_account_updated(event_data, session)

    return SuccessResponse(data={"received": True, "event_type": event_type})


async def handle_payment_intent_succeeded(data: dict, session: AsyncSession) -> None:
    """Handle successful payment intent.

    Args:
        data: Payment intent data from webhook
        session: Database session
    """
    payment_intent_id = data["id"]

    # Find transaction
    result = await session.execute(
        select(Transaction).where(Transaction.stripe_payment_intent_id == payment_intent_id)
    )
    transaction = result.scalar_one_or_none()

    if transaction and transaction.status == TransactionStatus.PENDING:
        transaction.status = TransactionStatus.COMPLETED
        transaction.stripe_charge_id = data.get("latest_charge")
        transaction.completed_at = datetime.utcnow()

        # Mark product as sold
        if transaction.product_id:
            from app.models.product import Product

            product = await session.get(Product, transaction.product_id)
            if product:
                product.is_available = False
                product.sold_at = datetime.utcnow()

        await session.commit()


async def handle_payment_intent_failed(data: dict, session: AsyncSession) -> None:
    """Handle failed payment intent.

    Args:
        data: Payment intent data from webhook
        session: Database session
    """
    payment_intent_id = data["id"]

    # Find transaction
    result = await session.execute(
        select(Transaction).where(Transaction.stripe_payment_intent_id == payment_intent_id)
    )
    transaction = result.scalar_one_or_none()

    if transaction and transaction.status == TransactionStatus.PENDING:
        transaction.status = TransactionStatus.FAILED
        await session.commit()


async def handle_transfer_created(data: dict, session: AsyncSession) -> None:
    """Handle transfer created event.

    Args:
        data: Transfer data from webhook
        session: Database session
    """
    transfer_id = data["id"]

    # Find transaction with matching payment intent
    source_transaction = data.get("source_transaction")
    if source_transaction:
        result = await session.execute(
            select(Transaction).where(Transaction.stripe_charge_id == source_transaction)
        )
        transaction = result.scalar_one_or_none()

        if transaction:
            transaction.stripe_transfer_id = transfer_id
            await session.commit()


async def handle_transfer_failed(data: dict, session: AsyncSession) -> None:
    """Handle failed transfer event.

    Args:
        data: Transfer data from webhook
        session: Database session
    """
    transfer_id = data["id"]

    # Find transaction
    result = await session.execute(select(Transaction).where(Transaction.stripe_transfer_id == transfer_id))
    transaction = result.scalar_one_or_none()

    if transaction:
        # Mark transaction as failed
        transaction.status = TransactionStatus.FAILED
        await session.commit()

        # TODO: Send notification to admin and seller


async def handle_payout_paid(data: dict, session: AsyncSession) -> None:
    """Handle successful payout event.

    Args:
        data: Payout data from webhook
        session: Database session
    """
    payout_id = data["id"]

    # Find payout record
    result = await session.execute(select(Payout).where(Payout.stripe_payout_id == payout_id))
    payout = result.scalar_one_or_none()

    if payout and payout.status in {PayoutStatus.PENDING, PayoutStatus.PROCESSING}:
        payout.status = PayoutStatus.PAID
        payout.paid_at = datetime.utcnow()
        await session.commit()

        # TODO: Send notification to seller


async def handle_payout_failed(data: dict, session: AsyncSession) -> None:
    """Handle failed payout event.

    Args:
        data: Payout data from webhook
        session: Database session
    """
    payout_id = data["id"]

    # Find payout record
    result = await session.execute(select(Payout).where(Payout.stripe_payout_id == payout_id))
    payout = result.scalar_one_or_none()

    if payout and payout.status in {PayoutStatus.PENDING, PayoutStatus.PROCESSING}:
        payout.status = PayoutStatus.FAILED
        payout.failure_reason = data.get("failure_message")
        await session.commit()

        # TODO: Send notification to seller and admin


async def handle_account_updated(data: dict, session: AsyncSession) -> None:
    """Handle Connect account update event.

    Args:
        data: Account data from webhook
        session: Database session
    """
    account_id = data["id"]

    # Find user with this Connect account
    from app.models.user import User

    result = await session.execute(select(User).where(User.stripe_connect_account_id == account_id))
    user = result.scalar_one_or_none()

    if user:
        # Update user verification status if charges_enabled changed
        charges_enabled = data.get("charges_enabled", False)
        payouts_enabled = data.get("payouts_enabled", False)

        # TODO: Update user status based on account capabilities
        # TODO: Send notification if account becomes fully onboarded

        await session.commit()
