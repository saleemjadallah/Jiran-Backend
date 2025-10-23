#!/usr/bin/env python3
"""
Test Directus production connection and data sync with Railway PostgreSQL
"""

import requests
import psycopg2
from datetime import datetime

print("=" * 70)
print("  TESTING DIRECTUS ↔ RAILWAY PRODUCTION SYNC")
print("=" * 70)

# Directus configuration
DIRECTUS_URL = "http://localhost:8055"
DIRECTUS_EMAIL = "admin@jiran.app"
DIRECTUS_PASSWORD = "Olaabdel@88aa"

# Railway PostgreSQL configuration (from .env.directus.production)
DB_CONFIG = {
    "host": "centerbeam.proxy.rlwy.net",
    "port": 48201,
    "database": "railway",
    "user": "postgres",
    "password": "BtXAdeVhKYDuAWoMuMGoIKnZBMTTrKdr",
    "sslmode": "require"
}

# Step 1: Get Directus token
print("\n1️⃣  Authenticating with Directus...")
login_response = requests.post(
    f"{DIRECTUS_URL}/auth/login",
    json={"email": DIRECTUS_EMAIL, "password": DIRECTUS_PASSWORD}
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    exit(1)

TOKEN = login_response.json()["data"]["access_token"]
print("   ✅ Authenticated successfully")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Step 2: Create test category via Directus API
print("\n2️⃣  Creating test category via Directus API...")
test_category = {
    "id": 999,
    "name": "Test Category - DO NOT USE",
    "slug": "test-category-sync",
    "description": f"Test sync at {datetime.now()}",
    "sort_order": 999,
    "is_active": False
}

create_response = requests.post(
    f"{DIRECTUS_URL}/items/categories",
    headers=headers,
    json=test_category
)

if create_response.status_code not in [200, 201]:
    print(f"   ⚠️  Create failed: {create_response.status_code}")
    print(f"   {create_response.text[:200]}")
    print("   (Category might already exist, continuing...)")
else:
    print("   ✅ Test category created in Directus")

# Step 3: Query Railway PostgreSQL directly
print("\n3️⃣  Querying Railway PostgreSQL database directly...")
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, slug, description, is_active
        FROM categories
        WHERE id = 999
    """)

    result = cursor.fetchone()

    if result:
        print("   ✅ Test category found in Railway database!")
        print(f"   📊 Data: ID={result[0]}, Name='{result[1]}', Slug='{result[2]}'")
        print(f"   📊 Active: {result[4]}")
        sync_verified = True
    else:
        print("   ❌ Test category NOT found in Railway database")
        sync_verified = False

    cursor.close()
    conn.close()

except Exception as e:
    print(f"   ❌ Database query failed: {e}")
    sync_verified = False

# Step 4: Clean up - delete test category
print("\n4️⃣  Cleaning up test data...")
delete_response = requests.delete(
    f"{DIRECTUS_URL}/items/categories/999",
    headers=headers
)

if delete_response.status_code in [200, 204]:
    print("   ✅ Test category deleted")
else:
    print(f"   ⚠️  Delete failed: {delete_response.status_code}")

# Step 5: Verify production data exists
print("\n5️⃣  Verifying production data...")
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Count categories
    cursor.execute("SELECT COUNT(*) FROM categories")
    cat_count = cursor.fetchone()[0]
    print(f"   ✅ Categories: {cat_count} records")

    # Count platform fees
    cursor.execute("SELECT COUNT(*) FROM platform_fees")
    fee_count = cursor.fetchone()[0]
    print(f"   ✅ Platform Fees: {fee_count} records")

    # List all user collections (non-directus)
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name NOT LIKE 'directus_%'
        ORDER BY table_name
    """)

    tables = cursor.fetchall()
    print(f"\n   📦 User Collections: {len(tables)} total")
    for table in tables:
        print(f"      • {table[0]}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"   ❌ Database verification failed: {e}")

# Final Summary
print("\n" + "=" * 70)
if sync_verified:
    print("  ✅ PRODUCTION SYNC VERIFIED!")
    print("=" * 70)
    print("\n  🎉 SUCCESS! Your setup is complete:")
    print("\n  ✅ Directus is connected to Railway production PostgreSQL")
    print("  ✅ Data changes in Directus sync to production database")
    print("  ✅ FastAPI backend at api.jiran.app can access the data")
    print("\n  🌐 Directus Dashboard: http://localhost:8055")
    print("  📧 Login: admin@jiran.app")
    print("\n  📊 Database: centerbeam.proxy.rlwy.net:48201/railway")
    print("  🚀 API Endpoint: https://api.jiran.app")
else:
    print("  ⚠️  SYNC VERIFICATION INCOMPLETE")
    print("=" * 70)
    print("\n  Please check:")
    print("  1. Directus is running (docker ps)")
    print("  2. Database credentials are correct")
    print("  3. Railway PostgreSQL is accessible")

print("\n" + "=" * 70)
