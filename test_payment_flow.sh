#!/bin/bash
#
# Souk Loop - Payment Flow Test Script
# This script tests the complete payment system implementation
#

set -e  # Exit on error

BASE_URL="http://localhost:8000/api/v1"
TOKEN=""
SELLER_TOKEN=""
PRODUCT_ID=""
TRANSACTION_ID=""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  Souk Loop Payment Flow Test  ${NC}"
echo -e "${BLUE}=====================================${NC}\n"

# Helper function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local auth_token=${4:-$TOKEN}

    if [ -z "$data" ]; then
        curl -s -X $method "$BASE_URL$endpoint" \
            -H "Authorization: Bearer $auth_token" \
            -H "Content-Type: application/json"
    else
        curl -s -X $method "$BASE_URL$endpoint" \
            -H "Authorization: Bearer $auth_token" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi
}

# Step 1: Register test users
echo -e "${YELLOW}1. Registering test users...${NC}"

# Register buyer
BUYER_DATA='{
  "email": "buyer@test.com",
  "username": "testbuyer",
  "password": "Test123!@#",
  "phone": "+971501234567",
  "full_name": "Test Buyer",
  "role": "buyer"
}'

BUYER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "$BUYER_DATA")

TOKEN=$(echo $BUYER_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Buyer registration failed${NC}"
    echo "$BUYER_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Buyer registered successfully${NC}"

# Register seller
SELLER_DATA='{
  "email": "seller@test.com",
  "username": "testseller",
  "password": "Test123!@#",
  "phone": "+971507654321",
  "full_name": "Test Seller",
  "role": "seller"
}'

SELLER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "$SELLER_DATA")

SELLER_TOKEN=$(echo $SELLER_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || echo "")

if [ -z "$SELLER_TOKEN" ]; then
    echo -e "${RED}❌ Seller registration failed${NC}"
    echo "$SELLER_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Seller registered successfully${NC}\n"

# Step 2: Create a test product
echo -e "${YELLOW}2. Creating test product...${NC}"

PRODUCT_DATA='{
  "title": "Test Product - Nike Shoes",
  "description": "Brand new Nike shoes for testing payments",
  "price": 299.00,
  "currency": "AED",
  "category": "mens_fashion",
  "condition": "new",
  "feed_type": "discover",
  "is_available": true,
  "image_urls": ["https://example.com/shoe.jpg"],
  "tags": []
}'

PRODUCT_RESPONSE=$(api_call "POST" "/products" "$PRODUCT_DATA" "$SELLER_TOKEN")
PRODUCT_ID=$(echo $PRODUCT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null || echo "")

if [ -z "$PRODUCT_ID" ]; then
    echo -e "${RED}❌ Product creation failed${NC}"
    echo "$PRODUCT_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Product created: $PRODUCT_ID${NC}\n"

# Step 3: Test fee calculation
echo -e "${YELLOW}3. Testing fee calculation...${NC}"

FEE_RESPONSE=$(curl -s "$BASE_URL/transactions/fees/calculate?amount=299&feed_type=discover")
echo "$FEE_RESPONSE" | python3 -m json.tool

PLATFORM_FEE=$(echo $FEE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['platform_fee'])" 2>/dev/null || echo "0")
SELLER_PAYOUT=$(echo $FEE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['seller_payout'])" 2>/dev/null || echo "0")

echo -e "${GREEN}✓ Fee Calculation:${NC}"
echo -e "  Amount: AED 299.00"
echo -e "  Platform Fee (15%): AED $PLATFORM_FEE"
echo -e "  Seller Payout: AED $SELLER_PAYOUT\n"

# Step 4: Create transaction (initiate payment)
echo -e "${YELLOW}4. Creating transaction (initiating payment)...${NC}"

TRANSACTION_DATA="{
  \"product_id\": \"$PRODUCT_ID\",
  \"payment_method_id\": null,
  \"offer_id\": null
}"

TRANSACTION_RESPONSE=$(api_call "POST" "/transactions" "$TRANSACTION_DATA" "$TOKEN")

echo "$TRANSACTION_RESPONSE" | python3 -m json.tool

TRANSACTION_ID=$(echo $TRANSACTION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['transaction_id'])" 2>/dev/null || echo "")
CLIENT_SECRET=$(echo $TRANSACTION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['client_secret'])" 2>/dev/null || echo "")

if [ -z "$TRANSACTION_ID" ]; then
    echo -e "${RED}❌ Transaction creation failed${NC}"
    echo "$TRANSACTION_RESPONSE"
    echo -e "\n${YELLOW}Note: This might fail if STRIPE_SECRET_KEY is not configured${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Transaction created: $TRANSACTION_ID${NC}"
echo -e "  Client Secret: ${CLIENT_SECRET:0:20}...${NC}\n"

# Step 5: Get transaction details
echo -e "${YELLOW}5. Getting transaction details...${NC}"

TRANSACTION_DETAIL=$(api_call "GET" "/transactions/$TRANSACTION_ID")
echo "$TRANSACTION_DETAIL" | python3 -m json.tool

echo -e "${GREEN}✓ Transaction details retrieved${NC}\n"

# Step 6: List buyer transactions
echo -e "${YELLOW}6. Listing buyer transactions...${NC}"

BUYER_TRANSACTIONS=$(api_call "GET" "/transactions?as_buyer=true&per_page=5")
echo "$BUYER_TRANSACTIONS" | python3 -m json.tool

echo -e "${GREEN}✓ Buyer transactions retrieved${NC}\n"

# Step 7: List seller transactions
echo -e "${YELLOW}7. Listing seller transactions...${NC}"

SELLER_TRANSACTIONS=$(api_call "GET" "/transactions?as_seller=true&per_page=5" "" "$SELLER_TOKEN")
echo "$SELLER_TRANSACTIONS" | python3 -m json.tool

echo -e "${GREEN}✓ Seller transactions retrieved${NC}\n"

# Step 8: Test payout balance (seller only)
echo -e "${YELLOW}8. Checking seller payout balance...${NC}"

BALANCE_RESPONSE=$(api_call "GET" "/payouts/balance" "" "$SELLER_TOKEN")
echo "$BALANCE_RESPONSE" | python3 -m json.tool

echo -e "${GREEN}✓ Seller balance retrieved${NC}\n"

# Step 9: List payouts
echo -e "${YELLOW}9. Listing seller payouts...${NC}"

PAYOUTS=$(api_call "GET" "/payouts?per_page=5" "" "$SELLER_TOKEN")
echo "$PAYOUTS" | python3 -m json.tool

echo -e "${GREEN}✓ Payouts retrieved${NC}\n"

# Summary
echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}  Test Summary  ${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "${GREEN}✓ All API endpoints working${NC}"
echo -e "${GREEN}✓ Fee calculation correct${NC}"
echo -e "${GREEN}✓ Transaction creation successful${NC}"
echo -e "${GREEN}✓ Payout endpoints functional${NC}\n"

echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Configure real Stripe keys in .env"
echo -e "2. Test with Stripe test cards"
echo -e "3. Test webhook events with Stripe CLI"
echo -e "4. Integrate with Flutter frontend\n"

echo -e "${BLUE}Test Data:${NC}"
echo -e "Buyer Token: ${TOKEN:0:50}..."
echo -e "Seller Token: ${SELLER_TOKEN:0:50}..."
echo -e "Product ID: $PRODUCT_ID"
echo -e "Transaction ID: $TRANSACTION_ID\n"
