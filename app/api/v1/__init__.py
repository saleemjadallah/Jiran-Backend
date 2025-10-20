from fastapi import APIRouter

from app.api.v1 import (
    activities,
    auth,
    categories,
    feeds,
    health,
    media,
    messages,
    moderation,
    notifications,
    offers,
    payouts,
    products,
    reviews,
    search,
    social,
    streams,
    transactions,
    verification,
    webhooks,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(feeds.router)
api_router.include_router(categories.router)
api_router.include_router(search.router)
api_router.include_router(messages.router)
api_router.include_router(offers.router)
api_router.include_router(media.router)
api_router.include_router(streams.router)
api_router.include_router(transactions.router)
api_router.include_router(payouts.router)
api_router.include_router(verification.router)
api_router.include_router(reviews.router)
api_router.include_router(moderation.router)
api_router.include_router(webhooks.router)
# Phase 7: Social Features
api_router.include_router(social.router)
api_router.include_router(notifications.router)
api_router.include_router(activities.router)

__all__ = ["api_router"]
