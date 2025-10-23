# Phase 6 Features - Quick Reference Guide

## 🚀 Quick Start

### 1. Enable Background Jobs

In `app/main.py`:

```python
from app.background.scheduler import start_scheduler, stop_scheduler

@app.on_event("startup")
async def startup_event():
    start_scheduler()  # Starts view sync, offer expiration, cleanup

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()
```

### 2. Add Batch Endpoints

```python
from app.api.endpoints import batch

app.include_router(batch.router, prefix="/api/v1")
```

---

## 📚 Feature Usage Examples

### Stale-While-Revalidate

**Use when**: You want instant responses but fresh data too

```python
from app.core.cache.cache_decorators import stale_while_revalidate

@stale_while_revalidate(key_prefix="product", ttl=900)  # 15 min
async def get_product(product_id: str):
    return await db.query(Product).filter(Product.id == product_id).first()
```

**Result**:
- First call: 200ms (DB query)
- Second call: 5ms (cached)
- Third call: 5ms (stale data) + background refresh

---

### Predictive Prefetching

**Use when**: Users scroll through paginated feeds

```python
from app.services.cache.feed_cache_service import FeedCacheService

# When user loads page 1
async def get_feed(page: int):
    # Get current page
    feed = await feed_service.get_discover_feed(page=page, per_page=20)

    if not feed:
        # Cache miss - fetch from DB
        feed = await fetch_from_db(page, 20)
        await feed_service.set_discover_feed(page, 20, feed)

    # Prefetch next page in background
    await feed_service.prefetch_next_page(
        current_page=page,
        per_page=20,
        feed_fetcher=fetch_from_db,
        feed_type="discover"
    )

    return feed
```

**Result**: Page 2 loads in <5ms when user scrolls

---

### View Count Tracking

**Use when**: Tracking product/stream views

```python
from app.services.cache.view_count_service import ViewCountService

@router.get("/products/{product_id}")
async def view_product(
    product_id: str,
    view_service: ViewCountService = Depends(get_view_count_service)
):
    # Increment view (2ms, non-blocking)
    await view_service.increment_view(product_id)

    # Get product
    product = await get_product(product_id)
    return product
```

**Background**: View counts auto-sync to DB every 5 seconds

---

### Offer Expiration

**Use when**: Creating time-limited offers

```python
from app.services.cache.offer_cache_service import OfferCacheService
from datetime import datetime, timedelta

# Create offer
offer = await db.create_offer(...)

# Track expiration
await offer_service.track_offer_expiration(
    offer_id=offer.id,
    expires_at=datetime.utcnow() + timedelta(hours=24)
)
```

**Background**: Expired offers auto-processed every 1 minute

**Check expiring soon** (for reminders):
```python
# Get offers expiring in next 5 minutes
expiring = await offer_service.get_expiring_soon(within_minutes=5)
# Send notifications
```

---

### Batch API Calls

**Use when**: Fetching multiple items (prevents N+1 queries)

```python
# Frontend
const response = await fetch('/api/v1/batch/users', {
  method: 'POST',
  body: JSON.stringify({
    user_ids: ['user1', 'user2', 'user3']
  })
});

const users = await response.json();
```

**Backend automatically**:
1. Checks Redis cache for all IDs (MGET)
2. Queries DB only for cache misses
3. Backfills cache
4. Returns all users

**Result**: 1 request instead of 20, 70-80% cache hit rate

---

### Cache Compression

**Use when**: Storing large objects (>1KB)

```python
# Automatically compress large feeds
await redis.set_compressed(
    key="feed:discover:page:1",
    value=large_feed_data,  # 10KB
    threshold=1024  # Compress if > 1KB
)

# Get decompresses automatically
feed = await redis.get_compressed("feed:discover:page:1")
```

**Result**: 60-80% memory savings for large objects

**When to use**:
- ✅ Large feeds (>5KB)
- ✅ User profiles with lots of data
- ✅ Search results with metadata
- ❌ Small objects (<1KB) - overhead not worth it
- ❌ Frequently accessed hot data - compression overhead adds latency

---

## 🔧 Service Dependencies

### ViewCountService

```python
from app.services.cache.view_count_service import ViewCountService
from app.core.cache.redis_manager import get_redis_manager
from app.core.database import get_db

def get_view_count_service(
    redis: RedisManager = Depends(get_redis_manager),
    db: AsyncSession = Depends(get_db)
):
    return ViewCountService(redis=redis, db=db)
```

### OfferCacheService

```python
from app.services.cache.offer_cache_service import OfferCacheService

def get_offer_cache_service(
    redis: RedisManager = Depends(get_redis_manager),
    db: AsyncSession = Depends(get_db)
):
    return OfferCacheService(redis=redis, db=db)
```

### FeedCacheService

```python
from app.services.cache.feed_cache_service import FeedCacheService

def get_feed_cache_service(
    redis: RedisManager = Depends(get_redis_manager)
):
    return FeedCacheService(redis=redis)
```

---

## 📊 Monitoring

### Check Cache Stats

```bash
curl http://localhost:8000/api/v1/batch/cache-stats
```

**Response**:
```json
{
  "memory_used_mb": 45.2,
  "total_keys": 12450,
  "hit_rate": 82.5
}
```

### Check Background Jobs

```python
from app.background.scheduler import get_scheduler

status = get_scheduler().get_job_status()
print(status)
# {
#   "running": true,
#   "jobs": [
#     {
#       "id": "sync_view_counts",
#       "name": "Sync view counts to database",
#       "next_run_time": "2025-01-20T10:30:05"
#     }
#   ]
# }
```

### Logs

View counts sync:
```
INFO: View count sync: 50 products, 25 streams, 1250 total views synced
```

Offer expiration:
```
INFO: Offer expiration: 10 offers processed, 10 updated, 0 errors
```

Cache cleanup:
```
INFO: Cache cleanup completed. Deleted 234 expired keys, 12 orphaned entries. Final total: 12450 keys
INFO: Redis memory usage: 45.2 MB
```

---

## 🎯 Best Practices

### 1. Choose the Right TTL

| Data Type | Recommended TTL | Reason |
|-----------|----------------|---------|
| User profile | 1 hour | Changes rarely |
| Product details | 15 minutes | Price/stock may change |
| Feed data | 5 minutes | New items added frequently |
| Search results | 10 minutes | Results change with new listings |
| Live stream data | 2 minutes | Very dynamic |

### 2. Use Compression Wisely

✅ **DO compress**:
- Large feed responses (>5KB)
- User activity history
- Search results with metadata
- Analytics data

❌ **DON'T compress**:
- Small objects (<1KB)
- Hot data (accessed every request)
- Real-time data (chat, notifications)

### 3. Prefetch Strategically

✅ **DO prefetch**:
- Next page in pagination
- Related products
- User's frequent searches

❌ **DON'T prefetch**:
- All pages (wasteful)
- Rarely accessed data
- User-specific dynamic content

### 4. Monitor Cache Hit Rates

**Target rates**:
- Feeds: >80%
- Products: >70%
- Users: >85%
- Search: >60%

**If below target**:
- Increase TTL
- Warm cache more aggressively
- Check invalidation frequency

---

## 🐛 Troubleshooting

### View counts not syncing

**Check**: Background job running
```python
get_scheduler().get_job_status()
```

**Fix**: Restart scheduler
```python
stop_scheduler()
start_scheduler()
```

### Cache compression errors

**Error**: `UnicodeDecodeError`

**Cause**: Binary data stored without base64 encoding

**Fix**: Update RedisManager (already fixed in Phase 6)

### High memory usage

**Check**: Compressed entries
```bash
redis-cli KEYS "*:compressed" | wc -l
```

**Fix**: Run cleanup job
```python
from app.background.jobs.cleanup_old_cache import cleanup_old_cache_job
await cleanup_old_cache_job()
```

### Offers not expiring

**Check**: Sorted set size
```python
count = await offer_service.get_active_offer_count()
```

**Fix**: Run expiration job manually
```python
stats = await offer_service.process_expired_offers()
```

---

## 📖 Documentation Links

- **Full Implementation**: `PHASE_6_IMPLEMENTATION_SUMMARY.md`
- **Unified Strategy**: `UNIFIED_CACHE_STRATEGY.md`
- **Tests**: `tests/test_phase6_simple.py`

---

## ⚡ Performance Cheat Sheet

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Cache hit (get) | <5ms | 50,000 ops/s |
| Cache miss (get+set) | 20-50ms | 5,000 ops/s |
| View increment | <2ms | 100,000 ops/s |
| Batch get (100 items) | <50ms | 2,000 ops/s |
| Compression (10KB) | <5ms | 20,000 ops/s |
| Decompression (10KB) | <2ms | 50,000 ops/s |

---

## 🚦 When to Use Each Feature

**Stale-While-Revalidate**: Product details, user profiles
**Prefetching**: Paginated feeds, search results
**View Counts**: Product views, stream views, clicks
**Offer Expiration**: Time-limited deals, auctions
**Batch APIs**: Loading multiple items (user lists, product grids)
**Compression**: Large responses (feeds, analytics)

---

**Need help?** Check logs or run tests:
```bash
python3 tests/test_phase6_simple.py
```
