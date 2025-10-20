"""Transaction endpoints for payment processing.

This module provides endpoints for:
- Creating and initiating transactions
- Confirming payments
- Getting transaction history
- Processing refunds
- Fee calculations
"""
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_active_user, get_db
from app.models.offer import Offer, OfferStatus
from app.models.product import Product
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.schemas.base import SuccessResponse
from app.schemas.transaction import (
    FeeCalculation,
    FeeCalculationRequest,
    TransactionConfirm,
    TransactionInitiate,
    TransactionInitiateResponse,
    TransactionRefundRequest,
    TransactionResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=SuccessResponse[TransactionInitiateResponse])
async def create_transaction(
    data: TransactionInitiate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[TransactionInitiateResponse]:
    """Initiate a new transaction.

    Creates a payment intent and returns client secret for frontend payment confirmation.

    Args:
        data: Transaction initiation request
        current_user: Authenticated user (buyer)
        session: Database session

    Returns:
        Transaction initiate response with client_secret

    Raises:
        HTTPException: If product not found, not available, or Stripe error
    """
    # Get product
    result = await session.execute(select(Product).where(Product.id == data.product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if not product.is_available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not available")

    # Determine price (from offer or product)
    amount = product.price
    if data.offer_id:
        offer_result = await session.execute(select(Offer).where(Offer.id == data.offer_id))
        offer = offer_result.scalar_one_or_none()
        if not offer or offer.status != OfferStatus.ACCEPTED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or non-accepted offer")
        amount = offer.offered_price

    # Calculate platform fee
    platform_fee = await PaymentService.calculate_platform_fee(amount, product.feed_type)
    seller_payout = amount - platform_fee

    # Ensure buyer has Stripe customer ID
    if not current_user.stripe_customer_id:
        customer_id = await PaymentService.create_stripe_customer(current_user)
        current_user.stripe_customer_id = customer_id
        await session.commit()
    else:
        customer_id = current_user.stripe_customer_id

    # Get seller
    seller = await session.get(User, product.seller_id)
    if not seller or not seller.stripe_connect_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seller has not set up payment account",
        )

    # Create payment intent
    payment_intent = await PaymentService.create_payment_intent(
        amount=amount,
        currency="AED",
        customer_id=customer_id,
        product_id=str(product.id),
        seller_account_id=seller.stripe_connect_account_id,
        platform_fee=platform_fee,
    )

    # Create transaction record
    transaction = Transaction(
        buyer_id=current_user.id,
        seller_id=seller.id,
        product_id=product.id,
        amount=amount,
        currency="AED",
        platform_fee=platform_fee,
        seller_payout=seller_payout,
        feed_type=product.feed_type,
        status=TransactionStatus.PENDING,
        stripe_payment_intent_id=payment_intent["payment_intent_id"],
        payment_method="card",
    )
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)

    return SuccessResponse(
        data=TransactionInitiateResponse(
            transaction_id=transaction.id,
            client_secret=payment_intent["client_secret"],
            amount=amount,
            platform_fee=platform_fee,
            seller_payout=seller_payout,
            currency="AED",
        )
    )


@router.post("/{transaction_id}/confirm", response_model=SuccessResponse[TransactionResponse])
async def confirm_transaction(
    transaction_id: UUID,
    data: TransactionConfirm,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[TransactionResponse]:
    """Confirm a completed payment.

    Captures the payment, marks product as sold, and updates transaction status.

    Args:
        transaction_id: Transaction UUID
        data: Confirmation request (empty body)
        current_user: Authenticated user (buyer)
        session: Database session

    Returns:
        Updated transaction details

    Raises:
        HTTPException: If transaction not found, unauthorized, or payment capture fails
    """
    # Get transaction
    transaction = await session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if transaction.buyer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    if transaction.status != TransactionStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction already processed")

    # Capture payment
    if not transaction.stripe_payment_intent_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No payment intent found")

    payment = await PaymentService.capture_payment(transaction.stripe_payment_intent_id)

    # Update transaction
    transaction.status = TransactionStatus.COMPLETED
    transaction.stripe_charge_id = payment["charge_id"]
    transaction.completed_at = datetime.utcnow()

    # Mark product as sold
    if transaction.product_id:
        product = await session.get(Product, transaction.product_id)
        if product:
            product.is_available = False
            product.sold_at = datetime.utcnow()

    await session.commit()
    await session.refresh(transaction)

    return SuccessResponse(data=TransactionResponse.model_validate(transaction))


@router.get("", response_model=SuccessResponse[list[TransactionResponse]])
async def get_transactions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    as_buyer: bool = True,
    as_seller: bool = False,
    status_filter: TransactionStatus | None = None,
    page: int = 1,
    per_page: int = 20,
) -> SuccessResponse[list[TransactionResponse]]:
    """Get user's transactions.

    Args:
        current_user: Authenticated user
        session: Database session
        as_buyer: Include transactions as buyer
        as_seller: Include transactions as seller
        status_filter: Filter by status
        page: Page number
        per_page: Items per page

    Returns:
        List of transactions
    """
    query = select(Transaction)

    # Build filters
    filters = []
    if as_buyer:
        filters.append(Transaction.buyer_id == current_user.id)
    if as_seller:
        filters.append(Transaction.seller_id == current_user.id)

    if filters:
        from sqlalchemy import or_

        query = query.where(or_(*filters))

    if status_filter:
        query = query.where(Transaction.status == status_filter)

    # Pagination
    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(Transaction.created_at.desc())

    result = await session.execute(query)
    transactions = result.scalars().all()

    return SuccessResponse(data=[TransactionResponse.model_validate(t) for t in transactions])


@router.get("/{transaction_id}", response_model=SuccessResponse[TransactionResponse])
async def get_transaction(
    transaction_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[TransactionResponse]:
    """Get single transaction details.

    Args:
        transaction_id: Transaction UUID
        current_user: Authenticated user
        session: Database session

    Returns:
        Transaction details

    Raises:
        HTTPException: If transaction not found or unauthorized
    """
    transaction = await session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Check authorization
    if transaction.buyer_id != current_user.id and transaction.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return SuccessResponse(data=TransactionResponse.model_validate(transaction))


@router.post("/{transaction_id}/refund", response_model=SuccessResponse[TransactionResponse])
async def refund_transaction(
    transaction_id: UUID,
    data: TransactionRefundRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[TransactionResponse]:
    """Refund a transaction.

    Args:
        transaction_id: Transaction UUID
        data: Refund request with reason
        current_user: Authenticated user
        session: Database session

    Returns:
        Updated transaction

    Raises:
        HTTPException: If transaction not found, not refundable, or refund fails
    """
    transaction = await session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Check authorization (buyer or seller can request refund)
    if transaction.buyer_id != current_user.id and transaction.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if transaction.status != TransactionStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction not completed")

    # Check if within 30 days
    if transaction.completed_at:
        days_since = (datetime.utcnow() - transaction.completed_at).days
        if days_since > 30:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refund period expired")

    # Process refund
    if not transaction.stripe_payment_intent_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No payment intent found")

    await PaymentService.create_refund(transaction.stripe_payment_intent_id, reason=data.reason)

    # Update transaction
    transaction.status = TransactionStatus.REFUNDED

    # Mark product as available again
    if transaction.product_id:
        product = await session.get(Product, transaction.product_id)
        if product:
            product.is_available = True
            product.sold_at = None

    await session.commit()
    await session.refresh(transaction)

    return SuccessResponse(data=TransactionResponse.model_validate(transaction))


@router.get("/fees/calculate", response_model=SuccessResponse[FeeCalculation])
async def calculate_fees(
    amount: Decimal,
    feed_type: str,
) -> SuccessResponse[FeeCalculation]:
    """Calculate platform fees for an amount.

    Args:
        amount: Transaction amount
        feed_type: Feed type (discover or community)

    Returns:
        Fee breakdown

    Raises:
        HTTPException: If invalid feed_type
    """
    from app.models.product import FeedType

    try:
        feed_type_enum = FeedType(feed_type.lower())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid feed_type") from None

    platform_fee = await PaymentService.calculate_platform_fee(amount, feed_type_enum)
    seller_payout = amount - platform_fee

    # Calculate percentage
    fee_percentage = float((platform_fee / amount) * 100) if amount > 0 else 0

    return SuccessResponse(
        data=FeeCalculation(
            amount=amount,
            currency="AED",
            platform_fee=platform_fee,
            platform_fee_percentage=fee_percentage,
            seller_payout=seller_payout,
            breakdown={
                "subtotal": amount,
                "platform_fee": -platform_fee,
                "total": seller_payout,
            },
        )
    )
