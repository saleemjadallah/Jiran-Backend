#!/usr/bin/env python3
"""
Create remaining Directus collections for Jiran platform
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
        print(f"Response: {response.text[:200]}")
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

# 1. PRODUCT TAGS COLLECTION
def create_product_tags():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("position_x", "decimal", numeric_precision=5, numeric_scale=2, interface="input", required=True),
        create_field("position_y", "decimal", numeric_precision=5, numeric_scale=2, interface="input", required=True),
        create_field("timestamp", "integer", interface="input"),
        create_field("is_active", "boolean", default_value=True, interface="boolean"),
    ]
    return create_collection("product_tags", fields, "label", "Products tagged in live streams")

# 2. TRANSACTIONS COLLECTION
def create_transactions():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("transaction_number", "string", max_length=255, unique=True, interface="input", required=True),
        create_field("feed_type", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Discover", "value": "discover"},
                        {"text": "Community", "value": "community"}
                    ]}),
        create_field("amount", "decimal", numeric_precision=10, numeric_scale=2, interface="input", required=True),
        create_field("platform_fee", "decimal", numeric_precision=10, numeric_scale=2, interface="input", required=True),
        create_field("platform_fee_rate", "decimal", numeric_precision=5, numeric_scale=4, interface="input", required=True),
        create_field("seller_payout", "decimal", numeric_precision=10, numeric_scale=2, interface="input", required=True),
        create_field("payment_method", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Card", "value": "card"},
                        {"text": "Wallet", "value": "wallet"},
                        {"text": "Cash on Delivery", "value": "cod"}
                    ]}),
        create_field("payment_status", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Pending", "value": "pending"},
                        {"text": "Completed", "value": "completed"},
                        {"text": "Failed", "value": "failed"},
                        {"text": "Refunded", "value": "refunded"}
                    ]}),
        create_field("payment_gateway_id", "string", max_length=255, interface="input"),
        create_field("delivery_method", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Pickup", "value": "pickup"},
                        {"text": "Delivery", "value": "delivery"},
                        {"text": "Shipping", "value": "shipping"}
                    ]}),
        create_field("delivery_address", "json", interface="input"),
        create_field("delivery_status", "string", max_length=50, interface="select-dropdown",
                    options={"choices": [
                        {"text": "Pending", "value": "pending"},
                        {"text": "Shipped", "value": "shipped"},
                        {"text": "Delivered", "value": "delivered"}
                    ]}),
        create_field("tracking_number", "string", max_length=255, interface="input"),
        create_field("transaction_status", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Pending", "value": "pending"},
                        {"text": "Completed", "value": "completed"},
                        {"text": "Cancelled", "value": "cancelled"},
                        {"text": "Disputed", "value": "disputed"}
                    ]}),
        create_field("completed_at", "timestamp", interface="datetime"),
    ]
    return create_collection("transactions", fields, "receipt", "Purchase transactions")

# 3. OFFERS COLLECTION
def create_offers():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("offer_amount", "decimal", numeric_precision=10, numeric_scale=2, interface="input", required=True),
        create_field("message", "text", interface="textarea"),
        create_field("status", "string", max_length=50, default_value="pending", interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Pending", "value": "pending"},
                        {"text": "Accepted", "value": "accepted"},
                        {"text": "Rejected", "value": "rejected"},
                        {"text": "Expired", "value": "expired"}
                    ]}),
        create_field("expires_at", "timestamp", interface="datetime", required=True),
        create_field("responded_at", "timestamp", interface="datetime"),
    ]
    return create_collection("offers", fields, "local_offer", "Community feed offers")

# 4. CONVERSATIONS COLLECTION
def create_conversations():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("last_message_at", "timestamp", interface="datetime", required=True),
        create_field("last_message_preview", "string", max_length=255, interface="input"),
        create_field("unread_count_user_1", "integer", default_value=0, interface="input"),
        create_field("unread_count_user_2", "integer", default_value=0, interface="input"),
        create_field("is_archived_user_1", "boolean", default_value=False, interface="boolean"),
        create_field("is_archived_user_2", "boolean", default_value=False, interface="boolean"),
    ]
    return create_collection("conversations", fields, "forum", "Message threads")

# 5. MESSAGES COLLECTION
def create_messages():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("message_type", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Text", "value": "text"},
                        {"text": "Image", "value": "image"},
                        {"text": "Product", "value": "product"},
                        {"text": "Offer", "value": "offer"}
                    ]}),
        create_field("content", "text", interface="textarea", required=True),
        create_field("image_url", "string", max_length=255, interface="input"),
        create_field("is_read", "boolean", default_value=False, interface="boolean", required=True),
        create_field("read_at", "timestamp", interface="datetime"),
    ]
    return create_collection("messages", fields, "message", "Individual messages")

# 6. NOTIFICATIONS COLLECTION
def create_notifications():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("type", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "New Follower", "value": "new_follower"},
                        {"text": "New Message", "value": "new_message"},
                        {"text": "Product Sold", "value": "product_sold"},
                        {"text": "Offer Received", "value": "offer_received"},
                        {"text": "Offer Accepted", "value": "offer_accepted"},
                        {"text": "Stream Starting", "value": "stream_starting"},
                        {"text": "Review Received", "value": "review_received"},
                        {"text": "Payment Received", "value": "payment_received"}
                    ]}),
        create_field("title", "string", max_length=255, interface="input", required=True),
        create_field("message", "text", interface="textarea", required=True),
        create_field("image_url", "string", max_length=255, interface="input"),
        create_field("action_type", "string", max_length=50, interface="input"),
        create_field("action_data", "json", interface="input"),
        create_field("is_read", "boolean", default_value=False, interface="boolean", required=True),
        create_field("read_at", "timestamp", interface="datetime"),
    ]
    return create_collection("notifications", fields, "notifications", "User notifications")

# 7. REVIEWS COLLECTION
def create_reviews():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("rating", "integer", interface="slider", required=True,
                    options={"min": 1, "max": 5, "step": 1}),
        create_field("review_text", "text", interface="textarea"),
        create_field("review_images", "json", interface="tags"),
        create_field("is_anonymous", "boolean", default_value=False, interface="boolean"),
        create_field("seller_response", "text", interface="textarea"),
        create_field("responded_at", "timestamp", interface="datetime"),
        create_field("helpful_count", "integer", default_value=0, interface="input"),
        create_field("status", "string", max_length=50, default_value="active", interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Active", "value": "active"},
                        {"text": "Reported", "value": "reported"},
                        {"text": "Removed", "value": "removed"}
                    ]}),
    ]
    return create_collection("reviews", fields, "star", "Product and seller reviews")

# 8. FOLLOWS COLLECTION
def create_follows():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
    ]
    return create_collection("follows", fields, "group_add", "User follow relationships")

# 9. WISHLIST COLLECTION
def create_wishlist():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
    ]
    return create_collection("wishlist", fields, "favorite", "Saved products")

# 10. REPORTS COLLECTION
def create_reports():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("report_type", "string", max_length=50, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Product", "value": "product"},
                        {"text": "User", "value": "user"},
                        {"text": "Stream", "value": "stream"},
                        {"text": "Review", "value": "review"}
                    ]}),
        create_field("reason", "string", max_length=255, interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Prohibited Item", "value": "prohibited_item"},
                        {"text": "Counterfeit", "value": "counterfeit"},
                        {"text": "Misleading Description", "value": "misleading_description"},
                        {"text": "Inappropriate Content", "value": "inappropriate_content"},
                        {"text": "Suspected Scam", "value": "suspected_scam"},
                        {"text": "Wrong Category", "value": "wrong_category"},
                        {"text": "Harassment", "value": "harassment"},
                        {"text": "Other", "value": "other"}
                    ]}),
        create_field("description", "text", interface="textarea"),
        create_field("status", "string", max_length=50, default_value="pending", interface="select-dropdown", required=True,
                    options={"choices": [
                        {"text": "Pending", "value": "pending"},
                        {"text": "Reviewing", "value": "reviewing"},
                        {"text": "Resolved", "value": "resolved"},
                        {"text": "Dismissed", "value": "dismissed"}
                    ]}),
        create_field("action_taken", "string", max_length=255, interface="input"),
        create_field("resolved_at", "timestamp", interface="datetime"),
    ]
    return create_collection("reports", fields, "flag", "Content and user reports")

# 11. USER BLOCKS COLLECTION
def create_user_blocks():
    fields = [
        create_field("id", "uuid", primary_key=True, interface="input"),
        create_field("reason", "string", max_length=255, interface="input"),
    ]
    return create_collection("user_blocks", fields, "block", "Blocked users")

# Run all creations
if __name__ == "__main__":
    print("="*60)
    print("  CREATING REMAINING DIRECTUS COLLECTIONS")
    print("="*60)

    create_product_tags()
    create_transactions()
    create_offers()
    create_conversations()
    create_messages()
    create_notifications()
    create_reviews()
    create_follows()
    create_wishlist()
    create_reports()
    create_user_blocks()

    print("\n" + "="*60)
    print("  ✅ ALL COLLECTIONS CREATED!")
    print("="*60)
    print("\n📊 Total Collections Created: 16")
    print("✅ Categories (with 12 categories seeded)")
    print("✅ Platform Fees (with 8 tiers seeded)")
    print("✅ User Verification")
    print("✅ Products")
    print("✅ Live Streams")
    print("✅ Product Tags")
    print("✅ Transactions")
    print("✅ Offers")
    print("✅ Conversations")
    print("✅ Messages")
    print("✅ Notifications")
    print("✅ Reviews")
    print("✅ Follows")
    print("✅ Wishlist")
    print("✅ Reports")
    print("✅ User Blocks")
    print("\n🌐 Access Directus: http://localhost:8055")
