#!/usr/bin/env python3
"""
Verify all collections have been created
"""

import requests
import json

# Get fresh token
login_response = requests.post(
    "http://localhost:8055/auth/login",
    json={"email": "admin@jiran.app", "password": "Olaabdel@88aa"}
)

TOKEN = login_response.json()["data"]["access_token"]

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Get all collections
response = requests.get(
    "http://localhost:8055/collections",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    all_collections = [c["collection"] for c in data["data"]]

    # Filter out directus system collections
    jiran_collections = [c for c in all_collections if not c.startswith("directus_")]

    print("="*60)
    print(f"  ✅ JIRAN COLLECTIONS ({len(jiran_collections)} total)")
    print("="*60)

    expected = [
        "categories",
        "platform_fees",
        "user_verification",
        "products",
        "live_streams",
        "product_tags",
        "transactions",
        "offers",
        "conversations",
        "messages",
        "notifications",
        "reviews",
        "follows",
        "wishlist",
        "reports",
        "user_blocks"
    ]

    for collection in sorted(jiran_collections):
        icon = "✅" if collection in expected else "⚠️"
        print(f"  {icon} {collection}")

    # Check for missing collections
    missing = [c for c in expected if c not in jiran_collections]
    if missing:
        print("\n⚠️  Missing collections:")
        for m in missing:
            print(f"    - {m}")

    # Check categories count
    print("\n📊 Checking seeded data...")

    cat_response = requests.get(
        "http://localhost:8055/items/categories",
        headers=headers
    )
    if cat_response.status_code == 200:
        cat_data = cat_response.json()
        cat_count = len(cat_data["data"])
        print(f"  ✅ Categories: {cat_count}/12 seeded")

    # Check platform fees count
    fee_response = requests.get(
        "http://localhost:8055/items/platform_fees",
        headers=headers
    )
    if fee_response.status_code == 200:
        fee_data = fee_response.json()
        fee_count = len(fee_data["data"])
        print(f"  ✅ Platform Fees: {fee_count}/8 seeded")

    print("\n" + "="*60)
    print("  🌐 Access Directus at: http://localhost:8055")
    print("  📧 Login: admin@jiran.app")
    print("="*60)
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
