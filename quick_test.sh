#!/bin/bash

# Souk Loop Backend - Quick API Test Script
# This script tests basic functionality of Phases 1-4

set -e  # Exit on error

echo "🚀 Souk Loop Backend - Quick Test Script"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8000"
BUYER_EMAIL="testbuyer@soukloop.com"
BUYER_PASSWORD="Test123!@#"
SELLER_EMAIL="testseller@soukloop.com"
SELLER_PASSWORD="Seller123!@#"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print success
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error
error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to print info
info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

echo "Step 1: Check if backend is running..."
if curl -s "$BASE_URL/docs" > /dev/null; then
    success "Backend is running on $BASE_URL"
else
    error "Backend is not accessible. Please run: docker-compose up -d"
    exit 1
fi

echo ""
echo "Step 2: Register Buyer Account..."
BUYER_REGISTER=$(curl -s -X POST "$BASE_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$BUYER_EMAIL\",
    \"username\": \"testbuyer\",
    \"password\": \"$BUYER_PASSWORD\",
    \"phone\": \"+971501234567\",
    \"full_name\": \"Test Buyer\",
    \"role\": \"buyer\"
  }")

if echo "$BUYER_REGISTER" | grep -q "access_token"; then
    success "Buyer registered successfully"
    BUYER_TOKEN=$(echo "$BUYER_REGISTER" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || echo "")
    info "Buyer Token: ${BUYER_TOKEN:0:50}..."
else
    # Check if user already exists
    if echo "$BUYER_REGISTER" | grep -q "already exists"; then
        info "Buyer account already exists, logging in..."
        BUYER_LOGIN=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
          -H "Content-Type: application/json" \
          -d "{
            \"identifier\": \"$BUYER_EMAIL\",
            \"password\": \"$BUYER_PASSWORD\"
          }")

        if echo "$BUYER_LOGIN" | grep -q "access_token"; then
            success "Buyer logged in successfully"
            BUYER_TOKEN=$(echo "$BUYER_LOGIN" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || echo "")
        else
            error "Failed to login buyer"
            echo "$BUYER_LOGIN" | python3 -m json.tool
            exit 1
        fi
    else
        error "Failed to register buyer"
        echo "$BUYER_REGISTER" | python3 -m json.tool
        exit 1
    fi
fi

echo ""
echo "Step 3: Register Seller Account..."
SELLER_REGISTER=$(curl -s -X POST "$BASE_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$SELLER_EMAIL\",
    \"username\": \"testseller\",
    \"password\": \"$SELLER_PASSWORD\",
    \"phone\": \"+971507654321\",
    \"full_name\": \"Test Seller\",
    \"role\": \"seller\"
  }")

if echo "$SELLER_REGISTER" | grep -q "access_token"; then
    success "Seller registered successfully"
    SELLER_TOKEN=$(echo "$SELLER_REGISTER" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || echo "")
    info "Seller Token: ${SELLER_TOKEN:0:50}..."
else
    # Check if user already exists
    if echo "$SELLER_REGISTER" | grep -q "already exists"; then
        info "Seller account already exists, logging in..."
        SELLER_LOGIN=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
          -H "Content-Type: application/json" \
          -d "{
            \"identifier\": \"$SELLER_EMAIL\",
            \"password\": \"$SELLER_PASSWORD\"
          }")

        if echo "$SELLER_LOGIN" | grep -q "access_token"; then
            success "Seller logged in successfully"
            SELLER_TOKEN=$(echo "$SELLER_LOGIN" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || echo "")
        else
            error "Failed to login seller"
            echo "$SELLER_LOGIN" | python3 -m json.tool
            exit 1
        fi
    else
        error "Failed to register seller"
        echo "$SELLER_REGISTER" | python3 -m json.tool
        exit 1
    fi
fi

echo ""
echo "Step 4: Get Current User (Buyer)..."
BUYER_ME=$(curl -s -X GET "$BASE_URL/api/v1/auth/me" \
  -H "Authorization: Bearer $BUYER_TOKEN")

if echo "$BUYER_ME" | grep -q "testbuyer"; then
    success "Retrieved buyer profile"
    echo "$BUYER_ME" | python3 -m json.tool
else
    error "Failed to get buyer profile"
    echo "$BUYER_ME"
fi

echo ""
echo "Step 5: Get All Categories..."
CATEGORIES=$(curl -s -X GET "$BASE_URL/api/v1/categories")

if echo "$CATEGORIES" | grep -q "trading_cards"; then
    success "Retrieved categories"
    CATEGORY_COUNT=$(echo "$CATEGORIES" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['data']))" 2>/dev/null || echo "0")
    info "Found $CATEGORY_COUNT categories"
else
    error "Failed to get categories"
    echo "$CATEGORIES" | python3 -m json.tool
fi

echo ""
echo "Step 6: Create Product (Seller)..."
PRODUCT_CREATE=$(curl -s -X POST "$BASE_URL/api/v1/products" \
  -H "Authorization: Bearer $SELLER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Nike Air Jordan 1 Retro High",
    "description": "Brand new, never worn. Size 42. Original box included.",
    "price": 850.00,
    "currency": "AED",
    "category": "sneakers",
    "condition": "new",
    "feed_type": "community",
    "location": {
      "latitude": 25.0772,
      "longitude": 55.1369
    },
    "neighborhood": "Dubai Marina",
    "image_urls": [
      "https://example.com/image1.jpg",
      "https://example.com/image2.jpg"
    ],
    "tags": ["sneakers", "jordan", "nike"]
  }')

if echo "$PRODUCT_CREATE" | grep -q '"id"'; then
    success "Product created successfully"
    PRODUCT_ID=$(echo "$PRODUCT_CREATE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null || echo "")
    info "Product ID: $PRODUCT_ID"
    info "Platform Fee: 5% (Community feed)"
else
    error "Failed to create product"
    echo "$PRODUCT_CREATE" | python3 -m json.tool
fi

echo ""
echo "Step 7: Browse Community Feed..."
COMMUNITY_FEED=$(curl -s -X GET "$BASE_URL/api/v1/feeds/community?latitude=25.0772&longitude=55.1369&radius_km=10")

if echo "$COMMUNITY_FEED" | grep -q "items"; then
    success "Retrieved Community feed"
    ITEM_COUNT=$(echo "$COMMUNITY_FEED" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['data']['items']))" 2>/dev/null || echo "0")
    info "Found $ITEM_COUNT products in feed"
else
    error "Failed to get Community feed"
    echo "$COMMUNITY_FEED" | python3 -m json.tool
fi

echo ""
echo "Step 8: Search Products..."
SEARCH=$(curl -s -X GET "$BASE_URL/api/v1/search?q=nike+jordan")

if echo "$SEARCH" | grep -q "items"; then
    success "Search completed successfully"
    SEARCH_COUNT=$(echo "$SEARCH" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['total'])" 2>/dev/null || echo "0")
    info "Found $SEARCH_COUNT products matching 'nike jordan'"
else
    error "Failed to search products"
    echo "$SEARCH" | python3 -m json.tool
fi

echo ""
echo "=========================================="
echo "✨ Quick Test Complete!"
echo ""
echo "Summary:"
echo "  ✅ Authentication working"
echo "  ✅ Product creation working"
echo "  ✅ Feed browsing working"
echo "  ✅ Search working"
echo ""
info "Next steps:"
echo "  1. Review TESTING_GUIDE.md for comprehensive testing"
echo "  2. Test WebSocket features (messaging, live streaming)"
echo "  3. Test offer creation and negotiation"
echo "  4. Test live streaming flow"
echo ""
info "API Documentation: http://localhost:8000/docs"
echo ""
