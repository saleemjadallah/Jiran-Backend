# Directus Collections Schema - Jiran Platform

## Overview
Comprehensive collection schema for Jiran live shopping platform admin dashboard.

**Platform**: Jiran (jiran.app)
**Purpose**: Live shopping marketplace with dual-feed architecture
**Directus Version**: 11.2.2

---

## Collection List

1. **users** - User accounts and profiles
2. **user_verification** - Identity verification data
3. **categories** - Product categories (12 standard)
4. **products** - Product listings
5. **live_streams** - Live and recorded video streams
6. **product_tags** - Products tagged in live streams
7. **transactions** - Purchase transactions
8. **offers** - Peer-to-peer offers (Community feed)
9. **conversations** - Message threads
10. **messages** - Individual messages
11. **notifications** - User notifications
12. **reviews** - Product and seller reviews
13. **follows** - User follow relationships
14. **wishlist** - Saved products
15. **reports** - Content reports
16. **user_blocks** - Blocked users
17. **platform_fees** - Fee configuration by tier

---

## 1. Users Collection

**Collection**: `users`
**Purpose**: Core user accounts (extends Directus users)

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| email | String | Yes | Email address (unique) |
| password | Hash | Yes | Hashed password |
| first_name | String | No | First name |
| last_name | String | No | Last name |
| username | String | Yes | Unique username |
| avatar_url | Image | No | Profile picture |
| phone_number | String | No | Phone number |
| account_type | String | Yes | buyer, seller, both |
| user_tier | String | Yes | free, plus, creator, pro |
| is_verified | Boolean | No | Identity verified (default: false) |
| verified_since | DateTime | No | Verification date |
| neighborhood | String | No | User location |
| coordinates | JSON | No | {lng, lat} |
| bio | Text | No | User bio (500 chars) |
| rating | Decimal | No | Average rating (0-5) |
| total_reviews | Integer | No | Review count |
| follower_count | Integer | No | Follower count |
| following_count | Integer | No | Following count |
| total_sales | Integer | No | Completed sales |
| total_purchases | Integer | No | Completed purchases |
| wallet_balance | Decimal | No | Wallet balance (AED) |
| joined_date | DateTime | Yes | Account creation |
| last_active | DateTime | No | Last activity |
| status | String | Yes | active, suspended, banned |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |

### Indexes
- `email` (unique)
- `username` (unique)
- `account_type`
- `user_tier`
- `is_verified`
- `status`

---

## 2. User Verification Collection

**Collection**: `user_verification`
**Purpose**: Identity verification details

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| user_id | M2O (users) | Yes | Related user |
| verification_type | String | Yes | seller, buyer, both |
| emirates_id | String | No | Emirates ID number (encrypted) |
| trade_license | String | No | Trade license number |
| id_document_front | File | No | ID front image |
| id_document_back | File | No | ID back image |
| selfie_verification | File | No | Selfie with ID |
| verification_status | String | Yes | pending, approved, rejected |
| verified_by | M2O (users) | No | Admin who verified |
| verified_at | DateTime | No | Verification timestamp |
| rejection_reason | Text | No | Reason if rejected |
| badges | JSON | No | Array of achievement badges |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |

### Indexes
- `user_id` (unique)
- `verification_status`

---

## 3. Categories Collection

**Collection**: `categories`
**Purpose**: Product categories (12 standard)

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | Yes | Primary key (1-12) |
| name | String | Yes | Category name (unique) |
| slug | String | Yes | URL-friendly slug |
| description | Text | No | Category description |
| icon_name | String | No | Icon identifier |
| primary_color | String | No | Hex color code |
| secondary_color | String | No | Hex color code |
| image_url | Image | No | Category image |
| viewer_count | Integer | No | Active viewers |
| live_stream_count | Integer | No | Live streams count |
| trending_tags | JSON | No | Array of trending tags |
| sort_order | Integer | Yes | Display order |
| is_active | Boolean | Yes | Active status (default: true) |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |

### Indexes
- `slug` (unique)
- `is_active`
- `sort_order`

### Pre-populated Data (12 Categories)
1. Trading Card Games
2. Men's Fashion
3. Sneakers & Streetwear
4. Sports Cards
5. Coins & Money
6. Books & Movies
7. Women's Fashion
8. Bags & Accessories
9. Baby & Kids
10. Toys & Hobbies
11. Electronics
12. Kitchen

---

## 4. Products Collection

**Collection**: `products`
**Purpose**: Product listings for both feeds

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| seller_id | M2O (users) | Yes | Product owner |
| title | String | Yes | Product title (80 chars) |
| description | Text | Yes | Description (500 chars) |
| category_id | M2O (categories) | Yes | Product category |
| listing_type | String | Yes | photo, video, live, scheduled_live |
| feed_type | String | Yes | discover, community |
| price | Decimal | Yes | Fixed price (AED) |
| is_negotiable | Boolean | No | Allow offers (default: false) |
| condition | String | Yes | brand_new, like_new, good, fair, for_parts |
| brand | String | No | Product brand |
| images | JSON | Yes | Array of image URLs (max 10 for discover, 5 for community) |
| cover_image | String | Yes | Main image URL |
| video_url | String | No | Product video URL |
| video_thumbnail | String | No | Video thumbnail |
| video_duration | Integer | No | Duration in seconds |
| neighborhood | String | Yes | Seller location |
| coordinates | JSON | No | {lng, lat} |
| delivery_options | JSON | Yes | {pickup, delivery, shipping} |
| tags | JSON | No | Array of tags |
| view_count | Integer | No | View count (default: 0) |
| save_count | Integer | No | Wishlist count |
| share_count | Integer | No | Share count |
| status | String | Yes | active, sold, removed, reported |
| is_featured | Boolean | No | Featured listing (default: false) |
| platform_fee_rate | Decimal | Yes | Fee percentage (0.05-0.15) |
| minimum_fee | Decimal | Yes | Min fee (AED 3 or 5) |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |
| sold_at | DateTime | No | Sale timestamp |

### Indexes
- `seller_id`
- `category_id`
- `listing_type`
- `feed_type`
- `status`
- `is_featured`
- `created_at` (DESC)

---

## 5. Live Streams Collection

**Collection**: `live_streams`
**Purpose**: Live and recorded video streams

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| seller_id | M2O (users) | Yes | Stream host |
| title | String | Yes | Stream title |
| description | Text | No | Stream description |
| feed_type | String | Yes | discover, community |
| stream_type | String | Yes | live, recorded, scheduled |
| video_url | String | No | Stream/video URL |
| thumbnail_url | String | Yes | Thumbnail image |
| hls_url | String | No | HLS stream URL |
| rtmp_url | String | No | RTMP ingest URL |
| is_live | Boolean | Yes | Live status (default: false) |
| started_at | DateTime | No | Stream start time |
| ended_at | DateTime | No | Stream end time |
| scheduled_for | DateTime | No | Scheduled start (for scheduled type) |
| duration | Integer | No | Duration in seconds |
| current_viewers | Integer | No | Live viewer count |
| peak_viewers | Integer | No | Max concurrent viewers |
| total_views | Integer | No | Total views |
| like_count | Integer | No | Like count |
| comment_count | Integer | No | Comment count |
| share_count | Integer | No | Share count |
| show_notes | Text | No | Show notes content |
| chat_enabled | Boolean | Yes | Chat enabled (default: true) |
| status | String | Yes | active, ended, scheduled, cancelled |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |

### Indexes
- `seller_id`
- `feed_type`
- `stream_type`
- `is_live`
- `status`
- `scheduled_for`
- `created_at` (DESC)

---

## 6. Product Tags Collection

**Collection**: `product_tags`
**Purpose**: Products tagged in live streams

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| stream_id | M2O (live_streams) | Yes | Related stream |
| product_id | M2O (products) | Yes | Tagged product |
| position_x | Decimal | Yes | X coordinate (0-100%) |
| position_y | Decimal | Yes | Y coordinate (0-100%) |
| timestamp | Integer | No | Video timestamp (seconds) |
| is_active | Boolean | Yes | Active tag (default: true) |
| created_at | DateTime | Yes | Auto-generated |

### Indexes
- `stream_id`
- `product_id`
- `is_active`

---

## 7. Transactions Collection

**Collection**: `transactions`
**Purpose**: Purchase transactions

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| transaction_number | String | Yes | Unique transaction ID |
| buyer_id | M2O (users) | Yes | Buyer |
| seller_id | M2O (users) | Yes | Seller |
| product_id | M2O (products) | Yes | Purchased product |
| stream_id | M2O (live_streams) | No | Related stream (if applicable) |
| feed_type | String | Yes | discover, community |
| amount | Decimal | Yes | Product price (AED) |
| platform_fee | Decimal | Yes | Platform fee amount |
| platform_fee_rate | Decimal | Yes | Fee percentage |
| seller_payout | Decimal | Yes | Amount to seller |
| payment_method | String | Yes | card, wallet, cod |
| payment_status | String | Yes | pending, completed, failed, refunded |
| payment_gateway_id | String | No | External payment ID |
| delivery_method | String | Yes | pickup, delivery, shipping |
| delivery_address | JSON | No | Delivery address object |
| delivery_status | String | No | pending, shipped, delivered |
| tracking_number | String | No | Shipping tracking |
| transaction_status | String | Yes | pending, completed, cancelled, disputed |
| completed_at | DateTime | No | Completion timestamp |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |

### Indexes
- `transaction_number` (unique)
- `buyer_id`
- `seller_id`
- `product_id`
- `payment_status`
- `transaction_status`
- `created_at` (DESC)

---

## 8. Offers Collection

**Collection**: `offers`
**Purpose**: Peer-to-peer offers (Community feed)

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| product_id | M2O (products) | Yes | Product offered on |
| buyer_id | M2O (users) | Yes | Offer sender |
| seller_id | M2O (users) | Yes | Offer recipient |
| offer_amount | Decimal | Yes | Offered price (AED) |
| message | Text | No | Offer message (200 chars) |
| status | String | Yes | pending, accepted, rejected, expired |
| expires_at | DateTime | Yes | Offer expiration (48 hours) |
| responded_at | DateTime | No | Response timestamp |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |

### Indexes
- `product_id`
- `buyer_id`
- `seller_id`
- `status`
- `expires_at`

---

## 9. Conversations Collection

**Collection**: `conversations`
**Purpose**: Message threads between users

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| participant_1_id | M2O (users) | Yes | First user |
| participant_2_id | M2O (users) | Yes | Second user |
| product_id | M2O (products) | No | Related product |
| last_message_at | DateTime | Yes | Last message timestamp |
| last_message_preview | String | No | Preview text (100 chars) |
| unread_count_user_1 | Integer | No | Unread for user 1 |
| unread_count_user_2 | Integer | No | Unread for user 2 |
| is_archived_user_1 | Boolean | No | Archived by user 1 |
| is_archived_user_2 | Boolean | No | Archived by user 2 |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |

### Indexes
- `participant_1_id`
- `participant_2_id`
- `product_id`
- `last_message_at` (DESC)

### Unique Constraint
- `participant_1_id + participant_2_id` (composite unique)

---

## 10. Messages Collection

**Collection**: `messages`
**Purpose**: Individual messages in conversations

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| conversation_id | M2O (conversations) | Yes | Parent conversation |
| sender_id | M2O (users) | Yes | Message sender |
| receiver_id | M2O (users) | Yes | Message recipient |
| message_type | String | Yes | text, image, product, offer |
| content | Text | Yes | Message content |
| image_url | String | No | Image attachment |
| product_id | M2O (products) | No | Shared product |
| offer_id | M2O (offers) | No | Related offer |
| is_read | Boolean | Yes | Read status (default: false) |
| read_at | DateTime | No | Read timestamp |
| created_at | DateTime | Yes | Auto-generated |

### Indexes
- `conversation_id`
- `sender_id`
- `receiver_id`
- `is_read`
- `created_at` (ASC)

---

## 11. Notifications Collection

**Collection**: `notifications`
**Purpose**: User notifications

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| user_id | M2O (users) | Yes | Notification recipient |
| type | String | Yes | Notification type |
| title | String | Yes | Notification title |
| message | Text | Yes | Notification message |
| image_url | String | No | Notification image |
| action_type | String | No | Navigation action type |
| action_data | JSON | No | Action payload |
| related_user_id | M2O (users) | No | Related user |
| related_product_id | M2O (products) | No | Related product |
| related_stream_id | M2O (live_streams) | No | Related stream |
| is_read | Boolean | Yes | Read status (default: false) |
| read_at | DateTime | No | Read timestamp |
| created_at | DateTime | Yes | Auto-generated |

### Notification Types
- new_follower
- new_message
- product_sold
- offer_received
- offer_accepted
- stream_starting
- review_received
- payment_received
- product_reported
- verification_approved

### Indexes
- `user_id`
- `type`
- `is_read`
- `created_at` (DESC)

---

## 12. Reviews Collection

**Collection**: `reviews`
**Purpose**: Product and seller reviews

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| transaction_id | M2O (transactions) | Yes | Related transaction |
| reviewer_id | M2O (users) | Yes | Review author |
| reviewed_user_id | M2O (users) | Yes | Seller being reviewed |
| product_id | M2O (products) | Yes | Reviewed product |
| rating | Integer | Yes | Rating 1-5 stars |
| review_text | Text | No | Review content (500 chars) |
| review_images | JSON | No | Array of image URLs |
| is_anonymous | Boolean | No | Anonymous review (default: false) |
| seller_response | Text | No | Seller's response |
| responded_at | DateTime | No | Response timestamp |
| helpful_count | Integer | No | Helpful votes |
| status | String | Yes | active, reported, removed |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |

### Indexes
- `transaction_id` (unique)
- `reviewer_id`
- `reviewed_user_id`
- `product_id`
- `rating`
- `status`
- `created_at` (DESC)

---

## 13. Follows Collection

**Collection**: `follows`
**Purpose**: User follow relationships

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| follower_id | M2O (users) | Yes | User who follows |
| following_id | M2O (users) | Yes | User being followed |
| created_at | DateTime | Yes | Auto-generated |

### Indexes
- `follower_id`
- `following_id`
- `created_at` (DESC)

### Unique Constraint
- `follower_id + following_id` (composite unique)

---

## 14. Wishlist Collection

**Collection**: `wishlist`
**Purpose**: Saved/favorited products

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| user_id | M2O (users) | Yes | User who saved |
| product_id | M2O (products) | Yes | Saved product |
| created_at | DateTime | Yes | Auto-generated |

### Indexes
- `user_id`
- `product_id`
- `created_at` (DESC)

### Unique Constraint
- `user_id + product_id` (composite unique)

---

## 15. Reports Collection

**Collection**: `reports`
**Purpose**: Content and user reports

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| reporter_id | M2O (users) | Yes | User who reported |
| report_type | String | Yes | product, user, stream, review |
| reported_product_id | M2O (products) | No | Reported product |
| reported_user_id | M2O (users) | No | Reported user |
| reported_stream_id | M2O (live_streams) | No | Reported stream |
| reported_review_id | M2O (reviews) | No | Reported review |
| reason | String | Yes | Report reason |
| description | Text | No | Additional details |
| status | String | Yes | pending, reviewing, resolved, dismissed |
| reviewed_by | M2O (users) | No | Admin reviewer |
| action_taken | String | No | Action description |
| resolved_at | DateTime | No | Resolution timestamp |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |

### Report Reasons
- prohibited_item
- counterfeit
- misleading_description
- inappropriate_content
- suspected_scam
- wrong_category
- harassment
- other

### Indexes
- `reporter_id`
- `report_type`
- `status`
- `created_at` (DESC)

---

## 16. User Blocks Collection

**Collection**: `user_blocks`
**Purpose**: Blocked users

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Primary key |
| blocker_id | M2O (users) | Yes | User who blocked |
| blocked_id | M2O (users) | Yes | User being blocked |
| reason | String | No | Block reason |
| created_at | DateTime | Yes | Auto-generated |

### Indexes
- `blocker_id`
- `blocked_id`
- `created_at` (DESC)

### Unique Constraint
- `blocker_id + blocked_id` (composite unique)

---

## 17. Platform Fees Collection

**Collection**: `platform_fees`
**Purpose**: Fee configuration by tier and feed

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | Yes | Primary key |
| user_tier | String | Yes | free, plus, creator, pro |
| feed_type | String | Yes | discover, community |
| fee_percentage | Decimal | Yes | Fee rate (0.03-0.15) |
| minimum_fee | Decimal | Yes | Min fee (AED) |
| is_active | Boolean | Yes | Active status (default: true) |
| created_at | DateTime | Yes | Auto-generated |
| updated_at | DateTime | Yes | Auto-updated |

### Pre-populated Data

| User Tier | Discover Fee | Community Fee | Min Fee (Discover) | Min Fee (Community) |
|-----------|--------------|---------------|-------------------|---------------------|
| Free | 15% | 5% | AED 5.0 | AED 3.0 |
| Plus | 10% | 3% | AED 5.0 | AED 3.0 |
| Creator | 8% | 3% | AED 5.0 | AED 3.0 |
| Pro | 5% | 3% | AED 5.0 | AED 3.0 |

### Indexes
- `user_tier`
- `feed_type`
- `is_active`

### Unique Constraint
- `user_tier + feed_type` (composite unique)

---

## Relationships Summary

### Users (1:M)
- user → products (seller_id)
- user → live_streams (seller_id)
- user → transactions (buyer_id, seller_id)
- user → offers (buyer_id, seller_id)
- user → messages (sender_id, receiver_id)
- user → notifications (user_id)
- user → reviews (reviewer_id, reviewed_user_id)
- user → follows (follower_id, following_id)
- user → wishlist (user_id)
- user → reports (reporter_id)
- user → user_blocks (blocker_id, blocked_id)

### Products (M:1, 1:M)
- product → user (M:1 seller_id)
- product → category (M:1 category_id)
- product → product_tags (1:M)
- product → transactions (1:M)
- product → offers (1:M)
- product → wishlist (1:M)

### Live Streams (M:1, 1:M)
- stream → user (M:1 seller_id)
- stream → product_tags (1:M)
- stream → transactions (1:M)

### Conversations (M:1, 1:M)
- conversation → users (M:1 participant_1_id, participant_2_id)
- conversation → product (M:1 product_id)
- conversation → messages (1:M)

---

## Next Steps

1. **Fix PostgreSQL Connection** (see DIRECTUS_SETUP_COMPLETE.md)
2. **Access Directus Admin** at http://localhost:8055
3. **Create Collections** using this schema
4. **Configure Permissions** for each collection
5. **Seed Initial Data** (categories, platform fees)
6. **Set up API Endpoints** for FastAPI integration
7. **Test CRUD Operations** via Directus API

---

## API Integration Example

Once collections are created, access via Directus API:

```bash
# Get all products
GET https://admin.jiran.app/items/products

# Create new product
POST https://admin.jiran.app/items/products
{
  "seller_id": "uuid",
  "title": "Product Title",
  "price": 100.00,
  ...
}

# Update product
PATCH https://admin.jiran.app/items/products/{id}

# Delete product
DELETE https://admin.jiran.app/items/products/{id}
```

---

**Created**: October 21, 2025
**Collections**: 17 total
**Estimated Fields**: 250+
**Status**: Ready for implementation
