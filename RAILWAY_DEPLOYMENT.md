# Railway Deployment Guide - Jiran Backend

This guide covers deploying the Jiran Backend (Souk Loop) to Railway.app.

## Prerequisites

- Railway account (https://railway.app)
- GitHub repository connected to Railway
- PostgreSQL database addon added in Railway

## Required Environment Variables

Configure these environment variables in your Railway project settings:

### 1. Security (CRITICAL)
```bash
# Generate a secure 32+ character secret key
SECRET_KEY=<generate-with-command-below>
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Example output: `0ngLxe7Uck0tODh7cg4x3DBmctJ4T5VfOT_4hsYCS0c`

### 2. Application Settings
```bash
APP_NAME=Souk Loop
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### 3. Database (Railway PostgreSQL)

Railway automatically provides a PostgreSQL database. You can use the `DATABASE_URL` variable:

```bash
# Option 1: Use Railway's DATABASE_URL directly (recommended)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Option 2: Or set individual variables
DATABASE_HOST=${{Postgres.PGHOST}}
DATABASE_PORT=${{Postgres.PGPORT}}
DATABASE_USER=${{Postgres.PGUSER}}
DATABASE_PASSWORD=${{Postgres.PGPASSWORD}}
DATABASE_NAME=${{Postgres.PGDATABASE}}
DATABASE_SCHEMA=public
```

### 4. Redis (Railway Redis)

Add Redis addon in Railway, then:

```bash
REDIS_URL=${{Redis.REDIS_URL}}
SOCKET_IO_MESSAGE_QUEUE=${{Redis.REDIS_URL}}
```

### 5. JWT Configuration
```bash
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ALGORITHM=HS256
```

### 6. CORS Origins
```bash
# Add your frontend URLs (comma-separated JSON array)
CORS_ALLOWED_ORIGINS=["https://yourdomain.com","https://app.yourdomain.com"]
```

### 7. File Storage (AWS S3 or Backblaze B2)

For Backblaze B2 (S3-compatible):
```bash
AWS_ACCESS_KEY_ID=your-b2-application-key-id
AWS_SECRET_ACCESS_KEY=your-b2-application-key
AWS_REGION=eu-central-1
B2_BUCKET_NAME=your-bucket-name
B2_ENDPOINT_URL=https://s3.eu-central-003.backblazeb2.com
```

For AWS S3:
```bash
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=eu-central-1
```

### 8. Email (SMTP) - Optional

For Mailgun:
```bash
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USERNAME=postmaster@yourdomain.mailgun.org
SMTP_PASSWORD=your-mailgun-password
SMTP_FROM_EMAIL=Souk Loop <noreply@yourdomain.com>
```

### 9. SMS (Twilio) - Optional
```bash
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_FROM_NUMBER=+971500000000
```

### 10. Payment (Stripe)
```bash
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

### 11. Monitoring (Sentry) - Optional
```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

## Deployment Steps

### Step 1: Connect GitHub Repository

1. Go to Railway dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `saleemjadallah/Jiran-Backend`
5. Railway will auto-detect it's a Python project

### Step 2: Add PostgreSQL Database

1. Click "New" in your project
2. Select "Database" → "PostgreSQL"
3. Railway will provision a PostgreSQL database
4. The `DATABASE_URL` variable will be automatically available

### Step 3: Add Redis (Optional but Recommended)

1. Click "New" in your project
2. Select "Database" → "Redis"
3. The `REDIS_URL` variable will be automatically available

### Step 4: Configure Environment Variables

1. Click on your backend service
2. Go to "Variables" tab
3. Add all required environment variables from the list above
4. **CRITICAL:** Generate and set a secure `SECRET_KEY`

### Step 5: Configure Build & Start Commands

Railway should auto-detect these, but verify:

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Step 6: Run Database Migrations

After first deployment, run migrations:

1. Go to your service settings
2. Open "Deploy Logs" or use Railway CLI
3. Run migrations:

```bash
alembic upgrade head
```

You can add this to a custom start command:
```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Step 7: Enable Deployment

1. Click "Deploy" or push to main branch
2. Railway will automatically deploy
3. Monitor logs for any errors

## Post-Deployment

### Health Check

Visit your Railway URL + `/health`:
```
https://your-app.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

### API Documentation

Access interactive API docs:
- Swagger UI: `https://your-app.up.railway.app/docs`
- ReDoc: `https://your-app.up.railway.app/redoc`

## Troubleshooting

### Error: "String should have at least 32 characters"

**Problem:** `SECRET_KEY` is too short or using default value.

**Solution:**
```bash
# Generate a new secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add it to Railway environment variables
SECRET_KEY=<generated-key-here>
```

### Error: "Connection refused" or Database errors

**Problem:** Database not properly configured.

**Solution:**
- Ensure PostgreSQL addon is added
- Verify `DATABASE_URL` variable is set: `${{Postgres.DATABASE_URL}}`
- Check database connection in Railway logs

### Error: "Module not found"

**Problem:** Dependencies not installed.

**Solution:**
- Verify `requirements.txt` is in root directory
- Check build logs for pip install errors
- Ensure Python version is 3.11+

### Migration Errors

**Problem:** Database schema not initialized.

**Solution:**
```bash
# Run migrations manually
alembic upgrade head

# Or add to start command:
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Environment Variable Checklist

Before deploying, ensure these are set:

- [ ] `SECRET_KEY` (32+ characters, randomly generated)
- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `DATABASE_URL` (from Railway PostgreSQL)
- [ ] `REDIS_URL` (from Railway Redis)
- [ ] `CORS_ALLOWED_ORIGINS` (your frontend URLs)
- [ ] `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY` (for file uploads)
- [ ] `STRIPE_SECRET_KEY` (for payments)
- [ ] `TWILIO_ACCOUNT_SID` & `TWILIO_AUTH_TOKEN` (for OTP/SMS)

## Monitoring & Logs

### View Logs
1. Go to your service in Railway
2. Click "View Logs"
3. Monitor real-time application logs

### Metrics
Railway provides:
- CPU usage
- Memory usage
- Network traffic
- Request metrics

## Custom Domain (Optional)

1. Go to service settings
2. Click "Settings" → "Domains"
3. Add custom domain
4. Update DNS records as instructed
5. Update `CORS_ALLOWED_ORIGINS` to include new domain

## Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Rotate SECRET_KEY regularly** - Change every 90 days
3. **Use strong database passwords** - Railway generates these
4. **Enable HTTPS only** - Railway provides SSL by default
5. **Restrict CORS origins** - Only allow your frontend domains
6. **Use Sentry for error tracking** - Set `SENTRY_DSN`
7. **Review logs regularly** - Check for suspicious activity

## Support

- Railway Docs: https://docs.railway.app
- Jiran Backend Issues: https://github.com/saleemjadallah/Jiran-Backend/issues
- FastAPI Docs: https://fastapi.tiangolo.com

---

**Generated with Claude Code**
