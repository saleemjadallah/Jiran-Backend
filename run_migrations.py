"""
Run Alembic migrations on Railway production database
"""
import asyncio
import os
from alembic import command
from alembic.config import Config


def run_migrations():
    """Run all pending Alembic migrations"""
    # Get alembic config
    alembic_cfg = Config("alembic.ini")

    # Override the database URL from environment
    database_url = os.getenv("ASYNC_DATABASE_URL")
    if not database_url:
        print("❌ ERROR: ASYNC_DATABASE_URL not found in environment")
        return

    print(f"🔗 Connecting to database...")
    print(f"   URL: {database_url[:50]}...")

    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    # Check current version
    print("\n📊 Checking current migration version...")
    try:
        command.current(alembic_cfg)
    except Exception as e:
        print(f"⚠️  Could not get current version: {e}")

    # Run upgrade
    print("\n🚀 Running migrations to head...")
    try:
        command.upgrade(alembic_cfg, "head")
        print("\n✅ Migrations completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise

    # Show final version
    print("\n📊 Final migration version:")
    command.current(alembic_cfg)


if __name__ == "__main__":
    run_migrations()
