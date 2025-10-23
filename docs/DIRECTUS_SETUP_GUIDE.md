# Directus Collections Setup Guide - Step by Step

## Prerequisites

1. ✅ Directus running at http://localhost:8055
2. ✅ Admin login: admin@jiran.app / JiranAdmin2025!
3. ✅ PostgreSQL connection fixed

---

## Quick Start: Create Collections via UI

### Step 1: Access Directus Admin

1. Open browser: http://localhost:8055
2. Login with admin credentials
3. Navigate to **Settings** → **Data Model**

---

## Collection 1: Categories

### Create Collection

1. Click **Create Collection**
2. Name: `categories`
3. Icon: Search for "category"
4. Click **Continue**

### Add Fields

Click **Create Field** for each:

#### 1. ID (Primary Key)
- Type: **Integer**
- Field Name: `id`
- Interface: **Input**
- Options:
  - ✓ Primary Key
  - ✓ Auto Increment
- **Save**

#### 2. Name
- Type: **String**
- Field Name: `name`
- Interface: **Input**
- Options:
  - ✓ Required
  - ✓ Unique
- **Save**

#### 3. Slug
- Type: **String**
- Field Name: `slug`
- Interface: **Input**
- Options:
  - ✓ Required
  - ✓ Unique
- **Save**

#### 4. Description
- Type: **Text**
- Field Name: `description`
- Interface: **Textarea**
- **Save**

#### 5. Icon Name
- Type: **String**
- Field Name: `icon_name`
- Interface: **Input**
- **Save**

#### 6. Primary Color
- Type: **String**
- Field Name: `primary_color`
- Interface: **Color**
- **Save**

#### 7. Secondary Color
- Type: **String**
- Field Name: `secondary_color`
- Interface: **Color**
- **Save**

#### 8. Image URL
- Type: **File**
- Field Name: `image_url`
- Interface: **File**
- **Save**

#### 9. Viewer Count
- Type: **Integer**
- Field Name: `viewer_count`
- Interface: **Input**
- Default Value: `0`
- **Save**

#### 10. Live Stream Count
- Type: **Integer**
- Field Name: `live_stream_count`
- Interface: **Input**
- Default Value: `0`
- **Save**

#### 11. Trending Tags
- Type: **JSON**
- Field Name: `trending_tags`
- Interface: **Tags**
- **Save**

#### 12. Sort Order
- Type: **Integer**
- Field Name: `sort_order`
- Interface: **Input**
- ✓ Required
- **Save**

#### 13. Is Active
- Type: **Boolean**
- Field Name: `is_active`
- Interface: **Boolean**
- Default Value: `true`
- **Save**

### Seed Categories Data

Navigate to **Content** → **Categories** → Click **+** to add each:

```
1. Trading Card Games
   - Slug: trading-card-games
   - Primary Color: #C1440E
   - Secondary Color: #E87A3E
   - Sort Order: 1

2. Men's Fashion
   - Slug: mens-fashion
   - Primary Color: #0D9488
   - Secondary Color: #C1440E
   - Sort Order: 2

3. Sneakers & Streetwear
   - Slug: sneakers-streetwear
   - Primary Color: #D4A745
   - Secondary Color: #E87A3E
   - Sort Order: 3

4. Sports Cards
   - Slug: sports-cards
   - Primary Color: #DC2626
   - Secondary Color: #D4A745
   - Sort Order: 4

5. Coins & Money
   - Slug: coins-money
   - Primary Color: #F59E0B
   - Secondary Color: #0D9488
   - Sort Order: 5

6. Books & Movies
   - Slug: books-movies
   - Primary Color: #C1440E
   - Secondary Color: #0D9488
   - Sort Order: 6

7. Women's Fashion
   - Slug: womens-fashion
   - Primary Color: #E87A3E
   - Secondary Color: #D4A745
   - Sort Order: 7

8. Bags & Accessories
   - Slug: bags-accessories
   - Primary Color: #0D9488
   - Secondary Color: #E87A3E
   - Sort Order: 8

9. Baby & Kids
   - Slug: baby-kids
   - Primary Color: #C1440E
   - Secondary Color: #F59E0B
   - Sort Order: 9

10. Toys & Hobbies
    - Slug: toys-hobbies
    - Primary Color: #DC2626
    - Secondary Color: #C1440E
    - Sort Order: 10

11. Electronics
    - Slug: electronics
    - Primary Color: #0D9488
    - Secondary Color: #D4A745
    - Sort Order: 11

12. Kitchen
    - Slug: kitchen
    - Primary Color: #F59E0B
    - Secondary Color: #DC2626
    - Sort Order: 12
```

---

## Collection 2: Platform Fees

### Create Collection

1. Click **Create Collection**
2. Name: `platform_fees`
3. Icon: Search for "payments"
4. Click **Continue**

### Add Fields

#### 1. ID
- Type: **Integer**
- Field Name: `id`
- ✓ Primary Key
- ✓ Auto Increment
- **Save**

#### 2. User Tier
- Type: **String**
- Field Name: `user_tier`
- Interface: **Dropdown**
- ✓ Required
- Choices:
  - `free` - Free
  - `plus` - Plus
  - `creator` - Creator
  - `pro` - Pro
- **Save**

#### 3. Feed Type
- Type: **String**
- Field Name: `feed_type`
- Interface: **Dropdown**
- ✓ Required
- Choices:
  - `discover` - Discover
  - `community` - Community
- **Save**

#### 4. Fee Percentage
- Type: **Decimal**
- Field Name: `fee_percentage`
- Precision: 5
- Scale: 4
- ✓ Required
- **Save**

#### 5. Minimum Fee
- Type: **Decimal**
- Field Name: `minimum_fee`
- Precision: 10
- Scale: 2
- ✓ Required
- **Save**

#### 6. Is Active
- Type: **Boolean**
- Field Name: `is_active`
- Default Value: `true`
- **Save**

### Seed Platform Fees Data

Add these 8 records:

```
1. Free - Discover
   - fee_percentage: 0.1500
   - minimum_fee: 5.00

2. Plus - Discover
   - fee_percentage: 0.1000
   - minimum_fee: 5.00

3. Creator - Discover
   - fee_percentage: 0.0800
   - minimum_fee: 5.00

4. Pro - Discover
   - fee_percentage: 0.0500
   - minimum_fee: 5.00

5. Free - Community
   - fee_percentage: 0.0500
   - minimum_fee: 3.00

6. Plus - Community
   - fee_percentage: 0.0300
   - minimum_fee: 3.00

7. Creator - Community
   - fee_percentage: 0.0300
   - minimum_fee: 3.00

8. Pro - Community
   - fee_percentage: 0.0300
   - minimum_fee: 3.00
```

---

## Collection 3: User Verification

### Create Collection

1. Click **Create Collection**
2. Name: `user_verification`
3. Icon: Search for "verified_user"
4. Click **Continue**

### Add Fields

#### 1. ID
- Type: **UUID**
- Field Name: `id`
- ✓ Primary Key
- **Save**

#### 2. User ID (Relationship)
- Type: **Many to One**
- Field Name: `user_id`
- Related Collection: **directus_users**
- ✓ Required
- **Save**

#### 3. Verification Type
- Type: **String**
- Field Name: `verification_type`
- Interface: **Dropdown**
- ✓ Required
- Choices:
  - `seller` - Seller
  - `buyer` - Buyer
  - `both` - Both
- **Save**

#### 4. Emirates ID
- Type: **String**
- Field Name: `emirates_id`
- Interface: **Input**
- **Save**

#### 5. Trade License
- Type: **String**
- Field Name: `trade_license`
- Interface: **Input**
- **Save**

#### 6. ID Document Front
- Type: **File**
- Field Name: `id_document_front`
- **Save**

#### 7. ID Document Back
- Type: **File**
- Field Name: `id_document_back`
- **Save**

#### 8. Selfie Verification
- Type: **File**
- Field Name: `selfie_verification`
- **Save**

#### 9. Verification Status
- Type: **String**
- Field Name: `verification_status`
- Interface: **Dropdown**
- ✓ Required
- Choices:
  - `pending` - Pending
  - `approved` - Approved
  - `rejected` - Rejected
- Default: `pending`
- **Save**

#### 10. Verified By
- Type: **Many to One**
- Field Name: `verified_by`
- Related Collection: **directus_users**
- **Save**

#### 11. Verified At
- Type: **Timestamp**
- Field Name: `verified_at`
- Interface: **Datetime**
- **Save**

#### 12. Rejection Reason
- Type: **Text**
- Field Name: `rejection_reason`
- Interface: **Textarea**
- **Save**

#### 13. Badges
- Type: **JSON**
- Field Name: `badges`
- Interface: **Tags**
- **Save**

---

## Collection 4: Products (Core Collection)

This is the most important collection. Follow carefully:

### Create Collection

1. Click **Create Collection**
2. Name: `products`
3. Icon: Search for "inventory"
4. Click **Continue**

### Add Fields (25 total)

#### Basic Info

1. **ID** - UUID (Primary Key)
2. **seller_id** - Many to One (directus_users) ✓ Required
3. **title** - String (max 80) ✓ Required
4. **description** - Text (max 500) ✓ Required

#### Category & Type

5. **category_id** - Many to One (categories) ✓ Required
6. **listing_type** - Dropdown ✓ Required
   - Choices: photo, video, live, scheduled_live
7. **feed_type** - Dropdown ✓ Required
   - Choices: discover, community

#### Pricing

8. **price** - Decimal (10, 2) ✓ Required
9. **is_negotiable** - Boolean (default: false)
10. **condition** - Dropdown ✓ Required
    - Choices: brand_new, like_new, good, fair, for_parts

#### Product Details

11. **brand** - String
12. **images** - JSON (array of URLs)
13. **cover_image** - String ✓ Required
14. **video_url** - String
15. **video_thumbnail** - String
16. **video_duration** - Integer

#### Location

17. **neighborhood** - String ✓ Required
18. **coordinates** - JSON ({lng, lat})

#### Delivery

19. **delivery_options** - JSON ({pickup, delivery, shipping})
20. **tags** - JSON (array)

#### Metrics

21. **view_count** - Integer (default: 0)
22. **save_count** - Integer (default: 0)
23. **share_count** - Integer (default: 0)

#### Status & Fees

24. **status** - Dropdown ✓ Required
    - Choices: active, sold, removed, reported
    - Default: active
25. **is_featured** - Boolean (default: false)
26. **platform_fee_rate** - Decimal (5, 4) ✓ Required
27. **minimum_fee** - Decimal (10, 2) ✓ Required

---

## Collection 5: Live Streams

### Key Fields

1. ID (UUID)
2. seller_id (M2O → directus_users)
3. title (String)
4. description (Text)
5. feed_type (discover/community)
6. stream_type (live/recorded/scheduled)
7. video_url (String)
8. thumbnail_url (String)
9. is_live (Boolean)
10. started_at (Timestamp)
11. ended_at (Timestamp)
12. duration (Integer)
13. current_viewers (Integer)
14. peak_viewers (Integer)
15. total_views (Integer)
16. status (active/ended/scheduled/cancelled)

---

## Quick Import Option (Advanced)

If you want to speed up the process, you can use the Directus API to bulk import:

```bash
# From backend directory
cd /Users/saleemjadallah/Desktop/Soukloop/backend

# Install requests if needed
pip install requests

# Run the setup script (when fully implemented)
python scripts/setup_directus_collections.py
```

---

## After Creating Collections

### 1. Configure Permissions

For each collection:
- Go to **Settings** → **Roles & Permissions**
- Click **Public** role
- Set permissions for each collection

**Recommended Public Permissions**:
- **categories**: Read only
- **platform_fees**: Read only
- **products**: Read only (active items)
- **live_streams**: Read only (is_live=true)
- All other collections: No public access

### 2. Set Up Relationships

The UI will show relationship fields automatically once both collections exist.

### 3. Customize Display

For each collection:
- Settings → Data Model → Select collection
- Click **Collection Setup**
- Set display template (e.g., for products: `{{title}} - AED {{price}}`)
- Set preview URL if applicable

### 4. Create Presets & Filters

Set up common filters:
- **Products**: Status = Active
- **Live Streams**: Is Live = True
- **User Verification**: Status = Pending

---

## Testing the API

Once collections are created:

```bash
# Get all categories
curl http://localhost:8055/items/categories

# Get specific category
curl http://localhost:8055/items/categories/1

# Get all active products
curl "http://localhost:8055/items/products?filter[status][_eq]=active"

# Get live streams
curl "http://localhost:8055/items/live_streams?filter[is_live][_eq]=true"
```

---

## Next: Remaining Collections

After Categories, Platform Fees, User Verification, Products, and Live Streams, create:

6. Product Tags (links products to live streams)
7. Transactions (purchase records)
8. Offers (community feed offers)
9. Conversations (message threads)
10. Messages (individual messages)
11. Notifications (user notifications)
12. Reviews (product/seller reviews)
13. Follows (user relationships)
14. Wishlist (saved products)
15. Reports (content moderation)
16. User Blocks (blocked users)

**See**: `DIRECTUS_COLLECTIONS_SCHEMA.md` for complete field definitions.

---

## Troubleshooting

### Collection Creation Fails
- Check PostgreSQL is running: `docker ps | grep postgres`
- Verify Directus connection in logs: `docker logs backend-directus-1`

### Can't See Collections
- Refresh browser (Ctrl+R / Cmd+R)
- Clear browser cache
- Check user permissions

### Relationship Fields Not Working
- Ensure both collections exist first
- Use correct field type (Many to One, One to Many, etc.)
- Verify collection names match exactly

---

## Support

- **Directus Docs**: https://docs.directus.io
- **Schema Reference**: `backend/docs/DIRECTUS_COLLECTIONS_SCHEMA.md`
- **Complete Setup**: `backend/docs/ADMIN_DASHBOARD.md`

---

**Status**: Ready to implement
**Estimated Time**: 2-3 hours for all 17 collections
**Priority Collections**: Categories, Platform Fees, Products, Live Streams
