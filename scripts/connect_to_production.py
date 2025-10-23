#!/usr/bin/env python3
"""
Connect Directus to Railway Production Database

This script helps you connect your local Directus to production Railway database.

Usage:
    python3 scripts/connect_to_production.py
"""

import sys
import os

print("="*60)
print("  CONNECT DIRECTUS TO RAILWAY PRODUCTION DATABASE")
print("="*60)

print("\n📋 Please provide your Railway PostgreSQL credentials:")
print("   (You can find these in Railway Dashboard → PostgreSQL → Variables)\n")

# Get credentials from user
db_host = input("PGHOST (e.g., containers-us-west-123.railway.app): ").strip()
db_port = input("PGPORT (default 5432): ").strip() or "5432"
db_database = input("PGDATABASE (e.g., railway or jiran): ").strip()
db_user = input("PGUSER (e.g., postgres): ").strip()
db_password = input("PGPASSWORD: ").strip()

if not all([db_host, db_port, db_database, db_user, db_password]):
    print("\n❌ Error: All credentials are required!")
    sys.exit(1)

# Create production environment file
env_content = f"""# Directus Production Configuration for Jiran
# ==============================================
# Connected to Railway PostgreSQL

# Directus Security Keys
KEY=aB3xK9mP2rT5vY8cN1dF4gH7jL0qW6eR9sU2tV5xZ8
SECRET=pQ7mN3kL9xB2vC5tR8yH1wF4jD0sA6eG9uI2oP5lZ8

# Admin Credentials
ADMIN_EMAIL=admin@jiran.app
ADMIN_PASSWORD=Olaabdel@88aa

# Public URL
PUBLIC_URL=http://localhost:8055

# ============================================
# RAILWAY PRODUCTION DATABASE
# ============================================
DB_CLIENT=pg
DB_HOST={db_host}
DB_PORT={db_port}
DB_DATABASE={db_database}
DB_USER={db_user}
DB_PASSWORD={db_password}

# SSL Mode for production
DB_SSL=true
DB_SSL_REJECT_UNAUTHORIZED=false

# ============================================
# CACHE (Optional)
# ============================================
CACHE_ENABLED=false

# Email Configuration (ZeptoMail)
EMAIL_FROM=Jiran <noreply@jiran.app>
EMAIL_SMTP_HOST=smtp.zeptomail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=emailapikey
EMAIL_SMTP_PASSWORD=wSsVR612/h75Df0vmTSqdeYxnQkDVQ73EBwrjQD3vX7/HPiUocc/wRKYVA+nH6AaQmdtHDAboe0syxcF0jINjt18nwtVCSiF9mqRe1U4J3x17qnvhDzCXGxclxaNJYkAxQtskmBlFcsh+g==

# CORS Configuration
CORS_ENABLED=true
CORS_ORIGIN=true

# Rate Limiting
RATE_LIMITER_ENABLED=true
RATE_LIMITER_POINTS=100
RATE_LIMITER_DURATION=1

# Telemetry
TELEMETRY=false

# Log Level
LOG_LEVEL=info
"""

# Save to file
env_file = ".env.directus.production"
with open(env_file, "w") as f:
    f.write(env_content)

print(f"\n✅ Production environment file created: {env_file}")

# Test connection
print("\n🔍 Testing database connection...")

import subprocess

test_cmd = f"""
psql "postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_database}?sslmode=require" \
  -c "SELECT version();" 2>&1
"""

result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True)

if "PostgreSQL" in result.stdout:
    print("✅ Database connection successful!")
    print(f"\n{result.stdout[:200]}...")
else:
    print("⚠️  Could not verify connection (psql might not be installed)")
    print("   This is okay - we'll test when we start Directus")

print("\n" + "="*60)
print("  NEXT STEPS")
print("="*60)

print("""
1. Stop local Directus (if running):
   docker stop backend-directus-1

2. Start Directus with production database:
   docker run -d \\
     --name directus-production \\
     -p 8055:8055 \\
     --env-file .env.directus.production \\
     directus/directus:11.2.2

3. Wait 10 seconds for startup, then verify:
   curl http://localhost:8055/server/health

4. Create collections in production:
   python3 scripts/create_collections_now.py
   python3 scripts/seed_data.py
   python3 scripts/create_remaining_collections.py

5. Access Directus:
   http://localhost:8055
   Login: admin@jiran.app / Olaabdel@88aa

6. Verify data sync:
   - Any changes in Directus will now affect production
   - Your FastAPI at api.jiran.app will see the same data
""")

print("="*60)
print("  🚀 Ready to connect to production!")
print("="*60)
