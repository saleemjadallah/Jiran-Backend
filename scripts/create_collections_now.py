#!/usr/bin/env python3
"""
Create all Directus collections for Jiran platform
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

def create_collection(name, fields, icon="box", note=""):
    """Create a collection with fields"""
    print(f"\n📦 Creating collection: {name}")

    payload = {
        "collection": name,
        "meta": {
            "collection": name,
            "icon": icon,
            "note": note,
            "singleton": False,
            "archive_field": None,
            "archive_value": None,
            "unarchive_value": None,
            "sort_field": None
        },
        "schema": {
            "name": name
        },
        "fields": fields
    }

    response = requests.post(
        f"{DIRECTUS_URL}/collections",
        headers=headers,
        json=payload
    )

    if response.status_code in [200, 201, 204]:
        print(f"✅ Collection '{name}' created successfully")
        return True
    else:
        print(f"⚠️  Error creating '{name}': {response.status_code}")
        print(f"Response: {response.text}")
        return False

def create_field(field_name, field_type, **kwargs):
    """Helper to create field definition"""
    field = {
        "field": field_name,
        "type": field_type,
        "schema": {},
        "meta": {}
    }

    # Add schema properties
    if kwargs.get("primary_key"):
        field["schema"]["is_primary_key"] = True
    if kwargs.get("auto_increment"):
        field["schema"]["has_auto_increment"] = True
    if kwargs.get("unique"):
        field["schema"]["is_unique"] = True
    if kwargs.get("nullable") is not None:
        field["schema"]["is_nullable"] = kwargs["nullable"]
    if kwargs.get("default_value") is not None:
        field["schema"]["default_value"] = kwargs["default_value"]
    if kwargs.get("numeric_precision"):
        field["schema"]["numeric_precision"] = kwargs["numeric_precision"]
    if kwargs.get("numeric_scale"):
        field["schema"]["numeric_scale"] = kwargs["numeric_scale"]
    if kwargs.get("max_length"):
        field["schema"]["max_length"] = kwargs["max_length"]

    # Add meta properties
    if kwargs.get("interface"):
        field["meta"]["interface"] = kwargs["interface"]
    if kwargs.get("required"):
        field["meta"]["required"] = True
    if kwargs.get("hidden"):
        field["meta"]["hidden"] = True
    if kwargs.get("options"):
        field["meta"]["options"] = kwargs["options"]
    if kwargs.get("display"):
        field["meta"]["display"] = kwargs["display"]
    if kwargs.get("readonly"):
        field["meta"]["readonly"] = True

    return field

# 1. CATEGORIES COLLECTION
def create_categories():
    fields = [
        create_field("id", "integer", primary_key=True, auto_increment=True, interface="input"),
        create_field("name", "string", max_length=255, unique=True, interface="input", required=True),
        create_field("slug", "string", max_length=255, unique=True, interface="input", required=True),
        create_field("description", "text", interface="textarea"),
        create_field("icon_name", "string", max_length=255, interface="input"),
        create_field("primary_color", "string", max_length=7, interface="select-color"),
        create_field("secondary_color", "string", max_length=7, interface="select-color"),
        create_field("viewer_count", "integer", default_value=0, interface="input"),
        create_field("live_stream_count", "integer", default_value=0, interface="input"),
        create_field("trending_tags", "json", interface="tags"),
        create_field("sort_order", "integer", interface="input", required=True),
        create_field("is_active", "boolean", default_value=True, interface="boolean"),
    ]

    return create_collection("categories", fields, "category", "Product categories (12 standard)")

# 2. PLATFORM FEES COLLECTION
def create_platform_fees():
    fields = [
        create_field("id", "integer", primary_key=True, auto_increment=True, interface="input"),
        create_field("user_tier", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Free", "value": "free"},
                        {"text": "Plus", "value": "plus"},
                        {"text": "Creator", "value": "creator"},
                        {"text": "Pro", "value": "pro"}
                    ]}),
        create_field("feed_type", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Discover", "value": "discover"},
                        {"text": "Community", "value": "community"}
                    ]}),
        create_field("fee_percentage", "decimal", numeric_precision=5, numeric_scale=4, interface="input", required=True),
        create_field("minimum_fee", "decimal", numeric_precision=10, numeric_scale=2, interface="input", required=True),
        create_field("is_active", "boolean", default_value=True, interface="boolean"),
    ]

    return create_collection("platform_fees", fields, "payments", "Platform fee configuration")

# 3. USER VERIFICATION COLLECTION
def create_user_verification():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("verification_type", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Seller", "value": "seller"},
                        {"text": "Buyer", "value": "buyer"},
                        {"text": "Both", "value": "both"}
                    ]}),
        create_field("emirates_id", "string", max_length=255, interface="input"),
        create_field("trade_license", "string", max_length=255, interface="input"),
        create_field("verification_status", "string", max_length=50, default_value="pending", interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Pending", "value": "pending"},
                        {"text": "Approved", "value": "approved"},
                        {"text": "Rejected", "value": "rejected"}
                    ]}),
        create_field("verified_at", "timestamp", interface="datetime"),
        create_field("rejection_reason", "text", interface="textarea"),
        create_field("badges", "json", interface="tags"),
    ]

    return create_collection("user_verification", fields, "verified_user", "User identity verification")

# 4. PRODUCTS COLLECTION
def create_products():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("title", "string", max_length=80, interface="input", required=True),
        create_field("description", "text", interface="textarea", required=True),
        create_field("listing_type", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Photo", "value": "photo"},
                        {"text": "Video", "value": "video"},
                        {"text": "Live", "value": "live"},
                        {"text": "Scheduled Live", "value": "scheduled_live"}
                    ]}),
        create_field("feed_type", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Discover", "value": "discover"},
                        {"text": "Community", "value": "community"}
                    ]}),
        create_field("price", "decimal", numeric_precision=10, numeric_scale=2, interface="input", required=True),
        create_field("is_negotiable", "boolean", default_value=False, interface="boolean"),
        create_field("condition", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Brand New", "value": "brand_new"},
                        {"text": "Like New", "value": "like_new"},
                        {"text": "Good", "value": "good"},
                        {"text": "Fair", "value": "fair"},
                        {"text": "For Parts", "value": "for_parts"}
                    ]}),
        create_field("brand", "string", max_length=255, interface="input"),
        create_field("images", "json", interface="tags"),
        create_field("cover_image", "string", max_length=255, interface="input", required=True),
        create_field("video_url", "string", max_length=255, interface="input"),
        create_field("video_thumbnail", "string", max_length=255, interface="input"),
        create_field("video_duration", "integer", interface="input"),
        create_field("neighborhood", "string", max_length=255, interface="input", required=True),
        create_field("coordinates", "json", interface="input"),
        create_field("delivery_options", "json", interface="input"),
        create_field("tags", "json", interface="tags"),
        create_field("view_count", "integer", default_value=0, interface="input"),
        create_field("save_count", "integer", default_value=0, interface="input"),
        create_field("share_count", "integer", default_value=0, interface="input"),
        create_field("status", "string", max_length=50, default_value="active", interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Active", "value": "active"},
                        {"text": "Sold", "value": "sold"},
                        {"text": "Removed", "value": "removed"},
                        {"text": "Reported", "value": "reported"}
                    ]}),
        create_field("is_featured", "boolean", default_value=False, interface="boolean"),
        create_field("platform_fee_rate", "decimal", numeric_precision=5, numeric_scale=4, interface="input", required=True),
        create_field("minimum_fee", "decimal", numeric_precision=10, numeric_scale=2, interface="input", required=True),
    ]

    return create_collection("products", fields, "inventory", "Product listings")

# 5. LIVE STREAMS COLLECTION
def create_live_streams():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("title", "string", max_length=255, interface="input", required=True),
        create_field("description", "text", interface="textarea"),
        create_field("feed_type", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Discover", "value": "discover"},
                        {"text": "Community", "value": "community"}
                    ]}),
        create_field("stream_type", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Live", "value": "live"},
                        {"text": "Recorded", "value": "recorded"},
                        {"text": "Scheduled", "value": "scheduled"}
                    ]}),
        create_field("video_url", "string", max_length=255, interface="input"),
        create_field("thumbnail_url", "string", max_length=255, interface="input", required=True),
        create_field("hls_url", "string", max_length=255, interface="input"),
        create_field("rtmp_url", "string", max_length=255, interface="input"),
        create_field("is_live", "boolean", default_value=False, interface="boolean", required=True),
        create_field("started_at", "timestamp", interface="datetime"),
        create_field("ended_at", "timestamp", interface="datetime"),
        create_field("scheduled_for", "timestamp", interface="datetime"),
        create_field("duration", "integer", interface="input"),
        create_field("current_viewers", "integer", default_value=0, interface="input"),
        create_field("peak_viewers", "integer", default_value=0, interface="input"),
        create_field("total_views", "integer", default_value=0, interface="input"),
        create_field("like_count", "integer", default_value=0, interface="input"),
        create_field("comment_count", "integer", default_value=0, interface="input"),
        create_field("share_count", "integer", default_value=0, interface="input"),
        create_field("show_notes", "text", interface="textarea"),
        create_field("chat_enabled", "boolean", default_value=True, interface="boolean"),
        create_field("status", "string", max_length=50, default_value="active", interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Active", "value": "active"},
                        {"text": "Ended", "value": "ended"},
                        {"text": "Scheduled", "value": "scheduled"},
                        {"text": "Cancelled", "value": "cancelled"}
                    ]}),
    ]

    return create_collection("live_streams", fields, "videocam", "Live and recorded streams")

# Run all creations
if __name__ == "__main__":
    print("="*60)
    print("  CREATING DIRECTUS COLLECTIONS FOR JIRAN")
    print("="*60)

    create_categories()
    create_platform_fees()
    create_user_verification()
    create_products()
    create_live_streams()

    print("\n" + "="*60)
    print("  ✅ CORE COLLECTIONS CREATED!")
    print("="*60)
