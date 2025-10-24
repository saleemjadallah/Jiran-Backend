"""
Execute plpgsql migration using public database URL
This should work since we're connecting from Railway network
"""
import os
import sys


def run_migration():
    # We'll use sqlalchemy since it's already installed
    from sqlalchemy import create_engine, text

    # Get the sync database URL
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not set")
        sys.exit(1)

    # For Railway internal network, use the URL as-is
    print(f"🔗 Connecting to database...")
    print(f"   URL: {database_url[:60]}...")

    # Read the SQL file
    with open("fix_products_plpgsql.sql", "r") as f:
        sql_content = f.read()

    try:
        # Create sync engine (not async) for direct SQL execution
        # Replace postgresql+asyncpg:// with postgresql://
        if "postgresql+asyncpg://" in database_url:
            database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

        engine = create_engine(database_url)

        print("\n🚀 Executing migration...")
        print("=" * 60)

        with engine.connect() as conn:
            # Execute the entire SQL file
            result = conn.execute(text(sql_content))
            conn.commit()

            # Get results if any
            try:
                rows = result.fetchall()
                for row in rows:
                    print(f"   {row[0]}: {row[1]}")
            except:
                pass

        print("=" * 60)
        print("\n✅ Migration completed!")

        # Verify the schema
        print("\n🔍 Verifying products table...")
        with engine.connect() as conn:
            verify_sql = text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'products'
                ORDER BY ordinal_position
            """)
            result = conn.execute(verify_sql)
            columns = result.fetchall()

            print(f"\n📋 Products table has {len(columns)} columns:")
            for col_name, col_type in columns:
                print(f"   - {col_name}: {col_type}")

        print("\n✅ Products table is ready!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
