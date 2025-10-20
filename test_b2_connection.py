"""
Test Backblaze B2 Connection

This script tests the B2 configuration and connection.
Run with: python test_b2_connection.py
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.storage.b2_config import B2Config


def test_b2_connection():
    """Test B2 configuration and connection"""

    print("=" * 60)
    print("Testing Backblaze B2 Connection")
    print("=" * 60)

    # Test 1: Validate configuration
    print("\n1. Validating B2 configuration...")
    try:
        B2Config.validate_config()
        print("   ✅ Configuration is valid")
    except ValueError as e:
        print(f"   ❌ Configuration error: {e}")
        return False

    # Test 2: Display configuration (sanitized)
    print("\n2. Configuration details:")
    print(f"   Endpoint: {B2Config.ENDPOINT_URL}")
    print(f"   Region: {B2Config.REGION}")
    print(f"   Access Key ID: {B2Config.ACCESS_KEY_ID[:10]}...")
    print(f"   Bucket (Photos): {B2Config.BUCKET_PHOTOS}")
    print(f"   Bucket (Videos): {B2Config.BUCKET_VIDEOS}")
    print(f"   Bucket (Live): {B2Config.BUCKET_LIVE_VIDEOS}")
    print(f"   Bucket (Thumbnails): {B2Config.BUCKET_THUMBNAILS}")
    if B2Config.CDN_URL:
        print(f"   CDN URL: {B2Config.CDN_URL}")

    # Test 3: Create S3 client
    print("\n3. Creating S3 client...")
    try:
        s3_client = B2Config.get_s3_client()
        print("   ✅ S3 client created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create S3 client: {e}")
        return False

    # Test 4: List buckets
    print("\n4. Testing connection by listing buckets...")
    try:
        response = s3_client.list_buckets()
        buckets = response.get('Buckets', [])

        if buckets:
            print(f"   ✅ Connection successful! Found {len(buckets)} bucket(s):")
            for bucket in buckets:
                print(f"      - {bucket['Name']}")
        else:
            print("   ⚠️  Connection successful but no buckets found")
            print("      Make sure you've created the 'jiranapp' bucket in B2")

    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        print("\n   Common issues:")
        print("   - Check that Access Key ID and Secret Key are correct")
        print("   - Verify the endpoint URL matches your bucket's region")
        print("   - Ensure the application key has proper permissions")
        return False

    # Test 5: Check if our bucket exists
    print("\n5. Checking if 'jiranapp' bucket exists...")
    try:
        s3_client.head_bucket(Bucket=B2Config.BUCKET_PHOTOS)
        print("   ✅ Bucket 'jiranapp' found and accessible")
    except Exception as e:
        print(f"   ❌ Cannot access bucket 'jiranapp': {e}")
        print("      Make sure you've created this bucket in B2 dashboard")
        return False

    print("\n" + "=" * 60)
    print("✅ All tests passed! B2 is configured correctly.")
    print("=" * 60)
    print("\nYou can now upload files using the FastAPI endpoints:")
    print("  - POST /api/v1/media/photos/upload")
    print("  - POST /api/v1/media/videos/upload")
    print("\n")

    return True


if __name__ == "__main__":
    success = test_b2_connection()
    sys.exit(0 if success else 1)
