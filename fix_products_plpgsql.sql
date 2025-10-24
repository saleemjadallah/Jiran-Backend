-- Create a plpgsql function to fix the products table
-- This can be executed via Railway CLI

CREATE OR REPLACE FUNCTION fix_products_table_schema()
RETURNS TABLE(status TEXT, message TEXT) AS $$
DECLARE
    column_exists BOOLEAN;
BEGIN
    -- Check if category column exists
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'products'
        AND column_name = 'category'
    ) INTO column_exists;

    IF column_exists THEN
        RETURN QUERY SELECT 'SUCCESS'::TEXT, 'Products table already has correct schema'::TEXT;
        RETURN;
    END IF;

    -- Drop existing table
    DROP TABLE IF EXISTS products CASCADE;

    -- Create enums
    CREATE TYPE IF NOT EXISTS product_category AS ENUM (
        'TRADING_CARDS', 'MENS_FASHION', 'SNEAKERS', 'SPORTS_CARDS',
        'COLLECTIBLES', 'ELECTRONICS', 'HOME_DECOR', 'BEAUTY',
        'KIDS_BABY', 'FURNITURE', 'BOOKS', 'OTHER'
    );

    CREATE TYPE IF NOT EXISTS product_condition AS ENUM (
        'NEW', 'LIKE_NEW', 'GOOD', 'FAIR'
    );

    CREATE TYPE IF NOT EXISTS feed_type AS ENUM (
        'DISCOVER', 'COMMUNITY'
    );

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

    RETURN QUERY SELECT 'SUCCESS'::TEXT, 'Products table recreated successfully'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Execute the function
SELECT * FROM fix_products_table_schema();

-- Clean up the function
DROP FUNCTION fix_products_table_schema();
