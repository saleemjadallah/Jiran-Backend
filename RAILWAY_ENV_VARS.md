# Railway Environment Variables - Jiran Backend

## 🚀 Copy these to Railway Dashboard

Go to: **Railway Project → Backend Service → Variables**

---

## ✅ Required Variables

### Application Settings
```bash
APP_NAME=Jiran
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### Security (⚠️ GENERATE NEW SECRET_KEY!)
```bash
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=YOUR_GENERATED_32_CHAR_SECRET_KEY_HERE
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256
```

### Database (Railway Auto-Provides)
```bash
# Railway PostgreSQL plugin will set these automatically:
# DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
#
# If Railway doesn't set ASYNC_DATABASE_URL, the app will auto-convert DATABASE_URL
```

### Redis (Railway Auto-Provides)
```bash
# Railway Redis plugin will set this automatically:
# REDIS_URL=redis://default:password@host:port
#
# Also set Socket.IO queue (uses same Redis, different DB):
SOCKET_IO_MESSAGE_QUEUE=${REDIS_URL}/1
```

### Elasticsearch (Optional - For Advanced Search)
```bash
# If you add Elasticsearch service to Railway:
ELASTICSEARCH_URL=http://elasticsearch.railway.internal:9200
#
# Note: Advanced search features require Elasticsearch
# If not set, app will use basic PostgreSQL search
```

### CORS (Update with your domains)
```bash
CORS_ALLOWED_ORIGINS=["https://jiran.app","https://www.jiran.app","https://api.jiran.app"]
```

---

## 📧 Email - ZeptoMail (Required for Auth)

```bash
SMTP_HOST=smtp.zeptomail.com
SMTP_PORT=587
SMTP_USERNAME=emailapikey
SMTP_PASSWORD=wSsVR612/h75Df0vmTSqdeYxnQkDVQ73EBwrjQD3vX7/HPiUocc/wRKYVA+nH6AaQmdtHDAboe0syxcF0jINjt18nwtVCSiF9mqRe1U4J3x17qnvhDzCXGxclxaNJYkAxQtskmBlFcsh+g==
SMTP_FROM_EMAIL=Jiran <noreply@jiran.app>
```

---

## ☁️ Backblaze B2 Storage (Required for Media)

```bash
B2_ENDPOINT_URL=https://s3.us-east-005.backblazeb2.com
B2_ACCESS_KEY_ID=005f718d128baa90000000002
B2_SECRET_ACCESS_KEY=K005BRCk1t06UNyLsdySpd3JZ/Eh258
B2_REGION=us-east-005

# Bucket Names (all using same bucket)
B2_BUCKET_LIVE_VIDEOS=jiranapp
B2_BUCKET_VIDEOS=jiranapp
B2_BUCKET_PHOTOS=jiranapp
B2_BUCKET_THUMBNAILS=jiranapp

# CDN (optional - leave empty if not using)
B2_CDN_URL=
```

---

## 💳 Stripe (Optional - Add when ready)

```bash
# Get from: https://dashboard.stripe.com/apikeys
STRIPE_SECRET_KEY=sk_live_YOUR_LIVE_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE
```

---

## 📱 SMS - Twilio (Optional - Add when ready)

```bash
# Get from: https://console.twilio.com/
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_FROM_NUMBER=+971501234567
```

---

## 📊 Monitoring - Sentry (Optional - Add when ready)

```bash
# Get from: https://sentry.io/
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

---

## 🔧 Railway-Specific Variables

Railway automatically injects these (don't add manually):
```bash
PORT                 # Railway sets this (usually 8000)
RAILWAY_ENVIRONMENT  # production, staging, etc.
RAILWAY_PROJECT_ID   # Your project ID
RAILWAY_SERVICE_ID   # Your service ID
```

---

## 📋 Step-by-Step Railway Setup

### 1. Create Project
- Go to Railway.app
- Click "New Project"
- Name it "Jiran"

### 2. Add PostgreSQL
- Click "+ New"
- Select "Database → PostgreSQL"
- Railway auto-sets `DATABASE_URL`

### 3. Add Redis
- Click "+ New"
- Select "Database → Redis"
- Railway auto-sets `REDIS_URL`

### 4. Add Elasticsearch (Optional - For Advanced Search)
- Click "+ New"
- Select "Database → Elasticsearch" (if available) OR use Docker template
- Set as environment variable: `ELASTICSEARCH_URL=http://elasticsearch.railway.internal:9200`
- Note: This is optional - app works without it using basic search

### 5. Add Backend Service
- Click "+ New"
- Select "GitHub Repo"
- Choose your backend repository
- Railway will detect Python and install dependencies

### 6. Add Environment Variables
- Click on Backend Service
- Go to "Variables" tab
- Click "Raw Editor"
- **Paste all variables from sections above**

### 7. Generate SECRET_KEY
```bash
# Run locally:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Example output:
# Xq3mK9pL2nR8tY5vW1zA4bC7dE6fG0hJ

# Add to Railway as SECRET_KEY
```

### 8. Set Build Command (if needed)
- Settings → Build
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 9. Deploy
- Click "Deploy"
- Railway will build and deploy automatically

---

## ✅ Variable Checklist

Copy this checklist and verify each one:

### Critical (App Won't Start Without)
- [ ] `SECRET_KEY` (generated, 32+ chars)
- [ ] `DATABASE_URL` (auto-set by Railway PostgreSQL)
- [ ] `REDIS_URL` (auto-set by Railway Redis)

### Email (Auth Won't Work Without)
- [ ] `SMTP_HOST=smtp.zeptomail.com`
- [ ] `SMTP_PORT=587`
- [ ] `SMTP_USERNAME=emailapikey`
- [ ] `SMTP_PASSWORD=<zepto-password>`
- [ ] `SMTP_FROM_EMAIL=Jiran <noreply@jiran.app>`

### Storage (Media Upload Won't Work Without)
- [ ] `B2_ENDPOINT_URL`
- [ ] `B2_ACCESS_KEY_ID`
- [ ] `B2_SECRET_ACCESS_KEY`
- [ ] `B2_REGION`
- [ ] `B2_BUCKET_LIVE_VIDEOS`
- [ ] `B2_BUCKET_VIDEOS`
- [ ] `B2_BUCKET_PHOTOS`
- [ ] `B2_BUCKET_THUMBNAILS`

### App Config
- [ ] `APP_NAME=Jiran`
- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `LOG_LEVEL=INFO`

### JWT Config
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES=15`
- [ ] `REFRESH_TOKEN_EXPIRE_DAYS=7`
- [ ] `JWT_ALGORITHM=HS256`

### CORS (Update domains)
- [ ] `CORS_ALLOWED_ORIGINS=["https://..."]`

### Socket.IO
- [ ] `SOCKET_IO_MESSAGE_QUEUE=${REDIS_URL}/1`

### Optional (Add Later)
- [ ] Stripe keys (when payment ready)
- [ ] Twilio credentials (when SMS ready)
- [ ] Sentry DSN (when monitoring ready)

---

## 🧪 Test After Deployment

### 1. Health Check
```bash
curl https://your-railway-url.railway.app/health
# Should return: {"status": "healthy"}
```

### 2. Test Email
```bash
# SSH into Railway or use Railway CLI
railway run python test_email.py
```

### 3. Test Auth Endpoints
```bash
# Register user
curl -X POST https://your-railway-url/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","phone":"+971501234567","password":"Test123!","full_name":"Test User","role":"buyer"}'

# Should send OTP email
```

---

## 🔒 Security Notes

### ⚠️ NEVER Commit These
- `.env` file
- Any files with credentials
- Railway deployment tokens

### ✅ Always Use
- Railway's secret variables (encrypted)
- Generated SECRET_KEY (not default)
- HTTPS for all production URLs
- Environment variables (not hardcoded)

---

## 📝 Quick Copy-Paste for Railway

**Copy everything below and paste into Railway "Raw Editor":**

```env
# Application
APP_NAME=Jiran
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security - GENERATE NEW SECRET_KEY!
SECRET_KEY=CHANGE_THIS_TO_GENERATED_32_CHAR_KEY
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256

# CORS - Update with your domains
CORS_ALLOWED_ORIGINS=["https://jiran.app","https://www.jiran.app","https://api.jiran.app"]

# Socket.IO (uses Railway Redis)
SOCKET_IO_MESSAGE_QUEUE=${REDIS_URL}/1

# Email - ZeptoMail
SMTP_HOST=smtp.zeptomail.com
SMTP_PORT=587
SMTP_USERNAME=emailapikey
SMTP_PASSWORD=wSsVR612/h75Df0vmTSqdeYxnQkDVQ73EBwrjQD3vX7/HPiUocc/wRKYVA+nH6AaQmdtHDAboe0syxcF0jINjt18nwtVCSiF9mqRe1U4J3x17qnvhDzCXGxclxaNJYkAxQtskmBlFcsh+g==
SMTP_FROM_EMAIL=Jiran <noreply@jiran.app>

# Backblaze B2 Storage
B2_ENDPOINT_URL=https://s3.us-east-005.backblazeb2.com
B2_ACCESS_KEY_ID=005f718d128baa90000000002
B2_SECRET_ACCESS_KEY=K005BRCk1t06UNyLsdySpd3JZ/Eh258
B2_REGION=us-east-005
B2_BUCKET_LIVE_VIDEOS=jiranapp
B2_BUCKET_VIDEOS=jiranapp
B2_BUCKET_PHOTOS=jiranapp
B2_BUCKET_THUMBNAILS=jiranapp
B2_CDN_URL=

# Stripe (Optional - add when ready)
# STRIPE_SECRET_KEY=sk_live_YOUR_KEY_HERE
# STRIPE_WEBHOOK_SECRET=whsec_YOUR_SECRET_HERE

# Twilio SMS (Optional - add when ready)
# TWILIO_ACCOUNT_SID=your_sid
# TWILIO_AUTH_TOKEN=your_token
# TWILIO_FROM_NUMBER=+971501234567

# Sentry (Optional - add when ready)
# SENTRY_DSN=https://your-dsn@sentry.io/project
```

**⚠️ REMEMBER TO:**
1. Generate new SECRET_KEY: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Replace `CHANGE_THIS_TO_GENERATED_32_CHAR_KEY` with generated value
3. Update CORS_ALLOWED_ORIGINS with your actual domains

---

## 🎯 Railway Auto-Provided Variables

These are **automatically set** by Railway when you add services (don't add manually):

```bash
DATABASE_URL          # From PostgreSQL plugin
REDIS_URL            # From Redis plugin
PORT                 # Railway sets this
RAILWAY_ENVIRONMENT  # production/staging
```

---

## 📞 Support

If variables don't work:
1. Check Railway logs: `railway logs`
2. Verify variable names match exactly (case-sensitive)
3. Ensure no quotes around values in Railway UI
4. Restart deployment after adding variables

---

**Last Updated**: October 21, 2025
**Status**: ✅ Ready for Railway Deployment
