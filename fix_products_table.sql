-- Fix products table: Check if columns exist and add if missing
-- This handles the case where the table was created without running migrations

-- First, check if category column exists
DO $$
BEGIN
    -- Check if category column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'products' AND column_name = 'category'
    ) THEN
        -- Drop and recreate the table with correct schema
        RAISE NOTICE 'Products table missing columns. Recreating...';

        -- Drop existing table (WARNING: This will delete all products!)
        DROP TABLE IF EXISTS products CASCADE;

        -- Create product_category enum if not exists
        DO $enum$ BEGIN
            CREATE TYPE product_category AS ENUM (
                'TRADING_CARDS', 'MENS_FASHION', 'SNEAKERS', 'SPORTS_CARDS',
                'COLLECTIBLES', 'ELECTRONICS', 'HOME_DECOR', 'BEAUTY',
                'KIDS_BABY', 'FURNITURE', 'BOOKS', 'OTHER'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $enum$;

        -- Create product_condition enum if not exists
        DO $enum$ BEGIN
            CREATE TYPE product_condition AS ENUM ('NEW', 'LIKE_NEW', 'GOOD', 'FAIR');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $enum$;

        -- Create feed_type enum if not exists
        DO $enum$ BEGIN
            CREATE TYPE feed_type AS ENUM ('DISCOVER', 'COMMUNITY');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $enum$;

        -- Create products table with correct schema
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

        RAISE NOTICE 'Products table recreated successfully!';
    ELSE
        RAISE NOTICE 'Products table already has correct schema.';
    END IF;
END $$;
