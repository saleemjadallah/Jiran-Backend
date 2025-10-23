#!/bin/bash

echo "====================================================================="
echo "  Testing Production Backend at api.jiran.app"
echo "====================================================================="

# Test 1: Health check
echo -e "\n1. Testing Health Endpoint..."
curl -s https://api.jiran.app/health | python3 -m json.tool

# Test 2: Registration
echo -e "\n\n2. Testing Registration Endpoint..."
TIMESTAMP=$(date +%s)
curl -X POST https://api.jiran.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"test${TIMESTAMP}@jiran.app\",
    \"username\": \"testuser${TIMESTAMP}\",
    \"password\": \"SecurePass123!\",
    \"phone\": \"+971${TIMESTAMP:0:9}\",
    \"full_name\": \"Test User\",
    \"role\": \"buyer\"
  }" -w "\n\nHTTP Status: %{http_code}\n" 2>&1

echo -e "\n====================================================================="
