#!/usr/bin/env python3
"""
Seed initial data for Directus collections
"""

import requests
import json

# Configuration
DIRECTUS_URL = "http://localhost:8055"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImYyYjIyOWZmLWUwZTQtNDUyNS04ZWYxLTI3NGI4ZTcwNzMyYyIsInJvbGUiOiI3ZGM1ZTk5Yy0zOGUxLTQyZjMtYWUwYy00ZmU0MmUxYTAyZmYiLCJhcHBfYWNjZXNzIjp0cnVlLCJhZG1pbl9hY2Nlc3MiOnRydWUsImlhdCI6MTc2MTA1OTAzNCwiZXhwIjoxNzYxMDU5OTM0LCJpc3MiOiJkaXJlY3R1cyJ9.xdGc5YTpe01SVPtTfHw1Lw3i6aYjg5HmV6ZZa41ODxY"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def seed_categories():
    """Seed 12 standard categories"""
    print("\n🌱 Seeding categories...")

    categories = [
        {
            "id": 1,
            "name": "Trading Card Games",
            "slug": "trading-card-games",
            "description": "Pokémon, Yu-Gi-Oh!, Magic: The Gathering",
            "icon_name": "style",
            "primary_color": "#C1440E",
            "secondary_color": "#E87A3E",
            "viewer_count": 12500,
            "live_stream_count": 45,
            "trending_tags": ["Pokémon", "Rare Cards", "Sealed Packs"],
            "sort_order": 1,
            "is_active": True
        },
        {
            "id": 2,
            "name": "Men's Fashion",
            "slug": "mens-fashion",
            "description": "Streetwear, Sneakers, Designer Apparel",
            "icon_name": "checkroom",
            "primary_color": "#0D9488",
            "secondary_color": "#C1440E",
            "viewer_count": 18700,
            "live_stream_count": 67,
            "trending_tags": ["Supreme", "Vintage Tees"],
            "sort_order": 2,
            "is_active": True
        },
        {
            "id": 3,
            "name": "Sneakers & Streetwear",
            "slug": "sneakers-streetwear",
            "description": "Limited edition sneakers & exclusive drops",
            "icon_name": "shopping_bag",
            "primary_color": "#D4A745",
            "secondary_color": "#E87A3E",
            "viewer_count": 25300,
            "live_stream_count": 89,
            "trending_tags": ["Jordan 1", "Yeezy", "Nike Dunk"],
            "sort_order": 3,
            "is_active": True
        },
        {
            "id": 4,
            "name": "Sports Cards",
            "slug": "sports-cards",
            "description": "NBA, NFL, Soccer, Baseball collectibles",
            "icon_name": "sports_basketball",
            "primary_color": "#DC2626",
            "secondary_color": "#D4A745",
            "viewer_count": 9800,
            "live_stream_count": 34,
            "trending_tags": ["Rookie Cards", "Autographs"],
            "sort_order": 4,
            "is_active": True
        },
        {
            "id": 5,
            "name": "Coins & Money",
            "slug": "coins-money",
            "description": "Rare coins, bills, and currency",
            "icon_name": "monetization_on",
            "primary_color": "#F59E0B",
            "secondary_color": "#0D9488",
            "viewer_count": 5600,
            "live_stream_count": 12,
            "trending_tags": ["Silver Coins", "Ancient Currency"],
            "sort_order": 5,
            "is_active": True
        },
        {
            "id": 6,
            "name": "Books & Movies",
            "slug": "books-movies",
            "description": "Collectible books, first editions, memorabilia",
            "icon_name": "menu_book",
            "primary_color": "#C1440E",
            "secondary_color": "#0D9488",
            "viewer_count": 4200,
            "live_stream_count": 18,
            "trending_tags": ["First Editions", "Signed Books"],
            "sort_order": 6,
            "is_active": True
        },
        {
            "id": 7,
            "name": "Women's Fashion",
            "slug": "womens-fashion",
            "description": "Designer, vintage, and luxury fashion",
            "icon_name": "woman",
            "primary_color": "#E87A3E",
            "secondary_color": "#D4A745",
            "viewer_count": 21400,
            "live_stream_count": 76,
            "trending_tags": ["Designer Bags", "Vintage Dresses"],
            "sort_order": 7,
            "is_active": True
        },
        {
            "id": 8,
            "name": "Bags & Accessories",
            "slug": "bags-accessories",
            "description": "Luxury handbags, jewelry, watches",
            "icon_name": "shopping_bag_outlined",
            "primary_color": "#0D9488",
            "secondary_color": "#E87A3E",
            "viewer_count": 16800,
            "live_stream_count": 52,
            "trending_tags": ["Louis Vuitton", "Gold Jewelry"],
            "sort_order": 8,
            "is_active": True
        },
        {
            "id": 9,
            "name": "Baby & Kids",
            "slug": "baby-kids",
            "description": "Baby toys, clothes, and essentials",
            "icon_name": "child_care",
            "primary_color": "#C1440E",
            "secondary_color": "#F59E0B",
            "viewer_count": 7900,
            "live_stream_count": 28,
            "trending_tags": ["Baby Clothes", "Educational Toys"],
            "sort_order": 9,
            "is_active": True
        },
        {
            "id": 10,
            "name": "Toys & Hobbies",
            "slug": "toys-hobbies",
            "description": "Funko Pops, LEGO, action figures",
            "icon_name": "toys",
            "primary_color": "#DC2626",
            "secondary_color": "#C1440E",
            "viewer_count": 11200,
            "live_stream_count": 41,
            "trending_tags": ["Funko", "LEGO Sets", "Vintage Toys"],
            "sort_order": 10,
            "is_active": True
        },
        {
            "id": 11,
            "name": "Electronics",
            "slug": "electronics",
            "description": "Gaming consoles, audio, tech gadgets",
            "icon_name": "headphones",
            "primary_color": "#0D9488",
            "secondary_color": "#D4A745",
            "viewer_count": 19600,
            "live_stream_count": 63,
            "trending_tags": ["PS5", "Gaming PC", "Audio Gear"],
            "sort_order": 11,
            "is_active": True
        },
        {
            "id": 12,
            "name": "Kitchen",
            "slug": "kitchen",
            "description": "Cookware, appliances, dining essentials",
            "icon_name": "restaurant_menu",
            "primary_color": "#F59E0B",
            "secondary_color": "#DC2626",
            "viewer_count": 6400,
            "live_stream_count": 22,
            "trending_tags": ["Stand Mixer", "Cast Iron"],
            "sort_order": 12,
            "is_active": True
        }
    ]

    for category in categories:
        response = requests.post(
            f"{DIRECTUS_URL}/items/categories",
            headers=headers,
            json=category
        )

        if response.status_code in [200, 201, 204]:
            print(f"  ✓ Seeded: {category['name']}")
        else:
            print(f"  ✗ Failed: {category['name']} - {response.status_code}")
            if response.status_code == 400:
                print(f"    (May already exist)")

def seed_platform_fees():
    """Seed 8 platform fee configurations"""
    print("\n🌱 Seeding platform fees...")

    fees = [
        # Discover fees
        {"user_tier": "free", "feed_type": "discover", "fee_percentage": 0.1500, "minimum_fee": 5.00, "is_active": True},
        {"user_tier": "plus", "feed_type": "discover", "fee_percentage": 0.1000, "minimum_fee": 5.00, "is_active": True},
        {"user_tier": "creator", "feed_type": "discover", "fee_percentage": 0.0800, "minimum_fee": 5.00, "is_active": True},
        {"user_tier": "pro", "feed_type": "discover", "fee_percentage": 0.0500, "minimum_fee": 5.00, "is_active": True},
        # Community fees
        {"user_tier": "free", "feed_type": "community", "fee_percentage": 0.0500, "minimum_fee": 3.00, "is_active": True},
        {"user_tier": "plus", "feed_type": "community", "fee_percentage": 0.0300, "minimum_fee": 3.00, "is_active": True},
        {"user_tier": "creator", "feed_type": "community", "fee_percentage": 0.0300, "minimum_fee": 3.00, "is_active": True},
        {"user_tier": "pro", "feed_type": "community", "fee_percentage": 0.0300, "minimum_fee": 3.00, "is_active": True},
    ]

    for fee in fees:
        response = requests.post(
            f"{DIRECTUS_URL}/items/platform_fees",
            headers=headers,
            json=fee
        )

        if response.status_code in [200, 201, 204]:
            print(f"  ✓ Seeded: {fee['user_tier']} - {fee['feed_type']} ({fee['fee_percentage']*100}%)")
        else:
            print(f"  ✗ Failed: {fee['user_tier']} - {fee['feed_type']} - {response.status_code}")
            if response.status_code == 400:
                print(f"    (May already exist)")

if __name__ == "__main__":
    print("="*60)
    print("  SEEDING DIRECTUS DATA")
    print("="*60)

    seed_categories()
    seed_platform_fees()

    print("\n" + "="*60)
    print("  ✅ DATA SEEDED!")
    print("="*60)
