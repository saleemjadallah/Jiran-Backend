"""
Verify all migrations have been applied by checking for key tables/columns.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://jiran:jiran@localhost:5432/jiran"


async def verify_migrations():
    """Check if all migrations created their expected tables/columns."""
    print("\n🔍 Verifying All Migrations Applied...")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.connect() as conn:
        # Check current migration
        result = await conn.execute(text("SELECT version_num FROM alembic_version;"))
        current = result.scalar()
        print(f"\n   📌 Current Migration: {current}")

        # Migration checks
        checks = [
            {
                "name": "Initial Migration (users table)",
                "query": "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');"
            },
            {
                "name": "Fulltext Search Index",
                "query": "SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = 'ix_products_search_vector');"
            },
            {
                "name": "Messaging Tables",
                "query": "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversations');"
            },
            {
                "name": "Stream Model",
                "query": "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'streams');"
            },
            {
                "name": "Payout Model",
                "query": "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'payouts');"
            },
            {
                "name": "Follow Table (Phase 7)",
                "query": "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'follows');"
            },
            {
                "name": "Admin Log Table (Phase 8)",
                "query": "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'admin_logs');"
            },
            {
                "name": "Location Lat/Lon Columns",
                "query": "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'location_lat');"
            }
        ]

        all_passed = True
        print(f"\n   📋 Migration Verification:")

        for check in checks:
            result = await conn.execute(text(check["query"]))
            exists = result.scalar()
            status = "✅" if exists else "❌"
            print(f"      {status} {check['name']}")
            if not exists:
                all_passed = False

        # Count tables
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            AND table_name != 'alembic_version';
        """))
        table_count = result.scalar()
        print(f"\n   📊 Total Tables: {table_count}")

        # List all tables
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            AND table_name != 'alembic_version'
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result.fetchall()]

        print(f"\n   📁 Database Tables:")
        for i, table in enumerate(tables, 1):
            print(f"      {i:2d}. {table}")

    await engine.dispose()
    return all_passed


async def main():
    print("=" * 70)
    print("  Migration Verification Report")
    print("=" * 70)

    all_passed = await verify_migrations()

    print("\n" + "=" * 70)
    if all_passed:
        print("  ✅ All Migrations Successfully Applied!")
        print("=" * 70)
        print("\n  Your database is fully migrated and ready to use.")
        print("  All tables, indexes, and columns are in place.")
    else:
        print("  ⚠️  Some Migration Features Missing")
        print("=" * 70)
        print("\n  Some expected tables/columns were not found.")
        print("  This could mean migrations need to be re-run.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
