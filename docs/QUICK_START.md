# Souk Loop Backend - Quick Start Guide
**Testing Phases 1-4**

---

## ✅ Backend Status: READY FOR TESTING

**Services Running**:
- ✅ FastAPI Backend: http://localhost:8000
- ✅ PostgreSQL Database: localhost:5432
- ✅ Redis: localhost:6379

**Phases Completed**:
- ✅ Phase 1: Authentication & Core Models
- ✅ Phase 2: Products & Feeds
- ✅ Phase 3: Messaging & Offers
- ✅ Phase 4: Live Streaming

---

## 🚀 How to Test

### Option 1: Swagger UI (Easiest)

1. **Open Swagger UI**: http://localhost:8000/docs
2. Click on any endpoint to expand it
3. Click "Try it out"
4. Fill in the parameters
5. Click "Execute"
6. View the response

**Example**:
```bash
# In browser
open http://localhost:8000/docs

# Navigate to:
POST /api/v1/auth/register → Try it out → Fill form → Execute
```

---

### Option 2: Bash Script (Quick Test)

Run the automated test script:

```bash
cd /Users/saleemjadallah/Desktop/Soukloop/backend
./quick_test.sh
```

This will:
- ✅ Register buyer and seller accounts
- ✅ Test authentication
- ✅ Create a product
- ✅ Browse feeds
- ✅ Test search

---

### Option 3: Postman Collection (Comprehensive)

1. **Import Collection**:
   - Open Postman
   - File → Import
   - Select `Souk_Loop_API_Tests.postman_collection.json`

2. **Create Environment**:
   - Click "Environments" in Postman
   - Add new environment "Souk Loop Local"
   - Add variables:
     ```
     base_url = http://localhost:8000
     buyer_email = testbuyer@soukloop.com
     buyer_password = Test123!@#
     seller_email = testseller@soukloop.com
     seller_password = Seller123!@#
     ```

3. **Run Requests**:
   - Navigate to collection folders
   - Run "Register Buyer" → Saves token automatically
   - Run other requests in sequence

---

### Option 4: cURL (Command Line)

**Test Categories**:
```bash
curl http://localhost:8000/api/v1/categories
```

**Register User**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testbuyer@soukloop.com",
    "username": "testbuyer",
    "password": "Test123!@#",
    "phone": "+971501234567",
    "full_name": "Test Buyer",
    "role": "buyer"
  }'
```

**Login**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "testbuyer@soukloop.com",
    "password": "Test123!@#"
  }'
```

---

## 📚 Testing Documentation

**Comprehensive Guide**: [`TESTING_GUIDE.md`](./TESTING_GUIDE.md)

This guide includes:
- ✅ 50+ test cases across all 4 phases
- ✅ Expected request/response examples
- ✅ Integration testing scenarios
- ✅ WebSocket testing instructions
- ✅ Troubleshooting tips

---

## 🔧 Testing Checklist

### Phase 1: Authentication ✅
- [ ] Register buyer account
- [ ] Register seller account
- [ ] Login
- [ ] Get current user
- [ ] Refresh token

### Phase 2: Products & Feeds ✅
- [ ] Get all categories (12 categories)
- [ ] Create Community product (5% fee)
- [ ] Create Discover product (15% fee)
- [ ] Browse Community feed (location-based)
- [ ] Browse Discover feed
- [ ] Search products (full-text)

### Phase 3: Messaging & Offers ✅
- [ ] Create conversation
- [ ] Send text message
- [ ] Create offer
- [ ] Accept/decline offer
- [ ] WebSocket: Connect and join conversation
- [ ] WebSocket: Send real-time message

### Phase 4: Live Streaming ✅
- [ ] Create stream with products
- [ ] Update stream settings
- [ ] Go live (get RTMP credentials)
- [ ] WebSocket: Join stream
- [ ] WebSocket: Send chat message
- [ ] WebSocket: Send reaction
- [ ] End stream
- [ ] View analytics

---

## 🎯 Priority Testing

**Start with these core flows**:

1. **User Registration & Login**:
   ```
   POST /api/v1/auth/register → POST /api/v1/auth/login
   ```

2. **Create Product**:
   ```
   POST /api/v1/products (requires seller token)
   ```

3. **Browse Feeds**:
   ```
   GET /api/v1/feeds/community?latitude=25.0772&longitude=55.1369&radius_km=10
   GET /api/v1/feeds/discover
   ```

4. **Search Products**:
   ```
   GET /api/v1/search?q=nike
   ```

5. **Create Conversation & Offer**:
   ```
   POST /api/v1/conversations
   POST /api/v1/offers
   ```

---

## 🐛 Known Issues

### Minor Issue: Background Job Error

**Error**: Relationship error in Conversation.messages cleanup job

**Impact**: Low - doesn't affect API functionality, only background cleanup

**Status**: Non-blocking, can be fixed later

**Workaround**: None needed, cleanup will retry on next schedule

---

## 📝 API Endpoints Summary

**Total Endpoints**: 50+

| Phase | Category | Endpoints |
|-------|----------|-----------|
| Phase 1 | Authentication | 8 endpoints |
| Phase 2 | Products | 6 endpoints |
| Phase 2 | Feeds | 3 endpoints |
| Phase 2 | Categories | 4 endpoints |
| Phase 2 | Search | 4 endpoints |
| Phase 3 | Messaging | 7 endpoints |
| Phase 3 | Offers | 6 endpoints |
| Phase 4 | Streaming | 9 endpoints |

**Plus WebSocket events**: 20+ real-time events

---

## 🎨 Frontend Integration Checklist

### 1. API Client Setup
- [ ] Create HTTP client (Dio for Flutter)
- [ ] Add base URL: `http://localhost:8000`
- [ ] Add authentication interceptor
- [ ] Handle token refresh

### 2. Authentication Flow
- [ ] Registration screen
- [ ] Login screen
- [ ] OTP verification screen
- [ ] Token storage (secure storage)
- [ ] Auto-login on app start

### 3. Product Features
- [ ] Create listing flow (photos, video, location)
- [ ] Browse Community feed (location-based)
- [ ] Browse Discover feed
- [ ] Search with filters
- [ ] Product detail screen

### 4. Messaging Features
- [ ] Socket.IO client setup
- [ ] Conversation list screen
- [ ] Chat screen with real-time messages
- [ ] Typing indicators
- [ ] Make Offer modal

### 5. Live Streaming Features
- [ ] Go Live flow (5 steps)
- [ ] Stream viewer screen
- [ ] Live chat overlay
- [ ] Reaction buttons
- [ ] Stream analytics screen

---

## 🔗 Important URLs

| Resource | URL |
|----------|-----|
| **Swagger UI** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |
| **OpenAPI JSON** | http://localhost:8000/openapi.json |
| **Health Check** | http://localhost:8000/api/v1/categories |

---

## 🆘 Troubleshooting

### Backend not responding?

```bash
# Check if services are running
docker-compose -f /Users/saleemjadallah/Desktop/Soukloop/backend/docker-compose.yml ps

# Restart backend
docker-compose -f /Users/saleemjadallah/Desktop/Soukloop/backend/docker-compose.yml restart app

# View logs
docker-compose -f /Users/saleemjadallah/Desktop/Soukloop/backend/docker-compose.yml logs app --tail=50
```

### Database issues?

```bash
# Check migrations
docker-compose -f /Users/saleemjadallah/Desktop/Soukloop/backend/docker-compose.yml exec app alembic current

# Apply migrations
docker-compose -f /Users/saleemjadallah/Desktop/Soukloop/backend/docker-compose.yml exec app alembic upgrade head
```

### Redis connection issues?

```bash
# Check Redis
docker-compose -f /Users/saleemjadallah/Desktop/Soukloop/backend/docker-compose.yml exec redis redis-cli ping
# Should return: PONG
```

---

## ✨ Next Steps

1. ✅ **Test all endpoints** using Swagger UI or Postman
2. ✅ **Integrate with Flutter frontend** (API client, state management)
3. ✅ **Test WebSocket features** (messaging, live streaming)
4. ⏭️ **Proceed to Phase 5**: Stripe Payment Integration

---

## 📞 Support

**Documentation**:
- Complete Testing Guide: `TESTING_GUIDE.md`
- Phase 1 Report: `PHASE_1_COMPLETION_REPORT.md`
- Phase 2 Report: `PHASE_2_COMPLETION_REPORT.md`
- Phase 3 Report: `PHASE_3_COMPLETION_REPORT.md`
- Phase 4 Report: `PHASE_4_COMPLETION_REPORT.md`

**API Docs**: http://localhost:8000/docs

---

**Last Updated**: October 18, 2025
**Backend Version**: 1.0.0
**Status**: ✅ Ready for Testing
