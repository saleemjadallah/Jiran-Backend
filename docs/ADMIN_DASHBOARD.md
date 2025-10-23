# Jiran Admin Dashboard - Directus Setup Guide

> Beautiful, user-friendly admin interface for managing your Jiran PostgreSQL database

## Table of Contents

1. [What is Directus?](#what-is-directus)
2. [Features Overview](#features-overview)
3. [Local Development Setup](#local-development-setup)
4. [Railway Production Deployment](#railway-production-deployment)
5. [First-Time Access](#first-time-access)
6. [User Roles & Permissions](#user-roles--permissions)
7. [Managing Your Data](#managing-your-data)
8. [Custom Branding](#custom-branding)
9. [Security Best Practices](#security-best-practices)
10. [Troubleshooting](#troubleshooting)

---

## What is Directus?

Directus is an **open-source data platform** that automatically generates a beautiful admin interface from your database schema. Think of it as an instant, customizable admin panel for your PostgreSQL database.

**Why Directus for Jiran?**
- ✅ **Auto-Discovery**: Instantly sees all 18+ tables (users, products, streams, transactions, etc.)
- ✅ **User-Friendly**: Non-technical staff can manage content without SQL knowledge
- ✅ **Free & Open-Source**: No licensing costs
- ✅ **Role-Based Access**: Different permissions for admins, moderators, support staff
- ✅ **REST & GraphQL APIs**: Bonus APIs for future integrations
- ✅ **Activity Logging**: Track all changes and who made them

---

## Features Overview

### What You Can Do with the Admin Dashboard

#### 👥 **User Management**
- View all users (buyers, sellers, admins)
- Edit user profiles and verification status
- See user activity logs and transaction history
- Manage blocked users and ban accounts
- Export user data for analytics

#### 📦 **Content Moderation**
- Browse all products and listings
- Review reported content (products, streams, messages)
- Delete inappropriate content
- Manage categories and tags
- Moderate live streams and videos

#### 💰 **Transaction Management**
- View all transactions and payment history
- Track payouts and seller earnings
- Monitor offers and negotiations
- Manage refunds and disputes
- Export financial reports

#### 📊 **Analytics & Insights**
- User growth metrics
- Sales and revenue tracking
- Content engagement statistics
- Real-time database insights
- Custom reports and exports

#### 🔐 **Admin Tools**
- Manage admin users and roles
- View audit logs of all admin actions
- Configure system settings
- Backup and restore data
- Database health monitoring

---

## Local Development Setup

### Prerequisites

- Docker and Docker Compose installed
- Existing Jiran backend running (PostgreSQL + Redis)

### Step 1: Environment Setup

Your `.env.directus` file is already configured with secure credentials:

```bash
# Admin credentials (change after first login)
DIRECTUS_ADMIN_EMAIL=admin@jiran.app
DIRECTUS_ADMIN_PASSWORD=JiranAdmin2025!

# Local URL
DIRECTUS_PUBLIC_URL=http://localhost:8055
```

**⚠️ SECURITY NOTE**: Change the admin password immediately after first login!

### Step 2: Start Directus

```bash
# Navigate to backend directory
cd backend

# Start Directus alongside existing services
docker-compose -f docker-compose.yml -f docker-compose.directus.yml up -d

# Check if Directus is running
docker-compose -f docker-compose.directus.yml ps
```

You should see output like:
```
NAME                COMMAND                  SERVICE    STATUS
backend-directus-1  "docker-entrypoint.s…"   directus   Up 30 seconds
```

### Step 3: Access the Admin Panel

Open your browser and navigate to:
```
http://localhost:8055
```

**First Login:**
- Email: `admin@jiran.app`
- Password: `JiranAdmin2025!`

### Step 4: Stop Directus

```bash
# Stop Directus only
docker-compose -f docker-compose.directus.yml down

# Stop all services (Directus + App)
docker-compose -f docker-compose.yml -f docker-compose.directus.yml down
```

---

## Railway Production Deployment

### Option 1: Deploy as Separate Railway Service (Recommended)

This approach keeps Directus isolated and easier to manage.

#### Step 1: Create New Service in Railway

1. Go to your Railway project dashboard
2. Click **"+ New Service"**
3. Select **"Docker Image"**
4. Use image: `directus/directus:11.2.2`

#### Step 2: Configure Environment Variables

Add these environment variables in Railway's service settings:

**Required Variables:**
```bash
# Directus Security
KEY=<generate-random-32-char-string>
SECRET=<generate-random-32-char-string>

# Admin User (First Run Only)
ADMIN_EMAIL=admin@jiran.app
ADMIN_PASSWORD=<create-strong-password>

# Database (Link to existing Railway PostgreSQL)
DB_CLIENT=pg
DB_HOST=${{Postgres.PGHOST}}
DB_PORT=${{Postgres.PGPORT}}
DB_DATABASE=${{Postgres.PGDATABASE}}
DB_USER=${{Postgres.PGUSER}}
DB_PASSWORD=${{Postgres.PGPASSWORD}}

# Redis Cache (Link to existing Railway Redis)
CACHE_ENABLED=true
CACHE_STORE=redis
REDIS=${{Redis.REDIS_URL}}

# Public URL (Railway will provide this)
PUBLIC_URL=${{RAILWAY_PUBLIC_DOMAIN}}

# CORS
CORS_ENABLED=true
CORS_ORIGIN=true

# Email (Use your ZeptoMail credentials)
EMAIL_FROM=Jiran <noreply@jiran.app>
EMAIL_TRANSPORT=smtp
EMAIL_SMTP_HOST=smtp.zeptomail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=emailapikey
EMAIL_SMTP_PASSWORD=<your-zeptomail-password>

# Telemetry
TELEMETRY=false

# Log Level
LOG_LEVEL=info
```

**Railway Variable References:**
- `${{Postgres.PGHOST}}` - Automatically references your PostgreSQL service
- `${{Redis.REDIS_URL}}` - Automatically references your Redis service
- `${{RAILWAY_PUBLIC_DOMAIN}}` - Auto-generated public URL

#### Step 3: Add Custom Domain (Optional)

1. In Railway service settings, go to **"Settings" → "Networking"**
2. Click **"Generate Domain"** (you'll get something like `admin-jiran.up.railway.app`)
3. Or add custom domain: `admin.jiran.app`
   - Add DNS record: `CNAME admin.jiran.app → <railway-domain>`
   - SSL certificate auto-configured by Railway

#### Step 4: Deploy

1. Click **"Deploy"** in Railway
2. Wait for deployment to complete (2-3 minutes)
3. Access at: `https://admin-jiran.up.railway.app` (or your custom domain)

### Option 2: Add to Existing Railway Service

If you want Directus in the same container as your FastAPI app:

1. Update your `Dockerfile` to include Directus
2. Use a process manager (like `supervisord`) to run both services
3. Configure Nginx to route `/admin` to Directus

**Note**: Option 1 (separate service) is recommended for better isolation and easier management.

---

## First-Time Access

### Initial Login

1. Navigate to your Directus URL (local or Railway)
2. You'll see the Directus login page
3. Enter admin credentials:
   - Email: `admin@jiran.app`
   - Password: (from your `.env.directus` or Railway env vars)

### Change Default Password

**⚠️ CRITICAL**: Change the default password immediately!

1. Click on user icon (top-right)
2. Go to **"User Profile"**
3. Click **"Change Password"**
4. Enter new strong password
5. Save changes

### Enable Two-Factor Authentication (Recommended)

1. Go to **User Profile → Security**
2. Click **"Enable 2FA"**
3. Scan QR code with authenticator app (Google Authenticator, Authy, etc.)
4. Enter verification code
5. Save backup codes in a secure location

---

## User Roles & Permissions

### Default Roles

Directus comes with these default roles:

1. **Administrator** - Full access to everything
2. **Public** - Unauthenticated access (disable for security)

### Creating Custom Roles

#### Example: Content Moderator Role

**Purpose**: Allow staff to moderate content but not access financial data or admin settings.

**Setup Steps:**

1. Go to **Settings → Roles & Permissions**
2. Click **"+ Create Role"**
3. Name: `Content Moderator`
4. Icon: `verified_user`
5. Description: `Can view and moderate content, cannot access financial data`

**Permissions to Grant:**

| Collection | Create | Read | Update | Delete | Notes |
|------------|--------|------|--------|--------|-------|
| Users | ❌ | ✅ | ⚠️ | ❌ | Read-only, update verification status only |
| Products | ❌ | ✅ | ✅ | ✅ | Full moderation access |
| Streams | ❌ | ✅ | ✅ | ✅ | Can end inappropriate streams |
| Messages | ❌ | ✅ | ❌ | ✅ | Can delete inappropriate messages |
| Reports | ❌ | ✅ | ✅ | ❌ | Can review and resolve reports |
| Reviews | ❌ | ✅ | ✅ | ✅ | Can moderate reviews |
| Transactions | ❌ | ❌ | ❌ | ❌ | No access to financial data |
| Payouts | ❌ | ❌ | ❌ | ❌ | No access to financial data |

#### Example: Customer Support Role

**Purpose**: View user data and assist with customer issues.

**Permissions:**

| Collection | Create | Read | Update | Delete | Notes |
|------------|--------|------|--------|--------|-------|
| Users | ❌ | ✅ | ⚠️ | ❌ | Can update support-related fields only |
| Products | ❌ | ✅ | ❌ | ❌ | Read-only for troubleshooting |
| Transactions | ❌ | ✅ | ❌ | ❌ | View transaction history |
| Messages | ❌ | ✅ | ❌ | ❌ | Read customer messages |
| Reports | ✅ | ✅ | ✅ | ❌ | Can create and update reports |

### Creating New Admin Users

1. Go to **User Directory** (left sidebar)
2. Click **"+ Create User"**
3. Fill in details:
   - Email: `moderator@jiran.app`
   - Password: (generate strong password)
   - Role: Select `Content Moderator` or `Customer Support`
   - Status: `Active`
4. Click **"Save"**
5. (Optional) Send invitation email

**⚠️ Best Practice**:
- Use individual email addresses (not shared accounts)
- Enable 2FA for all admin users
- Use strong, unique passwords
- Regularly audit user access

---

## Managing Your Data

### Browsing Collections (Tables)

Directus automatically discovers all your database tables as "Collections".

**Main Collections You'll Use:**

1. **Users** (`users` table)
   - All registered users (buyers, sellers, admins)
   - Fields: email, username, role, verification status, etc.

2. **Products** (`products` table)
   - All marketplace listings
   - Fields: title, description, price, category, condition, images, etc.

3. **Streams** (`streams` table)
   - Live and recorded video streams
   - Fields: title, seller, status, viewers, products, etc.

4. **Transactions** (`transactions` table)
   - All purchases and payments
   - Fields: buyer, seller, amount, status, payment method, etc.

5. **Messages** (`messages` table)
   - Direct messages between users
   - Fields: sender, receiver, content, timestamp, etc.

6. **Reports** (`reports` table)
   - User-reported content
   - Fields: reporter, content type, reason, status, etc.

### Searching and Filtering

**Search Bar** (top-right in any collection):
- Search across all visible fields
- Example: Search for user by email, username, or phone

**Filters** (funnel icon):
- Click funnel icon above data table
- Add multiple filter conditions
- Example: `role = seller AND verification_status = verified`

**Sorting**:
- Click column header to sort ascending/descending
- Multi-column sort: Hold Shift and click multiple columns

**Advanced Filters Example:**

Find all verified sellers in Dubai with rating > 4.5:
```
role = seller
AND verification_status = verified
AND neighborhood contains "Dubai"
AND rating >= 4.5
```

### Editing Data

**Single Item:**
1. Click on any row in the collection
2. Edit fields in the detail view
3. Click **"Save"** (top-right)

**Bulk Edit:**
1. Select multiple items (checkboxes)
2. Click **"Batch Edit"** button
3. Choose fields to update
4. Apply changes to all selected items

**⚠️ Warning**:
- Be careful with bulk edits - changes are immediate
- Always backup before major changes
- Test on a single item first

### Deleting Data

**Single Item:**
1. Open item detail view
2. Click **trash icon** (top-right)
3. Confirm deletion

**Bulk Delete:**
1. Select multiple items
2. Click **trash icon** in toolbar
3. Confirm deletion

**⚠️ CRITICAL**:
- Deletes are permanent (unless you have backups)
- Deleting users may cascade to related data (products, messages, etc.)
- Review carefully before confirming

### Exporting Data

**Export to CSV/JSON:**
1. Go to any collection
2. Apply filters (if needed)
3. Click **export icon** (top-right)
4. Choose format: CSV, JSON, or XML
5. Download file

**Use Cases:**
- Export user list for email campaigns
- Download transaction reports for accounting
- Backup specific data sets

---

## Custom Branding

### Add Jiran Logo and Colors

1. Go to **Settings → Project Settings**
2. Upload Jiran logo:
   - Click **"Project Logo"**
   - Upload `jiran_logo.png` (recommended size: 200x60px)
3. Set brand color:
   - **Primary Color**: `#C1440E` (Souk Red)
   - **Secondary Color**: `#D4A745` (Souk Gold)
4. Save changes

### Customize Interface

**Layout Options:**
- Go to **Settings → Data Model**
- Configure how each collection displays:
  - List view (table)
  - Card view (grid)
  - Calendar view (for date-based data)

**Example: Display Products as Cards**
1. Go to **Products** collection
2. Click **layout icon** (top-right)
3. Select **"Card"** layout
4. Configure card display:
   - Image field: `images[0]`
   - Title field: `title`
   - Subtitle: `price`

---

## Security Best Practices

### 1. Strong Passwords

✅ **Do:**
- Use passwords with 16+ characters
- Include uppercase, lowercase, numbers, symbols
- Use password manager (1Password, LastPass, Bitwarden)
- Change default passwords immediately

❌ **Don't:**
- Reuse passwords across services
- Use common passwords (e.g., "Password123!")
- Share admin credentials

### 2. Two-Factor Authentication

✅ **Enable 2FA for all admin users:**
1. Go to User Profile → Security
2. Enable 2FA with authenticator app
3. Save backup codes securely

### 3. Role-Based Access Control

✅ **Principle of Least Privilege:**
- Grant only necessary permissions
- Create specific roles for different tasks
- Regular access audits

**Example Roles:**
- `Administrator` - Full access (limit to 1-2 people)
- `Content Moderator` - Content management only
- `Customer Support` - Read-only + ticket management
- `Finance` - Transaction and payout management only

### 4. IP Whitelisting (Production)

For Railway production:

1. Use Railway's IP restrictions (if available)
2. Or use Cloudflare Access:
   - Add Cloudflare in front of admin subdomain
   - Configure Access policies
   - Require authentication before accessing Directus

### 5. Audit Logging

✅ **Monitor admin activity:**
1. Go to **Activity & Revisions** (left sidebar)
2. Review all changes made by admin users
3. Filter by user, collection, or date
4. Export logs for compliance

**What to Monitor:**
- User deletions
- Bulk data changes
- Permission changes
- Failed login attempts

### 6. Regular Backups

✅ **Backup Strategy:**

**Database Backups** (Railway handles this):
- Railway automatically backs up PostgreSQL
- Manual backups: Railway dashboard → Database → Backups

**Directus Configuration Backup:**
```bash
# Export Directus schema and settings
docker exec backend-directus-1 npx directus schema snapshot ./snapshot.yaml

# Backup uploads directory
docker cp backend-directus-1:/directus/uploads ./directus_uploads_backup
```

**Recovery Plan:**
1. Keep backups in multiple locations (local + cloud)
2. Test restore process quarterly
3. Document recovery procedures

### 7. SSL/HTTPS Only

✅ **Railway Production:**
- Railway auto-configures SSL/HTTPS
- Verify: Check for padlock icon in browser
- Force HTTPS: Railway handles this automatically

❌ **Never:**
- Access admin panel over HTTP in production
- Disable SSL certificate verification

### 8. Regular Security Updates

✅ **Keep Directus Updated:**

**Check for updates:**
```bash
# View current version
docker exec backend-directus-1 npx directus --version

# Update to latest version
# Edit docker-compose.directus.yml
# Change: image: directus/directus:11.2.2
# To:     image: directus/directus:latest

# Restart Directus
docker-compose -f docker-compose.directus.yml up -d
```

**Update Schedule:**
- Check monthly for security updates
- Review changelog before updating
- Test in staging environment first

---

## Troubleshooting

### Can't Access Directus (Connection Refused)

**Problem**: Browser shows "Connection refused" or "Can't connect"

**Solutions:**

1. **Check if Directus is running:**
   ```bash
   docker-compose -f docker-compose.directus.yml ps
   ```

2. **Check logs for errors:**
   ```bash
   docker-compose -f docker-compose.directus.yml logs directus
   ```

3. **Verify port 8055 is not in use:**
   ```bash
   lsof -i :8055  # Mac/Linux
   netstat -ano | findstr :8055  # Windows
   ```

4. **Restart Directus:**
   ```bash
   docker-compose -f docker-compose.directus.yml down
   docker-compose -f docker-compose.directus.yml up -d
   ```

### Database Connection Failed

**Problem**: Directus logs show "Database connection failed"

**Solutions:**

1. **Check PostgreSQL is running:**
   ```bash
   docker-compose ps postgres
   ```

2. **Verify database credentials in `.env.directus`:**
   ```bash
   # Should match your PostgreSQL settings
   DATABASE_NAME=jiran
   DATABASE_USER=jiran
   DATABASE_PASSWORD=jiran
   ```

3. **Check network connectivity:**
   ```bash
   # From Directus container to PostgreSQL
   docker exec backend-directus-1 pg_isready -h postgres -p 5432
   ```

4. **Restart both services:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.directus.yml restart
   ```

### Can't Login (Invalid Credentials)

**Problem**: Correct admin credentials don't work

**Solutions:**

1. **Reset admin password via Docker:**
   ```bash
   docker exec -it backend-directus-1 npx directus users update \
     --email admin@jiran.app \
     --password NewStrongPassword123!
   ```

2. **Create new admin user:**
   ```bash
   docker exec -it backend-directus-1 npx directus users create \
     --email newadmin@jiran.app \
     --password NewPassword123! \
     --role administrator
   ```

3. **Check if admin user exists:**
   ```bash
   # Connect to PostgreSQL
   docker exec -it backend-postgres-1 psql -U jiran -d jiran

   # Query Directus users table
   SELECT email, role FROM directus_users;
   ```

### Slow Performance

**Problem**: Directus is slow to load or respond

**Solutions:**

1. **Enable Redis cache** (already configured in `docker-compose.directus.yml`)

2. **Check database indexes:**
   ```sql
   -- Connect to PostgreSQL
   SELECT schemaname, tablename, indexname
   FROM pg_indexes
   WHERE schemaname = 'public';
   ```

3. **Increase Docker resources:**
   - Docker Desktop → Settings → Resources
   - Increase CPU and memory allocation

4. **Optimize large collections:**
   - Add filters to reduce result sets
   - Use pagination (limit results per page)
   - Create custom views with only necessary fields

### 502 Bad Gateway (Railway)

**Problem**: Railway shows 502 error when accessing Directus

**Solutions:**

1. **Check Railway service logs:**
   - Railway dashboard → Service → Logs
   - Look for startup errors or crashes

2. **Verify environment variables:**
   - Ensure `PUBLIC_URL` is set correctly
   - Check database connection variables

3. **Check health endpoint:**
   ```bash
   curl https://admin-jiran.up.railway.app/server/health
   ```

4. **Restart Railway service:**
   - Railway dashboard → Service → Settings → Restart

### Missing Collections/Tables

**Problem**: Some database tables don't appear in Directus

**Solutions:**

1. **Refresh schema:**
   - Settings → Data Model
   - Click **"Refresh"** or **"Sync from Database"**

2. **Check table visibility:**
   - Settings → Data Model
   - Click on collection
   - Ensure **"Hidden"** is not checked

3. **Verify table exists:**
   ```bash
   docker exec -it backend-postgres-1 psql -U jiran -d jiran -c "\dt"
   ```

4. **Manually create collection:**
   - Settings → Data Model → Create Collection
   - Map to existing database table

---

## Support & Resources

### Official Documentation

- **Directus Docs**: https://docs.directus.io
- **API Reference**: https://docs.directus.io/reference/introduction
- **Community Forum**: https://github.com/directus/directus/discussions

### Jiran Team Contacts

- **Technical Issues**: dev@jiran.app
- **Access Requests**: admin@jiran.app
- **Security Concerns**: security@jiran.app

### Quick Reference Commands

```bash
# Start Directus (local)
docker-compose -f docker-compose.yml -f docker-compose.directus.yml up -d

# Stop Directus
docker-compose -f docker-compose.directus.yml down

# View logs
docker-compose -f docker-compose.directus.yml logs -f directus

# Restart Directus
docker-compose -f docker-compose.directus.yml restart

# Access Directus CLI
docker exec -it backend-directus-1 npx directus --help

# Backup database
docker exec backend-postgres-1 pg_dump -U jiran jiran > backup.sql

# Export Directus schema
docker exec backend-directus-1 npx directus schema snapshot ./snapshot.yaml
```

---

## Next Steps

1. ✅ **Complete local setup** - Follow [Local Development Setup](#local-development-setup)
2. ✅ **Change default password** - [First-Time Access](#first-time-access)
3. ✅ **Enable 2FA** - [Security Best Practices](#security-best-practices)
4. ✅ **Create custom roles** - [User Roles & Permissions](#user-roles--permissions)
5. ✅ **Add team members** - [Creating New Admin Users](#creating-new-admin-users)
6. ✅ **Deploy to Railway** - [Railway Production Deployment](#railway-production-deployment)
7. ✅ **Customize branding** - [Custom Branding](#custom-branding)

---

**Questions or Issues?** Contact the Jiran development team at dev@jiran.app
