#!/bin/bash
# Railway startup script - reads PORT from environment

PORT=${PORT:-8080}

echo "Starting Uvicorn on port $PORT..."

python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
