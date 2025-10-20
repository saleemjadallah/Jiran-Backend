# Souk Loop Backend - IDE Build Prompts

This document contains comprehensive prompts to give your AI-powered IDE (Cursor, GitHub Copilot, etc.) to build each component of the Souk Loop backend API.

**Context**: These prompts reference the BACKEND_INTEGRATION_SPEC.md and CDN bandwidth document from the project knowledge. Make sure your IDE has access to those documents or provide them as context.

---

## 📋 PHASE 1: Core Infrastructure (Weeks 1-2)

### Prompt 1.1: Project Setup & Configuration

```
Create a production-ready FastAPI backend for Souk Loop, a hyperlocal social commerce platform for UAE combining live shopping (like Whatnot) with neighborhood marketplaces.

Requirements:
- FastAPI 0.104+ with Python 3.11+
- PostgreSQL 15+ with PostGIS extension for geospatial queries
- Redis 7+ for caching and sessions
- SQLAlchemy 2.0 with async support
- Alembic for database migrations
- Pydantic v2 for validation
- JWT authentication with access & refresh tokens
- Socket.IO for WebSocket real-time features
- Structured logging with JSON format
- Docker setup with docker-compose.yml
- Environment configuration using pydantic-settings

Project structure should follow clean architecture:
- app/main.py - FastAPI entry point
- app/config.py - Settings with pydantic-settings
- app/database.py - Database connection with async session
- app/dependencies.py - Dependency injection (auth, db, etc.)
- app/models/ - SQLAlchemy ORM models
- app/schemas/ - Pydantic request/response schemas
- app/api/v1/ - API route handlers
- app/services/ - Business logic layer
- app/utils/ - Utility functions
- app/websocket/ - WebSocket handlers

Include:
- requirements.txt with all dependencies
- .env.example with all configuration variables
- docker-compose.yml with postgres, redis, and app services
- Dockerfile for the FastAPI application
- alembic.ini for database migrations
- README.md with setup instructions

CDN Strategy (per project spec):
- Phase 1: Cloudflare Pro + Backblaze B2 (zero bandwidth costs)
- Storage via AWS S3-compatible API (Backblaze B2)
- Free egress from B2 to Cloudflare
```

### Prompt 1.2: Database Models - Core Entities

```
Create SQLAlchemy 2.0 async models for Souk Loop core entities with PostGIS support.

Models needed:

1. User Model (app/models/user.py):
- id (UUID primary key)
- email (unique, indexed)
- username (unique, indexed)
- phone (unique, indexed with country code)
- password_hash
- full_name
- avatar_url
- bio
- role (enum: 'buyer', 'seller', 'both', 'admin')
- is_verified (boolean)
- is_active (boolean)
- location (PostGIS Point) - user's primary address
- neighborhood (string) - e.g., "Dubai Marina"
- building_name (optional)
- created_at, updated_at timestamps
- last_login_at
- stripe_customer_id
- stripe_connect_account_id (for sellers)

2. Product Model (app/models/product.py):
- id (UUID)
- seller_id (foreign key to User)
- title (max 100 chars)
- description (max 2000 chars)
- price (Decimal, 2 decimal places)
- original_price (optional, for discounts)
- currency (default 'AED')
- category (enum: 12 categories from spec)
- condition (enum: 'new', 'like_new', 'good', 'fair')
- feed_type (enum: 'discover', 'community')
- location (PostGIS Point)
- neighborhood
- is_available (boolean)
- view_count (integer)
- like_count (integer)
- image_urls (JSON array)
- video_url (optional)
- video_thumbnail_url (optional)
- tags (JSON array) - lifestyle, urgency, events
- created_at, updated_at
- sold_at (nullable)

3. Stream Model (app/models/stream.py):
- id (UUID)
- user_id (foreign key)
- title
- description
- category
- status (enum: 'scheduled', 'live', 'ended')
- stream_type (enum: 'live', 'recorded')
- rtmp_url (for live streams)
- stream_key (for live streams)
- hls_url (playback URL)
- thumbnail_url
- viewer_count (integer, updated real-time)
- total_views (integer)
- duration_seconds
- started_at (nullable)
- ended_at (nullable)
- created_at, updated_at

NOTE: Additional fields for Go Live flow (audience, estimated_duration, notification settings, chat/comment toggles, analytics fields) will be added in Phase 4, Prompt 4.2.

Include proper indexes, constraints, and relationships. Use UUID for all primary keys. Add PostGIS geometry column for location with SRID 4326. Include cascade deletes where appropriate.
```

### Prompt 1.3: Database Models - Messaging & Transactions

```
Create SQLAlchemy 2.0 async models for messaging, offers, and transactions.

Models needed:

1. Conversation Model (app/models/conversation.py):
- id (UUID)
- buyer_id (foreign key to User)
- seller_id (foreign key to User)
- product_id (foreign key to Product, nullable)
- last_message_id (foreign key to Message, nullable)
- last_message_at
- unread_count_buyer (integer)
- unread_count_seller (integer)
- is_archived_buyer (boolean)
- is_archived_seller (boolean)
- created_at, updated_at

2. Message Model (app/models/message.py):
- id (UUID)
- conversation_id (foreign key)
- sender_id (foreign key to User)
- message_type (enum: 'text', 'image', 'offer', 'system')
- content (text, nullable)
- image_urls (JSON array, nullable)
- offer_data (JSON, nullable) - for offer messages
- is_read (boolean)
- read_at (nullable)
- created_at

3. Offer Model (app/models/offer.py):
- id (UUID)
- conversation_id (foreign key)
- product_id (foreign key)
- buyer_id (foreign key)
- seller_id (foreign key)
- offered_price (Decimal)
- original_price (Decimal)
- currency
- status (enum: 'pending', 'accepted', 'declined', 'expired', 'countered')
- counter_price (Decimal, nullable)
- message (text, optional)
- expires_at
- responded_at (nullable)
- created_at, updated_at

4. Transaction Model (app/models/transaction.py):
- id (UUID)
- buyer_id (foreign key)
- seller_id (foreign key)
- product_id (foreign key)
- amount (Decimal)
- currency
- platform_fee (Decimal)
- seller_payout (Decimal)
- feed_type (enum: 'discover', 'community')
- status (enum: 'pending', 'completed', 'failed', 'refunded')
- stripe_payment_intent_id
- stripe_charge_id
- stripe_transfer_id (for payout)
- payment_method
- created_at, updated_at
- completed_at (nullable)

5. Verification Model (app/models/verification.py):
- id (UUID)
- user_id (foreign key, unique)
- verification_type (enum: 'emirates_id', 'trade_license', 'both')
- status (enum: 'pending', 'approved', 'rejected')
- emirates_id_number (encrypted)
- emirates_id_front_image_url
- emirates_id_back_image_url
- trade_license_number (optional)
- trade_license_document_url (optional)
- submitted_at
- reviewed_at (nullable)
- reviewed_by (foreign key to User, nullable)
- rejection_reason (text, nullable)
- created_at, updated_at

Include proper indexes for frequently queried fields. Add database constraints for data integrity.
```

### Prompt 1.4: Pydantic Schemas

```
Create Pydantic v2 schemas for request validation and response serialization.

Schemas needed in app/schemas/:

1. auth.py:
- RegisterRequest (email, username, password, phone, full_name, role)
- LoginRequest (email/username, password)
- TokenResponse (access_token, refresh_token, token_type, expires_in)
- SendOTPRequest (phone or email)
- VerifyOTPRequest (phone/email, otp_code)
- RefreshTokenRequest (refresh_token)
- PasswordResetRequest (email)
- PasswordResetConfirm (token, new_password)

2. user.py:
- UserBase (base fields)
- UserCreate (for registration)
- UserUpdate (for profile updates)
- UserResponse (public profile)
- UserDetailResponse (own profile with sensitive data)
- UserLocation (latitude, longitude, neighborhood, building_name)
- UserStats (followers_count, following_count, products_count, rating)

3. product.py:
- ProductBase
- ProductCreate (with image_urls, video_url, location)
- ProductUpdate
- ProductResponse (with seller info, location)
- ProductDetailResponse (with full details)
- ProductFilter (for search/filtering)
- ProductTag (lifestyle, urgency, event tags)

4. stream.py:
- StreamBase
- StreamCreate (basic version here, enhanced in Phase 4 with audience, duration, notifications, etc.)
- StreamUpdate
- StreamResponse
- GoLiveRequest (basic version here, enhanced in Phase 4 with camera_ready, checklist_complete)
- GoLiveResponse (basic version here, enhanced in Phase 4 with notifications_sent count)
- StreamViewer (viewer info)
- ProductTagPosition (x, y coordinates for product tags)

NOTE: Stream schemas will be enhanced in Phase 4, Prompt 4.2 to support the complete Go Live flow with audience settings, notification preferences, and analytics.

5. message.py:
- ConversationResponse
- MessageCreate
- MessageResponse
- OfferMessageData (for offer-type messages)

6. offer.py:
- OfferCreate
- OfferResponse
- OfferUpdate (for accept/decline/counter)

7. transaction.py:
- TransactionCreate
- TransactionResponse
- FeeCalculation (breakdown of fees)

All schemas should:
- Use Pydantic v2 syntax (model_config, ConfigDict)
- Include proper validation (email validator, phone validator, price min/max)
- Have from_orm class method for SQLAlchemy models
- Include example values in Field() for OpenAPI docs
- Use datetime, Decimal, UUID types appropriately
```

### Prompt 1.5: Authentication System

```
Create a complete JWT-based authentication system for Souk Loop.

Files needed:

1. app/utils/jwt.py:
- create_access_token(data: dict, expires_delta: timedelta) -> str
- create_refresh_token(user_id: str) -> str
- verify_token(token: str) -> dict
- decode_access_token(token: str) -> dict
- Hash and verify passwords using passlib with bcrypt

2. app/utils/otp.py:
- generate_otp(length: int = 6) -> str
- send_otp_email(email: str, otp: str) -> bool
- send_otp_sms(phone: str, otp: str) -> bool (using Twilio)
- verify_otp(identifier: str, otp: str, redis_client) -> bool
- Store OTP in Redis with expiry (10 minutes)
- Rate limit OTP requests (max 3 attempts)

3. app/dependencies.py:
- get_db() - database session dependency
- get_current_user(token: str = Depends(oauth2_scheme)) -> User
- get_current_active_user() - ensures user is active
- require_seller_role() - ensures user has seller permissions
- require_admin_role() - admin only endpoints

4. app/api/v1/auth.py:
POST /api/v1/auth/register
- Register new user
- Validate email, username, phone uniqueness
- Hash password
- Create user in database
- Send OTP for verification
- Return tokens

POST /api/v1/auth/login
- Accept email/username + password
- Verify credentials
- Update last_login_at
- Return access + refresh tokens

POST /api/v1/auth/send-otp
- Send OTP to email or phone
- Rate limit: 3 per hour per identifier
- Store in Redis with 10min expiry

POST /api/v1/auth/verify-otp
- Verify OTP code
- Mark user as verified
- Return success response

POST /api/v1/auth/refresh
- Accept refresh token
- Validate token
- Issue new access token
- Return new tokens

POST /api/v1/auth/forgot-password
- Accept email
- Generate reset token
- Send email with reset link
- Token expires in 1 hour

POST /api/v1/auth/reset-password
- Accept reset token + new password
- Validate token
- Update password
- Invalidate token

GET /api/v1/auth/me
- Return current user profile
- Requires authentication

Include proper error handling, rate limiting, and security best practices.
```

---

## 📋 PHASE 2: Products & Feeds (Weeks 3-6)

### Prompt 2.1: Product CRUD Operations

```
Create product management endpoints for Souk Loop.

File: app/api/v1/products.py

Endpoints:

POST /api/v1/products
- Create new product listing
- Validate all required fields
- Store location as PostGIS Point
- Upload images to Backblaze B2 (get presigned URLs first)
- Support both Discover feed (requires video) and Community feed (photos only)
- Calculate and show platform fee on creation
- Return created product with ID

GET /api/v1/products/{product_id}
- Get product details
- Include seller info (name, avatar, rating, verified status)
- Include verification card data
- Calculate distance from requester's location
- Increment view_count
- Return full product details

PUT /api/v1/products/{product_id}
- Update product (only by owner or admin)
- Allow updating: title, description, price, images, availability
- Cannot change feed_type after creation
- Validate ownership

DELETE /api/v1/products/{product_id}
- Soft delete (set is_available = false)
- Only by owner or admin
- Cannot delete if active transactions exist

GET /api/v1/products/{product_id}/similar
- Find similar products using:
  - Same category
  - Similar price range (±30%)
  - Same neighborhood or nearby (within 5km)
- Limit to 10 results
- Order by relevance score

PATCH /api/v1/products/{product_id}/mark-sold
- Mark product as sold
- Set sold_at timestamp
- Set is_available = false
- Notify interested users (who messaged or made offers)

Include:
- Input validation with Pydantic
- Authorization checks (only owner can modify)
- Error handling for not found, unauthorized
- Rate limiting (50 products per user max)
```

### Prompt 2.2: Dual Feed System

```
Create the dual-feed architecture for Discover and Community feeds.

File: app/api/v1/feeds.py

Endpoints:

GET /api/v1/feeds/discover
Query params:
- page (default 1)
- per_page (default 20)
- category (optional filter)
- sort (options: 'live_first', 'recent', 'popular')
- latitude, longitude (for distance calculation)

Logic:
- Return products where feed_type = 'discover'
- Show LIVE streams first (status = 'live')
- Then recorded videos with streams, sorted by created_at DESC
- Include seller info with verification badges
- Calculate distance from user location
- Include viewer_count for live streams
- Include view_count for recorded videos
- Support infinite scroll pagination

Response format:
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "title": "...",
        "price": 299.0,
        "currency": "AED",
        "video_url": "https://...",
        "thumbnail_url": "https://...",
        "is_live": true,
        "viewer_count": 1234,
        "seller": {
          "id": "uuid",
          "username": "@DubaiMomLife",
          "avatar_url": "https://...",
          "is_verified": true,
          "neighborhood": "Dubai Marina"
        },
        "product_tags": [...],
        "created_at": "2025-10-17T12:00:00Z"
      }
    ],
    "page": 1,
    "per_page": 20,
    "total": 150,
    "has_more": true
  }
}

GET /api/v1/feeds/community
Query params:
- page, per_page
- category (optional)
- neighborhood (filter by specific area)
- latitude, longitude (required for distance)
- radius_km (default 5.0, max 50.0)
- sort (options: 'nearest', 'recent', 'price_low', 'price_high')
- min_price, max_price (optional)
- condition (optional: 'new', 'like_new', 'good', 'fair')

Logic:
- Return products where feed_type = 'community'
- Filter by location using PostGIS ST_DWithin
- Calculate distance using ST_Distance
- Show distance badge ("Same building", "0.2km away", etc.)
- Include seller trust indicators (rating, review count)
- Support grid layout (2 columns on mobile)
- Default sort by nearest

Response includes distance_km and distance_label for each product.

GET /api/v1/feeds/following
- Show products/streams from users that current user follows
- Combine both Discover and Community content
- Sort by created_at DESC
- Requires authentication

Include proper error handling, validation, and caching (Redis) for feed results.
```

### Prompt 2.3: Category System

```
Create category management system with live stream counts.

File: app/api/v1/categories.py

12 Categories (from spec):
1. trading_cards - Trading Card Games
2. mens_fashion - Men's Fashion
3. sneakers - Sneakers & Streetwear
4. sports_cards - Sports Cards
5. collectibles - Collectibles
6. electronics - Electronics
7. home_decor - Home & Decor
8. beauty - Beauty & Cosmetics
9. kids_baby - Kids & Baby
10. furniture - Furniture
11. books - Books & Media
12. other - Other

Endpoints:

GET /api/v1/categories
- Return all 12 categories
- Include counts:
  - total_products (all products in category)
  - live_streams_count (currently live)
  - active_listings_count (available products)
- Include category icons/colors for UI
- Cache results in Redis (5 minute TTL)

Response:
{
  "success": true,
  "data": [
    {
      "slug": "trading_cards",
      "name": "Trading Card Games",
      "icon": "🎴",
      "color": "#9333EA",
      "total_products": 245,
      "live_streams_count": 12,
      "active_listings_count": 180,
      "badge_count": 24  // Live stream count for badge
    },
    ...
  ]
}

GET /api/v1/categories/{category_slug}
- Get single category details
- Include top sellers in category
- Include trending products

GET /api/v1/categories/{category_slug}/streams
- Get all live + recorded streams for category
- Sort: live first, then by views
- Pagination support

GET /api/v1/categories/{category_slug}/products
- Get all products for category
- Support filtering and sorting
- Pagination support

Include category validation in product creation/update endpoints.
```

### Prompt 2.4: Search & Filtering System

```
Create comprehensive search and filtering system (90-point filter system from spec).

File: app/api/v1/search.py

Endpoints:

GET /api/v1/search
Query params:
- q (search query string)
- feed_type ('discover', 'community', 'all')
- category (optional)
- min_price, max_price
- condition (new, like_new, good, fair)
- location_lat, location_lng
- radius_km (default 5.0)
- neighborhood (exact match)
- sort (relevance, recent, price_low, price_high, nearest)
- page, per_page
- filters (JSON object with 90-point filter criteria)

Search Logic:
- Use PostgreSQL full-text search (to_tsvector, to_tsquery)
- Search in: title, description, tags, seller username
- Apply location filter if lat/lng provided
- Apply price range filter
- Apply category filter
- Apply condition filter
- Sort results by relevance score or user-selected sort

Create GIN index on:
```sql
CREATE INDEX idx_products_search ON products 
USING GIN (to_tsvector('english', title || ' ' || description));
```

Response includes:
- Matched products with highlighted search terms
- Facets (category counts, price ranges)
- Suggested searches
- Total results count

GET /api/v1/search/suggestions
- Auto-suggest as user types
- Query param: q (min 2 characters)
- Return top 10 suggestions based on:
  - Product titles
  - Categories
  - Seller usernames
  - Popular searches
- Cache results in Redis

GET /api/v1/search/trending
- Return top 10 trending search queries
- Based on search frequency in last 7 days
- Stored in Redis sorted set
- Update every hour

POST /api/v1/search/track
- Track search query (for trending calculations)
- Increment count in Redis sorted set
- No response needed (fire and forget)

90-Point Filter System:
Categories (12 points):
- Each category is a filter option

Price Ranges (6 points):
- Under AED 100
- AED 100-500
- AED 500-1000
- AED 1000-5000
- AED 5000-10000
- Above AED 10000

Condition (4 points):
- New
- Like New
- Good
- Fair

Distance (5 points):
- Same building (< 0.1km)
- Walking distance (< 0.5km)
- Same neighborhood (< 2km)
- Nearby (< 5km)
- Across Dubai (< 50km)

Seller Type (3 points):
- Verified sellers only
- Power sellers (high rating + many sales)
- Individual sellers

Feed Type (2 points):
- Discover feed (influencer)
- Community feed (local)

Availability (2 points):
- Available now
- Sold (for browsing history)

Product Features (varies by category):
For Electronics:
- Brand
- Year
- Warranty status
- Condition details

For Fashion:
- Size
- Brand
- Color
- Season

For Furniture:
- Material
- Dimensions
- Assembly required

Total: 90+ filter points

Include proper indexing strategy for fast filtering queries.
```

---

## 📋 PHASE 3: Messaging & Offers (Weeks 7-8)

### Prompt 3.1: Messaging System

```
Create real-time messaging system with conversations and offers.

File: app/api/v1/messages.py

Endpoints:

POST /api/v1/conversations
Body:
- other_user_id (UUID)
- product_id (UUID, optional)
- initial_message (optional)

Logic:
- Check if conversation already exists between users for this product
- If exists, return existing conversation
- If not, create new conversation
- Send initial message if provided
- Return conversation with messages

GET /api/v1/conversations
Query params:
- page, per_page
- filter (all, unread, archived)

Logic:
- Get all conversations for current user (as buyer or seller)
- Include unread_count
- Include last_message preview
- Sort by last_message_at DESC
- Support pagination

GET /api/v1/conversations/{conversation_id}
- Get single conversation details
- Include all messages (paginated)
- Include other user info
- Include product info if applicable
- Mark messages as read for current user

POST /api/v1/conversations/{conversation_id}/messages
Body:
- message_type ('text', 'image', 'offer')
- content (for text messages)
- image_urls (for image messages, array)
- offer_data (for offer messages, see schema)

Logic:
- Create message in database
- Emit WebSocket event to other user (real-time delivery)
- Update conversation.last_message_at
- Increment unread_count for recipient
- Send push notification to recipient if offline
- Return created message

GET /api/v1/conversations/{conversation_id}/messages
Query params:
- page, per_page
- before_message_id (cursor pagination)

Logic:
- Get messages for conversation
- Sort by created_at DESC
- Support cursor-based pagination for smooth infinite scroll
- Return messages with sender info

PATCH /api/v1/conversations/{conversation_id}/read
- Mark all messages in conversation as read
- Set is_read = true for unread messages
- Reset unread_count to 0
- Emit read receipt via WebSocket

DELETE /api/v1/conversations/{conversation_id}
- Soft delete: set is_archived = true for current user
- Don't actually delete (other user may still need it)
- Remove from user's conversation list

Include typing indicators (handled via WebSocket, see Phase 3.2).
```

### Prompt 3.2: WebSocket Real-Time Messaging

```
Create WebSocket handlers for real-time messaging features.

File: app/websocket/manager.py

Create Socket.IO server with these event handlers:

CONNECTION EVENTS:

@socketio.on('connect')
- Authenticate user via JWT token
- Add user to online_users set in Redis
- Join user's personal room (for 1-to-1 messaging)
- Emit 'user:online' to user's contacts

@socketio.on('disconnect')
- Remove user from online_users
- Leave all rooms
- Emit 'user:offline' to contacts

CONVERSATION EVENTS:

@socketio.on('conversation:join')
- Join conversation room
- Mark messages as read
- Emit read receipts

@socketio.on('conversation:leave')
- Leave conversation room

MESSAGING EVENTS:

@socketio.on('message:send')
- Validate message
- Save to database
- Emit 'message:new' to recipient
- Update conversation last_message_at
- Send push notification if recipient offline

@socketio.on('typing:start')
- Emit 'typing:active' to other user
- Set Redis key with 5-second expiry

@socketio.on('typing:stop')
- Emit 'typing:inactive' to other user
- Delete Redis key

@socketio.on('message:read')
- Mark message as read
- Emit 'message:read' to sender

CLIENT-BOUND EVENTS (emitted by server):

emit('message:new', data)
- New message received
- Data includes full message object

emit('message:delivered', {message_id})
- Message delivered to recipient

emit('message:read', {message_id, read_at})
- Message read by recipient

emit('typing:active', {user_id, conversation_id})
- Other user started typing

emit('typing:inactive', {user_id, conversation_id})
- Other user stopped typing

emit('user:online', {user_id})
- Contact came online

emit('user:offline', {user_id})
- Contact went offline

emit('offer:new', offer_data)
- New offer received on product

emit('offer:updated', offer_data)
- Offer status changed (accepted/declined/countered)

File: app/websocket/manager.py (Connection Manager)

Create ConnectionManager class:
- Track active WebSocket connections
- Handle user authentication
- Manage rooms for conversations
- Handle broadcasting to rooms
- Handle private messages to specific users
- Store connection metadata in Redis
- Handle reconnection logic

Include:
- Proper error handling
- Connection pooling
- Redis pub/sub for horizontal scaling
- Heartbeat/ping-pong for connection health
```

### Prompt 3.3: Offers & Negotiation System

```
Create offer submission and negotiation system with real-time updates.

File: app/api/v1/offers.py

Endpoints:

POST /api/v1/offers
Body:
- product_id (UUID)
- offered_price (Decimal)
- message (optional, string)

Logic:
- Validate product exists and is available
- Validate offered_price > 0 and < original_price
- Create offer in database with status 'pending'
- Set expires_at to 24 hours from now
- Create message in conversation with offer details
- Emit WebSocket event 'offer:new' to seller
- Send push notification to seller
- Return created offer

PATCH /api/v1/offers/{offer_id}/accept
- Only seller can accept
- Validate offer not expired
- Set status = 'accepted'
- Mark product as sold
- Create transaction record
- Emit 'offer:updated' event
- Notify buyer
- Initiate payment flow

PATCH /api/v1/offers/{offer_id}/decline
- Only seller can decline
- Set status = 'declined'
- Add message to conversation
- Emit 'offer:updated' event
- Notify buyer

PATCH /api/v1/offers/{offer_id}/counter
Body:
- counter_price (Decimal)
- message (optional)

Logic:
- Only seller can counter
- Create new offer or update existing
- Set status = 'countered'
- Store counter_price
- Emit 'offer:updated' event
- Notify buyer
- Reset expiry to 24 hours

GET /api/v1/offers
Query params:
- status (pending, accepted, declined, expired)
- as_buyer (boolean, filter by role)
- page, per_page

Logic:
- Get all offers for current user
- Include product details
- Include other party (buyer/seller) info
- Sort by created_at DESC

GET /api/v1/products/{product_id}/offers
- Get all offers for a specific product
- Only accessible by product owner
- Include buyer info
- Show offer history (counters, etc.)
- Sort by created_at DESC

Background Job (run every hour):
- Find expired offers (expires_at < now() AND status = 'pending')
- Set status = 'expired'
- Notify buyer that offer expired
- Clean up old expired offers (> 30 days)

File: app/websocket/offers.py

Handle real-time offer updates:

@socketio.on('offer:create')
- Create offer
- Emit to seller real-time
- Show in scrolling offers feed on Community videos

@socketio.on('offer:respond')
- Accept/decline/counter offer
- Emit to buyer real-time

Scrolling Offers Feed:
- For Community videos, show real-time offer chips
- Format: "Ali M. AED 450 • 2s ago"
- Auto-scroll as new offers come in
- Store last 20 offers in Redis for quick display
```

---

## 📋 PHASE 4: Live Streaming (Weeks 9-11)

### Prompt 4.1: Video Upload & Processing

```
Create video upload and transcoding system using FFmpeg.

File: app/api/v1/media.py

Endpoints:

POST /api/v1/media/upload-url
Body:
- file_type ('image' or 'video')
- file_count (for multiple images, default 1)
- content_type (mime type)

Logic:
- Validate file_type and count
- Generate presigned upload URL(s) for Backblaze B2
- URL expires in 1 hour
- Return upload URLs with file keys

Response:
{
  "success": true,
  "data": {
    "uploadUrls": [
      {
        "fileKey": "uploads/user_123/video_1697552800.mp4",
        "uploadUrl": "https://s3.us-west-004.backblazeb2.com/...",
        "expiresAt": "2025-10-17T15:30:00Z"
      }
    ]
  }
}

POST /api/v1/media/video/process
Body:
- file_key (from upload-url response)
- file_url (final S3 URL after upload)

Logic:
- Create video processing job
- Extract metadata using FFprobe (duration, resolution, bitrate)
- Generate thumbnail at 1 second mark
- Transcode to HLS format (multiple resolutions: 720p, 1080p)
- Generate DASH manifest
- Upload processed files to B2
- Serve via Cloudflare CDN
- Return job_id for status tracking

Response:
{
  "success": true,
  "data": {
    "jobId": "job_abc123",
    "status": "processing",
    "progress": 0.0
  }
}

GET /api/v1/media/status/{job_id}
- Check video processing status
- Return progress (0.0 to 1.0)
- Return processed URLs when complete

Response (processing):
{
  "success": true,
  "data": {
    "jobId": "job_abc123",
    "status": "processing",
    "progress": 0.65,
    "videoUrl": null,
    "thumbnailUrl": null
  }
}

Response (completed):
{
  "success": true,
  "data": {
    "jobId": "job_abc123",
    "status": "completed",
    "progress": 1.0,
    "videoUrl": "https://video.soukloop.com/videos/video_123.m3u8",
    "thumbnailUrl": "https://cdn.soukloop.com/thumbnails/video_123.jpg",
    "duration": 45,
    "resolutions": ["720p", "1080p"]
  }
}

File: app/services/video_processing.py

Create VideoProcessor class with methods:

async def extract_metadata(video_path: str) -> dict:
- Use FFprobe to get duration, resolution, bitrate, codec
- Return metadata dict

async def generate_thumbnail(video_path: str, timestamp: int = 1) -> str:
- Extract frame at timestamp
- Resize to 1280x720
- Upload to B2
- Return thumbnail URL

async def transcode_to_hls(video_path: str, output_dir: str) -> str:
- Transcode to H.264 + AAC
- Generate HLS playlist (.m3u8)
- Create segments (6 second duration)
- Create multiple resolutions (adaptive bitrate)
- Upload to B2
- Return HLS URL

async def transcode_to_dash(video_path: str, output_dir: str) -> str:
- Similar to HLS but DASH format
- Generate MPD manifest
- Upload to B2
- Return DASH URL

FFmpeg commands:
# Extract thumbnail
ffmpeg -i input.mp4 -ss 00:00:01 -vframes 1 -vf scale=1280:720 thumbnail.jpg

# HLS transcode (720p)
ffmpeg -i input.mp4 -vf scale=1280:720 -c:v libx264 -b:v 2500k -c:a aac -b:a 128k \
  -hls_time 6 -hls_list_size 0 -hls_segment_filename "segment_%03d.ts" \
  output_720p.m3u8

# HLS transcode (1080p)
ffmpeg -i input.mp4 -vf scale=1920:1080 -c:v libx264 -b:v 5000k -c:a aac -b:a 192k \
  -hls_time 6 -hls_list_size 0 -hls_segment_filename "segment_%03d.ts" \
  output_1080p.m3u8

Use async task queue (Celery or similar) for video processing.
Store job status in Redis for progress tracking.
```

### Prompt 4.2: Live Streaming Infrastructure

```
Create live streaming system with RTMP ingest and HLS playback, supporting the complete 5-step Go Live flow:
1. Camera Setup
2. Product Selection
3. Stream Settings
4. Pre-Live Checklist
5. Countdown → Broadcaster

File: app/api/v1/streams.py

Endpoints:

POST /api/v1/streams (ENHANCED VERSION)
Body:
- title (string, max 150 chars)
- description (string, max 500 chars, optional)
- category (enum)
- audience (enum: 'everyone', 'followers', 'neighborhood', default 'everyone')
- estimated_duration (int, minutes, range 5-240, default 30)
- notify_followers (boolean, default true)
- notify_neighborhood (boolean, default false)
- enable_chat (boolean, default true)
- enable_comments (boolean, default true)
- record_stream (boolean, default true)
- product_ids (array of UUIDs, products to showcase)
- scheduled_at (datetime, optional)

Logic:
- Validate all fields
- Create stream record with status 'scheduled'
- Store audience settings (everyone/followers/neighborhood)
- Store estimated_duration for analytics
- Store notification preferences
- Store stream options (chat, comments, recording)
- Attach selected products to stream (via StreamProduct join table)
- Generate unique stream_key (for later Go Live)
- Return stream details

Response:
{
  "success": true,
  "data": {
    "streamId": "stream_abc123",
    "title": "Flash Sale - Up to 50% Off!",
    "status": "scheduled",
    "audience": "everyone",
    "estimatedDuration": 30,
    "productCount": 2,
    "createdAt": "2025-10-18T14:00:00Z"
  }
}

POST /api/v1/streams/{stream_id}/products
Description: Attach products to a stream (used in Step 2: Product Selection)

Body:
- product_ids (array of UUIDs)

Logic:
- Validate stream exists and user is owner
- Validate all product_ids exist and belong to user
- Attach products to stream (many-to-many via StreamProduct)
- Update stream.product_count
- Return attached products

Response:
{
  "success": true,
  "data": {
    "streamId": "stream_abc123",
    "products": [
      {
        "id": "prod_123",
        "title": "Nike Air Jordan 1",
        "price": 850.0,
        "imageUrl": "https://..."
      }
    ],
    "totalCount": 2
  }
}

PATCH /api/v1/streams/{stream_id}/settings
Description: Update stream settings (used in Step 3: Stream Settings)

Body:
- title (string, optional)
- description (string, optional)
- audience (enum, optional)
- estimated_duration (int, optional)
- notify_followers (boolean, optional)
- notify_neighborhood (boolean, optional)
- enable_chat (boolean, optional)
- enable_comments (boolean, optional)
- record_stream (boolean, optional)

Logic:
- Validate stream exists and user is owner
- Validate stream status is 'scheduled' (cannot update live streams)
- Update stream settings
- Return updated stream

Response:
{
  "success": true,
  "data": {
    "streamId": "stream_abc123",
    "title": "Updated Title",
    "settings": {
      "audience": "followers",
      "estimatedDuration": 45,
      "notifyFollowers": true,
      "notifyNeighborhood": true,
      "enableChat": true,
      "enableComments": false,
      "recordStream": true
    },
    "updatedAt": "2025-10-18T14:05:00Z"
  }
}

POST /api/v1/streams/{stream_id}/go-live (ENHANCED VERSION)
Description: Start live streaming (used in Step 5: After Countdown)

Body:
- camera_ready (boolean, required)
- checklist_complete (boolean, required)

Logic:
- Validate stream exists and user is owner
- Validate stream status is 'scheduled'
- Validate stream has at least 1 product attached
- Generate RTMP ingest URL and stream key
- Update status to 'live'
- Set started_at timestamp
- Initialize viewer_count = 0
- Setup HLS endpoint for playback
- Send notifications based on audience setting:
  * If audience = 'everyone': Notify all followers
  * If audience = 'followers': Notify followers only
  * If audience = 'neighborhood': Notify users in same neighborhood (within 2km)
- Apply notification preferences:
  * Only send if notify_followers = true OR notify_neighborhood = true
- Emit 'stream:started' WebSocket event
- Return RTMP credentials + HLS URL

Response:
{
  "success": true,
  "data": {
    "streamId": "stream_abc123",
    "status": "live",
    "rtmpUrl": "rtmp://live.soukloop.com/live",
    "streamKey": "sk_abc123xyz...",
    "hlsUrl": "https://video.soukloop.com/live/stream_abc123/index.m3u8",
    "dashUrl": "https://video.soukloop.com/live/stream_abc123/manifest.mpd",
    "startedAt": "2025-10-18T14:10:00Z",
    "notificationsSent": 1247
  }
}

POST /api/v1/streams/{stream_id}/end (ENHANCED VERSION)
Description: End live stream (used in Broadcaster screen "End Stream" button)

Logic:
- Validate user is stream owner
- Update status to 'ended'
- Set ended_at timestamp
- Calculate duration_seconds (ended_at - started_at)
- Generate stream statistics:
  * Peak viewer count (track during stream)
  * Total unique viewers
  * Average watch time
  * Total likes/reactions
  * Chat messages count
  * Products tagged count
  * Clicks on products
- Convert live recording to VOD if record_stream = true
- Generate final HLS URLs for VOD playback
- Update viewer_count to total_views
- Emit 'stream:ended' event to all viewers
- Return comprehensive stream stats

Response:
{
  "success": true,
  "data": {
    "streamId": "stream_abc123",
    "status": "ended",
    "duration": 1847,
    "stats": {
      "peakViewers": 1234,
      "uniqueViewers": 5678,
      "totalLikes": 892,
      "chatMessages": 456,
      "averageWatchTime": 342,
      "productsTagged": 3,
      "clicksOnProducts": 127
    },
    "vodUrl": "https://video.soukloop.com/vods/stream_abc123.m3u8",
    "endedAt": "2025-10-18T14:40:47Z"
  }
}

GET /api/v1/streams/{stream_id}/analytics
Description: Get detailed stream analytics (for post-stream review)

Logic:
- Validate stream exists
- Return comprehensive analytics:
  * Viewer metrics (peak, unique, average watch time)
  * Engagement metrics (likes, reactions breakdown, chat messages, new followers)
  * Product performance (clicks, views, inquiries, purchases per product)
  * Revenue generated (total sales, gross revenue, platform fee, net revenue)
  * Geographic distribution (top neighborhoods)
  * Viewer retention graph data

Response:
{
  "success": true,
  "data": {
    "streamId": "stream_abc123",
    "basicStats": {
      "duration": 1847,
      "peakViewers": 1234,
      "uniqueViewers": 5678,
      "averageWatchTime": 342
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
      "newFollowers": 67
    },
    "products": [
      {
        "productId": "prod_123",
        "title": "Nike Air Jordan 1",
        "clicks": 89,
        "views": 1200,
        "inquiries": 12,
        "purchases": 3,
        "revenue": 2550.0
      }
    ],
    "revenue": {
      "totalSales": 3,
      "grossRevenue": 2550.0,
      "platformFee": 382.5,
      "netRevenue": 2167.5
    },
    "geography": {
      "topNeighborhoods": [
        {"name": "Dubai Marina", "count": 456},
        {"name": "JBR", "count": 234}
      ]
    }
  }
}

GET /api/v1/streams/{stream_id}
- Get stream details
- Include seller info
- Include viewer_count (if live)
- Include tagged products
- Return HLS URL for playback

GET /api/v1/streams/{stream_id}/viewers
- Get current viewers list (if live)
- Include viewer avatars and usernames
- Return count

PATCH /api/v1/streams/{stream_id}/viewer-join
- Increment viewer_count
- Add user to viewers list in Redis
- Emit 'viewer:joined' event
- Track view for analytics

PATCH /api/v1/streams/{stream_id}/viewer-leave
- Decrement viewer_count
- Remove user from viewers list
- Emit 'viewer:left' event

POST /api/v1/streams/{stream_id}/products/{product_id}/tag
Body:
- x (float, 0-1, normalized x coordinate)
- y (float, 0-1, normalized y coordinate)
- timestamp_seconds (when product appears in video)

Logic:
- Create product tag on stream
- Store coordinates
- Tag becomes clickable on video overlay
- Return tag details

GET /api/v1/streams/{stream_id}/products
- Get all tagged products for stream
- Include product details
- Include tag positions
- Return sorted by timestamp

Database Model Updates:

Update Stream model (app/models/stream.py) to add these fields:

audience: Mapped[str] = mapped_column(
    String(20),
    default='everyone',
    nullable=False
)  # 'everyone', 'followers', 'neighborhood'

estimated_duration: Mapped[int | None] = mapped_column(Integer)  # minutes

notify_followers: Mapped[bool] = mapped_column(Boolean, default=True)
notify_neighborhood: Mapped[bool] = mapped_column(Boolean, default=False)

enable_chat: Mapped[bool] = mapped_column(Boolean, default=True)
enable_comments: Mapped[bool] = mapped_column(Boolean, default=True)
record_stream: Mapped[bool] = mapped_column(Boolean, default=True)

vod_url: Mapped[str | None] = mapped_column(String(1024))  # Video-on-demand URL

# Analytics fields
peak_viewers: Mapped[int] = mapped_column(Integer, default=0)
unique_viewers: Mapped[int] = mapped_column(Integer, default=0)
total_likes: Mapped[int] = mapped_column(Integer, default=0)
chat_messages_count: Mapped[int] = mapped_column(Integer, default=0)
average_watch_time: Mapped[int | None] = mapped_column(Integer)  # seconds

Create new StreamProduct model (app/models/stream_product.py):

class StreamProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stream_products"

    stream_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("streams.id", ondelete="CASCADE"),
        nullable=False
    )
    product_id: Mapped[UUIDType] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )

    # Product tag position (if tagged during stream)
    x_position: Mapped[float | None] = mapped_column(Float)  # 0-1 normalized
    y_position: Mapped[float | None] = mapped_column(Float)  # 0-1 normalized
    timestamp_seconds: Mapped[int | None] = mapped_column(Integer)  # When tagged

    # Analytics for this product in stream
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    inquiries: Mapped[int] = mapped_column(Integer, default=0)
    purchases: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    stream: Mapped["Stream"] = relationship("Stream", back_populates="stream_products")
    product: Mapped["Product"] = relationship("Product")

    __table_args__ = (
        Index("ix_stream_products_stream", "stream_id"),
        Index("ix_stream_products_product", "product_id"),
    )

Pydantic Schema Updates:

Update StreamCreate schema (app/schemas/stream.py):

class StreamCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None, max_length=500)
    category: str
    audience: Literal['everyone', 'followers', 'neighborhood'] = 'everyone'
    estimated_duration: int = Field(30, ge=5, le=240)  # 5 min to 4 hours
    notify_followers: bool = True
    notify_neighborhood: bool = False
    enable_chat: bool = True
    enable_comments: bool = True
    record_stream: bool = True
    product_ids: list[str] = []  # UUIDs of products to showcase
    scheduled_at: datetime | None = None

Add GoLiveRequest schema:

class GoLiveRequest(BaseModel):
    camera_ready: bool = Field(..., description="Camera setup complete")
    checklist_complete: bool = Field(..., description="Pre-live checklist verified")

Update GoLiveResponse schema:

class GoLiveResponse(BaseModel):
    stream_id: str
    status: str
    rtmp_url: str
    stream_key: str
    hls_url: str
    dash_url: str | None = None
    started_at: datetime
    notifications_sent: int  # Number of users notified

Notification Logic:

Create send_stream_notifications function (app/services/notification_service.py):

async def send_stream_notifications(
    stream: Stream,
    user: User,
    db: AsyncSession
) -> int:
    """
    Send notifications based on stream audience setting
    Returns count of notifications sent
    """
    notification_count = 0

    if stream.notify_followers:
        if stream.audience == 'everyone':
            # Notify all followers
            followers = await get_user_followers(user.id, db)
            notification_count += await notify_users(
                user_ids=[f.id for f in followers],
                notification_type='stream_started',
                title=f'{user.username} is live!',
                body=stream.title,
                data={
                    'streamId': str(stream.id),
                    'hlsUrl': stream.hls_url,
                    'sellerName': user.full_name
                }
            )

        elif stream.audience == 'followers':
            # Notify followers only
            followers = await get_user_followers(user.id, db)
            notification_count += await notify_users(
                user_ids=[f.id for f in followers],
                notification_type='stream_started',
                title=f'{user.username} is live!',
                body=f'Followers-only stream: {stream.title}',
                data={'streamId': str(stream.id)}
            )

    if stream.notify_neighborhood and stream.audience in ['everyone', 'neighborhood']:
        # Notify users in same neighborhood
        neighbors = await get_users_in_neighborhood(
            user.location,
            user.neighborhood,
            radius_km=2.0,
            db
        )
        notification_count += await notify_users(
            user_ids=[n.id for n in neighbors],
            notification_type='stream_started',
            title=f'Live nearby: {user.neighborhood}',
            body=stream.title,
            data={'streamId': str(stream.id)}
        )

    return notification_count

Live Streaming Architecture:

1. RTMP Ingest Server:
- Use Nginx with RTMP module OR
- Use AWS MediaLive OR
- Use self-hosted OBS Server
- Accept RTMP stream from mobile app
- Transcode to HLS/DASH in real-time

2. HLS/DASH Delivery:
- Store HLS segments in B2
- Serve via Cloudflare CDN
- Low latency: 3-6 second delay
- Adaptive bitrate streaming

3. Viewer Management:
- Track viewers in Redis set
- Update viewer_count every 10 seconds
- Broadcast count via WebSocket
- Remove stale viewers (timeout 60 seconds)

nginx.conf example for RTMP:
```
rtmp {
    server {
        listen 1935;
        application live {
            live on;
            hls on;
            hls_path /tmp/hls;
            hls_fragment 6s;
            hls_playlist_length 60s;

            # Validate stream key
            on_publish http://api.soukloop.com/api/v1/streams/validate-key;
        }
    }
}
```

File: app/websocket/streams.py

Handle real-time stream events:

@socketio.on('stream:join')
- Join stream room
- Increment viewer count
- Emit viewer joined to other viewers

@socketio.on('stream:leave')
- Leave stream room
- Decrement viewer count

@socketio.on('stream:prepare')
- Sent by frontend during countdown
- Data: {"streamId": "stream_abc123"}
- Response: Prepare RTMP connection, warm up CDN

emit('stream:ready', {
    "streamId": "stream_abc123",
    "rtmpUrl": "rtmp://...",
    "estimatedLatency": 3
})
- Emitted when stream is ready to accept RTMP connection

emit('stream:notification_sent', {
    "streamId": "stream_abc123",
    "count": 1247,
    "audience": "everyone"
})
- Emitted when notifications are sent to followers

emit('stream:first_viewer', {
    "streamId": "stream_abc123",
    "viewerId": "user_456",
    "username": "@john_doe"
})
- Emitted when first viewer joins

emit('stream:viewer-count', {stream_id, count})
- Broadcast viewer count every 10 seconds

emit('stream:ended', {stream_id})
- Notify all viewers that stream ended

Frontend Flow → Backend Endpoint Mapping:

| Frontend Step | Backend Endpoint | Purpose |
|--------------|------------------|---------|
| 1. Camera Setup | - | No backend call (camera is local) |
| 2. Product Selection | POST /api/v1/streams | Create stream + attach products |
| 2. Product Selection | POST /api/v1/streams/{id}/products | Attach more products |
| 3. Stream Settings | PATCH /api/v1/streams/{id}/settings | Update settings |
| 4. Pre-Live Checklist | - | No backend call (validation is local) |
| 5. Countdown | WS: stream:prepare | Warm up RTMP/CDN |
| 5. Go Live | POST /api/v1/streams/{id}/go-live | Start broadcasting |
| Broadcaster | POST /api/v1/streams/{id}/products/{pid}/tag | Tag products |
| Broadcaster | WS: stream:join/leave | Track viewers |
| Broadcaster | POST /api/v1/streams/{id}/end | End stream |
| Post-Stream | GET /api/v1/streams/{id}/analytics | View stats |
```

### Prompt 4.3: Live Chat & Reactions

```
Create live chat and reactions system for streams.

File: app/api/v1/streams.py (add to existing)

Endpoints:

POST /api/v1/streams/{stream_id}/chat
Body:
- message (string, max 200 chars)

Logic:
- Validate user is authenticated
- Rate limit: max 10 messages per minute
- Create chat message
- Store in Redis (last 100 messages only)
- Emit 'chat:new-message' via WebSocket
- Return message

GET /api/v1/streams/{stream_id}/chat
Query params:
- limit (default 50, max 100)
- before_id (cursor pagination)

Logic:
- Get recent chat messages from Redis
- If not enough, fallback to database
- Include user info (username, avatar, badges)
- Return messages sorted by created_at DESC

POST /api/v1/streams/{stream_id}/reactions
Body:
- emoji (string, one of: ❤️ 🔥 👏 😂 😮 💎)

Logic:
- Track reaction in Redis
- Increment reaction count for emoji
- Emit 'reaction:new' via WebSocket
- Reaction floats up on screen (handled by frontend)
- Auto-expire after 5 seconds

GET /api/v1/streams/{stream_id}/reactions
- Get reaction counts for current stream
- Return object with emoji counts

File: app/websocket/streams.py (add to existing)

@socketio.on('chat:send')
- Validate message
- Save to Redis
- Broadcast to all viewers in stream room
- Rate limit per user

emit('chat:new-message', data)
Data:
{
  "messageId": "msg_123",
  "userId": "user_456",
  "username": "@john",
  "avatarUrl": "https://...",
  "message": "This looks amazing!",
  "badges": ["verified", "power_buyer"],
  "timestamp": "2025-10-17T14:30:00Z"
}

@socketio.on('reaction:send')
- Validate emoji
- Broadcast to all viewers
- Create floating animation

emit('reaction:new', data)
Data:
{
  "userId": "user_456",
  "emoji": "❤️",
  "x": 0.5,  // Spawn position (random)
  "y": 0.8
}

Chat Features:
- Display username + avatar
- Show verification badge if user is verified
- Show "power_buyer" or "top_seller" badges
- Auto-scroll to latest message
- Tap username to open profile
- Report/block abusive users
- Moderator controls for seller (mute, ban)
```

---

## 📋 PHASE 5: Transactions & Payments (Weeks 12-13)

### Prompt 5.1: Stripe Integration

```
Create Stripe payment integration with Stripe Connect for seller payouts.

File: app/services/payment_service.py

Create PaymentService class:

async def create_stripe_customer(user: User) -> str:
- Create Stripe customer
- Store customer_id in user record
- Return customer_id

async def create_connect_account(user: User) -> str:
- Create Stripe Connect Express account for seller
- Generate onboarding link
- Store account_id in user record
- Return onboarding_url

async def create_payment_intent(
    amount: Decimal,
    currency: str,
    customer_id: str,
    product_id: str,
    seller_account_id: str
) -> dict:
- Calculate platform fee
- Create Stripe PaymentIntent
- Set up transfer to seller's Connect account
- Store payment intent ID
- Return client_secret for frontend

async def calculate_platform_fee(
    amount: Decimal,
    feed_type: str
) -> Decimal:
- If feed_type == 'discover': 15% fee, min AED 5.0
- If feed_type == 'community': 5% fee, min AED 2.0
- Return fee amount

async def capture_payment(payment_intent_id: str) -> dict:
- Capture the payment
- Transfer funds to seller (minus platform fee)
- Update transaction status
- Return payment details

async def create_refund(payment_intent_id: str, reason: str) -> dict:
- Create refund
- Reverse transfer to seller
- Update transaction status
- Return refund details

async def create_payout(seller_account_id: str, amount: Decimal) -> dict:
- Create payout to seller's bank account
- Track payout status
- Return payout details

File: app/api/v1/transactions.py

Endpoints:

POST /api/v1/transactions
Body:
- product_id (UUID)
- payment_method_id (from Stripe.js)
- offer_id (UUID, optional - if buying via accepted offer)

Logic:
- Validate product available
- Get product price (or offer price if offer_id provided)
- Calculate platform fee
- Create Stripe payment intent
- Create transaction record with status 'pending'
- Return client_secret for payment confirmation

Response:
{
  "success": true,
  "data": {
    "transactionId": "txn_123",
    "clientSecret": "pi_xxx_secret_yyy",
    "amount": 299.0,
    "platformFee": 44.85,
    "sellerPayout": 254.15,
    "currency": "AED"
  }
}

POST /api/v1/transactions/{transaction_id}/confirm
- Confirm payment completed on client
- Capture payment
- Mark product as sold
- Update transaction status to 'completed'
- Create payout to seller
- Send notifications to buyer and seller
- Return transaction details

GET /api/v1/transactions
Query params:
- as_buyer (boolean)
- as_seller (boolean)
- status (pending, completed, failed, refunded)
- page, per_page

Logic:
- Get transactions for current user
- Filter by role and status
- Include product details
- Include other party info
- Sort by created_at DESC

GET /api/v1/transactions/{transaction_id}
- Get single transaction details
- Include full breakdown (amount, fees, payout)
- Include product info
- Include buyer/seller info
- Include payment method
- Include Stripe receipt URL

POST /api/v1/transactions/{transaction_id}/refund
Body:
- reason (string)

Logic:
- Validate transaction is refundable (within 30 days)
- Create Stripe refund
- Reverse payout to seller
- Update transaction status to 'refunded'
- Send notifications
- Return refund details

GET /api/v1/fees/calculate
Query params:
- amount (Decimal)
- feed_type (discover or community)

Logic:
- Calculate platform fee
- Calculate seller payout
- Return breakdown

Response:
{
  "success": true,
  "data": {
    "amount": 299.0,
    "currency": "AED",
    "platformFee": 44.85,
    "platformFeePercentage": 15.0,
    "sellerPayout": 254.15,
    "breakdown": {
      "subtotal": 299.0,
      "platformFee": -44.85,
      "total": 254.15
    }
  }
}

Webhook Handler:

POST /api/v1/webhooks/stripe
- Verify Stripe signature
- Handle events:
  - payment_intent.succeeded
  - payment_intent.payment_failed
  - transfer.created
  - transfer.failed
  - payout.paid
  - payout.failed
  - account.updated (Connect account status)
- Update transaction records
- Send notifications
- Return 200 OK

Include proper error handling for:
- Payment declined
- Insufficient funds
- Invalid payment method
- Seller account not setup
- Network errors
```

### Prompt 5.2: Payout System

```
Create automated payout system for sellers.

File: app/api/v1/payouts.py

Endpoints:

GET /api/v1/payouts
Query params:
- status (pending, processing, paid, failed)
- start_date, end_date
- page, per_page

Logic:
- Get all payouts for current user (seller)
- Include transaction details
- Show payout amount, date, status
- Calculate total earnings
- Sort by created_at DESC

GET /api/v1/payouts/{payout_id}
- Get single payout details
- Include associated transactions
- Show breakdown of fees
- Include bank account info (last 4 digits)
- Return payout details

GET /api/v1/payouts/balance
- Get current available balance for seller
- Calculate: completed transactions - platform fees - paid out amounts
- Return balance details

Response:
{
  "success": true,
  "data": {
    "availableBalance": 1250.50,
    "pendingBalance": 450.00,
    "totalEarnings": 15780.00,
    "currency": "AED",
    "nextPayoutDate": "2025-10-24T00:00:00Z",
    "payoutSchedule": "weekly"  // or "instant", "monthly"
  }
}

POST /api/v1/payouts/request
- Request instant payout (if enabled)
- Validate available balance > minimum (AED 50)
- Create payout via Stripe
- Charge instant payout fee (2%)
- Update balance
- Return payout details

PATCH /api/v1/payouts/settings
Body:
- payout_schedule (weekly, instant, monthly)
- minimum_payout_amount (AED)

Logic:
- Update seller payout preferences
- Store in user metadata
- Return updated settings

Background Jobs:

Job: process_automatic_payouts (runs daily)
- Find sellers with balance > minimum payout amount
- Create payouts via Stripe
- Update payout records
- Send email notifications
- Handle payout failures

Job: check_payout_status (runs every hour)
- Check status of pending payouts with Stripe
- Update payout records
- Send notifications on completion or failure

File: app/models/payout.py

Create Payout model:
- id (UUID)
- seller_id (foreign key to User)
- amount (Decimal)
- currency
- platform_fee_total (Decimal) - fees from included transactions
- transaction_count (int) - number of transactions in payout
- status (enum: 'pending', 'processing', 'paid', 'failed')
- stripe_payout_id
- stripe_transfer_id
- bank_account_last4
- failure_reason (text, nullable)
- paid_at (nullable)
- created_at, updated_at

Include proper error handling and retry logic for failed payouts.
```

---

## 📋 PHASE 6: Verification & Trust (Weeks 14-15)

### Prompt 6.1: Verification System

```
Create Emirates ID and Trade License verification system.

File: app/api/v1/verification.py

Endpoints:

POST /api/v1/verification/submit
Body:
- verification_type ('emirates_id', 'trade_license', or 'both')
- emirates_id_number (string, optional)
- emirates_id_front_image (file, optional)
- emirates_id_back_image (file, optional)
- trade_license_number (string, optional)
- trade_license_document (file, optional)

Logic:
- Validate user not already verified
- Upload documents to B2 (encrypted)
- Store verification request with status 'pending'
- Encrypt Emirates ID number before storing
- Send notification to admin for review
- Return verification request details

Response:
{
  "success": true,
  "data": {
    "verificationId": "ver_123",
    "status": "pending",
    "estimatedReviewTime": "24 hours",
    "submittedAt": "2025-10-17T14:00:00Z"
  }
}

GET /api/v1/verification/status
- Get current user's verification status
- Return verification details without sensitive data

Response:
{
  "success": true,
  "data": {
    "isVerified": false,
    "status": "pending",
    "verificationType": "emirates_id",
    "submittedAt": "2025-10-17T14:00:00Z",
    "reviewedAt": null,
    "rejectionReason": null
  }
}

GET /api/v1/verification/{user_id}
- Get verification card for any user (public endpoint)
- Return Airbnb-style verification card data
- Hide sensitive information

Response:
{
  "success": true,
  "data": {
    "userId": "user_123",
    "name": "Ahmed Hassan",
    "avatarUrl": "https://...",
    "verifiedSince": "2024-06-15T00:00:00Z",
    "isVerified": true,
    "verificationType": "both",
    "trustMessage": "Verified seller since June 2024",
    "details": {
      "completedTransactions": 47,
      "rating": 4.8,
      "reviewCount": 32,
      "badges": ["power_seller", "top_rated", "quick_responder"],
      "neighborhood": "Dubai Marina",
      "joinedDate": "2024-01-10T00:00:00Z"
    }
  }
}

POST /api/v1/verification/submit-business
Body:
- business_name (string)
- trade_license_number (string)
- trade_license_document (file)
- business_location (lat, lng)

Logic:
- Upload trade license to B2
- Create business verification request
- Verify with Dubai Economy Department API (if integrated)
- Return verification request details

Admin Endpoints (require admin role):

GET /api/v1/verification/pending
- Get all pending verification requests
- Include user info and documents
- Sort by submitted_at
- Pagination support

PATCH /api/v1/verification/{verification_id}/approve
- Approve verification request
- Set user.is_verified = true
- Add verification badge
- Send notification to user
- Return updated verification

PATCH /api/v1/verification/{verification_id}/reject
Body:
- reason (string)

Logic:
- Reject verification request
- Store rejection reason
- Send notification to user
- Allow user to resubmit

File: app/utils/encryption.py

Create encryption utilities:
- encrypt_emirates_id(id_number: str) -> str
- decrypt_emirates_id(encrypted: str) -> str
- Use Fernet symmetric encryption with SECRET_KEY

Verification Badges:
- verified (green checkmark) - Emirates ID verified
- business_verified (blue checkmark) - Trade license verified
- power_seller (⭐) - High rating + many sales
- top_rated (🏆) - Rating > 4.7
- quick_responder (⚡) - Responds within 1 hour average
```

### Prompt 6.2: Reviews & Ratings System

```
Create review and rating system for products and sellers.

File: app/api/v1/reviews.py

Endpoints:

POST /api/v1/reviews
Body:
- transaction_id (UUID)
- product_id (UUID)
- seller_id (UUID)
- rating (int, 1-5)
- review_text (string, max 500 chars, optional)
- review_type ('product' or 'seller')

Logic:
- Validate user completed transaction
- Validate user hasn't already reviewed
- Create review
- Update seller average rating
- Update product rating (if product review)
- Send notification to seller
- Return created review

Response:
{
  "success": true,
  "data": {
    "reviewId": "rev_123",
    "rating": 5,
    "reviewText": "Great quality and fast delivery!",
    "createdAt": "2025-10-17T15:00:00Z"
  }
}

GET /api/v1/reviews
Query params:
- user_id (get reviews for specific seller)
- product_id (get reviews for specific product)
- rating (filter by rating)
- sort (recent, highest, lowest)
- page, per_page

Logic:
- Get reviews with filters
- Include reviewer info (name, avatar, verified badge)
- Include helpful count (upvotes)
- Sort by criteria
- Return paginated reviews

GET /api/v1/reviews/{review_id}
- Get single review details
- Include full reviewer info
- Include seller response (if any)
- Return review details

PATCH /api/v1/reviews/{review_id}
Body:
- rating (int, optional)
- review_text (string, optional)

Logic:
- Validate user is review author
- Update review (only within 7 days of creation)
- Recalculate seller rating
- Return updated review

DELETE /api/v1/reviews/{review_id}
- Soft delete review
- Only by author or admin
- Recalculate seller rating
- Return success

POST /api/v1/reviews/{review_id}/response
Body:
- response_text (string, max 300 chars)

Logic:
- Only seller can respond to their reviews
- Create seller response
- Send notification to reviewer
- Return response details

POST /api/v1/reviews/{review_id}/helpful
- Mark review as helpful
- Increment helpful_count
- Track user who marked (prevent duplicates)
- Return updated count

GET /api/v1/users/{user_id}/rating-summary
- Get rating breakdown for seller
- Show count by star (5 stars, 4 stars, etc.)
- Calculate average rating
- Return summary

Response:
{
  "success": true,
  "data": {
    "averageRating": 4.7,
    "totalReviews": 128,
    "ratingBreakdown": {
      "5": 89,
      "4": 28,
      "3": 7,
      "2": 3,
      "1": 1
    },
    "recentReviews": [...]  // Last 3 reviews
  }
}

File: app/models/review.py

Create Review model:
- id (UUID)
- transaction_id (foreign key, unique)
- product_id (foreign key, nullable)
- seller_id (foreign key)
- reviewer_id (foreign key to User)
- review_type (enum: 'product', 'seller')
- rating (int, 1-5)
- review_text (text, nullable)
- seller_response (text, nullable)
- helpful_count (int, default 0)
- is_verified_purchase (boolean, always true)
- created_at, updated_at
- responded_at (nullable)

Add trigger to update user.rating when review created/updated/deleted.
```

### Prompt 6.3: Report & Block System

```
Create reporting and blocking system for safety.

File: app/api/v1/moderation.py

Endpoints:

POST /api/v1/products/{product_id}/report
Body:
- reason (enum: 'prohibited_item', 'fake_product', 'offensive_content', 'scam', 'other')
- description (string, optional)
- evidence_urls (array of image URLs, optional)

Logic:
- Create product report
- Increment report_count on product
- If report_count > 3, auto-hide product
- Send to moderation queue
- Notify admin
- Return report details

POST /api/v1/users/{user_id}/report
Body:
- reason (enum: 'harassment', 'spam', 'fake_account', 'fraud', 'inappropriate_behavior', 'other')
- description (string, optional)
- evidence_urls (array, optional)
- related_conversation_id (UUID, optional)

Logic:
- Create user report
- Increment report_count on user
- If report_count > 5, auto-suspend user
- Send to moderation queue
- Notify admin
- Return report details

POST /api/v1/users/{user_id}/block
- Block user (cannot message, view products, interact)
- Add to blocked_users list
- Remove from followers if following
- Return success

DELETE /api/v1/users/{user_id}/block
- Unblock user
- Remove from blocked_users list
- Return success

GET /api/v1/users/blocked
- Get list of blocked users
- Include user info
- Sort by blocked_at DESC
- Return blocked users list

Admin Endpoints:

GET /api/v1/moderation/reports
Query params:
- type ('product', 'user')
- status ('pending', 'reviewed', 'resolved')
- page, per_page

Logic:
- Get all reports for review
- Include reporter info
- Include reported item/user details
- Sort by priority (report_count DESC, created_at DESC)
- Return paginated reports

GET /api/v1/moderation/reports/{report_id}
- Get single report details
- Include full evidence
- Include history of actions taken
- Return report details

PATCH /api/v1/moderation/reports/{report_id}/resolve
Body:
- action (enum: 'remove_content', 'suspend_user', 'warn_user', 'no_action')
- admin_notes (string, optional)

Logic:
- Take action based on action type
- If remove_content: delete/hide product
- If suspend_user: set user.is_active = false
- If warn_user: send warning notification
- Update report status to 'resolved'
- Log admin action
- Return resolution details

POST /api/v1/moderation/users/{user_id}/suspend
Body:
- reason (string)
- duration_days (int, optional, null for permanent)

Logic:
- Suspend user account
- Hide all active products
- Cancel ongoing transactions
- Send notification
- Return suspension details

POST /api/v1/moderation/users/{user_id}/unsuspend
- Reactivate user account
- Restore products
- Send notification
- Return success

File: app/models/report.py

Create Report model:
- id (UUID)
- reporter_id (foreign key to User)
- reported_user_id (foreign key to User, nullable)
- reported_product_id (foreign key to Product, nullable)
- report_type (enum: 'product', 'user')
- reason (enum)
- description (text, nullable)
- evidence_urls (JSON array, nullable)
- status (enum: 'pending', 'under_review', 'resolved', 'dismissed')
- resolved_by (foreign key to User, nullable - admin)
- resolution_action (enum, nullable)
- admin_notes (text, nullable)
- created_at, updated_at
- resolved_at (nullable)

Include moderation dashboard for admins to review reports efficiently.
```

---

## 📋 PHASE 7: Social Features (Weeks 16-17)

### Prompt 7.1: Follow System

```
Create social follow system.

File: app/api/v1/users.py (add to existing user endpoints)

Endpoints:

POST /api/v1/users/{user_id}/follow
- Follow user
- Create follower relationship
- Increment follower_count for followed user
- Increment following_count for current user
- Send notification to followed user
- Return relationship details

DELETE /api/v1/users/{user_id}/follow
- Unfollow user
- Remove follower relationship
- Decrement counts
- Return success

GET /api/v1/users/{user_id}/followers
Query params:
- page, per_page
- search (search by username)

Logic:
- Get list of followers for user
- Include user info (username, avatar, verified badge)
- Show if current user follows each follower (mutual follow indicator)
- Sort by followed_at DESC
- Return paginated followers

GET /api/v1/users/{user_id}/following
Query params:
- page, per_page
- search

Logic:
- Get list of users that user is following
- Include user info
- Show if they follow back (mutual follow indicator)
- Sort by followed_at DESC
- Return paginated following

GET /api/v1/users/{user_id}/relationship
- Check relationship between current user and specified user
- Return whether following, followed_by, blocked, etc.

Response:
{
  "success": true,
  "data": {
    "following": true,
    "followed_by": false,
    "blocked": false,
    "blocked_by": false,
    "can_message": true
  }
}

File: app/models/follow.py

Create Follow model:
- id (UUID)
- follower_id (foreign key to User)
- following_id (foreign key to User)
- created_at
- Unique constraint on (follower_id, following_id)

Add to User model:
- follower_count (int, default 0)
- following_count (int, default 0)

Update counts with database triggers or in application logic.
```

### Prompt 7.2: Notification System

```
Create push notification system with Firebase Cloud Messaging.

File: app/api/v1/notifications.py

Endpoints:

GET /api/v1/notifications
Query params:
- unread_only (boolean, default false)
- type (optional filter by notification type)
- page, per_page

Logic:
- Get notifications for current user
- Include notification data (product, user, etc.)
- Mark as read when fetched (optional behavior)
- Sort by created_at DESC
- Return paginated notifications

GET /api/v1/notifications/unread-count
- Get count of unread notifications
- Return count

PATCH /api/v1/notifications/{notification_id}/read
- Mark notification as read
- Return success

PATCH /api/v1/notifications/read-all
- Mark all notifications as read
- Return success

DELETE /api/v1/notifications/{notification_id}
- Delete notification
- Return success

POST /api/v1/notifications/register-device
Body:
- fcm_token (string)
- platform (enum: 'ios', 'android')
- device_id (string)

Logic:
- Store FCM token for user
- Associate with device
- Replace old token if device_id exists
- Return success

DELETE /api/v1/notifications/unregister-device
Body:
- device_id (string)

Logic:
- Remove FCM token
- Return success

GET /api/v1/notifications/settings
- Get notification preferences
- Return settings

PATCH /api/v1/notifications/settings
Body:
- push_enabled (boolean)
- email_enabled (boolean)
- notification_types (object with boolean for each type)

Logic:
- Update user notification preferences
- Return updated settings

Notification Types:
- new_follower - Someone followed you
- new_message - New message received
- new_offer - New offer on your product
- offer_accepted - Your offer was accepted
- offer_declined - Your offer was declined
- product_sold - Your product sold
- transaction_completed - Transaction completed
- review_received - Someone reviewed you
- stream_started - Someone you follow went live
- price_drop - Product on wishlist had price drop
- verification_approved - Verification approved
- verification_rejected - Verification rejected

File: app/services/notification_service.py

Create NotificationService class:

async def send_notification(
    user_id: str,
    notification_type: str,
    title: str,
    body: str,
    data: dict = None
) -> bool:
- Get user's FCM tokens
- Check notification preferences
- Create notification record in database
- Send push notification via FCM
- Send email if email_enabled
- Return success status

async def send_push(fcm_tokens: list, title: str, body: str, data: dict) -> bool:
- Use Firebase Admin SDK
- Send to multiple tokens
- Handle invalid tokens
- Return success status

async def send_bulk_notification(
    user_ids: list,
    notification_type: str,
    title: str,
    body: str,
    data: dict = None
) -> dict:
- Send to multiple users
- Batch FCM requests
- Return success/failure counts

File: app/models/notification.py

Create Notification model:
- id (UUID)
- user_id (foreign key)
- notification_type (enum)
- title (string)
- body (string)
- data (JSON, optional - extra data)
- is_read (boolean, default false)
- read_at (nullable)
- created_at

Create DeviceToken model:
- id (UUID)
- user_id (foreign key)
- fcm_token (string)
- platform (enum: 'ios', 'android')
- device_id (string, unique)
- created_at, updated_at

Notification Triggers:
- Trigger notifications on key events across the app
- Use event-driven architecture or direct calls
- Queue notifications for batch processing
```

### Prompt 7.3: Activity Feed

```
Create user activity feed showing recent actions.

File: app/api/v1/activity.py

Endpoints:

GET /api/v1/activity
Query params:
- page, per_page

Logic:
- Get activities for users that current user follows
- Include different activity types:
  - User went live
  - User posted new product
  - User sold a product
  - User received 5-star review
  - User achieved milestone (100 sales, etc.)
- Sort by created_at DESC
- Return paginated activities

GET /api/v1/activity/me
Query params:
- page, per_page

Logic:
- Get current user's own activity history
- Include all actions:
  - Products listed
  - Products sold
  - Reviews received
  - New followers
  - Milestones achieved
- Sort by created_at DESC
- Return paginated activities

File: app/models/activity.py

Create Activity model:
- id (UUID)
- user_id (foreign key)
- activity_type (enum: 'went_live', 'new_product', 'product_sold', 'review_received', 'milestone', 'new_follower')
- related_product_id (nullable)
- related_stream_id (nullable)
- related_user_id (nullable)
- metadata (JSON - additional data)
- created_at

Create activities automatically when events occur:
- When user goes live: create 'went_live' activity
- When product created: create 'new_product' activity
- When product sold: create 'product_sold' activity
- When review received: create 'review_received' activity
- When milestone hit: create 'milestone' activity

Cache activity feed in Redis for performance.
```

---

## 📋 PHASE 8: Advanced Features (Weeks 18-20)

### Prompt 8.1: Elasticsearch Integration

```
Integrate Elasticsearch for advanced search capabilities.

File: app/services/elasticsearch_service.py

Create ElasticsearchService class:

async def index_product(product: Product) -> bool:
- Index product in Elasticsearch
- Include all searchable fields
- Include geospatial data
- Return success status

async def update_product(product_id: str, fields: dict) -> bool:
- Update product document
- Return success status

async def delete_product(product_id: str) -> bool:
- Remove product from index
- Return success status

async def search(
    query: str,
    filters: dict = None,
    location: tuple = None,
    radius_km: float = None,
    page: int = 1,
    per_page: int = 20
) -> dict:
- Perform advanced search with:
  - Full-text search with fuzzy matching
  - Geospatial filtering
  - Multiple filter criteria
  - Faceted search (category counts, price ranges)
  - Autocomplete suggestions
- Return results with scores and facets

Index Mapping:
```json
{
  "mappings": {
    "properties": {
      "id": {"type": "keyword"},
      "title": {
        "type": "text",
        "analyzer": "standard",
        "fields": {
          "keyword": {"type": "keyword"},
          "autocomplete": {
            "type": "text",
            "analyzer": "autocomplete"
          }
        }
      },
      "description": {"type": "text"},
      "price": {"type": "float"},
      "category": {"type": "keyword"},
      "condition": {"type": "keyword"},
      "feed_type": {"type": "keyword"},
      "location": {"type": "geo_point"},
      "neighborhood": {"type": "keyword"},
      "tags": {"type": "keyword"},
      "seller": {
        "properties": {
          "id": {"type": "keyword"},
          "username": {"type": "text"},
          "is_verified": {"type": "boolean"}
        }
      },
      "is_available": {"type": "boolean"},
      "view_count": {"type": "integer"},
      "created_at": {"type": "date"}
    }
  }
}
```

Autocomplete Analyzer:
```json
{
  "analysis": {
    "analyzer": {
      "autocomplete": {
        "tokenizer": "autocomplete_tokenizer",
        "filter": ["lowercase"]
      }
    },
    "tokenizer": {
      "autocomplete_tokenizer": {
        "type": "edge_ngram",
        "min_gram": 2,
        "max_gram": 10,
        "token_chars": ["letter", "digit"]
      }
    }
  }
}
```

Background Job:
- Sync products from PostgreSQL to Elasticsearch
- Run hourly or on-demand
- Handle bulk indexing
- Update statistics

Use Elasticsearch for:
- Fast autocomplete
- Typo-tolerant search
- Relevance ranking
- Faceted navigation
- Geospatial queries at scale
```

### Prompt 8.2: Analytics Dashboard

```
Create analytics system for users and admin.

File: app/api/v1/analytics.py

Endpoints:

GET /api/v1/analytics/seller/overview
Query params:
- start_date, end_date (date range)

Logic:
- Calculate seller metrics:
  - Total sales
  - Total revenue
  - Average order value
  - Conversion rate
  - Product views
  - Stream views
  - Follower growth
  - Top products
  - Best selling categories
- Return analytics data

Response:
{
  "success": true,
  "data": {
    "period": {"startDate": "...", "endDate": "..."},
    "sales": {
      "totalOrders": 47,
      "totalRevenue": 14250.00,
      "averageOrderValue": 303.19,
      "platformFees": 2137.50
    },
    "traffic": {
      "productViews": 3450,
      "profileViews": 892,
      "streamViews": 12400
    },
    "engagement": {
      "messagesReceived": 234,
      "offersReceived": 67,
      "newFollowers": 45,
      "averageRating": 4.8
    },
    "topProducts": [...],
    "topCategories": [...]
  }
}

GET /api/v1/analytics/product/{product_id}
- Get analytics for specific product
- Include:
  - Total views
  - Unique viewers
  - Conversion rate
  - Messages received
  - Offers received
  - Price history
  - View sources (discover feed, community, search, profile)
- Return product analytics

GET /api/v1/analytics/stream/{stream_id}
- Get analytics for specific stream
- Include:
  - Peak concurrent viewers
  - Total unique viewers
  - Average watch time
  - Chat messages count
  - Reactions count
  - Products tagged
  - Sales from stream
  - Revenue from stream
- Return stream analytics

Admin Endpoints:

GET /api/v1/analytics/admin/overview
- Platform-wide metrics:
  - Total users (buyers, sellers, both)
  - Total products listed
  - Total transactions
  - Total GMV (Gross Merchandise Value)
  - Platform revenue
  - Active users (DAU, MAU)
  - Top sellers
  - Top categories
  - Growth trends
- Return admin analytics

GET /api/v1/analytics/admin/cohorts
- User cohort analysis
- Retention rates
- Churn analysis
- Return cohort data

File: app/services/analytics_service.py

Create AnalyticsService class:

async def track_event(
    user_id: str,
    event_type: str,
    event_data: dict
) -> None:
- Track user event
- Store in analytics database or time-series DB
- Queue for processing

async def calculate_seller_metrics(
    seller_id: str,
    start_date: date,
    end_date: date
) -> dict:
- Query transactions, products, streams
- Calculate metrics
- Cache results
- Return metrics

async def calculate_conversion_rate(
    seller_id: str,
    start_date: date,
    end_date: date
) -> float:
- Calculate: sales / (product views + stream views)
- Return rate

Events to track:
- product_viewed
- product_liked
- product_shared
- search_performed
- stream_viewed
- message_sent
- offer_made
- purchase_completed

Store events in time-series format for efficient querying.
Use Redis for real-time counters and aggregations.
```

### Prompt 8.3: Admin Moderation Tools

```
Create comprehensive admin dashboard and moderation tools.

File: app/api/v1/admin.py (require admin role on all endpoints)

Endpoints:

GET /api/v1/admin/dashboard
- Get admin dashboard metrics
- Include:
  - Pending verifications count
  - Pending reports count
  - Active users online
  - Live streams count
  - Recent transactions
  - Platform health metrics
- Return dashboard data

GET /api/v1/admin/users
Query params:
- search (username, email, phone)
- status (active, suspended, deleted)
- role (buyer, seller, both)
- verified (boolean)
- sort (joined, last_active, transactions)
- page, per_page

Logic:
- Get all users with filters
- Include user stats
- Support advanced search
- Return paginated users

GET /api/v1/admin/users/{user_id}
- Get detailed user info
- Include:
  - Full profile
  - Verification status
  - Transaction history
  - Products listed
  - Reports filed
  - Reports against user
  - Login history
  - Device information
- Return user details

PATCH /api/v1/admin/users/{user_id}
- Update any user field
- Admin override
- Log action
- Return updated user

GET /api/v1/admin/products
Query params:
- status (active, sold, removed)
- reported (boolean)
- feed_type
- search
- page, per_page

Logic:
- Get all products with filters
- Include seller info
- Include report count
- Support bulk actions
- Return paginated products

DELETE /api/v1/admin/products/{product_id}
Body:
- reason (string)

Logic:
- Remove product (hard delete or soft delete)
- Notify seller
- Log action
- Return success

GET /api/v1/admin/transactions
Query params:
- status
- min_amount, max_amount
- start_date, end_date
- search (by buyer/seller name)
- page, per_page

Logic:
- Get all transactions
- Include full details
- Support refunds
- Return paginated transactions

POST /api/v1/admin/transactions/{transaction_id}/refund
Body:
- reason (string)
- refund_amount (optional, default full refund)

Logic:
- Process refund
- Update transaction status
- Notify buyer and seller
- Log action
- Return refund details

GET /api/v1/admin/streams
Query params:
- status (live, ended, scheduled)
- search
- start_date, end_date
- page, per_page

Logic:
- Get all streams
- Include analytics
- Support filtering
- Return paginated streams

POST /api/v1/admin/streams/{stream_id}/end
Body:
- reason (string)

Logic:
- Force end stream
- Notify streamer
- Log action
- Return success

GET /api/v1/admin/logs
Query params:
- action_type (user_suspended, product_removed, etc.)
- admin_user_id
- start_date, end_date
- page, per_page

Logic:
- Get admin action logs
- Include details of what was changed
- Support filtering
- Return paginated logs

File: app/models/admin_log.py

Create AdminLog model:
- id (UUID)
- admin_user_id (foreign key)
- action_type (enum)
- target_type (enum: 'user', 'product', 'stream', 'transaction')
- target_id (UUID)
- old_values (JSON)
- new_values (JSON)
- reason (text)
- ip_address
- created_at

Log all admin actions for audit trail.
```

---

## 🔧 Additional Utilities

### Prompt: Geospatial Utilities

```
Create geospatial utility functions using PostGIS.

File: app/utils/geospatial.py

Functions needed:

def calculate_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float
) -> float:
- Calculate distance in kilometers using Haversine formula
- Return distance

def get_distance_label(distance_km: float) -> str:
- Return human-readable distance label
- Examples:
  - < 0.1 km: "Same building"
  - < 0.5 km: "Walking distance"
  - < 2 km: "Same neighborhood"
  - < 5 km: "Nearby"
  - >= 5 km: "X.X km away"
- Return label string

def point_from_lat_lng(lat: float, lng: float) -> str:
- Create PostGIS POINT geometry from lat/lng
- Return WKT format: "POINT(lng lat)"

async def get_products_within_radius(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_km: float,
    filters: dict = None
) -> List[Product]:
- Query products within radius using PostGIS ST_DWithin
- Apply additional filters
- Order by distance
- Return products with distance

SQL example:
```sql
SELECT 
  *,
  ST_Distance(location, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) / 1000 as distance_km
FROM products
WHERE ST_DWithin(
  location::geography,
  ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
  :radius_m
)
AND is_available = true
ORDER BY distance_km ASC;
```

def validate_coordinates(lat: float, lng: float) -> bool:
- Validate latitude: -90 to 90
- Validate longitude: -180 to 180
- Return boolean

Dubai neighborhoods mapping:
- Map lat/lng to neighborhood names
- Use reverse geocoding or predefined polygons
- Return neighborhood name
```

---

## 🧪 Testing Suite

### Prompt: API Tests

```
Create comprehensive test suite for Souk Loop API.

File: tests/conftest.py

Setup test fixtures:
- Database fixture with test database
- Authenticated client fixture
- Sample user fixtures (buyer, seller, admin)
- Sample product fixtures
- Sample stream fixtures
- Mock Stripe API calls
- Mock Twilio SMS
- Mock FCM notifications

File: tests/test_auth.py

Test authentication endpoints:
- test_register_success
- test_register_duplicate_email
- test_register_invalid_email
- test_login_success
- test_login_invalid_credentials
- test_send_otp_email
- test_send_otp_sms
- test_verify_otp_success
- test_verify_otp_invalid
- test_refresh_token
- test_forgot_password
- test_reset_password

File: tests/test_products.py

Test product endpoints:
- test_create_product
- test_create_product_without_auth
- test_get_product
- test_update_product
- test_delete_product
- test_list_products_with_filters
- test_search_products
- test_mark_product_sold

File: tests/test_feeds.py

Test feed endpoints:
- test_discover_feed
- test_community_feed
- test_feed_with_location_filter
- test_feed_pagination

File: tests/test_messaging.py

Test messaging endpoints:
- test_create_conversation
- test_send_message
- test_get_conversations
- test_get_messages
- test_mark_as_read

File: tests/test_offers.py

Test offer endpoints:
- test_create_offer
- test_accept_offer
- test_decline_offer
- test_counter_offer
- test_expired_offer

File: tests/test_transactions.py

Test transaction endpoints:
- test_create_transaction
- test_confirm_payment
- test_refund_transaction
- test_fee_calculation

File: tests/test_verification.py

Test verification endpoints:
- test_submit_verification
- test_get_verification_status
- test_get_verification_card
- test_approve_verification (admin)
- test_reject_verification (admin)

Use pytest with async support:
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_register_success():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "Test123!",
            "phone": "+971501234567",
            "full_name": "Test User",
            "role": "both"
        })
        assert response.status_code == 200
        assert response.json()["success"] is True
```

Run tests:
```bash
pytest tests/ -v --cov=app --cov-report=html
```
```

---

## 📝 Final Documentation

### Prompt: API Documentation

```
Generate comprehensive API documentation.

File: docs/API_DOCUMENTATION.md

Structure:
1. Introduction
2. Authentication
3. Rate Limits
4. Error Handling
5. Endpoints by Feature
6. Data Models
7. WebSocket Events
8. Webhooks
9. Code Examples
10. Best Practices

For each endpoint, include:
- HTTP method and path
- Authentication required (yes/no)
- Request parameters
- Request body schema
- Response schema
- Example requests (cURL, Python, JavaScript)
- Example responses (success and error)
- Rate limits
- Notes and tips

Example format:

## Create Product

**Endpoint:** `POST /api/v1/products`  
**Authentication:** Required  
**Rate Limit:** 50 requests/hour

### Request Body

```json
{
  "title": "iPhone 15 Pro - Like New",
  "description": "Barely used, includes box and accessories",
  "price": 3500.00,
  "category": "electronics",
  "condition": "like_new",
  "feed_type": "community",
  "location": {
    "latitude": 25.0808,
    "longitude": 55.1398,
    "neighborhood": "Dubai Marina",
    "building_name": "Marina Heights Tower"
  },
  "image_urls": ["https://...", "https://..."],
  "tags": ["urgent_sale", "moving_sale"]
}
```

### Response (Success)

```json
{
  "success": true,
  "data": {
    "id": "prod_123abc",
    "title": "iPhone 15 Pro - Like New",
    "price": 3500.00,
    "platformFee": 175.00,
    "created_at": "2025-10-17T14:00:00Z",
    ...
  }
}
```

### cURL Example

```bash
curl -X POST https://api.soukloop.com/api/v1/products \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "iPhone 15 Pro - Like New", ...}'
```

Generate OpenAPI/Swagger documentation automatically from FastAPI.
```

---

## 🚀 Deployment

### Prompt: Docker & Deployment

```
Create production-ready Docker configuration and deployment scripts.

File: Dockerfile

Create multi-stage Dockerfile:
- Stage 1: Build dependencies
- Stage 2: Production image
- Use Python 3.11-slim
- Install FFmpeg
- Copy application code
- Set up non-root user
- Expose port 8000

File: docker-compose.yml

Create docker-compose for development:
- PostgreSQL with PostGIS
- Redis
- FastAPI app
- Nginx (optional)
- Elasticsearch (optional)

File: docker-compose.prod.yml

Create docker-compose for production:
- Use environment variables
- Production-ready PostgreSQL
- Redis with persistence
- Multiple app workers
- Health checks
- Resource limits

File: scripts/deploy.sh

Create deployment script:
- Build Docker image
- Push to registry
- Pull on server
- Run database migrations
- Rolling restart
- Health check
- Rollback on failure

File: scripts/backup.sh

Create backup script:
- Backup PostgreSQL database
- Backup uploaded files
- Upload to S3
- Retention policy (30 days)

File: .github/workflows/ci-cd.yml

Create GitHub Actions workflow:
- Run tests on PR
- Build Docker image
- Deploy to staging on merge to develop
- Deploy to production on merge to main
- Run database migrations
- Send deployment notifications

Include instructions for deploying to:
- AWS EC2/ECS
- DigitalOcean Droplet/App Platform
- Google Cloud Run
- Railway.app
- Fly.io

Setup monitoring with:
- Application logs to CloudWatch/Datadog
- Error tracking with Sentry
- Uptime monitoring with UptimeRobot
- APM with New Relic or Datadog
```

---

This completes all the prompts for building the Souk Loop backend! Each prompt is designed to be self-contained and can be given to your IDE to generate the code for that specific component.

The prompts follow the implementation roadmap from the backend spec and include all necessary details for building a production-ready API.
