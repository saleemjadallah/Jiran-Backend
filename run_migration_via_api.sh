#!/bin/bash

# Run database migration via admin API endpoint
# This works because the API runs inside Railway network

echo "🔐 Step 1: Login as admin to get token..."
echo ""

# Login (replace with your admin credentials)
read -p "Enter admin email: " ADMIN_EMAIL
read -sp "Enter admin password: " ADMIN_PASSWORD
echo ""

LOGIN_RESPONSE=$(curl -s -X POST https://api.jiran.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"identifier\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")

# Extract token
TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Login failed!"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Login successful!"
echo "Token: ${TOKEN:0:30}..."
echo ""

echo "🚀 Step 2: Running migration..."
echo ""

# Run migration
MIGRATION_RESPONSE=$(curl -s -X POST https://api.jiran.app/api/v1/admin/fix-products-table \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo "Response:"
echo $MIGRATION_RESPONSE | python3 -m json.tool

echo ""
echo "✅ Done!"
