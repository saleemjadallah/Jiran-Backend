"""
Admin endpoint to run database migrations
TEMPORARY - For fixing products table schema
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_admin_role
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/fix-products-table")
async def fix_products_table(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """
    Fix products table by recreating it with correct schema.

    WARNING: This will drop and recreate the products table!
    Only use if the table is missing columns.

    Requires admin role.
    """

    try:
        # Check if category column exists
        check_sql = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'products' AND column_name = 'category'
        """)
        result = await session.execute(check_sql)
        has_category = result.scalar_one_or_none()

        if has_category:
            return {
                "success": True,
                "message": "Products table already has correct schema. No migration needed.",
                "migrated": False
            }

        # Drop and recreate table
        migration_sql = text("""
            -- Drop existing table
            DROP TABLE IF EXISTS products CASCADE;

            -- Create enums if they don't exist
            DO $$ BEGIN
                CREATE TYPE product_category AS ENUM (
                    'TRADING_CARDS', 'MENS_FASHION', 'SNEAKERS', 'SPORTS_CARDS',
                    'COLLECTIBLES', 'ELECTRONICS', 'HOME_DECOR', 'BEAUTY',
                    'KIDS_BABY', 'FURNITURE', 'BOOKS', 'OTHER'
                );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;

            DO $$ BEGIN
                CREATE TYPE product_condition AS ENUM ('NEW', 'LIKE_NEW', 'GOOD', 'FAIR');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;

            DO $$ BEGIN
                CREATE TYPE feed_type AS ENUM ('DISCOVER', 'COMMUNITY');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;

            -- Create products table
            CREATE TABLE products (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                seller_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(100) NOT NULL,
                description TEXT,
                price NUMERIC(10, 2) NOT NULL,
                original_price NUMERIC(10, 2),
                currency VARCHAR(3) NOT NULL DEFAULT 'AED',
                category product_category NOT NULL,
                condition product_condition NOT NULL DEFAULT 'GOOD',
                feed_type feed_type NOT NULL DEFAULT 'COMMUNITY',
                location GEOMETRY(POINT, 4326),
                neighborhood VARCHAR(255),
                is_available BOOLEAN NOT NULL DEFAULT TRUE,
                view_count INTEGER NOT NULL DEFAULT 0,
                like_count INTEGER NOT NULL DEFAULT 0,
                image_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
                video_url VARCHAR(1024),
                video_thumbnail_url VARCHAR(1024),
                tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                sold_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );

            -- Create indexes
            CREATE INDEX ix_products_seller_id ON products(seller_id);
            CREATE INDEX ix_products_category_feed ON products(category, feed_type);
            CREATE INDEX ix_products_is_available ON products(is_available);
            CREATE INDEX idx_products_location ON products USING GIST(location);
        """)

        await session.execute(migration_sql)
        await session.commit()

        # Verify
        verify_sql = text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'products'
            ORDER BY ordinal_position
        """)
        result = await session.execute(verify_sql)
        columns = result.fetchall()

        return {
            "success": True,
            "message": "Products table recreated successfully!",
            "migrated": True,
            "columns": [{"name": col[0], "type": col[1]} for col in columns]
        }

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
