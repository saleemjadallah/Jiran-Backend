"""
Fix the enum case mismatch by updating database enum values to lowercase.
This script will safely update the user_role enum values from UPPERCASE to lowercase.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://jiran:jiran@localhost:5432/jiran"


async def backup_users_table():
    """Create a backup of users table before making changes."""
    print("\n📦 Creating backup of users table...")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        # Create backup table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users_backup_enum_fix AS
            SELECT * FROM users;
        """))

        # Count backup records
        result = await conn.execute(text("SELECT COUNT(*) FROM users_backup_enum_fix;"))
        count = result.scalar()

        print(f"   ✅ Backup created with {count} records")

    await engine.dispose()
    return True


async def fix_enum_case():
    """Fix the enum case mismatch."""
    print("\n🔧 Fixing enum case mismatch...")

    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with engine.begin() as conn:
            # Step 1: Rename old enum type
            print("   1️⃣ Renaming old enum type...")
            await conn.execute(text("ALTER TYPE user_role RENAME TO user_role_old;"))

            # Step 2: Create new enum with lowercase values
            print("   2️⃣ Creating new enum with lowercase values...")
            await conn.execute(text("""
                CREATE TYPE user_role AS ENUM ('buyer', 'seller', 'both', 'admin');
            """))

            # Step 3: Update users table to use new enum
            print("   3️⃣ Updating users table...")
            await conn.execute(text("""
                ALTER TABLE users
                  ALTER COLUMN role TYPE user_role
                  USING LOWER(role::text)::user_role;
            """))

            # Step 4: Update backup table to use new enum (to remove dependency)
            print("   4️⃣ Updating backup table...")
            await conn.execute(text("""
                ALTER TABLE users_backup_enum_fix
                  ALTER COLUMN role TYPE user_role
                  USING LOWER(role::text)::user_role;
            """))

            # Step 5: Drop old enum type
            print("   5️⃣ Dropping old enum type...")
            await conn.execute(text("DROP TYPE user_role_old;"))

            print("   ✅ Enum fix completed successfully!")

    except Exception as e:
        print(f"   ❌ Fix failed: {str(e)}")
        print("\n   🔄 To restore from backup:")
        print("      DROP TABLE users;")
        print("      ALTER TABLE users_backup_enum_fix RENAME TO users;")
        return False

    await engine.dispose()
    return True


async def verify_fix():
    """Verify the enum fix was successful."""
    print("\n🔍 Verifying fix...")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Check new enum values
        result = await conn.execute(text("""
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'user_role'
            ORDER BY e.enumsortorder;
        """))

        enum_values = [v[0] for v in result.fetchall()]

        print(f"   📋 New enum values: {enum_values}")

        expected = ['buyer', 'seller', 'both', 'admin']
        if enum_values == expected:
            print(f"   ✅ Enum values match expected!")
        else:
            print(f"   ❌ Enum values don't match expected: {expected}")
            return False

        # Try a test insert
        print("\n   🧪 Testing insert with new enum...")
        try:
            await conn.execute(text("""
                INSERT INTO users (
                    email, username, phone, password_hash, full_name, role
                )
                VALUES (
                    'test_enum_fix@example.com',
                    'test_enum_user',
                    '+971509999999',
                    'dummy_hash',
                    'Test Enum User',
                    'buyer'
                )
                RETURNING id;
            """))

            # Clean up test user
            await conn.execute(text("""
                DELETE FROM users WHERE email = 'test_enum_fix@example.com';
            """))
            await conn.commit()

            print(f"   ✅ Test insert successful with 'buyer' enum!")

        except Exception as e:
            print(f"   ❌ Test insert failed: {str(e)}")
            return False

    await engine.dispose()
    return True


async def main():
    """Run the fix process."""
    print("=" * 70)
    print("  Enum Case Fix - user_role UPPERCASE → lowercase")
    print("=" * 70)

    # Step 1: Backup
    backup_ok = await backup_users_table()
    if not backup_ok:
        print("\n❌ Backup failed, aborting...")
        return

    # Step 2: Fix enum
    fix_ok = await fix_enum_case()
    if not fix_ok:
        print("\n❌ Fix failed, backup preserved at users_backup_enum_fix")
        return

    # Step 3: Verify
    verify_ok = await verify_fix()

    print("\n" + "=" * 70)
    if verify_ok:
        print("  ✅ Enum Fix Complete!")
        print("=" * 70)
        print("\n  Next steps:")
        print("  1. Apply pending migrations: alembic upgrade head")
        print("  2. Test registration: python3 test_registration.py")
        print("  3. Remove backup when confident: DROP TABLE users_backup_enum_fix;")
    else:
        print("  ⚠️  Fix Applied but Verification Failed")
        print("=" * 70)
        print("\n  Check the issues above and verify manually")

    print()


if __name__ == "__main__":
    asyncio.run(main())
