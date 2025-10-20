# Souk Loop Backend - Testing Guide
**Phases 1-4 Integration Testing**

**Date**: October 18, 2025
**Backend Version**: 1.0.0
**Status**: Ready for Frontend Integration Testing

---

## Overview

This guide provides step-by-step testing procedures for all completed backend phases (1-4) before proceeding to Phase 5 (Transactions & Payments).

**What's Complete**:
- ✅ Phase 1: Core Infrastructure (Auth, Database Models)
- ✅ Phase 2: Products & Feeds (CRUD, Search, Categories)
- ✅ Phase 3: Messaging & Offers (Real-time chat, Negotiations)
- ✅ Phase 4: Live Streaming (Go Live flow, WebSocket events)

---

## Quick Start

### 1. Verify Backend is Running

```bash
cd backend
docker-compose ps
```

**Expected Output**: All 3 services should be "Up"
- `backend-app-1` - Port 8000
- `backend-postgres-1` - Port 5432
- `backend-redis-1` - Port 6379

### 2. Check API Health

```bash
# Open in browser
open http://localhost:8000/docs

# Or test with curl
curl http://localhost:8000/api/v1/categories
```

### 3. Access Interactive API Documentation

**Swagger UI**: http://localhost:8000/docs
**ReDoc**: http://localhost:8000/redoc

---

## Testing Environment Setup

### Prerequisites

**Tools Needed**:
- [Postman](https://www.postman.com/downloads/) or [Thunder Client](https://www.thunderclient.com/) (VSCode extension)
- [Socket.IO Client](https://socket.io/docs/v4/client-initialization/) (for WebSocket testing)
- Web browser (for Swagger UI)

### Environment Variables

Create a `.env.testing` file for testing:

```env
# Backend URL
BACKEND_URL=http://localhost:8000

# Test User Credentials
TEST_EMAIL=testbuyer@soukloop.com
TEST_PASSWORD=Test123!@#
TEST_PHONE=+971501234567

# Test Seller Credentials
SELLER_EMAIL=testseller@soukloop.com
SELLER_PASSWORD=Seller123!@#
SELLER_PHONE=+971507654321
```

---

## PHASE 1: Authentication & Core Models

### Objective
Verify user registration, login, OTP verification, and JWT authentication.

### Test Cases

#### 1.1 User Registration (Buyer)

**Endpoint**: `POST /api/v1/auth/register`

**Request Body**:
```json
{
  "email": "testbuyer@soukloop.com",
  "username": "testbuyer",
  "password": "Test123!@#",
  "phone": "+971501234567",
  "full_name": "Test Buyer",
  "role": "buyer"
}
```

**Expected Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
      "id": "uuid",
      "email": "testbuyer@soukloop.com",
      "username": "testbuyer",
      "role": "buyer",
      "is_verified": false
    }
  }
}
```

**✅ Pass Criteria**:
- Returns 201 status
- Tokens are valid JWTs
- User created in database
- `is_verified` is false initially

#### 1.2 User Registration (Seller)

**Request Body**:
```json
{
  "email": "testseller@soukloop.com",
  "username": "testseller",
  "password": "Seller123!@#",
  "phone": "+971507654321",
  "full_name": "Test Seller",
  "role": "seller"
}
```

**✅ Pass Criteria**:
- Seller account created with `role: "seller"`

#### 1.3 Send OTP for Verification

**Endpoint**: `POST /api/v1/auth/send-otp`

**Request Body**:
```json
{
  "identifier": "testbuyer@soukloop.com",
  "type": "email"
}
```

**Expected Response** (200 OK):
```json
{
  "success": true,
  "message": "OTP sent to testbuyer@soukloop.com",
  "expires_in": 600
}
```

**✅ Pass Criteria**:
- Returns success message
- OTP stored in Redis with 10-minute expiry
- Check Redis: `redis-cli GET otp:testbuyer@soukloop.com`

#### 1.4 Verify OTP

**Endpoint**: `POST /api/v1/auth/verify-otp`

**Request Body**:
```json
{
  "identifier": "testbuyer@soukloop.com",
  "otp_code": "123456"
}
```

**Note**: Get the actual OTP from Redis:
```bash
docker-compose exec redis redis-cli GET "otp:testbuyer@soukloop.com"
```

**Expected Response** (200 OK):
```json
{
  "success": true,
  "message": "OTP verified successfully"
}
```

**✅ Pass Criteria**:
- User's `is_verified` set to `true` in database
- OTP removed from Redis after verification

#### 1.5 Login

**Endpoint**: `POST /api/v1/auth/login`

**Request Body**:
```json
{
  "identifier": "testbuyer@soukloop.com",
  "password": "Test123!@#"
}
```

**Expected Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

**✅ Pass Criteria**:
- Returns valid JWT tokens
- `last_login_at` updated in database

#### 1.6 Get Current User

**Endpoint**: `GET /api/v1/auth/me`

**Headers**:
```
Authorization: Bearer {access_token}
```

**Expected Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "email": "testbuyer@soukloop.com",
    "username": "testbuyer",
    "full_name": "Test Buyer",
    "role": "buyer",
    "is_verified": true,
    "is_active": true,
    "created_at": "2025-10-18T10:00:00Z"
  }
}
```

**✅ Pass Criteria**:
- Returns current user details
- Requires valid JWT token

#### 1.7 Refresh Token

**Endpoint**: `POST /api/v1/auth/refresh`

**Request Body**:
```json
{
  "refresh_token": "eyJ..."
}
```

**✅ Pass Criteria**:
- Returns new access token
- Old token still valid until expiry

---

## PHASE 2: Products & Feeds

### Objective
Test product CRUD, feed browsing, search, and category filtering.

### Test Cases

#### 2.1 Create Product (Community Feed)

**Endpoint**: `POST /api/v1/products`

**Headers**:
```
Authorization: Bearer {seller_access_token}
```

**Request Body**:
```json
{
  "title": "Nike Air Jordan 1 Retro High",
  "description": "Brand new, never worn. Size 42. Original box included.",
  "price": 850.00,
  "currency": "AED",
  "category": "sneakers",
  "condition": "new",
  "feed_type": "community",
  "location": {
    "latitude": 25.0772,
    "longitude": 55.1369
  },
  "neighborhood": "Dubai Marina",
  "image_urls": [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg"
  ],
  "tags": ["sneakers", "jordan", "nike"]
}
```

**Expected Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "Nike Air Jordan 1 Retro High",
    "price": 850.00,
    "feed_type": "community",
    "platform_fee": 42.50,
    "seller_payout": 807.50,
    "is_available": true,
    "created_at": "2025-10-18T10:00:00Z"
  }
}
```

**✅ Pass Criteria**:
- Product created with 5% platform fee (Community)
- Location stored as PostGIS Point
- Returns product with seller info

#### 2.2 Create Product (Discover Feed with Video)

**Request Body**:
```json
{
  "title": "Live Trading Card Pack Opening - Pokemon 2025",
  "description": "Join me live as I open rare Pokemon packs!",
  "price": 299.00,
  "category": "trading_cards",
  "condition": "new",
  "feed_type": "discover",
  "location": {
    "latitude": 25.2048,
    "longitude": 55.2708
  },
  "neighborhood": "Downtown Dubai",
  "video_url": "https://example.com/video.m3u8",
  "video_thumbnail_url": "https://example.com/thumb.jpg",
  "image_urls": ["https://example.com/img1.jpg"]
}
```

**✅ Pass Criteria**:
- Product created with 15% platform fee (Discover)
- Video URL required for Discover feed
- Platform fee: AED 44.85 (15% of 299)

#### 2.3 Browse Discover Feed

**Endpoint**: `GET /api/v1/feeds/discover`

**Query Params**:
```
?page=1&per_page=20&category=sneakers&sort=recent
```

**Expected Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "...",
        "price": 850.00,
        "video_url": "...",
        "thumbnail_url": "...",
        "is_live": false,
        "seller": {
          "username": "@testseller",
          "avatar_url": "...",
          "is_verified": true
        }
      }
    ],
    "page": 1,
    "per_page": 20,
    "total": 1,
    "has_more": false
  }
}
```

**✅ Pass Criteria**:
- Returns Discover feed products only
- Live streams appear first (if any)
- Seller info included

#### 2.4 Browse Community Feed (Location-based)

**Endpoint**: `GET /api/v1/feeds/community`

**Query Params**:
```
?latitude=25.0772&longitude=55.1369&radius_km=5&sort=nearest
```

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "Nike Air Jordan 1 Retro High",
        "price": 850.00,
        "distance_km": 0.5,
        "distance_label": "Walking distance",
        "neighborhood": "Dubai Marina",
        "seller": {...}
      }
    ],
    "page": 1,
    "total": 1
  }
}
```

**✅ Pass Criteria**:
- Returns products within 5km radius
- Sorted by nearest first
- Distance calculated correctly (PostGIS)

#### 2.5 Search Products

**Endpoint**: `GET /api/v1/search`

**Query Params**:
```
?q=nike jordan&category=sneakers&min_price=500&max_price=1000
```

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "items": [...],
    "facets": {
      "categories": [
        {"category": "sneakers", "count": 1}
      ],
      "price_ranges": [
        {"label": "AED 500-1000", "count": 1}
      ]
    },
    "total": 1
  }
}
```

**✅ Pass Criteria**:
- Full-text search works (PostgreSQL GIN index)
- Filters applied correctly
- Facets returned for refinement

#### 2.6 Get Categories

**Endpoint**: `GET /api/v1/categories`

**Expected Response**:
```json
{
  "success": true,
  "data": [
    {
      "slug": "trading_cards",
      "name": "Trading Card Games",
      "icon": "🎴",
      "color": "#9333EA",
      "secondary_color": "#EC4899",
      "total_products": 1,
      "live_streams_count": 0,
      "active_listings_count": 1
    },
    {
      "slug": "sneakers",
      "name": "Sneakers & Streetwear",
      ...
    }
    // ... 12 categories total
  ]
}
```

**✅ Pass Criteria**:
- Returns all 12 categories
- Counts accurate
- Cached in Redis (5-minute TTL)

---

## PHASE 3: Messaging & Offers

### Objective
Test real-time messaging, offer creation, and negotiation flow.

### Test Cases

#### 3.1 Create Conversation

**Endpoint**: `POST /api/v1/conversations`

**Headers**:
```
Authorization: Bearer {buyer_access_token}
```

**Request Body**:
```json
{
  "other_user_id": "{seller_user_id}",
  "product_id": "{product_id}",
  "initial_message": "Hi! Is this item still available?"
}
```

**Expected Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "id": "conv_uuid",
    "buyer_id": "buyer_uuid",
    "seller_id": "seller_uuid",
    "product_id": "product_uuid",
    "unread_count_buyer": 0,
    "unread_count_seller": 1,
    "created_at": "2025-10-18T10:00:00Z"
  }
}
```

**✅ Pass Criteria**:
- Conversation created
- Initial message sent
- Seller has unread_count = 1

#### 3.2 Send Message

**Endpoint**: `POST /api/v1/conversations/{conversation_id}/messages`

**Request Body**:
```json
{
  "message_type": "text",
  "content": "Yes! It's available. Would you like to see more photos?"
}
```

**Expected Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "id": "msg_uuid",
    "conversation_id": "conv_uuid",
    "sender_id": "seller_uuid",
    "message_type": "text",
    "content": "Yes! It's available...",
    "created_at": "2025-10-18T10:05:00Z"
  }
}
```

**✅ Pass Criteria**:
- Message created
- Conversation `last_message_at` updated
- Buyer `unread_count` incremented

#### 3.3 WebSocket - Connect to Messaging

**Socket.IO Client**:
```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:8000', {
  auth: {
    token: buyer_access_token
  }
});

socket.on('connected', (data) => {
  console.log('Connected:', data);
});

socket.on('user:online', (data) => {
  console.log('User online:', data);
});
```

**✅ Pass Criteria**:
- Connection established
- User added to online_users in Redis
- `connected` event received

#### 3.4 WebSocket - Join Conversation & Receive Messages

```javascript
socket.emit('conversation:join', {
  conversation_id: 'conv_uuid'
});

socket.on('message:new', (data) => {
  console.log('New message:', data);
  // { messageId, userId, username, content, timestamp }
});
```

**✅ Pass Criteria**:
- Joined conversation room
- Receives real-time messages
- Messages marked as read

#### 3.5 WebSocket - Typing Indicators

```javascript
// Start typing
socket.emit('typing:start', {
  conversation_id: 'conv_uuid'
});

// Listen for other user typing
socket.on('typing:active', (data) => {
  console.log('User is typing:', data);
});

// Stop typing
socket.emit('typing:stop', {
  conversation_id: 'conv_uuid'
});
```

**✅ Pass Criteria**:
- Typing events broadcast in real-time
- Redis key expires after 5 seconds

#### 3.6 Create Offer

**Endpoint**: `POST /api/v1/offers`

**Request Body**:
```json
{
  "product_id": "{product_id}",
  "offered_price": 750.00,
  "message": "Would you accept 750 AED? I can pick up today."
}
```

**Expected Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "id": "offer_uuid",
    "product_id": "product_uuid",
    "offered_price": 750.00,
    "original_price": 850.00,
    "status": "pending",
    "expires_at": "2025-10-19T10:00:00Z",
    "created_at": "2025-10-18T10:00:00Z"
  }
}
```

**✅ Pass Criteria**:
- Offer created with 24-hour expiry
- Offer message added to conversation
- Seller notified (TODO: push notification)

#### 3.7 Accept Offer

**Endpoint**: `PATCH /api/v1/offers/{offer_id}/accept`

**Headers**:
```
Authorization: Bearer {seller_access_token}
```

**Expected Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": "offer_uuid",
    "status": "accepted",
    "transaction_id": "txn_uuid",
    "message": "Offer accepted! Transaction created."
  }
}
```

**✅ Pass Criteria**:
- Offer status changed to "accepted"
- Product marked as sold
- Transaction created with status "pending"
- Platform fee calculated (5% for Community = AED 37.50)

#### 3.8 WebSocket - Real-time Offer Creation

```javascript
socket.emit('offer:create', {
  product_id: 'product_uuid',
  offered_price: 700.00,
  message: 'My final offer'
});

socket.on('offer:created', (data) => {
  console.log('Offer created:', data);
});

// Seller receives
socket.on('offer:new', (data) => {
  console.log('New offer received:', data);
});
```

**✅ Pass Criteria**:
- Offer created via WebSocket
- Seller receives real-time notification
- Offer added to scrolling feed (Community videos)

---

## PHASE 4: Live Streaming

### Objective
Test complete Go Live flow, WebSocket stream events, and analytics.

### Test Cases

#### 4.1 Create Stream (Step 2: Product Selection)

**Endpoint**: `POST /api/v1/streams`

**Headers**:
```
Authorization: Bearer {seller_access_token}
```

**Request Body**:
```json
{
  "title": "Flash Sale - Up to 50% Off Sneakers!",
  "description": "Live shopping event with exclusive deals",
  "category": "sneakers",
  "audience": "everyone",
  "estimated_duration": 30,
  "notify_followers": true,
  "notify_neighborhood": true,
  "enable_chat": true,
  "enable_comments": true,
  "record_stream": true,
  "product_ids": ["{product_id_1}", "{product_id_2}"]
}
```

**Expected Response** (201 Created):
```json
{
  "success": true,
  "data": {
    "streamId": "stream_uuid",
    "title": "Flash Sale...",
    "status": "scheduled",
    "audience": "everyone",
    "estimatedDuration": 30,
    "productCount": 2,
    "createdAt": "2025-10-18T10:00:00Z"
  }
}
```

**✅ Pass Criteria**:
- Stream created with status "scheduled"
- Products attached via StreamProduct junction table
- Settings stored correctly

#### 4.2 Update Stream Settings (Step 3)

**Endpoint**: `PATCH /api/v1/streams/{stream_id}/settings`

**Request Body**:
```json
{
  "audience": "followers",
  "estimated_duration": 45,
  "notify_neighborhood": false
}
```

**✅ Pass Criteria**:
- Settings updated (only for scheduled streams)
- Cannot update live streams

#### 4.3 Go Live (Step 5)

**Endpoint**: `POST /api/v1/streams/{stream_id}/go-live`

**Request Body**:
```json
{
  "camera_ready": true,
  "checklist_complete": true
}
```

**Expected Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "streamId": "stream_uuid",
    "status": "live",
    "rtmpUrl": "rtmp://live.soukloop.com/live",
    "streamKey": "sk_abc123xyz...",
    "hlsUrl": "https://video.soukloop.com/live/stream_abc123/index.m3u8",
    "dashUrl": "https://video.soukloop.com/live/stream_abc123/manifest.mpd",
    "startedAt": "2025-10-18T10:10:00Z",
    "notificationsSent": 1247
  }
}
```

**✅ Pass Criteria**:
- Status changed to "live"
- RTMP credentials generated
- HLS URL returned
- Notifications sent (placeholder: 1247)
- started_at timestamp set

#### 4.4 WebSocket - Join Stream

```javascript
socket.emit('stream:join', {
  stream_id: 'stream_uuid'
});

socket.on('stream:joined', (data) => {
  console.log('Joined stream:', data);
  // { streamId, viewerCount, status }
});

socket.on('viewer:joined', (data) => {
  console.log('Another viewer joined:', data);
});
```

**✅ Pass Criteria**:
- Viewer added to Redis set `stream:{id}:unique_viewers`
- Current viewer count incremented
- Peak viewers updated if needed
- Database `viewer_count` updated

#### 4.5 WebSocket - Live Chat

```javascript
socket.emit('stream:chat', {
  stream_id: 'stream_uuid',
  message: 'This is amazing! 🔥'
});

socket.on('chat:message', (data) => {
  console.log('Chat message:', data);
  // { userId, username, avatarUrl, message, timestamp }
});
```

**✅ Pass Criteria**:
- Rate limit: max 10 messages/minute per user
- Message broadcast to all viewers
- Last 100 messages stored in Redis
- Chat count incremented

#### 4.6 WebSocket - Reactions

```javascript
socket.emit('stream:reaction', {
  stream_id: 'stream_uuid',
  emoji: '❤️'
});

socket.on('reaction:new', (data) => {
  console.log('Reaction:', data);
  // { emoji, userId }
});
```

**✅ Pass Criteria**:
- Reaction count incremented in Redis
- Total likes incremented
- Reaction broadcast to all viewers

#### 4.7 Tag Product on Video

**Endpoint**: `POST /api/v1/streams/{stream_id}/products/{product_id}/tag`

**Request Body**:
```json
{
  "x": 0.42,
  "y": 0.63,
  "timestamp_seconds": 120
}
```

**✅ Pass Criteria**:
- StreamProduct position updated
- Coordinates stored (0-1 normalized)
- Timestamp recorded

#### 4.8 End Stream

**Endpoint**: `POST /api/v1/streams/{stream_id}/end`

**Expected Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "streamId": "stream_uuid",
    "status": "ended",
    "duration": 1847,
    "stats": {
      "peakViewers": 234,
      "uniqueViewers": 567,
      "totalLikes": 892,
      "chatMessages": 456,
      "averageWatchTime": null,
      "productsTagged": 2,
      "clicksOnProducts": 0
    },
    "vodUrl": "https://video.soukloop.com/vods/stream_abc123.m3u8",
    "endedAt": "2025-10-18T10:40:47Z"
  }
}
```

**✅ Pass Criteria**:
- Status changed to "ended"
- Duration calculated (ended_at - started_at)
- Stats fetched from Redis
- VOD URL generated (if recording enabled)
- `stream:ended` event emitted to all viewers

#### 4.9 Get Stream Analytics

**Endpoint**: `GET /api/v1/streams/{stream_id}/analytics`

**Expected Response**:
```json
{
  "success": true,
  "data": {
    "basicStats": {
      "duration": 1847,
      "peakViewers": 234,
      "uniqueViewers": 567,
      "averageWatchTime": null
    },
    "engagement": {
      "totalLikes": 892,
      "totalReactions": {
        "❤️": 450,
        "🔥": 220,
        "👏": 122,
        "😂": 100
      },
      "chatMessages": 456,
      "newFollowers": 0
    },
    "products": [
      {
        "productId": "prod_123",
        "title": "Nike Air Jordan 1",
        "clicks": 0,
        "views": 0,
        "inquiries": 0,
        "purchases": 0,
        "revenue": 0
      }
    ],
    "revenue": {
      "totalSales": 0,
      "grossRevenue": 0,
      "platformFee": 0,
      "netRevenue": 0
    },
    "geography": {
      "topNeighborhoods": []
    }
  }
}
```

**✅ Pass Criteria**:
- Only stream owner can access
- All analytics populated
- Per-product performance tracked

---

## Integration Testing Scenarios

### Scenario 1: Complete Product Purchase Flow (Community)

**Steps**:
1. Seller creates product (Community feed)
2. Buyer browses Community feed (location-based)
3. Buyer views product details
4. Buyer starts conversation with seller
5. Buyer makes offer
6. Seller accepts offer
7. Transaction created (pending payment)

**Expected Result**:
- Product visible in Community feed within 5km
- Conversation created with messages
- Offer accepted, product marked as sold
- Transaction record with 5% platform fee

---

### Scenario 2: Complete Live Shopping Flow (Discover)

**Steps**:
1. Seller creates stream with products
2. Seller updates stream settings (audience: followers)
3. Seller goes live
4. Viewers join stream via WebSocket
5. Viewers send chat messages
6. Viewers send reactions
7. Seller tags products during stream
8. Seller ends stream
9. Seller views analytics

**Expected Result**:
- Stream goes live successfully
- Viewers tracked in real-time
- Chat and reactions work
- Analytics populated correctly
- VOD URL generated

---

### Scenario 3: Multi-User Real-Time Messaging

**Steps**:
1. User A and User B connect via WebSocket
2. User A sends message to User B
3. User B receives message in real-time
4. User B starts typing
5. User A sees typing indicator
6. User B sends message
7. User A marks messages as read

**Expected Result**:
- Messages delivered in real-time
- Typing indicators work both ways
- Read receipts broadcast correctly
- Unread counts accurate

---

## Performance Testing

### Load Test: Concurrent Stream Viewers

**Tool**: [Artillery](https://www.artillery.io/) or [k6](https://k6.io/)

**Scenario**:
- 100 users join same live stream
- Each user sends 5 chat messages
- Each user sends 3 reactions
- Measure response times and success rate

**Expected**:
- All users successfully join
- Chat messages broadcast to all
- Viewer count accurate
- No errors in logs

---

## Known Issues & Limitations

### TODO Items (Not Yet Implemented)

**Phase 3**:
- [ ] Push notifications when message received (offline user)
- [ ] Push notifications for offer events
- [ ] WebSocket event emission from REST endpoints

**Phase 4**:
- [ ] Actual notification service (returns placeholder: 1247)
- [ ] Background scheduler for viewer count broadcasts
- [ ] RTMP stream key validation webhook
- [ ] Average watch time calculation
- [ ] Revenue analytics integration
- [ ] Geographic distribution analytics

**Production**:
- [ ] RTMP server setup (Nginx + RTMP module or AWS MediaLive)
- [ ] CDN integration (Cloudflare + Backblaze B2)
- [ ] VOD processing (convert recordings to HLS)
- [ ] Horizontal scaling with Redis pub/sub

---

## Troubleshooting

### Issue: Cannot connect to backend

**Solution**:
```bash
# Check if services are running
docker-compose ps

# Restart services
docker-compose restart

# Check logs
docker-compose logs -f app
```

---

### Issue: Database migration out of sync

**Solution**:
```bash
# Check current migration
docker-compose exec app alembic current

# Apply migrations
docker-compose exec app alembic upgrade head

# Check migration history
docker-compose exec app alembic history
```

---

### Issue: Redis keys not expiring

**Solution**:
```bash
# Check Redis keys
docker-compose exec redis redis-cli KEYS "*"

# Check specific key TTL
docker-compose exec redis redis-cli TTL "otp:testbuyer@soukloop.com"

# Flush all Redis keys (CAUTION: Development only)
docker-compose exec redis redis-cli FLUSHALL
```

---

### Issue: WebSocket connection refused

**Solution**:
```bash
# Check if Socket.IO is initialized
docker-compose logs app | grep "socket"

# Verify token is being sent
# In browser console:
const socket = io('http://localhost:8000', {
  auth: { token: 'YOUR_TOKEN_HERE' }
});

socket.on('connect', () => console.log('Connected!'));
socket.on('connect_error', (err) => console.error('Error:', err));
```

---

## Testing Checklist

Use this checklist to track your testing progress:

### Phase 1: Authentication
- [ ] Register buyer account
- [ ] Register seller account
- [ ] Send OTP (email)
- [ ] Verify OTP
- [ ] Login with email + password
- [ ] Get current user (/auth/me)
- [ ] Refresh token
- [ ] Test invalid credentials
- [ ] Test expired token

### Phase 2: Products & Feeds
- [ ] Create Community product
- [ ] Create Discover product (with video)
- [ ] Update product
- [ ] Delete product (soft delete)
- [ ] Browse Discover feed
- [ ] Browse Community feed (with location)
- [ ] Search products (full-text)
- [ ] Get all categories
- [ ] Get category details
- [ ] Test 50 product limit per seller

### Phase 3: Messaging & Offers
- [ ] Create conversation
- [ ] Send text message
- [ ] Send image message
- [ ] Mark conversation as read
- [ ] Archive conversation
- [ ] WebSocket: Connect
- [ ] WebSocket: Join conversation
- [ ] WebSocket: Send message
- [ ] WebSocket: Typing indicators
- [ ] Create offer
- [ ] Accept offer
- [ ] Decline offer
- [ ] Counter offer
- [ ] Test offer expiration (24 hours)

### Phase 4: Live Streaming
- [ ] Create stream
- [ ] Attach products
- [ ] Update stream settings
- [ ] Go live (get RTMP credentials)
- [ ] WebSocket: Join stream
- [ ] WebSocket: Send chat message
- [ ] WebSocket: Send reaction
- [ ] WebSocket: Leave stream
- [ ] Tag product on video
- [ ] End stream
- [ ] View analytics

---

## Next Steps

Once all testing is complete:

1. **Document any bugs** found during testing
2. **Fix critical issues** before Phase 5
3. **Integrate with Flutter frontend** (API client, WebSocket, state management)
4. **Proceed to Phase 5**: Transactions & Payments (Stripe integration)

---

## Resources

**API Documentation**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Database**:
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

**Completion Reports**:
- Phase 1: `backend/PHASE_1_COMPLETION_REPORT.md`
- Phase 2: `backend/PHASE_2_COMPLETION_REPORT.md`
- Phase 3: `backend/PHASE_3_COMPLETION_REPORT.md`
- Phase 4: `backend/PHASE_4_COMPLETION_REPORT.md`

---

**Testing Guide Version**: 1.0
**Last Updated**: October 18, 2025
