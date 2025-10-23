# Registration Failed - Issue Identified! 🔍

## The Problem

**Your Flutter app is trying to connect to the PRODUCTION backend, but your backend is only running LOCALLY.**

### Current Configuration:

**Flutter App** (`api_config.dart`):
```dart
return 'https://api.jiran.app';  // ← Trying to connect here
```

**Backend**:
```
Running on: http://localhost:8000  // ← Actually running here
```

**Result**: Flutter app cannot reach the backend → Registration fails ❌

---

## Solution Options

### Option 1: Quick Test - Point Flutter to Local Backend

**For testing on iOS Simulator or Android Emulator:**

Edit `/Users/saleemjadallah/Desktop/Soukloop/frontend/lib/core/config/api_config.dart`:

```dart
static String get baseUrl {
  const override = String.fromEnvironment('API_BASE_URL');
  if (override.isNotEmpty) {
    return override;
  }

  // FOR TESTING: Use local backend
  if (kDebugMode) {
    // iOS Simulator
    if (defaultTargetPlatform == TargetPlatform.iOS) {
      return 'http://localhost:8000';
    }
    // Android Emulator
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000';  // Special IP for Android emulator
    }
  }

  // Production API deployed on Railway
  return 'https://api.jiran.app';
}
```

**Then restart the Flutter app.**

---

### Option 2: Deploy Backend to Railway (RECOMMENDED)

You asked about this Railway configuration - **YES, you need it for production!**

#### Step 1: Add DATABASE_URL Variable in Railway

1. Go to your Railway Postgres service
2. Copy the `DATABASE_URL` value (it looks like: `postgresql://user:pass@host:port/dbname`)
3. Go to your Backend service in Railway
4. Add a new variable:
   - **Key**: `DATABASE_URL`
   - **Value**: `${{ Postgres.DATABASE_URL }}` (Railway will auto-populate this)

#### Step 2: Update Backend .env for Railway

The backend code will automatically use `DATABASE_URL` if it's set. Your `app/config.py` already supports this:

```python
@property
def async_database_url(self) -> str:
    if self.ASYNC_DATABASE_URL:  # ← Railway sets this from DATABASE_URL
        return str(self.ASYNC_DATABASE_URL)
    # Falls back to individual vars for local development
    return f"postgresql+asyncpg://{self.DATABASE_USER}:..."
```

#### Step 3: Set Required Environment Variables on Railway

In your Railway backend service, add these variables:

```bash
# Database (handled by DATABASE_URL reference)
DATABASE_URL=${{ Postgres.DATABASE_URL }}

# Security (CRITICAL - generate a secure key!)
SECRET_KEY=<generate-a-32+-character-secure-key>

# Application
ENVIRONMENT=production
DEBUG=false

# CORS (add your frontend URL)
CORS_ALLOWED_ORIGINS=["https://jiran.app","https://www.jiran.app"]

# Email (already configured)
SMTP_HOST=smtp.zeptomail.com
SMTP_PORT=587
SMTP_USERNAME=emailapikey
SMTP_PASSWORD=<your-zepto-password>
SMTP_FROM_EMAIL=Jiran <noreply@jiran.app>

# Redis (if using Railway Redis)
REDIS_URL=${{ Redis.REDIS_URL }}

# Backblaze B2 (copy from your .env)
B2_ENDPOINT_URL=https://s3.us-east-005.backblazeb2.com
B2_ACCESS_KEY_ID=<your-key>
B2_SECRET_ACCESS_KEY=<your-secret>
B2_BUCKET_LIVE_VIDEOS=jiranapp
B2_BUCKET_VIDEOS=jiranapp
B2_BUCKET_PHOTOS=jiranapp
B2_BUCKET_THUMBNAILS=jiranapp
```

#### Step 4: Deploy to Railway

```bash
cd /Users/saleemjadallah/Desktop/Soukloop/backend

# Push to your git repository
git add .
git commit -m "Configure for Railway deployment"
git push origin main

# Railway will auto-deploy if connected to GitHub
```

#### Step 5: Run Migrations on Railway

After deployment, run migrations on the Railway Postgres:

**Option A: Via Railway CLI**
```bash
railway run alembic upgrade head
```

**Option B: Via Railway Dashboard**
1. Go to your backend service
2. Open "Deployments" tab
3. Click on latest deployment
4. Go to "Command" and run: `alembic upgrade head`

---

### Option 3: Use ngrok for Temporary Testing

If you want to test without deploying:

```bash
# Install ngrok
brew install ngrok

# Start your backend locally
cd /Users/saleemjadallah/Desktop/Soukloop/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal, expose it
ngrok http 8000
```

Then update Flutter app to use the ngrok URL (e.g., `https://abc123.ngrok.io`).

---

## CORS Configuration

Your backend needs to allow requests from your Flutter app.

**Update `/backend/.env`**:

```bash
# For local testing (iOS Simulator)
CORS_ALLOWED_ORIGINS=["http://localhost:3000"]

# For production (Railway)
CORS_ALLOWED_ORIGINS=["https://jiran.app","https://www.jiran.app"]
```

**The backend code already handles CORS**, but you need to add your frontend domain.

---

## Summary

### Why Registration is Failing:

1. ❌ Flutter app tries to connect to `https://api.jiran.app`
2. ❌ Backend is NOT deployed there (only running locally)
3. ❌ Connection fails → Registration fails

### Quick Fix (For Testing):

✅ Edit Flutter `api_config.dart` to use `http://localhost:8000`
✅ Restart Flutter app
✅ Test registration

### Production Fix (Recommended):

1. ✅ Deploy backend to Railway
2. ✅ Set `DATABASE_URL=${{ Postgres.DATABASE_URL }}` in Railway
3. ✅ Run migrations on Railway Postgres
4. ✅ Configure CORS for your domain
5. ✅ Flutter app will now work with production backend

---

## Testing After Fix

**Test locally:**
```bash
# Start backend
cd backend
python3 -m uvicorn app.main:app --reload

# Run Flutter app
cd ../frontend
flutter run
```

**Test production:**
```bash
# Just run Flutter app (it will use api.jiran.app)
cd frontend
flutter run --release
```

---

## Need Help?

**If registration still fails after fixing the endpoint:**
1. Check Flutter console for error messages
2. Check backend logs for incoming requests
3. Verify CORS headers in network tab
4. Test the API directly with curl

Let me know which approach you want to take! 🚀
