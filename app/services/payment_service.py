"""Payment service for Stripe integration.

This module handles all Stripe payment operations including:
- Customer management
- Connect account creation
- Payment intents and processing
- Platform fee calculations
- Refunds and payouts
"""
from decimal import Decimal
from typing import Any

import stripe

from app.config import settings
from app.models.product import FeedType
from app.models.user import User

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentService:
    """Service class for Stripe payment operations."""

    @staticmethod
    async def create_stripe_customer(user: User) -> str:
        """Create a Stripe customer for a user.

        Args:
            user: User model instance

        Returns:
            Stripe customer ID

        Raises:
            stripe.error.StripeError: If customer creation fails
        """
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            phone=user.phone,
            metadata={
                "user_id": str(user.id),
                "username": user.username,
            },
        )
        return customer.id

    @staticmethod
    async def create_connect_account(user: User) -> dict[str, str]:
        """Create a Stripe Connect Express account for a seller.

        Args:
            user: User model instance

        Returns:
            Dictionary with account_id and onboarding_url

        Raises:
            stripe.error.StripeError: If account creation fails
        """
        account = stripe.Account.create(
            type="express",
            country="AE",  # United Arab Emirates
            email=user.email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            business_type="individual",
            metadata={
                "user_id": str(user.id),
                "username": user.username,
            },
        )

        # Generate account onboarding link
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=f"https://soukloop.com/seller/connect/refresh",
            return_url=f"https://soukloop.com/seller/connect/success",
            type="account_onboarding",
        )

        return {
            "account_id": account.id,
            "onboarding_url": account_link.url,
        }

    @staticmethod
    async def calculate_platform_fee(amount: Decimal, feed_type: FeedType) -> Decimal:
        """Calculate platform fee based on amount and feed type.

        Fee structure:
        - Discover feed: 15%, minimum AED 5.0
        - Community feed: 5%, minimum AED 2.0

        Args:
            amount: Transaction amount
            feed_type: Type of feed (discover or community)

        Returns:
            Platform fee amount
        """
        if feed_type == FeedType.DISCOVER:
            fee_percentage = Decimal("0.15")  # 15%
            min_fee = Decimal("5.0")
        else:  # COMMUNITY
            fee_percentage = Decimal("0.05")  # 5%
            min_fee = Decimal("2.0")

        calculated_fee = amount * fee_percentage
        return max(calculated_fee, min_fee)

    @staticmethod
    async def create_payment_intent(
        amount: Decimal,
        currency: str,
        customer_id: str,
        product_id: str,
        seller_account_id: str,
        platform_fee: Decimal,
    ) -> dict[str, Any]:
        """Create a Stripe PaymentIntent with platform fee.

        Args:
            amount: Total transaction amount
            currency: Currency code (e.g., "AED")
            customer_id: Stripe customer ID
            product_id: Product UUID
            seller_account_id: Seller's Stripe Connect account ID
            platform_fee: Platform fee amount

        Returns:
            Dictionary with payment intent details including client_secret

        Raises:
            stripe.error.StripeError: If payment intent creation fails
        """
        # Convert Decimal to cents (Stripe uses smallest currency unit)
        amount_cents = int(amount * 100)
        platform_fee_cents = int(platform_fee * 100)

        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency.lower(),
            customer=customer_id,
            application_fee_amount=platform_fee_cents,
            transfer_data={
                "destination": seller_account_id,
            },
            metadata={
                "product_id": product_id,
            },
            automatic_payment_methods={
                "enabled": True,
            },
        )

        return {
            "payment_intent_id": payment_intent.id,
            "client_secret": payment_intent.client_secret,
            "status": payment_intent.status,
            "amount": amount,
            "platform_fee": platform_fee,
        }

    @staticmethod
    async def capture_payment(payment_intent_id: str) -> dict[str, Any]:
        """Capture a payment intent.

        Args:
            payment_intent_id: Stripe payment intent ID

        Returns:
            Payment details

        Raises:
            stripe.error.StripeError: If capture fails
        """
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        # If payment intent requires capture (not automatic)
        if payment_intent.status == "requires_capture":
            payment_intent = stripe.PaymentIntent.capture(payment_intent_id)

        return {
            "payment_intent_id": payment_intent.id,
            "status": payment_intent.status,
            "amount": Decimal(str(payment_intent.amount / 100)),
            "currency": payment_intent.currency.upper(),
            "charge_id": payment_intent.latest_charge,
        }

    @staticmethod
    async def create_refund(payment_intent_id: str, reason: str = "requested_by_customer") -> dict[str, Any]:
        """Create a refund for a payment.

        Args:
            payment_intent_id: Stripe payment intent ID
            reason: Refund reason

        Returns:
            Refund details

        Raises:
            stripe.error.StripeError: If refund creation fails
        """
        refund = stripe.Refund.create(
            payment_intent=payment_intent_id,
            reason=reason,
            refund_application_fee=True,  # Also refund the platform fee
            reverse_transfer=True,  # Reverse the transfer to seller
        )

        return {
            "refund_id": refund.id,
            "status": refund.status,
            "amount": Decimal(str(refund.amount / 100)),
            "currency": refund.currency.upper(),
        }

    @staticmethod
    async def create_payout(seller_account_id: str, amount: Decimal, currency: str = "AED") -> dict[str, Any]:
        """Create a payout to seller's bank account.

        Args:
            seller_account_id: Seller's Stripe Connect account ID
            amount: Payout amount
            currency: Currency code

        Returns:
            Payout details

        Raises:
            stripe.error.StripeError: If payout creation fails
        """
        # Convert to cents
        amount_cents = int(amount * 100)

        # Create payout on the connected account
        payout = stripe.Payout.create(
            amount=amount_cents,
            currency=currency.lower(),
            stripe_account=seller_account_id,
        )

        return {
            "payout_id": payout.id,
            "status": payout.status,
            "amount": Decimal(str(payout.amount / 100)),
            "currency": payout.currency.upper(),
            "arrival_date": payout.arrival_date,
        }

    @staticmethod
    async def get_account_balance(seller_account_id: str) -> dict[str, Any]:
        """Get balance for a connected account.

        Args:
            seller_account_id: Seller's Stripe Connect account ID

        Returns:
            Balance information

        Raises:
            stripe.error.StripeError: If balance retrieval fails
        """
        balance = stripe.Balance.retrieve(stripe_account=seller_account_id)

        available_balance = Decimal("0")
        pending_balance = Decimal("0")

        for balance_item in balance.available:
            if balance_item.currency.upper() == "AED":
                available_balance = Decimal(str(balance_item.amount / 100))

        for balance_item in balance.pending:
            if balance_item.currency.upper() == "AED":
                pending_balance = Decimal(str(balance_item.amount / 100))

        return {
            "available_balance": available_balance,
            "pending_balance": pending_balance,
            "currency": "AED",
        }

    @staticmethod
    async def verify_webhook_signature(payload: bytes, signature: str) -> dict[str, Any]:
        """Verify Stripe webhook signature.

        Args:
            payload: Raw request body bytes
            signature: Stripe-Signature header value

        Returns:
            Verified event object

        Raises:
            stripe.error.SignatureVerificationError: If signature is invalid
        """
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

        event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )

        return event
