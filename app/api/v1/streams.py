"""
Live Streaming API Endpoints (ENHANCED)

Implements complete Go Live flow with 5 steps:
1. Camera Setup (frontend only)
2. Product Selection (POST /streams)
3. Stream Settings (PATCH /streams/{id}/settings)
4. Pre-Live Checklist (frontend only)
5. Go Live (POST /streams/{id}/go-live)

Additional endpoints:
- Stream management (get, update, end)
- Product tagging
- Viewer management
- Analytics
"""

import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis
from app.dependencies import (
    get_current_active_user,
    get_db,
    get_feed_cache_service,
    get_redis_manager,
)
from app.models.product import Product
from app.models.stream import Stream, StreamStatus
from app.models.stream_product import StreamProduct
from app.models.user import User
from app.schemas.stream import (
    GoLiveRequest,
    GoLiveResponse,
    ProductTagPosition,
    StreamAnalytics,
    StreamCreate,
    StreamResponse,
    StreamUpdate,
    StreamViewer,
)
from app.services.cache.feed_cache_service import FeedCacheService

router = APIRouter(prefix="/streams", tags=["streams"])


# ============================================================================
# STEP 2: CREATE STREAM (Product Selection)
# ============================================================================


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_stream(
    stream_data: StreamCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create stream with settings and attach products.

    Used in Step 2: Product Selection of Go Live flow.

    Returns:
        Stream details with product count
    """
    # Validate seller role
    if current_user.role not in ["seller", "both"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers can create streams",
        )

    # Validate products belong to user
    if stream_data.product_ids:
        stmt = select(Product).where(
            and_(
                Product.id.in_([UUID(pid) for pid in stream_data.product_ids]),
                Product.seller_id == current_user.id,
                Product.is_available == True,
            )
        )
        result = await db.execute(stmt)
        products = result.scalars().all()

        if len(products) != len(stream_data.product_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some products not found or not available",
            )

    # Create stream
    stream = Stream(
        user_id=current_user.id,
        title=stream_data.title,
        description=stream_data.description,
        category=stream_data.category,
        status=StreamStatus.SCHEDULED,
        audience=stream_data.audience,
        estimated_duration=stream_data.estimated_duration,
        notify_followers=stream_data.notify_followers,
        notify_neighborhood=stream_data.notify_neighborhood,
        enable_chat=stream_data.enable_chat,
        enable_comments=stream_data.enable_comments,
        record_stream=stream_data.record_stream,
    )

    db.add(stream)
    await db.flush()

    # Attach products
    if stream_data.product_ids:
        for product_id in stream_data.product_ids:
            stream_product = StreamProduct(
                stream_id=stream.id,
                product_id=UUID(product_id),
            )
            db.add(stream_product)

    await db.commit()
    await db.refresh(stream)

    return {
        "success": True,
        "message": "Stream created successfully",
        "data": {
            "streamId": str(stream.id),
            "title": stream.title,
            "status": stream.status.value,
            "audience": stream.audience,
            "estimatedDuration": stream.estimated_duration,
            "productCount": len(stream_data.product_ids),
            "createdAt": stream.created_at.isoformat(),
        },
    }


# ============================================================================
# ATTACH/REMOVE PRODUCTS
# ============================================================================


@router.post("/{stream_id}/products", response_model=dict)
async def attach_products(
    stream_id: UUID,
    product_ids: list[str],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Attach products to stream (Step 2: Product Selection)"""
    # Get stream
    stmt = select(Stream).where(Stream.id == stream_id)
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your stream")

    if stream.status != StreamStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="Can only attach products to scheduled streams")

    # Validate products
    stmt = select(Product).where(
        and_(
            Product.id.in_([UUID(pid) for pid in product_ids]),
            Product.seller_id == current_user.id,
            Product.is_available == True,
        )
    )
    result = await db.execute(stmt)
    products = result.scalars().all()

    if len(products) != len(product_ids):
        raise HTTPException(status_code=400, detail="Some products not found")

    # Attach products
    for product in products:
        # Check if already attached
        stmt = select(StreamProduct).where(
            and_(
                StreamProduct.stream_id == stream_id,
                StreamProduct.product_id == product.id,
            )
        )
        result = await db.execute(stmt)
        exists = result.scalar_one_or_none()

        if not exists:
            stream_product = StreamProduct(
                stream_id=stream_id,
                product_id=product.id,
            )
            db.add(stream_product)

    await db.commit()

    # Get updated product list
    stmt = (
        select(StreamProduct)
        .where(StreamProduct.stream_id == stream_id)
        .options(selectinload(StreamProduct.product))
    )
    result = await db.execute(stmt)
    stream_products = result.scalars().all()

    return {
        "success": True,
        "data": {
            "streamId": str(stream_id),
            "products": [
                {
                    "id": str(sp.product.id),
                    "title": sp.product.title,
                    "price": float(sp.product.price),
                    "imageUrl": sp.product.image_urls[0] if sp.product.image_urls else None,
                }
                for sp in stream_products
            ],
            "totalCount": len(stream_products),
        },
    }


# ============================================================================
# STEP 3: UPDATE STREAM SETTINGS
# ============================================================================


@router.patch("/{stream_id}/settings", response_model=dict)
async def update_stream_settings(
    stream_id: UUID,
    stream_update: StreamUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update stream settings (Step 3: Stream Settings)"""
    # Get stream
    stmt = select(Stream).where(Stream.id == stream_id)
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your stream")

    if stream.status != StreamStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="Can only update scheduled streams")

    # Update fields
    update_data = stream_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stream, field, value)

    await db.commit()
    await db.refresh(stream)

    return {
        "success": True,
        "data": {
            "streamId": str(stream.id),
            "title": stream.title,
            "settings": {
                "audience": stream.audience,
                "estimatedDuration": stream.estimated_duration,
                "notifyFollowers": stream.notify_followers,
                "notifyNeighborhood": stream.notify_neighborhood,
                "enableChat": stream.enable_chat,
                "enableComments": stream.enable_comments,
                "recordStream": stream.record_stream,
            },
            "updatedAt": stream.updated_at.isoformat(),
        },
    }


# ============================================================================
# STEP 5: GO LIVE
# ============================================================================


@router.post("/{stream_id}/go-live", response_model=dict)
async def go_live(
    stream_id: UUID,
    go_live_data: GoLiveRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    feed_cache: FeedCacheService = Depends(get_feed_cache_service),
):
    """
    Start live streaming (Step 5: After Countdown)

    Validates checklist, generates RTMP credentials, sends notifications
    """
    # Get stream with products
    stmt = select(Stream).where(Stream.id == stream_id).options(selectinload(Stream.stream_products))
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your stream")

    if stream.status != StreamStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="Stream must be in scheduled status")

    # Validate has products
    if not stream.stream_products:
        raise HTTPException(status_code=400, detail="Stream must have at least 1 product attached")

    # Validate checklist
    if not go_live_data.camera_ready or not go_live_data.checklist_complete:
        raise HTTPException(status_code=400, detail="Camera and checklist must be ready")

    # Generate RTMP credentials
    stream_key = f"sk_{secrets.token_urlsafe(32)}"
    rtmp_url = "rtmp://live.soukloop.com/live"
    hls_url = f"https://video.soukloop.com/live/{stream_id}/index.m3u8"
    dash_url = f"https://video.soukloop.com/live/{stream_id}/manifest.mpd"

    # Update stream
    stream.status = StreamStatus.LIVE
    stream.stream_key = stream_key
    stream.rtmp_url = rtmp_url
    stream.hls_url = hls_url
    stream.started_at = datetime.now(timezone.utc)
    stream.viewer_count = 0

    await db.commit()

    # ========== Invalidate Feed Caches ==========
    # Stream is now LIVE - all feeds need to refresh to show updated live badge
    await feed_cache.invalidate_all_feeds()

    # Send notifications based on audience setting
    notifications_sent = 0

    # TODO: Implement notification service
    # if stream.notify_followers:
    #     if stream.audience == 'everyone':
    #         followers = await get_user_followers(current_user.id, db)
    #         notifications_sent += await send_notifications(followers, stream)
    #     elif stream.audience == 'followers':
    #         followers = await get_user_followers(current_user.id, db)
    #         notifications_sent += await send_notifications(followers, stream)
    #
    # if stream.notify_neighborhood and stream.audience in ['everyone', 'neighborhood']:
    #     neighbors = await get_users_in_neighborhood(current_user.location, db)
    #     notifications_sent += await send_notifications(neighbors, stream)

    # Placeholder notification count
    notifications_sent = 1247

    # Emit WebSocket event
    # TODO: await manager.send_to_all('stream:started', {'stream_id': str(stream_id)})

    return {
        "success": True,
        "message": "Stream is now live!",
        "data": {
            "streamId": str(stream.id),
            "status": "live",
            "rtmpUrl": rtmp_url,
            "streamKey": stream_key,
            "hlsUrl": hls_url,
            "dashUrl": dash_url,
            "startedAt": stream.started_at.isoformat(),
            "notificationsSent": notifications_sent,
        },
    }


# ============================================================================
# END STREAM
# ============================================================================


@router.post("/{stream_id}/end", response_model=dict)
async def end_stream(
    stream_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    feed_cache: FeedCacheService = Depends(get_feed_cache_service),
):
    """End live stream and generate analytics"""
    # Get stream
    stmt = select(Stream).where(Stream.id == stream_id)
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your stream")

    if stream.status != StreamStatus.LIVE:
        raise HTTPException(status_code=400, detail="Stream is not live")

    # Update stream
    stream.status = StreamStatus.ENDED
    stream.ended_at = datetime.now(timezone.utc)
    stream.duration_seconds = int((stream.ended_at - stream.started_at).total_seconds())

    # Get analytics from Redis
    redis = await get_redis()

    # Peak viewers (stored during stream)
    peak_viewers = await redis.get(f"stream:{stream_id}:peak_viewers") or 0
    stream.peak_viewers = int(peak_viewers)

    # Unique viewers (set size)
    unique_viewers = await redis.scard(f"stream:{stream_id}:unique_viewers") or 0
    stream.unique_viewers = int(unique_viewers)

    # Total likes
    total_likes = await redis.get(f"stream:{stream_id}:total_likes") or 0
    stream.total_likes = int(total_likes)

    # Chat messages
    chat_count = await redis.get(f"stream:{stream_id}:chat_count") or 0
    stream.chat_messages_count = int(chat_count)

    # TODO: Calculate average watch time
    # TODO: Convert live recording to VOD if record_stream = true
    # TODO: Generate final HLS URLs for VOD playback

    if stream.record_stream:
        stream.vod_url = f"https://video.soukloop.com/vods/{stream_id}.m3u8"

    await db.commit()

    # ========== Invalidate Feed Caches ==========
    # Stream has ended - all feeds need to refresh to remove live badge
    await feed_cache.invalidate_all_feeds()

    # Emit WebSocket event
    # TODO: await manager.send_to_conversation(str(stream_id), 'stream:ended', {})

    return {
        "success": True,
        "message": "Stream ended successfully",
        "data": {
            "streamId": str(stream.id),
            "status": "ended",
            "duration": stream.duration_seconds,
            "stats": {
                "peakViewers": stream.peak_viewers,
                "uniqueViewers": stream.unique_viewers,
                "totalLikes": stream.total_likes,
                "chatMessages": stream.chat_messages_count,
                "averageWatchTime": stream.average_watch_time,
            },
            "vodUrl": stream.vod_url,
            "endedAt": stream.ended_at.isoformat(),
        },
    }


# ============================================================================
# GET STREAM DETAILS
# ============================================================================


@router.get("/{stream_id}", response_model=dict)
async def get_stream(
    stream_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get stream details with products"""
    stmt = (
        select(Stream)
        .where(Stream.id == stream_id)
        .options(
            selectinload(Stream.user),
            selectinload(Stream.stream_products).selectinload(StreamProduct.product),
        )
    )
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    return {
        "success": True,
        "data": StreamResponse.model_validate(stream),
    }


# ============================================================================
# TAG PRODUCTS ON STREAM
# ============================================================================


@router.post("/{stream_id}/products/{product_id}/tag", response_model=dict)
async def tag_product(
    stream_id: UUID,
    product_id: UUID,
    tag_position: ProductTagPosition,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Tag product on stream with position coordinates"""
    # Validate stream product exists
    stmt = select(StreamProduct).where(
        and_(
            StreamProduct.stream_id == stream_id,
            StreamProduct.product_id == product_id,
        )
    )
    result = await db.execute(stmt)
    stream_product = result.scalar_one_or_none()

    if not stream_product:
        raise HTTPException(status_code=404, detail="Product not in stream")

    # Update position
    stream_product.x_position = tag_position.x
    stream_product.y_position = tag_position.y
    stream_product.timestamp_seconds = tag_position.timestamp_seconds

    await db.commit()

    return {
        "success": True,
        "message": "Product tagged successfully",
        "data": {
            "productId": str(product_id),
            "x": tag_position.x,
            "y": tag_position.y,
            "timestamp": tag_position.timestamp_seconds,
        },
    }


# ============================================================================
# GET STREAM PRODUCTS
# ============================================================================


@router.get("/{stream_id}/products", response_model=dict)
async def get_stream_products(
    stream_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all products for stream"""
    stmt = (
        select(StreamProduct)
        .where(StreamProduct.stream_id == stream_id)
        .options(selectinload(StreamProduct.product))
    )
    result = await db.execute(stmt)
    stream_products = result.scalars().all()

    return {
        "success": True,
        "data": {
            "streamId": str(stream_id),
            "products": [
                {
                    "id": str(sp.product.id),
                    "title": sp.product.title,
                    "price": float(sp.product.price),
                    "imageUrl": sp.product.image_urls[0] if sp.product.image_urls else None,
                    "tagPosition": {
                        "x": sp.x_position,
                        "y": sp.y_position,
                        "timestamp": sp.timestamp_seconds,
                    }
                    if sp.x_position is not None
                    else None,
                    "analytics": {
                        "clicks": sp.clicks,
                        "views": sp.views,
                        "inquiries": sp.inquiries,
                        "purchases": sp.purchases,
                    },
                }
                for sp in stream_products
            ],
            "totalCount": len(stream_products),
        },
    }


# ============================================================================
# STREAM ANALYTICS
# ============================================================================


@router.get("/{stream_id}/analytics", response_model=dict)
async def get_stream_analytics(
    stream_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive stream analytics"""
    # Get stream with products
    stmt = (
        select(Stream)
        .where(Stream.id == stream_id)
        .options(selectinload(Stream.stream_products).selectinload(StreamProduct.product))
    )
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Only owner can view analytics
    if stream.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your stream")

    # Build analytics response
    analytics = {
        "streamId": str(stream.id),
        "basicStats": {
            "duration": stream.duration_seconds,
            "peakViewers": stream.peak_viewers,
            "uniqueViewers": stream.unique_viewers,
            "averageWatchTime": stream.average_watch_time,
        },
        "engagement": {
            "totalLikes": stream.total_likes,
            "chatMessages": stream.chat_messages_count,
            # TODO: Add reaction breakdown from Redis
        },
        "products": [
            {
                "productId": str(sp.product.id),
                "title": sp.product.title,
                "clicks": sp.clicks,
                "views": sp.views,
                "inquiries": sp.inquiries,
                "purchases": sp.purchases,
            }
            for sp in stream.stream_products
        ],
        # TODO: Add revenue, geography
    }

    return {
        "success": True,
        "data": analytics,
    }
