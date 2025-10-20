# Souk Loop - Database Architecture (Phase 1)

## Overview

PostgreSQL 17 database with PostGIS extension for geospatial queries. Uses Alembic for migrations and SQLAlchemy 2.0 async ORM.

## Technology Stack

- **Database**: PostgreSQL 17 with PostGIS 3.5
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic (async support)
- **Connection Pool**: asyncpg (async PostgreSQL driver)
- **Geospatial**: GeoAlchemy2 (PostGIS integration)

## Phase 1 Core Models (8 Tables)

### 1. Users (`users`)
**Purpose**: Authentication, profiles, and user management

**Key Features**:
- UUID primary key
- Email, username, phone (all unique + indexed)
- Role-based access control (buyer, seller, both, admin)
- PostGIS location with automatic GIST indexing
- Stripe integration (customer_id, connect_account_id)
- Verification status tracking

**Indexes**:
- `ix_users_email` (unique, B-tree)
- `ix_users_username` (unique, B-tree)
- `ix_users_phone` (unique, B-tree)
- `idx_users_location` (GIST, auto-created by GeoAlchemy2)

**Relationships**:
- `products` → Product (1:many, cascade delete)
- `streams` → Stream (1:many, cascade delete)
- `conversations_as_buyer` → Conversation (1:many)
- `conversations_as_seller` → Conversation (1:many)
- `offers_made` → Offer (1:many)
- `offers_received` → Offer (1:many)
- `transactions_bought` → Transaction (1:many)
- `transactions_sold` → Transaction (1:many)
- `verification` → Verification (1:1, cascade delete)

---

### 2. Products (`products`)
**Purpose**: Marketplace product listings

**Key Features**:
- Dual-feed architecture (Discover vs Community)
- 12 standard categories (aligned with Flutter frontend)
- Product condition tracking (new, like_new, good, fair)
- PostGIS location with automatic GIST indexing
- Media support (images JSONB array, video, thumbnail)
- Engagement metrics (views, likes)
- Availability and sold tracking

**Categories** (matching Flutter):
1. Trading Cards (Pokémon, Yu-Gi-Oh!, Magic)
2. Men's Fashion (Streetwear, apparel)
3. Sneakers (Limited editions & exclusives)
4. Sports Cards (NBA, NFL, Soccer, Baseball)
5. Collectibles (Coins, money, rare items)
6. Electronics (Gaming, audio, tech)
7. Home Decor (Furniture, kitchen, home)
8. Beauty (Cosmetics, skincare)
9. Kids & Baby (Toys, clothes, essentials)
10. Furniture (Home furniture)
11. Books (Books, movies, media)
12. Other (Miscellaneous)

**Indexes**:
- `ix_products_seller_id` (B-tree)
- `ix_products_category_feed` (composite B-tree)
- `ix_products_is_available` (B-tree)
- `idx_products_location` (GIST, auto-created by GeoAlchemy2)

**Relationships**:
- `seller` → User (many:1)
- `offers` → Offer (1:many, cascade delete)
- `transactions` → Transaction (1:many, cascade delete)
- `conversations` → Conversation (1:many)

---

### 3. Streams (`streams`)
**Purpose**: Live and recorded video streams

**Key Features**:
- Live shopping stream management
- Status tracking (scheduled, live, ended)
- Category-based classification (matching product categories)
- Engagement metrics (views, likes, comments, shares)
- Scheduled start time for upcoming streams
- Stream metadata (thumbnail, stream URL, recording URL)

**Indexes**:
- `ix_streams_user_id` (B-tree)
- `ix_streams_status` (B-tree)
- `ix_streams_category` (B-tree)

**Relationships**:
- `user` → User (many:1)

---

### 4. Conversations (`conversations`)
**Purpose**: Direct messaging between buyers and sellers

**Key Features**:
- Buyer-seller chat threads
- Optional product context
- Per-user unread counts
- Per-user archive status
- Last message tracking with timestamp
- **Circular dependency resolution** with Message model (see below)

**Indexes**:
- `ix_conversations_buyer_seller` (composite B-tree)
- `ix_conversations_product` (B-tree)

**Relationships**:
- `buyer` → User (many:1)
- `seller` → User (many:1)
- `product` → Product (many:1, optional)
- `messages` → Message (1:many, cascade delete)
- `last_message` → Message (1:1, post_update=True)
- `offers` → Offer (1:many, cascade delete)

**Circular Dependency Fix**:
```python
# In Conversation model
last_message_id: Mapped[UUIDType | None] = mapped_column(
    ForeignKey("messages.id", ondelete="SET NULL", use_alter=True, name="fk_conversations_last_message")
)

last_message: Mapped["Message | None"] = relationship(
    "Message",
    foreign_keys=[last_message_id],
    post_update=True,  # Required for circular dependency
)
```

This resolves the circular dependency where:
- Conversation references Message.last_message_id
- Message references Conversation.conversation_id

---

### 5. Messages (`messages`)
**Purpose**: Individual messages within conversations

**Key Features**:
- Text, image, or offer message types
- Read status and timestamp tracking
- Optional media content (images, videos)
- Optional offer reference

**Indexes**:
- `ix_messages_conversation` (B-tree)
- `ix_messages_sender` (B-tree)

**Relationships**:
- `conversation` → Conversation (many:1)
- `sender` → User (many:1)
- `offer` → Offer (1:1, optional)

---

### 6. Offers (`offers`)
**Purpose**: Peer-to-peer price negotiation (Community feed)

**Key Features**:
- Offer amount and optional message
- Status tracking (pending, accepted, rejected, expired, cancelled)
- Expiration timestamp
- Buyer and seller tracking
- Optional conversation context

**Indexes**:
- `ix_offers_product` (B-tree)
- `ix_offers_conversation` (B-tree)
- `ix_offers_status` (B-tree)

**Relationships**:
- `product` → Product (many:1)
- `buyer` → User (many:1)
- `seller` → User (many:1)
- `conversation` → Conversation (many:1, optional)

---

### 7. Transactions (`transactions`)
**Purpose**: Payment and purchase tracking

**Key Features**:
- Stripe payment integration (payment_intent_id, charge_id)
- Transaction amounts (subtotal, platform fee, seller payout)
- Status tracking (pending, completed, failed, refunded, cancelled)
- Payment and payout timestamps
- Buyer and seller tracking

**Indexes**:
- `ix_transactions_buyer` (B-tree)
- `ix_transactions_seller` (B-tree)
- `ix_transactions_product` (B-tree)
- `ix_transactions_status` (B-tree)

**Relationships**:
- `buyer` → User (many:1)
- `seller` → User (many:1)
- `product` → Product (many:1)

---

### 8. Verifications (`verifications`)
**Purpose**: Identity verification for trust and safety

**Key Features**:
- Verification type (email, phone, government_id, address)
- Status tracking (pending, verified, rejected)
- Verification data (JSONB for flexibility)
- Timestamps for submission and verification
- Optional rejection reason

**Indexes**:
- `ix_verifications_user_id` (B-tree)
- `ix_verifications_status` (B-tree)

**Relationships**:
- `user` → User (1:1)

---

## PostGIS Integration

### Automatic GIST Indexing

GeoAlchemy2 **automatically creates** GIST spatial indexes on `Geometry` columns. These indexes are named `idx_{table}_location`.

**Affected Tables**:
- `users.location` → `idx_users_location` (GIST)
- `products.location` → `idx_products_location` (GIST)

**Important Notes**:
1. Do NOT manually add these indexes to `__table_args__` - causes duplicate index errors
2. Alembic autogenerate will detect these indexes
3. Migration files should comment out duplicate `create_index` statements for location columns
4. Spatial queries use these indexes automatically

**Example Spatial Query**:
```python
from geoalchemy2.functions import ST_Distance, ST_Point

# Find products within 5km of a location
nearby_products = (
    session.query(Product)
    .filter(
        ST_Distance(
            Product.location,
            ST_Point(longitude, latitude, srid=4326)
        ) < 5000  # 5km in meters
    )
    .all()
)
```

---

## Alembic Configuration

### Environment Setup (`alembic/env.py`)

**Key Features**:
1. **PostGIS Table Exclusion**: Filters out tiger/topology schema tables from autogenerate
2. **Async Support**: Uses `async_engine_from_config` for async operations
3. **Transaction Per Migration**: Enabled for better error handling

**PostGIS Table Filter**:
```python
def include_object(object, name, type_, reflected, compare_to):
    """Exclude PostGIS tables from autogenerate."""
    if type_ == "table":
        # Exclude PostGIS tiger and topology tables
        if hasattr(object, "schema") and object.schema in ("tiger", "topology"):
            return False
        # Exclude PostGIS system tables
        postgis_tables = {
            "spatial_ref_sys", "geocode_settings", "geocode_settings_default",
            "layer", "topology", ...
        }
        if name in postgis_tables:
            return False
    return True
```

### Migration Workflow

**Create Migration**:
```bash
docker-compose exec app alembic revision --autogenerate -m "description"
```

**Apply Migration**:
```bash
docker-compose exec app alembic upgrade head
```

**Check Current Version**:
```bash
docker-compose exec app alembic current
```

**Rollback Migration**:
```bash
docker-compose exec app alembic downgrade -1
```

### Migration Best Practices

1. **Always add `geoalchemy2` import** to migration files that create Geometry columns:
   ```python
   import geoalchemy2
   ```

2. **Comment out duplicate location index creation**:
   ```python
   # GeoAlchemy2 creates this automatically
   # op.create_index('idx_users_location', 'users', ['location'], unique=False, postgresql_using='gist')
   ```

3. **Use `use_alter=True` for circular dependencies**:
   ```python
   ForeignKey("messages.id", ondelete="SET NULL", use_alter=True, name="fk_conversations_last_message")
   ```

4. **Test migrations in Docker** before committing:
   ```bash
   docker-compose down -v  # Clean slate
   docker-compose up -d
   docker-compose exec app alembic upgrade head
   ```

---

## Database Indexes Summary

### Automatic Indexes (Created by SQLAlchemy)
- All primary keys (UUID)
- All unique constraints (email, username, phone)
- All foreign keys
- Columns with `index=True` parameter

### Custom Composite Indexes
- `ix_conversations_buyer_seller` (buyer_id, seller_id)
- `ix_products_category_feed` (category, feed_type)

### Spatial Indexes (Auto-created by GeoAlchemy2)
- `idx_users_location` (GIST)
- `idx_products_location` (GIST)

---

## Entity Relationship Diagram (ERD)

```
┌─────────────┐
│    User     │
└──────┬──────┘
       │
       ├──────────> Products (seller_id)
       ├──────────> Streams (user_id)
       ├──────────> Conversations (buyer_id, seller_id)
       ├──────────> Messages (sender_id)
       ├──────────> Offers (buyer_id, seller_id)
       ├──────────> Transactions (buyer_id, seller_id)
       └──────────> Verification (user_id) [1:1]

┌─────────────┐
│   Product   │
└──────┬──────┘
       │
       ├──────────> Offers (product_id)
       ├──────────> Transactions (product_id)
       └──────────> Conversations (product_id) [optional]

┌─────────────────┐
│  Conversation   │ ◄──┐ Circular
└────────┬────────┘    │ Dependency
         │             │ (use_alter=True)
         └──────────> Messages (conversation_id)
                       │
                       └──> last_message_id

┌─────────────┐
│   Offer     │
└──────┬──────┘
       │
       └──────────> Conversation (conversation_id) [optional]
```

---

## Connection Pool Configuration

**File**: `app/database.py`

```python
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,        # Base connections
    max_overflow=10,     # Additional connections
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle after 1 hour
)
```

---

## Next Steps (Phase 2)

### Additional Tables to Implement
1. **Notifications** - Push/in-app notifications
2. **Reviews** - User ratings and reviews
3. **Follows** - Social following relationships
4. **Wishlists** - Saved products
5. **Reports** - Content moderation
6. **Analytics** - Event tracking
7. **Stream Products** - Products tagged in streams
8. **Badges** - User achievement system

### Features to Add
1. Full-text search (PostgreSQL `tsvector`)
2. Read replicas for scaling
3. Database backups and restore procedures
4. Performance monitoring (pg_stat_statements)
5. Connection pooling optimization

---

## Troubleshooting

### Issue: Duplicate Index Error (idx_users_location)
**Cause**: GeoAlchemy2 creates GIST indexes automatically
**Solution**: Remove manual index creation from `__table_args__` and comment out in migration files

### Issue: Circular Dependency (Conversation ↔ Message)
**Cause**: Both tables reference each other
**Solution**: Use `use_alter=True` on one FK and `post_update=True` on relationship

### Issue: PostGIS Tables in Migration
**Cause**: Alembic detects tiger/topology schema tables
**Solution**: Use `include_object` filter in `alembic/env.py`

### Issue: Missing geoalchemy2 Import
**Cause**: Migration file doesn't import geoalchemy2
**Solution**: Add `import geoalchemy2` at top of migration file

---

## Database Schema Version

**Current Version**: `35644ce37583` (Phase 1 Complete)
**Migration**: `initial migration - phase 1 core models`
**Date**: October 2025
**Tables**: 8 core tables with full relationships

---

## Contact & Resources

- **Alembic Docs**: https://alembic.sqlalchemy.org/
- **SQLAlchemy 2.0**: https://docs.sqlalchemy.org/en/20/
- **GeoAlchemy2**: https://geoalchemy-2.readthedocs.io/
- **PostGIS**: https://postgis.net/documentation/

