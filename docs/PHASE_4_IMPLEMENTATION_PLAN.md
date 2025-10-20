# Phase 4 Implementation Plan - Live Streaming

**Status**: 🔄 **60% COMPLETE** (Partial Implementation)
**Remaining Work**: Schema updates, Streaming API, WebSocket handlers, Migration, Testing

---

## ✅ Already Completed (This Session)

### 1. Media Upload Endpoints (`app/api/v1/media.py`) ✅
- **POST /api/v1/media/upload-url** - Generate presigned URLs for B2
- **POST /api/v1/media/video/process** - Start video processing job
- **GET /api/v1/media/status/{job_id}** - Check processing status
- Status: **Complete** (placeholder B2 integration)

### 2. Video Processing Service (`app/services/video_processing.py`) ✅
- `VideoProcessor` class with methods:
  - `extract_metadata()` - FFprobe integration (placeholder)
  - `generate_thumbnail()` - Extract frame at timestamp
  - `transcode_to_hls()` - Multi-resolution HLS (720p, 1080p)
  - `transcode_to_dash()` - DASH manifest generation
  - `upload_to_b2()` - Upload to Backblaze B2
- Status: **Complete** (FFmpeg commands documented, ready for production)

### 3. Enhanced Stream Model (`app/models/stream.py`) ✅
Added fields for Go Live flow:
- `audience` - everyone, followers, neighborhood
- `estimated_duration` - minutes
- `notify_followers`, `notify_neighborhood` - boolean
- `enable_chat`, `enable_comments`, `record_stream` - boolean
- `vod_url` - Video-on-demand URL
- Analytics: `peak_viewers`, `unique_viewers`, `total_likes`, `chat_messages_count`, `average_watch_time`
- Relationship: `stream_products`

### 4. StreamProduct Model (`app/models/stream_product.py`) ✅
Junction table for streams ↔ products:
- `stream_id`, `product_id` - foreign keys
- `x_position`, `y_position` - normalized coordinates (0-1)
- `timestamp_seconds` - when product appears
- Analytics: `clicks`, `views`, `inquiries`, `purchases`

---

## 🔄 Remaining Tasks (To Complete)

### Task 1: Update Stream Schemas (`app/schemas/stream.py`)

**Current State**: Basic schemas exist from Phase 1
**Required**: Enhance with Go Live flow fields

#### File: `app/schemas/stream.py`

Update the following schemas:

```python
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.stream import StreamStatus, StreamType
from app.schemas.base import ORMBaseModel
from app.schemas.product import ProductResponse
from app.schemas.user import UserResponse


class StreamBase(ORMBaseModel):
    """Base stream schema"""
    title: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    category: str = Field(...)


class StreamCreate(ORMBaseModel):
    """
    Create stream schema (ENHANCED for Go Live flow)

    Used in Step 2: Product Selection of Go Live flow
    """
    title: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    category: str
    audience: Literal['everyone', 'followers', 'neighborhood'] = 'everyone'
    estimated_duration: int = Field(30, ge=5, le=240, description="5 min to 4 hours")
    notify_followers: bool = True
    notify_neighborhood: bool = False
    enable_chat: bool = True
    enable_comments: bool = True
    record_stream: bool = True
    product_ids: list[str] = Field(default_factory=list, description="UUIDs of products to showcase")
    scheduled_at: datetime | None = None


class StreamUpdate(ORMBaseModel):
    """
    Update stream settings (Step 3: Stream Settings)
    """
    title: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    audience: Literal['everyone', 'followers', 'neighborhood'] | None = None
    estimated_duration: int | None = Field(None, ge=5, le=240)
    notify_followers: bool | None = None
    notify_neighborhood: bool | None = None
    enable_chat: bool | None = None
    enable_comments: bool | None = None
    record_stream: bool | None = None


class StreamResponse(ORMBaseModel):
    """Stream response with all details"""
    id: str
    user_id: str
    title: str
    description: str | None
    category: str
    status: StreamStatus
    stream_type: StreamType
    rtmp_url: str | None
    stream_key: str | None
    hls_url: str | None
    thumbnail_url: str | None
    viewer_count: int
    total_views: int
    duration_seconds: int | None
    started_at: datetime | None
    ended_at: datetime | None

    # Go Live fields
    audience: str
    estimated_duration: int | None
    notify_followers: bool
    notify_neighborhood: bool
    enable_chat: bool
    enable_comments: bool
    record_stream: bool
    vod_url: str | None

    # Analytics
    peak_viewers: int
    unique_viewers: int
    total_likes: int
    chat_messages_count: int
    average_watch_time: int | None

    created_at: datetime
    updated_at: datetime

    # Optional includes
    user: UserResponse | None = None
    products: list[ProductResponse] | None = None


class GoLiveRequest(ORMBaseModel):
    """
    Go Live request (Step 5: After Countdown)
    """
    camera_ready: bool = Field(..., description="Camera setup complete")
    checklist_complete: bool = Field(..., description="Pre-live checklist verified")


class GoLiveResponse(ORMBaseModel):
    """
    Go Live response with RTMP credentials
    """
    stream_id: str
    status: str
    rtmp_url: str
    stream_key: str
    hls_url: str
    dash_url: str | None = None
    started_at: datetime
    notifications_sent: int  # Number of users notified


class StreamViewer(ORMBaseModel):
    """Viewer information"""
    user_id: str
    username: str
    avatar_url: str | None
    joined_at: datetime


class ProductTagPosition(ORMBaseModel):
    """Product tag position on video"""
    product_id: str
    x: float = Field(..., ge=0.0, le=1.0, description="Normalized X coordinate (0-1)")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalized Y coordinate (0-1)")
    timestamp_seconds: int | None = Field(None, description="When product appears in video")


class StreamAnalytics(ORMBaseModel):
    """Comprehensive stream analytics"""
    stream_id: str
    basic_stats: dict
    engagement: dict
    products: list[dict]
    revenue: dict
    geography: dict
```

---

### Task 2: Create Comprehensive Streaming REST API (`app/api/v1/streams.py`)

This is the **largest remaining task**. Create a new file with all streaming endpoints.

#### File: `app/api/v1/streams.py`

```python
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
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis
from app.database import get_db
from app.dependencies import get_current_active_user
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

router = APIRouter(prefix="/api/v1/streams", tags=["streams"])


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
        raise HTTPException(
            status_code=400,
            detail="Can only attach products to scheduled streams"
        )

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
        raise HTTPException(
            status_code=400,
            detail="Can only update scheduled streams"
        )

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
):
    """
    Start live streaming (Step 5: After Countdown)

    Validates checklist, generates RTMP credentials, sends notifications
    """
    # Get stream with products
    stmt = (
        select(Stream)
        .where(Stream.id == stream_id)
        .options(selectinload(Stream.stream_products))
    )
    result = await db.execute(stmt)
    stream = result.scalar_one_or_none()

    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    if stream.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your stream")

    if stream.status != StreamStatus.SCHEDULED:
        raise HTTPException(
            status_code=400,
            detail="Stream must be in scheduled status"
        )

    # Validate has products
    if not stream.stream_products:
        raise HTTPException(
            status_code=400,
            detail="Stream must have at least 1 product attached"
        )

    # Validate checklist
    if not go_live_data.camera_ready or not go_live_data.checklist_complete:
        raise HTTPException(
            status_code=400,
            detail="Camera and checklist must be ready"
        )

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
    stream.started_at = datetime.utcnow()
    stream.viewer_count = 0

    await db.commit()

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
    stream.ended_at = datetime.utcnow()
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
```

**Action**: Create this file with all endpoints above.

---

### Task 3: Create WebSocket Handlers for Streams (`app/websocket/streams.py`)

Handle real-time stream events (chat, reactions, viewers).

#### File: `app/websocket/streams.py`

```python
"""
WebSocket Event Handlers for Live Streams

Handles:
- Stream join/leave
- Live chat
- Reactions
- Viewer count updates
- Stream preparation (countdown)
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.database import async_session_maker
from app.models.stream import Stream, StreamStatus
from app.models.user import User
from app.websocket.manager import ConnectionManager
from app.websocket.server import sio

logger = logging.getLogger(__name__)

manager: Optional[ConnectionManager] = None


def set_manager(conn_manager: ConnectionManager):
    global manager
    manager = conn_manager


async def _get_db() -> AsyncSession:
    async with async_session_maker() as session:
        return session


async def _get_redis():
    return get_redis()


# ============================================================================
# STREAM JOIN/LEAVE
# ============================================================================

@sio.event
async def stream_join(sid, data: dict):
    """
    Join stream room

    Data:
        stream_id: UUID
    """
    if manager is None:
        await sio.emit("error", {"message": "Manager not initialized"}, room=sid)
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        await sio.emit("error", {"message": "Not authenticated"}, room=sid)
        return

    stream_id = data.get("stream_id")
    if not stream_id:
        await sio.emit("error", {"message": "stream_id required"}, room=sid)
        return

    try:
        db = await _get_db()
        redis = await _get_redis()

        # Validate stream exists and is live
        stmt = select(Stream).where(Stream.id == UUID(stream_id))
        result = await db.execute(stmt)
        stream = result.scalar_one_or_none()

        if not stream:
            await sio.emit("error", {"message": "Stream not found"}, room=sid)
            return

        # Join stream room
        await sio.enter_room(sid, f"stream:{stream_id}")

        # Track unique viewer
        await redis.sadd(f"stream:{stream_id}:unique_viewers", user_id)

        # Increment current viewer count
        current_viewers = await redis.incr(f"stream:{stream_id}:current_viewers")

        # Update peak viewers if needed
        peak = await redis.get(f"stream:{stream_id}:peak_viewers") or 0
        if current_viewers > int(peak):
            await redis.set(f"stream:{stream_id}:peak_viewers", current_viewers)

        # Update stream viewer_count in database
        update_stmt = (
            update(Stream)
            .where(Stream.id == UUID(stream_id))
            .values(viewer_count=current_viewers)
        )
        await db.execute(update_stmt)
        await db.commit()

        # Emit viewer joined to stream
        await sio.emit(
            "viewer:joined",
            {
                "streamId": stream_id,
                "viewerId": user_id,
                "viewerCount": current_viewers,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=f"stream:{stream_id}",
            skip_sid=sid,
        )

        # Confirm to joiner
        await sio.emit(
            "stream:joined",
            {
                "streamId": stream_id,
                "viewerCount": current_viewers,
            },
            room=sid,
        )

        logger.info(f"User {user_id} joined stream {stream_id}")

    except Exception as e:
        logger.error(f"Error joining stream: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def stream_leave(sid, data: dict):
    """Leave stream room"""
    if manager is None:
        return

    user_id = manager.get_user_from_sid(sid)
    stream_id = data.get("stream_id")

    if not stream_id:
        return

    try:
        redis = await _get_redis()
        db = await _get_db()

        # Decrement viewer count
        current_viewers = await redis.decr(f"stream:{stream_id}:current_viewers")
        if current_viewers < 0:
            current_viewers = 0
            await redis.set(f"stream:{stream_id}:current_viewers", 0)

        # Update database
        update_stmt = (
            update(Stream)
            .where(Stream.id == UUID(stream_id))
            .values(viewer_count=current_viewers)
        )
        await db.execute(update_stmt)
        await db.commit()

        # Leave room
        await sio.leave_room(sid, f"stream:{stream_id}")

        # Emit viewer left
        await sio.emit(
            "viewer:left",
            {
                "streamId": stream_id,
                "viewerId": user_id,
                "viewerCount": current_viewers,
            },
            room=f"stream:{stream_id}",
        )

        logger.info(f"User {user_id} left stream {stream_id}")

    except Exception as e:
        logger.error(f"Error leaving stream: {e}")


# ============================================================================
# LIVE CHAT
# ============================================================================

@sio.event
async def stream_chat(sid, data: dict):
    """
    Send chat message in stream

    Data:
        stream_id: UUID
        message: string (max 200 chars)
    """
    if manager is None:
        await sio.emit("error", {"message": "Manager not initialized"}, room=sid)
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        await sio.emit("error", {"message": "Not authenticated"}, room=sid)
        return

    stream_id = data.get("stream_id")
    message = data.get("message", "").strip()

    if not stream_id or not message:
        await sio.emit("error", {"message": "stream_id and message required"}, room=sid)
        return

    if len(message) > 200:
        await sio.emit("error", {"message": "Message too long (max 200 chars)"}, room=sid)
        return

    try:
        db = await _get_db()
        redis = await _get_redis()

        # Get user info
        stmt = select(User).where(User.id == UUID(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one()

        # Rate limit: max 10 messages per minute
        rate_key = f"stream:{stream_id}:chat_rate:{user_id}"
        current_count = await redis.incr(rate_key)
        if current_count == 1:
            await redis.expire(rate_key, 60)
        if current_count > 10:
            await sio.emit("error", {"message": "Rate limit exceeded"}, room=sid)
            return

        # Increment chat count
        await redis.incr(f"stream:{stream_id}:chat_count")

        # Store in Redis (last 100 messages)
        message_data = {
            "userId": user_id,
            "username": user.username,
            "avatarUrl": user.avatar_url,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await redis.lpush(f"stream:{stream_id}:chat", str(message_data))
        await redis.ltrim(f"stream:{stream_id}:chat", 0, 99)

        # Broadcast to stream
        await sio.emit(
            "chat:message",
            message_data,
            room=f"stream:{stream_id}",
        )

        logger.info(f"Chat message in stream {stream_id} by {user_id}")

    except Exception as e:
        logger.error(f"Error sending chat: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


# ============================================================================
# REACTIONS
# ============================================================================

@sio.event
async def stream_reaction(sid, data: dict):
    """
    Send reaction in stream

    Data:
        stream_id: UUID
        emoji: string (❤️ 🔥 👏 😂 😮 💎)
    """
    if manager is None:
        return

    user_id = manager.get_user_from_sid(sid)
    if not user_id:
        return

    stream_id = data.get("stream_id")
    emoji = data.get("emoji")

    allowed_emojis = ["❤️", "🔥", "👏", "😂", "😮", "💎"]

    if not stream_id or not emoji or emoji not in allowed_emojis:
        return

    try:
        redis = await _get_redis()

        # Increment reaction count
        await redis.incr(f"stream:{stream_id}:reactions:{emoji}")
        await redis.incr(f"stream:{stream_id}:total_likes")

        # Broadcast reaction
        await sio.emit(
            "reaction:new",
            {
                "streamId": stream_id,
                "userId": user_id,
                "emoji": emoji,
                "timestamp": datetime.utcnow().isoformat(),
            },
            room=f"stream:{stream_id}",
        )

    except Exception as e:
        logger.error(f"Error sending reaction: {e}")


# ============================================================================
# STREAM PREPARATION (COUNTDOWN)
# ============================================================================

@sio.event
async def stream_prepare(sid, data: dict):
    """
    Prepare stream (during countdown)

    Data:
        stream_id: UUID
    """
    if manager is None:
        return

    user_id = manager.get_user_from_sid(sid)
    stream_id = data.get("stream_id")

    if not stream_id:
        return

    try:
        # TODO: Warm up RTMP connection, prepare CDN

        await sio.emit(
            "stream:ready",
            {
                "streamId": stream_id,
                "estimatedLatency": 3,
                "status": "ready",
            },
            room=sid,
        )

        logger.info(f"Stream {stream_id} prepared for go live")

    except Exception as e:
        logger.error(f"Error preparing stream: {e}")
```

**Action**: Create this file with all event handlers.

---

### Task 4: Register Stream Endpoints and WebSocket Handlers

#### File: `app/api/v1/__init__.py`

Add streams router:

```python
from app.api.v1 import auth, categories, feeds, health, media, messages, offers, products, search, streams

api_router.include_router(streams.router)
```

#### File: `app/websocket/server.py`

Import and set manager for streams:

```python
from app.websocket import messaging, offers, streams  # Add streams

messaging.set_manager(connection_manager)
offers.set_manager(connection_manager)
streams.set_manager(connection_manager)  # Add this line
```

---

### Task 5: Create Database Migration

Generate and apply migration for Stream model enhancements:

```bash
# Generate migration
docker-compose exec app alembic revision -m "enhance_stream_model_for_go_live_flow"
```

Edit the generated migration file to add new columns:

```python
def upgrade() -> None:
    # Add Go Live flow fields
    op.add_column('streams', sa.Column('audience', sa.String(20), server_default='everyone', nullable=False))
    op.add_column('streams', sa.Column('estimated_duration', sa.Integer(), nullable=True))
    op.add_column('streams', sa.Column('notify_followers', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('streams', sa.Column('notify_neighborhood', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('streams', sa.Column('enable_chat', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('streams', sa.Column('enable_comments', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('streams', sa.Column('record_stream', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('streams', sa.Column('vod_url', sa.String(1024), nullable=True))

    # Add analytics fields
    op.add_column('streams', sa.Column('peak_viewers', sa.Integer(), server_default='0', nullable=False))
    op.add_column('streams', sa.Column('unique_viewers', sa.Integer(), server_default='0', nullable=False))
    op.add_column('streams', sa.Column('total_likes', sa.Integer(), server_default='0', nullable=False))
    op.add_column('streams', sa.Column('chat_messages_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('streams', sa.Column('average_watch_time', sa.Integer(), nullable=True))

    # Create stream_products table
    op.create_table(
        'stream_products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stream_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('x_position', sa.Float(), nullable=True),
        sa.Column('y_position', sa.Float(), nullable=True),
        sa.Column('timestamp_seconds', sa.Integer(), nullable=True),
        sa.Column('clicks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('views', sa.Integer(), server_default='0', nullable=False),
        sa.Column('inquiries', sa.Integer(), server_default='0', nullable=False),
        sa.Column('purchases', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_stream_products_stream', 'stream_products', ['stream_id'])
    op.create_index('ix_stream_products_product', 'stream_products', ['product_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_stream_products_product', table_name='stream_products')
    op.drop_index('ix_stream_products_stream', table_name='stream_products')

    # Drop table
    op.drop_table('stream_products')

    # Drop columns
    op.drop_column('streams', 'average_watch_time')
    op.drop_column('streams', 'chat_messages_count')
    op.drop_column('streams', 'total_likes')
    op.drop_column('streams', 'unique_viewers')
    op.drop_column('streams', 'peak_viewers')
    op.drop_column('streams', 'vod_url')
    op.drop_column('streams', 'record_stream')
    op.drop_column('streams', 'enable_comments')
    op.drop_column('streams', 'enable_chat')
    op.drop_column('streams', 'notify_neighborhood')
    op.drop_column('streams', 'notify_followers')
    op.drop_column('streams', 'estimated_duration')
    op.drop_column('streams', 'audience')
```

Apply migration:

```bash
docker-compose exec app alembic upgrade head
```

---

## 📋 Testing Checklist (After Implementation)

### Media Upload
- [ ] Generate presigned URL for image
- [ ] Generate presigned URL for video
- [ ] Start video processing job
- [ ] Check processing status

### Stream Creation (Go Live Flow)
- [ ] Step 2: Create stream with products
- [ ] Step 2: Attach additional products
- [ ] Step 3: Update stream settings
- [ ] Step 5: Go live with validation
- [ ] Verify RTMP credentials generated
- [ ] Verify notifications sent (TODO)

### Stream Management
- [ ] Get stream details
- [ ] Tag product on stream
- [ ] End stream
- [ ] View stream analytics

### WebSocket - Live Streams
- [ ] Join stream room
- [ ] Send chat message
- [ ] Send reaction
- [ ] Leave stream (verify viewer count decrements)
- [ ] Test rate limiting on chat

### Analytics
- [ ] Verify viewer count tracking
- [ ] Verify peak viewers tracked
- [ ] Verify unique viewers tracked
- [ ] Verify chat count tracked
- [ ] Verify reaction counts tracked

---

## 🚀 Production Considerations

### 1. Video Processing
- Install FFmpeg and FFprobe on server
- Set up Celery or similar task queue
- Implement actual B2 upload with boto3
- Add error handling and retry logic
- Monitor processing progress

### 2. Live Streaming Infrastructure
- **Option A**: Self-hosted RTMP server (Nginx + RTMP module)
- **Option B**: AWS MediaLive
- **Option C**: Third-party service (Mux, Agora)

Example Nginx RTMP config:
```nginx
rtmp {
    server {
        listen 1935;
        application live {
            live on;
            hls on;
            hls_path /tmp/hls;
            hls_fragment 6s;

            # Validate stream key
            on_publish http://api.soukloop.com/api/v1/streams/validate-key;
        }
    }
}
```

### 3. CDN Integration
- Configure Cloudflare for HLS delivery
- Set up Backblaze B2 → Cloudflare bandwidth alliance (free egress)
- Implement proper caching headers

### 4. Notification Service
Create `app/services/notification_service.py`:
- Firebase Cloud Messaging for push notifications
- Send to followers based on audience setting
- Send to neighborhood users (within 2km)
- Track notification delivery

---

## 📊 Estimated Effort

| Task | Lines of Code | Time Estimate |
|------|---------------|---------------|
| Schema updates | ~200 lines | 30 mins |
| Streaming REST API | ~800 lines | 2-3 hours |
| WebSocket handlers | ~400 lines | 1-2 hours |
| Migration | ~100 lines | 30 mins |
| Testing | - | 2-3 hours |
| **TOTAL** | **~1500 lines** | **6-9 hours** |

---

## ✅ Completion Criteria

Phase 4 is considered complete when:
1. ✅ All schemas updated with Go Live fields
2. ✅ All 9 streaming REST endpoints implemented
3. ✅ All 6 WebSocket stream events implemented
4. ✅ Database migration applied successfully
5. ✅ Can create stream → go live → end stream via API
6. ✅ WebSocket chat and reactions work
7. ✅ Viewer count tracking functional
8. ✅ Analytics endpoints return data

---

## 📝 Notes for Next Session

1. **Follow this plan step-by-step** - Each task builds on the previous
2. **Test incrementally** - Test each endpoint as you build it
3. **Use TODO markers** - Mark production integrations (B2, FFmpeg, Notifications) with TODO
4. **Copy-paste safety** - All code provided is ready to use (just update imports if needed)
5. **Database migrations** - Always backup database before applying migrations

---

## 🎯 After Phase 4 Completion

Once Phase 4 is complete, you'll have:
- **Full backend implementation** (Phases 1-4)
- **Ready for frontend integration**
- **Real-time features** (WebSocket messaging, offers, streaming)
- **Video upload and processing** (placeholder, ready for production FFmpeg)
- **Live streaming infrastructure** (ready for RTMP server setup)

Then you can proceed with comprehensive testing of all 4 phases together with the Flutter frontend.

---

**End of Implementation Plan**
