"""
Test script to upload a sample video to Backblaze B2 and create a product with video.

This script:
1. Downloads a sample video from a public URL
2. Uploads it directly to Backblaze B2
3. Creates a product entry with the video URL
4. Prints the video URL for testing in the app
"""

import asyncio
import hashlib
import os
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import select
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database import async_session_maker
from app.models.product import Product, ProductCategory, FeedType
from app.models.user import User
from app.storage.b2_config import B2Config


async def download_sample_video(url: str, output_path: str) -> bool:
    """Download a sample video from a public URL."""
    print(f"📥 Downloading sample video from {url}...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=60.0)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                f.write(response.content)

            file_size = os.path.getsize(output_path)
            print(f"✅ Downloaded {file_size / 1024 / 1024:.2f} MB to {output_path}")
            return True
    except Exception as e:
        print(f"❌ Failed to download video: {e}")
        return False


async def upload_video_to_b2(file_path: str, user_id: str) -> tuple[str, str] | None:
    """Upload video to Backblaze B2 and return video URL and file key."""
    print(f"☁️  Uploading video to Backblaze B2...")

    try:
        # Read video file
        with open(file_path, 'rb') as f:
            content = f.read()

        file_size = len(content)
        print(f"   File size: {file_size / 1024 / 1024:.2f} MB")

        # Generate unique key
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        file_key = f"recorded/{user_id}/{timestamp}_{unique_id}.mp4"

        # Get S3 client and upload
        s3_client = B2Config.get_s3_client()
        bucket_name = B2Config.BUCKET_VIDEOS

        print(f"   Uploading to bucket: {bucket_name}")
        print(f"   File key: {file_key}")

        # Upload to B2
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=content,
            ContentType='video/mp4',
            Metadata={
                'user_id': user_id,
                'upload_type': 'test',
                'uploaded_at': datetime.now().isoformat()
            }
        )

        # Generate public URL
        video_url = f"{B2Config.ENDPOINT_URL}/{bucket_name}/{file_key}"

        print(f"✅ Video uploaded successfully!")
        print(f"   URL: {video_url}")

        return video_url, file_key

    except Exception as e:
        print(f"❌ Failed to upload video: {e}")
        import traceback
        traceback.print_exc()
        return None


async def create_product_with_video(
    video_url: str,
    video_key: str,
    user_id: str,
    title: str = "Test Video Product",
    description: str = "🎬 First real video uploaded to Backblaze B2! Testing the full integration pipeline."
) -> Product | None:
    """Create a product with video in the database."""
    print(f"💾 Creating product with video in database...")

    async with async_session_maker() as session:
        try:
            # Use a placeholder thumbnail (can be enhanced later with real thumbnail extraction)
            thumbnail_url = "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80"

            # Create product with video
            product = Product(
                id=uuid.uuid4(),
                seller_id=uuid.UUID(user_id),
                title=title,
                description=description,
                price=Decimal("99.99"),
                currency="AED",
                category=ProductCategory.ELECTRONICS,
                feed_type=FeedType.DISCOVER,
                is_available=True,
                video_url=video_url,
                video_thumbnail_url=thumbnail_url,
                image_urls=[thumbnail_url],  # Use thumbnail as product image
                tags=[],
                view_count=0,
                like_count=0
            )

            session.add(product)
            await session.commit()
            await session.refresh(product)

            print(f"✅ Product created with ID: {product.id}")
            return product

        except Exception as e:
            await session.rollback()
            print(f"❌ Failed to create product: {e}")
            import traceback
            traceback.print_exc()
            return None


async def get_or_create_test_user() -> str | None:
    """Get or create a test user for video uploads."""
    async with async_session_maker() as session:
        try:
            # Try to find existing test user
            result = await session.execute(
                select(User).where(User.email == 'test@jiran.app').limit(1)
            )
            user = result.scalar_one_or_none()

            if user:
                print(f"✅ Using existing test user: {user.email} (ID: {user.id})")
                return str(user.id)

            # Create test user
            print("👤 Creating test user...")
            user = User(
                id=uuid.uuid4(),
                email='test@jiran.app',
                phone='+971500000000',  # Required field
                password_hash='$2b$12$dummyhashfortesting',  # Required field (placeholder)
                username='testuser',
                full_name='Test User',
                is_verified=True,
                is_active=True
            )

            session.add(user)
            await session.commit()
            await session.refresh(user)

            print(f"✅ Test user created: {user.email} (ID: {user.id})")
            return str(user.id)

        except Exception as e:
            await session.rollback()
            print(f"❌ Failed to get/create test user: {e}")
            import traceback
            traceback.print_exc()
            return None


async def main():
    """Main test flow."""
    print("=" * 70)
    print("🎬 Backblaze B2 Video Upload Test")
    print("=" * 70)
    print()

    # Sample video URL (Flutter's sample bee.mp4)
    sample_video_url = "https://flutter.github.io/assets-for-api-docs/assets/videos/bee.mp4"
    temp_video_path = "/tmp/test_video.mp4"

    # Step 1: Get or create test user
    print("Step 1: Get/Create Test User")
    print("-" * 70)
    user_id = await get_or_create_test_user()
    if not user_id:
        print("\n❌ Failed to get test user. Exiting.")
        return

    print()

    # Step 2: Download sample video
    print("Step 2: Download Sample Video")
    print("-" * 70)
    if not await download_sample_video(sample_video_url, temp_video_path):
        print("\n❌ Failed to download sample video. Exiting.")
        return

    print()

    # Step 3: Upload to B2
    print("Step 3: Upload to Backblaze B2")
    print("-" * 70)
    result = await upload_video_to_b2(temp_video_path, user_id)
    if not result:
        print("\n❌ Failed to upload video to B2. Exiting.")
        return

    video_url, video_key = result
    print()

    # Step 4: Create product with video in database
    print("Step 4: Create Product in Database")
    print("-" * 70)
    product = await create_product_with_video(
        video_url=video_url,
        video_key=video_key,
        user_id=user_id,
        title="Backblaze B2 Test Video",
        description="🎬 Testing real video upload and playback from B2! This is a sample video to verify the integration works."
    )

    if not product:
        print("\n❌ Failed to create product with video. Exiting.")
        return

    print()
    print("=" * 70)
    print("✅ SUCCESS! Video uploaded and ready for testing")
    print("=" * 70)
    print()
    print(f"📦 Product ID: {product.id}")
    print(f"📹 Video URL: {video_url}")
    print(f"🔑 Video Key: {video_key}")
    print(f"📸 Thumbnail: {product.video_thumbnail_url}")
    print(f"👤 User ID: {user_id}")
    print(f"💰 Price: {product.price} {product.currency}")
    print(f"📂 Feed Type: {product.feed_type.value}")
    print()
    print("🎯 Next steps:")
    print("1. Restart your Flutter app")
    print("2. Navigate to Discover feed")
    print("3. You should see the video in the feed!")
    print()
    print("📝 Note: The frontend .env file has been updated to disable mock data.")
    print()

    # Cleanup
    if os.path.exists(temp_video_path):
        os.remove(temp_video_path)
        print(f"🧹 Cleaned up temporary file: {temp_video_path}")


if __name__ == "__main__":
    asyncio.run(main())
