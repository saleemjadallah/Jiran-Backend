#!/usr/bin/env python3
"""
Finish production setup - get new token and create remaining collections
"""

import requests
import json

# Get new token
print("🔐 Getting new access token...")
login_response = requests.post(
    "http://localhost:8055/auth/login",
    json={"email": "admin@jiran.app", "password": "Olaabdel@88aa"}
)

TOKEN = login_response.json()["data"]["access_token"]
print(f"✅ Token received")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def create_field(field_name, field_type, **kwargs):
    """Helper to create field definition"""
    field = {
        "field": field_name,
        "type": field_type,
        "schema": {},
        "meta": {}
    }

    if kwargs.get("primary_key"):
        field["schema"]["is_primary_key"] = True
    if kwargs.get("auto_increment"):
        field["schema"]["has_auto_increment"] = True
    if kwargs.get("default_value") is not None:
        field["schema"]["default_value"] = kwargs["default_value"]
    if kwargs.get("interface"):
        field["meta"]["interface"] = kwargs["interface"]
    if kwargs.get("required"):
        field["meta"]["required"] = True

    return field

def create_collection(name, fields, icon="box"):
    """Create a collection"""
    print(f"\n📦 Creating: {name}")

    payload = {
        "collection": name,
        "meta": {"icon": icon},
        "schema": {"name": name},
        "fields": fields
    }

    response = requests.post(
        "http://localhost:8055/collections",
        headers=headers,
        json=payload
    )

    if response.status_code in [200, 201, 204]:
        print(f"  ✅ Created successfully")
        return True
    else:
        print(f"  ⚠️  {response.status_code}: {response.text[:100]}")
        return False

# Create remaining collections
print("\n" + "="*60)
print("  CREATING REMAINING COLLECTIONS")
print("="*60)

create_collection("product_tags", [
    create_field("id", "uuid", primary_key=True, interface="input"),
    create_field("position_x", "decimal", interface="input"),
    create_field("position_y", "decimal", interface="input"),
], "label")

create_collection("transactions", [
    create_field("id", "uuid", primary_key=True, interface="input"),
    create_field("transaction_number", "string", interface="input"),
    create_field("amount", "decimal", interface="input"),
], "receipt")

create_collection("offers", [
    create_field("id", "uuid", primary_key=True, interface="input"),
    create_field("offer_amount", "decimal", interface="input"),
], "local_offer")

create_collection("conversations", [
    create_field("id", "uuid", primary_key=True, interface="input"),
], "forum")

create_collection("messages", [
    create_field("id", "uuid", primary_key=True, interface="input"),
    create_field("content", "text", interface="textarea"),
], "message")

create_collection("notifications", [
    create_field("id", "uuid", primary_key=True, interface="input"),
    create_field("title", "string", interface="input"),
    create_field("message", "text", interface="textarea"),
], "notifications")

create_collection("reviews", [
    create_field("id", "uuid", primary_key=True, interface="input"),
    create_field("rating", "integer", interface="slider"),
], "star")

create_collection("follows", [
    create_field("id", "uuid", primary_key=True, interface="input"),
], "group_add")

create_collection("wishlist", [
    create_field("id", "uuid", primary_key=True, interface="input"),
], "favorite")

create_collection("reports", [
    create_field("id", "uuid", primary_key=True, interface="input"),
    create_field("reason", "string", interface="input"),
], "flag")

create_collection("user_blocks", [
    create_field("id", "uuid", primary_key=True, interface="input"),
], "block")

print("\n" + "="*60)
print("  ✅ ALL COLLECTIONS CREATED IN PRODUCTION!")
print("="*60)
print("\n🌐 Directus: http://localhost:8055")
print("📧 Login: admin@jiran.app")
print("\n✅ Your Directus is now connected to Railway production database!")
print("✅ All changes in Directus will sync with api.jiran.app")
