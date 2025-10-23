"""
Check enum values in the database.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://jiran:jiran@localhost:5432/jiran"


async def check_enum_values():
    """Check what enum values exist for user_role."""
    print("\n🔍 Checking Enum Values...")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Get enum type definition
        result = await conn.execute(text("""
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'user_role'
            ORDER BY e.enumsortorder;
        """))

        enum_values = result.fetchall()

        if enum_values:
            print(f"\n   📋 user_role Enum Values in Database:")
            for value in enum_values:
                print(f"      • {value[0]}")

            # Check what the model expects
            print(f"\n   📋 user_role Enum Values in Model (UserRole):")
            print(f"      • BUYER = 'buyer'")
            print(f"      • SELLER = 'seller'")
            print(f"      • BOTH = 'both'")
            print(f"      • ADMIN = 'admin'")

            # Check if there's a mismatch
            db_values = [v[0] for v in enum_values]
            expected_values = ['buyer', 'seller', 'both', 'admin']

            missing_in_db = set(expected_values) - set(db_values)
            extra_in_db = set(db_values) - set(expected_values)

            if missing_in_db:
                print(f"\n   ⚠️  Missing in database: {missing_in_db}")

            if extra_in_db:
                print(f"\n   ⚠️  Extra in database: {extra_in_db}")

            if not missing_in_db and not extra_in_db:
                print(f"\n   ✅ Enum values match!")

        else:
            print(f"\n   ❌ No user_role enum found in database")

    await engine.dispose()


async def check_all_migrations():
    """List all migrations."""
    print("\n🔍 Checking All Migrations...")

    import os
    migrations_dir = "/Users/saleemjadallah/Desktop/Soukloop/backend/alembic/versions"

    if os.path.exists(migrations_dir):
        migrations = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.py') and not f.startswith('__')])

        print(f"\n   📁 All migrations ({len(migrations)}):")
        for i, mig in enumerate(migrations, 1):
            version = mig.split('_')[0]
            name = '_'.join(mig.split('_')[1:]).replace('.py', '')
            print(f"      {i:2d}. {version} - {name[:60]}")

        # Check current version
        engine = create_async_engine(DATABASE_URL, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version;"))
            current = result.scalar()

            print(f"\n   📌 Current database version: {current}")

            # Find which migration number we're at
            for i, mig in enumerate(migrations, 1):
                if mig.startswith(current):
                    print(f"   📍 We are at migration #{i} of {len(migrations)}")
                    if i < len(migrations):
                        print(f"   ⚠️  There are {len(migrations) - i} pending migrations!")
                        print(f"\n   🔧 Run: cd backend && alembic upgrade head")
                    break

        await engine.dispose()


async def main():
    """Run all checks."""
    print("=" * 70)
    print("  Database Enum and Migration Check")
    print("=" * 70)

    await check_enum_values()
    await check_all_migrations()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
