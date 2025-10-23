"""
Check for schema mismatches between User model and database.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://jiran:jiran@localhost:5432/jiran"


async def check_location_columns():
    """Check location-related columns in users table."""
    print("\n🔍 Checking Location Columns...")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Check what location columns exist
        result = await conn.execute(text("""
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'users'
            AND (column_name LIKE '%location%' OR column_name LIKE '%lat%' OR column_name LIKE '%lon%')
            ORDER BY column_name;
        """))

        columns = result.fetchall()

        print(f"\n   📋 Location-Related Columns:")
        for col in columns:
            col_name, data_type, udt_name = col
            print(f"      • {col_name:25s} {data_type:30s} (udt: {udt_name})")

        # Check if we have the old PostGIS location column
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'users'
            AND column_name = 'location';
        """))

        has_old_location = result.fetchone() is not None

        # Check if we have the new lat/lon columns
        result = await conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'users'
            AND column_name IN ('location_lat', 'location_lon');
        """))

        latlon_columns = result.fetchall()

        print(f"\n   📊 Column Analysis:")
        print(f"      • Old 'location' column exists: {has_old_location}")
        print(f"      • New 'location_lat/lon' columns: {len(latlon_columns)} found")

        if has_old_location and len(latlon_columns) == 0:
            print(f"\n   ⚠️  SCHEMA MISMATCH DETECTED!")
            print(f"      Database has old PostGIS 'location' column")
            print(f"      User model expects 'location_lat' and 'location_lon'")
            print(f"\n   🔧 Solution:")
            print(f"      Run migration to update schema:")
            print(f"      cd backend && alembic upgrade head")
            return False

        elif len(latlon_columns) == 2:
            print(f"\n   ✅ Schema matches User model (using lat/lon columns)")
            return True

        else:
            print(f"\n   ⚠️  Partial schema - only {len(latlon_columns)}/2 lat/lon columns found")
            return False

    await engine.dispose()


async def check_missing_migrations():
    """Check if there are pending migrations."""
    print("\n🔍 Checking Migration Status...")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Check alembic version
        try:
            result = await conn.execute(text("SELECT version_num FROM alembic_version;"))
            current_version = result.scalar()
            print(f"   📌 Current migration version: {current_version}")

            # List recent migrations
            import os
            migrations_dir = "/Users/saleemjadallah/Desktop/Soukloop/backend/alembic/versions"
            if os.path.exists(migrations_dir):
                migrations = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.py') and not f.startswith('__')])
                print(f"\n   📁 Available migrations ({len(migrations)}):")
                for mig in migrations[-5:]:  # Show last 5
                    version = mig.split('_')[0]
                    indicator = '✅' if version == current_version else '  '
                    print(f"      {indicator} {mig}")

        except Exception as e:
            print(f"   ⚠️  Could not check migrations: {str(e)}")

    await engine.dispose()


async def test_simple_insert():
    """Try a simple user insert to see the exact error."""
    print("\n🔍 Testing Direct User Insert...")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        try:
            # Try to insert a simple test user
            result = await conn.execute(text("""
                INSERT INTO users (
                    email, username, phone, password_hash, full_name, role
                )
                VALUES (
                    'test@example.com',
                    'testuser999',
                    '+971501234567',
                    'dummy_hash',
                    'Test User',
                    'buyer'
                )
                RETURNING id, email;
            """))

            user = result.fetchone()
            print(f"   ✅ Direct insert successful!")
            print(f"      • ID: {user[0]}")
            print(f"      • Email: {user[1]}")

            # Clean up
            await conn.execute(text("DELETE FROM users WHERE email = 'test@example.com';"))
            await conn.commit()

            return True

        except Exception as e:
            print(f"   ❌ Direct insert failed: {str(e)}")
            return False

    await engine.dispose()


async def main():
    """Run all schema checks."""
    print("=" * 70)
    print("  Database Schema Verification")
    print("=" * 70)

    # Check location columns
    location_ok = await check_location_columns()

    # Check migration status
    await check_missing_migrations()

    # Test direct insert
    insert_ok = await test_simple_insert()

    print("\n" + "=" * 70)
    if location_ok and insert_ok:
        print("  ✅ Schema Looks Good!")
    else:
        print("  ⚠️  Schema Issues Detected")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
