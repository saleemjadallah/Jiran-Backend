"""
Make Backblaze B2 bucket publicly readable.

This script configures the bucket policy to allow public read access
to all files in the bucket while keeping write access restricted.
"""

import boto3
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def make_bucket_public():
    """Configure bucket policy to allow public read access."""

    # Initialize S3 client for B2
    s3_client = boto3.client(
        's3',
        endpoint_url=os.getenv('B2_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('B2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('B2_SECRET_ACCESS_KEY'),
        region_name=os.getenv('B2_REGION')
    )

    bucket_name = os.getenv('B2_BUCKET_VIDEOS')

    print("=" * 70)
    print("🔓 Making Backblaze B2 Bucket Publicly Readable")
    print("=" * 70)
    print()
    print(f"📦 Bucket: {bucket_name}")
    print(f"🌐 Endpoint: {os.getenv('B2_ENDPOINT_URL')}")
    print()

    # Bucket policy to allow public read access
    # This allows anyone to GET (read/download) files but NOT upload/delete
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadAccess",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
            }
        ]
    }

    try:
        # Apply bucket policy
        print("⚙️  Applying public read bucket policy...")
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )

        print("✅ Bucket policy applied successfully!")
        print()

        # Verify the policy
        print("🔍 Verifying bucket policy...")
        response = s3_client.get_bucket_policy(Bucket=bucket_name)
        policy = json.loads(response['Policy'])

        print("✅ Current Bucket Policy:")
        print(json.dumps(policy, indent=2))
        print()

        print("=" * 70)
        print("✅ Bucket is Now Publicly Readable!")
        print("=" * 70)
        print()
        print("🎯 What this enables:")
        print("  • Anyone can view/download files from the bucket")
        print("  • Only you (with API keys) can upload/delete files")
        print("  • Videos will load in your Flutter app without auth")
        print()
        print("🔒 Security Notes:")
        print("  • Files are READ-ONLY to the public")
        print("  • Write operations still require authentication")
        print("  • Consider using signed URLs for sensitive content")
        print()
        print("📝 Next steps:")
        print("  1. Test video URL in browser")
        print("  2. Test video playback in Flutter app")
        print("  3. Video should load without errors!")
        print()

        # Show example URL
        example_url = f"{os.getenv('B2_ENDPOINT_URL')}/{bucket_name}/recorded/c798c6e9-2dc4-4ffc-8dfe-58c0e3e56ce8/20251023_051058_e49c3118.mp4"
        print("🔗 Test URL:")
        print(f"   {example_url}")
        print()

    except Exception as e:
        print(f"❌ Error configuring bucket policy: {e}")
        print()
        print("💡 Troubleshooting:")
        print("  • Verify B2 credentials in .env file")
        print("  • Check bucket name is correct")
        print("  • Ensure you have permission to modify bucket settings")
        print()
        print("⚠️  Note: Backblaze B2 might use 'Bucket Info' settings")
        print("   instead of S3-style bucket policies for public access.")
        print("   You may need to configure this in the B2 web console:")
        print("   Bucket Settings → Bucket Info → 'allPublic'")
        return False

    return True


if __name__ == "__main__":
    make_bucket_public()
