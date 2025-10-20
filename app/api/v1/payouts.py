"""Payout endpoints for seller earnings management.

This module provides endpoints for:
- Getting payout history
- Checking available balance
- Requesting instant payouts
- Managing payout settings
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_active_user, get_db, require_seller_role
from app.models.payout import Payout, PayoutStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.schemas.base import SuccessResponse
from app.schemas.payout import PayoutBalanceResponse, PayoutRequestSchema, PayoutResponse, PayoutSettingsUpdate
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payouts", tags=["payouts"])


@router.get("", response_model=SuccessResponse[list[PayoutResponse]])
async def get_payouts(
    current_user: Annotated[User, Depends(require_seller_role)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: PayoutStatus | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    page: int = 1,
    per_page: int = 20,
) -> SuccessResponse[list[PayoutResponse]]:
    """Get seller's payout history.

    Args:
        current_user: Authenticated seller
        session: Database session
        status_filter: Filter by payout status
        start_date: Start date filter
        end_date: End date filter
        page: Page number
        per_page: Items per page

    Returns:
        List of payouts
    """
    query = select(Payout).where(Payout.seller_id == current_user.id)

    if status_filter:
        query = query.where(Payout.status == status_filter)
    if start_date:
        query = query.where(Payout.created_at >= start_date)
    if end_date:
        query = query.where(Payout.created_at <= end_date)

    # Pagination
    query = query.offset((page - 1) * per_page).limit(per_page)
    query = query.order_by(Payout.created_at.desc())

    result = await session.execute(query)
    payouts = result.scalars().all()

    return SuccessResponse(data=[PayoutResponse.model_validate(p) for p in payouts])


@router.get("/{payout_id}", response_model=SuccessResponse[PayoutResponse])
async def get_payout(
    payout_id: UUID,
    current_user: Annotated[User, Depends(require_seller_role)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[PayoutResponse]:
    """Get single payout details.

    Args:
        payout_id: Payout UUID
        current_user: Authenticated seller
        session: Database session

    Returns:
        Payout details

    Raises:
        HTTPException: If payout not found or unauthorized
    """
    payout = await session.get(Payout, payout_id)
    if not payout:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found")
    if payout.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return SuccessResponse(data=PayoutResponse.model_validate(payout))


@router.get("/balance", response_model=SuccessResponse[PayoutBalanceResponse])
async def get_balance(
    current_user: Annotated[User, Depends(require_seller_role)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[PayoutBalanceResponse]:
    """Get seller's current balance.

    Calculates:
    - Available balance (completed transactions not yet paid out)
    - Pending balance (transactions pending completion)
    - Total lifetime earnings

    Args:
        current_user: Authenticated seller
        session: Database session

    Returns:
        Balance information

    Raises:
        HTTPException: If seller hasn't set up Stripe Connect
    """
    if not current_user.stripe_connect_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe Connect account not set up",
        )

    # Get balance from Stripe
    balance = await PaymentService.get_account_balance(current_user.stripe_connect_account_id)

    # Calculate total lifetime earnings
    result = await session.execute(
        select(func.sum(Transaction.seller_payout))
        .where(Transaction.seller_id == current_user.id)
        .where(Transaction.status == TransactionStatus.COMPLETED)
    )
    total_earnings = result.scalar() or Decimal("0")

    # Get next payout date (assuming weekly schedule)
    next_payout_date = datetime.utcnow() + timedelta(days=7)

    return SuccessResponse(
        data=PayoutBalanceResponse(
            available_balance=balance["available_balance"],
            pending_balance=balance["pending_balance"],
            total_earnings=total_earnings,
            currency="AED",
            next_payout_date=next_payout_date,
            payout_schedule="weekly",
        )
    )


@router.post("/request", response_model=SuccessResponse[PayoutResponse])
async def request_payout(
    data: PayoutRequestSchema,
    current_user: Annotated[User, Depends(require_seller_role)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[PayoutResponse]:
    """Request instant payout.

    Args:
        data: Payout request (empty body)
        current_user: Authenticated seller
        session: Database session

    Returns:
        Created payout details

    Raises:
        HTTPException: If balance insufficient, account not set up, or payout creation fails
    """
    if not current_user.stripe_connect_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe Connect account not set up",
        )

    # Get available balance
    balance = await PaymentService.get_account_balance(current_user.stripe_connect_account_id)
    available_balance = balance["available_balance"]

    # Check minimum payout amount
    min_payout = Decimal("50.0")
    if available_balance < min_payout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum payout amount is AED {min_payout}",
        )

    # Calculate instant payout fee (2%)
    instant_fee = available_balance * Decimal("0.02")
    payout_amount = available_balance - instant_fee

    # Get completed transactions for this payout
    result = await session.execute(
        select(Transaction)
        .where(Transaction.seller_id == current_user.id)
        .where(Transaction.status == TransactionStatus.COMPLETED)
        .where(Transaction.stripe_transfer_id.is_not(None))  # Only transferred funds
    )
    transactions = result.scalars().all()

    # Calculate total platform fees
    total_platform_fee = sum(t.platform_fee for t in transactions)

    # Create payout via Stripe
    stripe_payout = await PaymentService.create_payout(
        seller_account_id=current_user.stripe_connect_account_id,
        amount=payout_amount,
        currency="AED",
    )

    # Create payout record
    payout = Payout(
        seller_id=current_user.id,
        amount=payout_amount,
        currency="AED",
        platform_fee_total=total_platform_fee,
        transaction_count=len(transactions),
        status=PayoutStatus.PROCESSING,
        stripe_payout_id=stripe_payout["payout_id"],
    )
    session.add(payout)
    await session.commit()
    await session.refresh(payout)

    return SuccessResponse(data=PayoutResponse.model_validate(payout))


@router.patch("/settings", response_model=SuccessResponse[dict])
async def update_payout_settings(
    data: PayoutSettingsUpdate,
    current_user: Annotated[User, Depends(require_seller_role)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SuccessResponse[dict]:
    """Update payout settings.

    Args:
        data: Payout settings update
        current_user: Authenticated seller
        session: Database session

    Returns:
        Updated settings

    Raises:
        HTTPException: If validation fails
    """
    # Validate payout schedule
    valid_schedules = ["weekly", "instant", "monthly"]
    if data.payout_schedule not in valid_schedules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid schedule. Must be one of: {', '.join(valid_schedules)}",
        )

    # TODO: Store settings in user metadata or separate settings table
    # For now, return the settings as confirmation
    settings = {
        "payout_schedule": data.payout_schedule,
        "minimum_payout_amount": data.minimum_payout_amount,
        "updated_at": datetime.utcnow().isoformat(),
    }

    return SuccessResponse(data=settings)
