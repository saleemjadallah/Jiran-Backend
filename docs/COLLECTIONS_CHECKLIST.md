# Directus Collections Checklist

## Progress Tracker

Use this checklist to track your collection creation progress.

---

## Core Collections (Priority)

### ☐ 1. Categories
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 13 total
**Seed Data**: 12 categories
**Estimated Time**: 30 minutes

**Quick Check**:
- [ ] Collection created with "category" icon
- [ ] All 13 fields added
- [ ] 12 categories seeded with colors
- [ ] Tested API: `GET /items/categories`

---

### ☐ 2. Platform Fees
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 6 total
**Seed Data**: 8 fee configurations
**Estimated Time**: 15 minutes

**Quick Check**:
- [ ] Collection created with "payments" icon
- [ ] All 6 fields added
- [ ] 8 fee tiers seeded (4 discover + 4 community)
- [ ] Tested API: `GET /items/platform_fees`

---

### ☐ 3. User Verification
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 13 total
**Relationships**: 2 (directus_users)
**Estimated Time**: 25 minutes

**Quick Check**:
- [ ] Collection created with "verified_user" icon
- [ ] All 13 fields added
- [ ] Relationship to directus_users configured
- [ ] File upload fields working
- [ ] Tested API: `GET /items/user_verification`

---

### ☐ 4. Products (Most Important)
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 27 total
**Relationships**: 2 (users, categories)
**Estimated Time**: 45 minutes

**Quick Check**:
- [ ] Collection created with "inventory" icon
- [ ] Basic info fields (4) added
- [ ] Category & type fields (3) added
- [ ] Pricing fields (3) added
- [ ] Product detail fields (6) added
- [ ] Location fields (2) added
- [ ] Delivery fields (2) added
- [ ] Metrics fields (3) added
- [ ] Status & fee fields (4) added
- [ ] Relationships configured
- [ ] Tested API: `GET /items/products`

---

### ☐ 5. Live Streams
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 20 total
**Relationships**: 1 (directus_users)
**Estimated Time**: 35 minutes

**Quick Check**:
- [ ] Collection created with "videocam" icon
- [ ] All 20 fields added
- [ ] seller_id relationship configured
- [ ] Stream type dropdown configured
- [ ] Feed type dropdown configured
- [ ] Tested API: `GET /items/live_streams`

---

## Secondary Collections

### ☐ 6. Product Tags
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 7 total
**Relationships**: 2 (products, live_streams)
**Estimated Time**: 20 minutes

**Purpose**: Link products to live stream timestamps

---

### ☐ 7. Transactions
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 19 total
**Relationships**: 4 (buyer, seller, product, stream)
**Estimated Time**: 40 minutes

**Purpose**: Purchase transaction records

---

### ☐ 8. Offers
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 9 total
**Relationships**: 3 (product, buyer, seller)
**Estimated Time**: 20 minutes

**Purpose**: Community feed peer-to-peer offers

---

## Communication Collections

### ☐ 9. Conversations
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 10 total
**Relationships**: 3 (participant_1, participant_2, product)
**Estimated Time**: 25 minutes

**Purpose**: Message thread containers

---

### ☐ 10. Messages
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 11 total
**Relationships**: 4 (conversation, sender, receiver, product/offer)
**Estimated Time**: 25 minutes

**Purpose**: Individual messages in conversations

---

### ☐ 11. Notifications
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 14 total
**Relationships**: 4 (user, related_user, product, stream)
**Estimated Time**: 30 minutes

**Purpose**: User notification system

---

## Social Collections

### ☐ 12. Reviews
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 12 total
**Relationships**: 4 (transaction, reviewer, reviewed_user, product)
**Estimated Time**: 25 minutes

**Purpose**: Product and seller ratings/reviews

---

### ☐ 13. Follows
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 3 total
**Relationships**: 2 (follower, following)
**Estimated Time**: 10 minutes

**Purpose**: User follow relationships

**Unique Constraint**: follower_id + following_id

---

### ☐ 14. Wishlist
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 3 total
**Relationships**: 2 (user, product)
**Estimated Time**: 10 minutes

**Purpose**: Saved/favorited products

**Unique Constraint**: user_id + product_id

---

## Moderation Collections

### ☐ 15. Reports
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 13 total
**Relationships**: 5 (reporter, product, user, stream, review)
**Estimated Time**: 30 minutes

**Purpose**: Content and user reporting system

---

### ☐ 16. User Blocks
**Status**: Not Started | In Progress | ✅ Complete
**Fields**: 4 total
**Relationships**: 2 (blocker, blocked)
**Estimated Time**: 10 minutes

**Purpose**: User blocking functionality

**Unique Constraint**: blocker_id + blocked_id

---

## Overall Progress

**Total Collections**: 16 (excluding directus_users)
**Completed**: 0
**In Progress**: 0
**Not Started**: 16

**Estimated Total Time**: 4-5 hours

---

## Quick Start Recommendations

### Phase 1: Essential Data (60 minutes)
1. ✅ Categories (30 min) - Needed for product listings
2. ✅ Platform Fees (15 min) - Needed for transactions
3. ✅ User Verification (15 min) - Needed for trust

### Phase 2: Core Features (80 minutes)
4. ✅ Products (45 min) - Main product listings
5. ✅ Live Streams (35 min) - Live shopping feature

### Phase 3: Transactions (60 minutes)
6. ✅ Product Tags (20 min) - Link products to streams
7. ✅ Transactions (40 min) - Purchase records

### Phase 4: Social Features (70 minutes)
8. ✅ Offers (20 min) - Community offers
9. ✅ Reviews (25 min) - Rating system
10. ✅ Follows (10 min) - Social connections
11. ✅ Wishlist (10 min) - Saved items

### Phase 5: Messaging (50 minutes)
12. ✅ Conversations (25 min) - Message threads
13. ✅ Messages (25 min) - Individual messages

### Phase 6: System (40 minutes)
14. ✅ Notifications (30 min) - User alerts
15. ✅ Reports (30 min) - Moderation
16. ✅ User Blocks (10 min) - User blocking

---

## Testing Checklist

After creating each collection:

- [ ] **API Access**: Test GET endpoint
- [ ] **Create Item**: Test POST endpoint
- [ ] **Update Item**: Test PATCH endpoint
- [ ] **Delete Item**: Test DELETE endpoint
- [ ] **Relationships**: Verify related items load correctly
- [ ] **Permissions**: Configure role-based access
- [ ] **Display Template**: Set readable item display
- [ ] **Search**: Test collection search functionality
- [ ] **Filters**: Create common filter presets

---

## API Test Commands

```bash
# Test Categories
curl http://localhost:8055/items/categories

# Test Products (with filter)
curl "http://localhost:8055/items/products?filter[status][_eq]=active"

# Test Live Streams (live only)
curl "http://localhost:8055/items/live_streams?filter[is_live][_eq]=true"

# Test with authentication
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8055/items/products
```

---

## Common Issues & Solutions

### Issue: Can't create relationship field
**Solution**: Ensure target collection exists first

### Issue: Field validation failing
**Solution**: Check required fields are marked correctly

### Issue: Can't see collection in sidebar
**Solution**: Refresh browser or clear cache

### Issue: Permission denied
**Solution**: Check role permissions in Settings → Roles

### Issue: Duplicate key errors
**Solution**: Verify unique constraints are set correctly

---

## Post-Setup Tasks

After all collections are created:

### 1. Configure Permissions
- [ ] Set Public role permissions (read-only for most)
- [ ] Set Administrator role permissions (full access)
- [ ] Create custom roles (Seller, Buyer, Moderator)

### 2. Create Sample Data
- [ ] Add 5-10 sample products
- [ ] Create 2-3 sample live streams
- [ ] Add sample transactions
- [ ] Create test reviews

### 3. API Integration
- [ ] Update FastAPI endpoints to use Directus
- [ ] Test CRUD operations from backend
- [ ] Set up authentication flow
- [ ] Configure webhooks (if needed)

### 4. Documentation
- [ ] Document API endpoints
- [ ] Create collection relationship diagram
- [ ] Write admin user guide
- [ ] Document permission structure

---

## Resources

- **Full Schema**: `backend/docs/DIRECTUS_COLLECTIONS_SCHEMA.md`
- **Setup Guide**: `backend/docs/DIRECTUS_SETUP_GUIDE.md`
- **Admin Dashboard**: `backend/docs/ADMIN_DASHBOARD.md`
- **Directus Docs**: https://docs.directus.io

---

**Last Updated**: October 21, 2025
**Status**: Ready for implementation
**Next Step**: Start with Phase 1 (Categories, Platform Fees, User Verification)
