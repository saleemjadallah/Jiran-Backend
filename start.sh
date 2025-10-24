#!/bin/bash
# Railway startup script - runs migrations then starts server

echo "🔄 Running database migrations..."
alembic upgrade head

if [ $? -ne 0 ]; then
    echo "⚠️  Migration failed, but continuing startup..."
fi

PORT=${PORT:-8080}

echo "🚀 Starting Uvicorn on port $PORT..."

python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
