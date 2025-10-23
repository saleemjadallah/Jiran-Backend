# Connect Directus to Production Database

## Current Setup

**Local Development:**
- Directus: `http://localhost:8055`
- Database: Local PostgreSQL container
- FastAPI: `http://localhost:8000`
- **Status**: Directus and FastAPI share the same LOCAL database

**Production:**
- FastAPI: `https://api.jiran.app`
- Database: Production PostgreSQL (Railway/EC2)
- **Status**: ⚠️ Directus is NOT connected to production

---

## Architecture Options

### Option 1: Directus as Primary Backend (Recommended)

**Architecture:**
```
Flutter App → Directus API → PostgreSQL
              (api.jiran.app)
```

**Benefits:**
- ✅ Single source of truth
- ✅ Built-in admin interface
- ✅ Automatic REST & GraphQL APIs
- ✅ Real-time webhooks
- ✅ File management built-in
- ✅ No need to maintain separate FastAPI

**Drawbacks:**
- Need to migrate existing FastAPI endpoints to Directus
- Custom business logic requires Directus extensions

**Best for:** New projects or if you want to replace FastAPI entirely

---

### Option 2: Directus as Admin Interface Only

**Architecture:**
```
Flutter App → FastAPI Backend → PostgreSQL
                                    ↑
Admin Panel → Directus ─────────────┘
```

**Benefits:**
- ✅ Keep existing FastAPI backend
- ✅ Directus only for admin/CMS tasks
- ✅ No migration needed
- ✅ Flexible architecture

**Drawbacks:**
- Two systems to maintain
- Potential sync issues if not careful
- More complex deployment

**Best for:** Existing projects with complex business logic in FastAPI

---

### Option 3: Hybrid Approach (Recommended for Jiran)

**Architecture:**
```
Flutter App → FastAPI (Custom Logic) ┐
                                     ↓
              Directus (CRUD + Admin) → PostgreSQL
```

**Benefits:**
- ✅ Directus handles standard CRUD operations
- ✅ FastAPI handles custom business logic
- ✅ Best of both worlds
- ✅ Admin interface for content management

**Use cases:**
- Directus: Categories, Products, Users, Reviews (standard CRUD)
- FastAPI: Payment processing, Live streaming logic, Complex queries

---

## How to Connect to Production

### Step 1: Get Production Database Credentials

You need these from your production PostgreSQL:

```bash
# Option A: If using Railway
# Go to Railway project → PostgreSQL → Variables tab
# Copy these values:
DB_HOST=containers-us-west-xxx.railway.app
DB_PORT=5432
DB_DATABASE=railway
DB_USER=postgres
DB_PASSWORD=<your-password>

# Option B: If using EC2 PostgreSQL
# SSH into your EC2 and get credentials
ssh ubuntu@15.185.132.23
# Check PostgreSQL credentials in your .env file
cat /path/to/.env | grep DATABASE_URL
```

### Step 2: Update Production Environment File

Edit `.env.directus.production`:

```bash
cd backend

# Copy the template
cp .env.directus.production .env.directus.production.local

# Edit with your actual credentials
nano .env.directus.production.local
```

Update these values:
```env
DB_HOST=your-actual-production-host
DB_PORT=5432
DB_DATABASE=jiran
DB_USER=your-production-user
DB_PASSWORD=your-production-password
DB_SSL=true
```

### Step 3: Run Directus with Production Database

**⚠️ IMPORTANT: Backup your production database first!**

```bash
# Backup production database
pg_dump -h your-production-host -U your-user jiran > backup_$(date +%Y%m%d).sql

# Run Directus with production config
docker run -d \
  --name directus-production \
  -p 8055:8055 \
  --env-file .env.directus.production.local \
  directus/directus:11.2.2
```

### Step 4: Re-create Collections in Production

Since production has a different database, you need to create collections again:

```bash
# Get new access token
python3 scripts/verify_collections.py

# Create collections in production
python3 scripts/create_collections_now.py
python3 scripts/seed_data.py
python3 scripts/create_remaining_collections.py
```

---

## Deployment to Railway (Production)

### Step 1: Deploy Directus to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init

# Add PostgreSQL (if not exists)
railway add postgresql

# Deploy Directus
railway up
```

### Step 2: Set Environment Variables in Railway

In Railway dashboard, go to your Directus service → Variables:

```env
# Directus Config
PUBLIC_URL=https://admin.jiran.app
KEY=<generate-new-random-key>
SECRET=<generate-new-random-key>
ADMIN_EMAIL=admin@jiran.app
ADMIN_PASSWORD=<strong-password>

# Database (Railway will auto-populate these)
DB_CLIENT=pg
DB_HOST=${{Postgres.PGHOST}}
DB_PORT=${{Postgres.PGPORT}}
DB_DATABASE=${{Postgres.PGDATABASE}}
DB_USER=${{Postgres.PGUSER}}
DB_PASSWORD=${{Postgres.PGPASSWORD}}

# Redis (if you added Redis)
REDIS=${{Redis.REDIS_URL}}

# Email
EMAIL_FROM=Jiran <noreply@jiran.app>
EMAIL_SMTP_HOST=smtp.zeptomail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=emailapikey
EMAIL_SMTP_PASSWORD=<your-zeptomail-password>

# Security
CORS_ENABLED=true
CORS_ORIGIN=https://jiran.app,https://api.jiran.app
RATE_LIMITER_ENABLED=true
```

### Step 3: Set Up Custom Domain

In Railway:
1. Go to Settings → Domains
2. Add custom domain: `admin.jiran.app`
3. Update DNS records:
   ```
   Type: CNAME
   Name: admin
   Value: <railway-generated-domain>.up.railway.app
   ```

### Step 4: Run Collection Setup Scripts

Once deployed, run the setup scripts targeting production:

```bash
# Update scripts with production URL
DIRECTUS_URL=https://admin.jiran.app python3 scripts/create_collections_now.py
```

---

## Integration with FastAPI Backend

### Option A: Keep FastAPI, Use Directus for Admin Only

Your FastAPI endpoints remain unchanged. Directus is just for admin tasks.

**FastAPI** (api.jiran.app):
- Handles all mobile app requests
- Custom business logic
- Payment processing
- Live streaming

**Directus** (admin.jiran.app):
- Admin dashboard for team members
- Content management
- User moderation
- Analytics

### Option B: Migrate to Directus API

Replace FastAPI endpoints with Directus API calls:

**Before (FastAPI):**
```python
@app.get("/api/categories")
async def get_categories():
    categories = db.query(Category).all()
    return categories
```

**After (Flutter → Directus):**
```dart
// Call Directus directly from Flutter
final response = await http.get(
  Uri.parse('https://admin.jiran.app/items/categories'),
  headers: {'Authorization': 'Bearer $token'},
);
```

**Pros:**
- Simpler architecture
- Less code to maintain
- Built-in features (auth, files, etc.)

**Cons:**
- Less control over custom logic
- Need to migrate existing code

### Option C: Hybrid (Best Approach)

Use Directus for standard CRUD, FastAPI for complex logic:

```dart
// Flutter App

// Get categories from Directus (simple CRUD)
final categories = await directusService.getCategories();

// Process payment via FastAPI (complex business logic)
final payment = await fastApiService.processPayment(amount);
```

**Configure in Flutter:**
```dart
class ApiConfig {
  static const String directusUrl = 'https://admin.jiran.app';
  static const String fastApiUrl = 'https://api.jiran.app';

  // Use Directus for:
  // - Categories, Products, Reviews, Users (CRUD)

  // Use FastAPI for:
  // - Payment processing
  // - Live streaming logic
  // - Complex calculations
  // - Third-party integrations
}
```

---

## Testing Production Connection

### 1. Test Database Connection

```bash
# Test from local machine
psql -h your-production-host -U your-user -d jiran

# If successful, you'll see:
# jiran=#
```

### 2. Test Directus API

```bash
# Get categories
curl https://admin.jiran.app/items/categories

# Get products
curl https://admin.jiran.app/items/products?limit=10
```

### 3. Test from Flutter

```dart
import 'package:http/http.dart' as http;

Future<void> testDirectusConnection() async {
  final response = await http.get(
    Uri.parse('https://admin.jiran.app/items/categories'),
  );

  if (response.statusCode == 200) {
    print('✅ Connected to Directus production!');
    print(response.body);
  } else {
    print('❌ Connection failed: ${response.statusCode}');
  }
}
```

---

## Security Checklist for Production

Before connecting to production:

- [ ] **Backup production database** (critical!)
- [ ] **Change default admin password**
- [ ] **Generate new KEY and SECRET** (don't use development keys)
- [ ] **Enable SSL** for database connection
- [ ] **Set up firewall rules** (only allow specific IPs)
- [ ] **Enable 2FA** on admin account
- [ ] **Configure CORS** properly (don't use `*`)
- [ ] **Set up rate limiting**
- [ ] **Enable monitoring** and logging
- [ ] **Test on staging first** (if available)

---

## Rollback Plan

If something goes wrong:

```bash
# Stop Directus
docker stop directus-production

# Restore database from backup
psql -h your-production-host -U your-user jiran < backup_20251021.sql

# Verify data
psql -h your-production-host -U your-user -d jiran -c "SELECT COUNT(*) FROM products;"
```

---

## FAQ

### Q: Will this affect my current FastAPI backend?
**A:** No, if you keep FastAPI running. Directus will just add another way to access the same database. However, be careful with schema changes.

### Q: Can I use both FastAPI and Directus together?
**A:** Yes! Many apps use this hybrid approach. Use Directus for admin/CRUD, FastAPI for custom logic.

### Q: Do I need to migrate all my FastAPI code?
**A:** No. You can gradually migrate endpoints or keep both systems running.

### Q: What happens to my existing data?
**A:** If you connect to the same database, existing data is preserved. Directus just adds its own system tables (prefixed with `directus_`).

### Q: Is it safe to connect to production?
**A:** Yes, IF you:
1. Backup first
2. Test on staging
3. Configure permissions properly
4. Use SSL connections

---

## Recommended Approach for Jiran

Based on your current setup, I recommend:

**Phase 1: Local Development** (Current)
- ✅ Use local Directus for testing admin interface
- ✅ Keep FastAPI for mobile app
- ✅ Test Directus collections and permissions

**Phase 2: Deploy Directus to Railway** (Next)
- Deploy Directus as separate service
- Connect to production database
- Use as admin dashboard only

**Phase 3: Gradual Migration** (Later)
- Move simple CRUD endpoints to Directus
- Keep complex logic in FastAPI
- Eventually decide: full migration or hybrid

**Phase 4: Production** (Final)
- Directus: Admin interface + simple CRUD
- FastAPI: Complex business logic
- Both share same PostgreSQL database

---

## Next Steps

1. **Get production database credentials**
   ```bash
   # From Railway or EC2
   ```

2. **Backup production database**
   ```bash
   pg_dump -h your-host -U your-user jiran > backup.sql
   ```

3. **Update `.env.directus.production.local`** with real credentials

4. **Test connection locally** first
   ```bash
   docker run --env-file .env.directus.production.local directus/directus:11.2.2
   ```

5. **Deploy to Railway** when ready

---

**Need Help?**
- Railway Deployment: `docs/ADMIN_DASHBOARD.md` (Section: Railway Production Deployment)
- Directus Docs: https://docs.directus.io
- Railway Docs: https://docs.railway.app

---

**Status**: Ready to connect to production
**Action Required**: Get production database credentials and decide on architecture approach
