"""Check database state - existing tables and enums"""
import os
from sqlalchemy import text, create_engine

# Use sync engine for this check
db_url = os.getenv('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

engine = create_engine(db_url)

with engine.connect() as conn:
    # Check existing tables
    print('=== EXISTING TABLES ===')
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
    for row in result:
        print(row[0])

    print('\n=== EXISTING ENUMS ===')
    result = conn.execute(text("SELECT typname FROM pg_type WHERE typtype='e' ORDER BY typname"))
    for row in result:
        print(row[0])

    print('\n=== STREAMS TABLE CHECK ===')
    result = conn.execute(text("SELECT to_regclass('public.streams')"))
    streams_exists = result.scalar()
    print(f'Streams table exists: {streams_exists}')
