"""
Test Product Creation with Authentication

This script tests the video upload → product creation flow to debug the 401 error.
"""
import httpx
import asyncio
import json
from pathlib import Path


API_URL = "https://api.jiran.app/api/v1"
TEST_EMAIL = "test@jiran.app"
TEST_PASSWORD = "Test@123"


async def test_product_creation_flow():
    """Test the complete flow: login → video upload → product creation"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 60)
        print("STEP 1: Login")
        print("=" * 60)

        # Login
        login_response = await client.post(
            f"{API_URL}/auth/login",
            json={
                "identifier": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )

        print(f"Status: {login_response.status_code}")
        print(f"Response: {login_response.text[:200]}")

        if login_response.status_code != 200:
            print("❌ Login failed!")
            return

        login_data = login_response.json()
        access_token = login_data.get("access_token")

        if not access_token:
            print("❌ No access token in response!")
            return

        print(f"✅ Access token: {access_token[:50]}...")

        # Set authorization header
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        print("\n" + "=" * 60)
        print("STEP 2: Get current user info")
        print("=" * 60)

        # Get user info
        me_response = await client.get(
            f"{API_URL}/auth/me",
            headers=headers
        )

        print(f"Status: {me_response.status_code}")
        print(f"Response: {me_response.text[:300]}")

        if me_response.status_code != 200:
            print("❌ Get user failed!")
            return

        user_data = me_response.json()
        print(f"✅ User: {user_data.get('email')}, Role: {user_data.get('role')}")

        print("\n" + "=" * 60)
        print("STEP 3: Upload test video")
        print("=" * 60)

        # Create a small test video file (or use existing)
        test_video_path = Path("/tmp/test_video.mp4")
        if not test_video_path.exists():
            # Create a minimal MP4 file for testing
            with open(test_video_path, "wb") as f:
                f.write(b"fake video content for testing")

        # Upload video
        with open(test_video_path, "rb") as video_file:
            files = {
                "file": ("test_video.mp4", video_file, "video/mp4")
            }

            video_response = await client.post(
                f"{API_URL}/media/videos/upload",
                headers=headers,
                files=files,
                data={"video_type": "recorded"}
            )

        print(f"Status: {video_response.status_code}")
        print(f"Response: {video_response.text[:500]}")

        if video_response.status_code != 200:
            print("❌ Video upload failed!")
            return

        video_data = video_response.json()
        video_url = video_data.get("data", {}).get("file_url")
        thumbnail_url = video_data.get("data", {}).get("thumbnail_url")

        print(f"✅ Video URL: {video_url}")
        print(f"✅ Thumbnail URL: {thumbnail_url}")

        print("\n" + "=" * 60)
        print("STEP 4: Create product")
        print("=" * 60)

        # Prepare product data
        product_data = {
            "title": "Test Product from API",
            "description": "Testing product creation after video upload",
            "price": 100.00,
            "category": "electronics",
            "condition": "new",
            "feed_type": "community",
            "location": {
                "latitude": 25.0808,
                "longitude": 55.1398,
                "neighborhood": "Dubai Marina"
            },
            "video_url": video_url,
            "video_thumbnail_url": thumbnail_url,
            "tags": []
        }

        print(f"Headers being sent:")
        print(f"  Authorization: Bearer {access_token[:30]}...")
        print(f"  Content-Type: application/json")
        print(f"\nProduct data:")
        print(json.dumps(product_data, indent=2))

        # Create product
        product_response = await client.post(
            f"{API_URL}/products",
            headers=headers,
            json=product_data
        )

        print(f"\nStatus: {product_response.status_code}")
        print(f"Response: {product_response.text[:500]}")

        if product_response.status_code == 401:
            print("\n❌ 401 UNAUTHORIZED!")
            print("Possible causes:")
            print("  1. Token not being sent correctly")
            print("  2. Token expired between upload and product creation")
            print("  3. Token validation failing")
            print("\nResponse headers:")
            for key, value in product_response.headers.items():
                print(f"  {key}: {value}")
        elif product_response.status_code == 403:
            print("\n❌ 403 FORBIDDEN!")
            print("User doesn't have seller role")
        elif product_response.status_code == 201:
            print("\n✅ Product created successfully!")
            product_result = product_response.json()
            print(f"Product ID: {product_result.get('id')}")
        else:
            print(f"\n❌ Unexpected status code: {product_response.status_code}")


if __name__ == "__main__":
    asyncio.run(test_product_creation_flow())
