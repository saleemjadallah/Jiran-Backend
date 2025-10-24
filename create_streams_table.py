"""Create streams table directly, skipping enum creation if they exist"""
import os
from sqlalchemy import text, create_engine

db_url = os.getenv('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

engine = create_engine(db_url)

# SQL to create streams table
create_streams_sql = """
CREATE TABLE IF NOT EXISTS streams (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    category stream_category NOT NULL,
    status stream_status NOT NULL,
    stream_type stream_type NOT NULL,
    rtmp_url VARCHAR(1024),
    stream_key VARCHAR(512),
    hls_url VARCHAR(1024),
    thumbnail_url VARCHAR(1024),
    viewer_count INTEGER NOT NULL DEFAULT 0,
    total_views INTEGER NOT NULL DEFAULT 0,
    duration_seconds INTEGER,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_streams_user_id_users FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_streams_user_id ON streams(user_id);
CREATE INDEX IF NOT EXISTS ix_streams_status ON streams(status);
"""

with engine.connect() as conn:
    print("🚀 Creating streams table...")
    try:
        # Execute the SQL
        conn.execute(text(create_streams_sql))
        conn.commit()
        print("✅ Streams table created successfully!")

        # Verify
        result = conn.execute(text("SELECT to_regclass('public.streams')"))
        streams_exists = result.scalar()
        print(f"✅ Verification: Streams table exists = {streams_exists}")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
