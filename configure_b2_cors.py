"""
Configure CORS for Backblaze B2 bucket to allow video playback from Flutter app.

This script sets up CORS rules to allow:
- Video playback from any origin (for development and production)
- GET and HEAD requests (needed for video streaming)
- Proper headers for video playback
"""

import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def configure_cors():
    """Configure CORS for the B2 bucket."""

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
    print("🔧 Configuring CORS for Backblaze B2 Bucket")
    print("=" * 70)
    print()
    print(f"📦 Bucket: {bucket_name}")
    print(f"🌐 Endpoint: {os.getenv('B2_ENDPOINT_URL')}")
    print()

    # CORS Configuration
    # This allows video playback from any origin with proper headers
    cors_configuration = {
        'CORSRules': [
            {
                'ID': 'AllowVideoPlayback',
                'AllowedOrigins': ['*'],  # Allow all origins (for dev/prod flexibility)
                'AllowedMethods': ['GET', 'HEAD'],  # Required for video streaming
                'AllowedHeaders': [
                    'Authorization',
                    'Content-Type',
                    'Range',  # Critical for video seeking/buffering
                    'Accept',
                    'Accept-Encoding',
                    'Accept-Language',
                    'User-Agent'
                ],
                'ExposeHeaders': [
                    'Content-Range',
                    'Content-Length',
                    'Content-Type',
                    'ETag',
                    'Accept-Ranges'
                ],
                'MaxAgeSeconds': 3600  # Cache preflight requests for 1 hour
            }
        ]
    }

    try:
        # Apply CORS configuration
        print("⚙️  Applying CORS configuration...")
        s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )

        print("✅ CORS configuration applied successfully!")
        print()

        # Verify the configuration
        print("🔍 Verifying CORS configuration...")
        response = s3_client.get_bucket_cors(Bucket=bucket_name)

        print("✅ Current CORS Rules:")
        print()

        for idx, rule in enumerate(response['CORSRules'], 1):
            print(f"Rule {idx}: {rule.get('ID', 'Unnamed')}")
            print(f"  Allowed Origins: {', '.join(rule['AllowedOrigins'])}")
            print(f"  Allowed Methods: {', '.join(rule['AllowedMethods'])}")
            print(f"  Allowed Headers: {len(rule.get('AllowedHeaders', []))} headers")
            print(f"  Exposed Headers: {len(rule.get('ExposeHeaders', []))} headers")
            print(f"  Max Age: {rule.get('MaxAgeSeconds', 0)} seconds")
            print()

        print("=" * 70)
        print("✅ CORS Configuration Complete!")
        print("=" * 70)
        print()
        print("🎯 What this enables:")
        print("  • Video playback from any origin (Flutter app, web, etc.)")
        print("  • Video seeking and buffering (Range requests)")
        print("  • Proper caching of CORS preflight requests")
        print()
        print("📝 Next steps:")
        print("  1. Test video playback in your Flutter app")
        print("  2. Videos should now load without CORS errors")
        print("  3. Consider restricting AllowedOrigins in production for security")
        print()

    except Exception as e:
        print(f"❌ Error configuring CORS: {e}")
        print()
        print("💡 Troubleshooting:")
        print("  • Verify B2 credentials in .env file")
        print("  • Check bucket name is correct")
        print("  • Ensure you have permission to modify bucket settings")
        return False

    return True


def show_security_recommendations():
    """Show security recommendations for production."""
    print()
    print("🔒 Security Recommendations for Production:")
    print("-" * 70)
    print()
    print("1. Restrict AllowedOrigins:")
    print("   Replace '*' with specific domains:")
    print("   - 'https://jiran.app'")
    print("   - 'https://api.jiran.app'")
    print("   - 'app://jiran' (for mobile app)")
    print()
    print("2. Use B2 CDN:")
    print("   Consider using Cloudflare or Bunny CDN with B2")
    print("   for better performance and additional security")
    print()
    print("3. Implement signed URLs:")
    print("   For sensitive videos, use time-limited signed URLs")
    print("   instead of public access")
    print()


if __name__ == "__main__":
    success = configure_cors()

    if success:
        show_security_recommendations()
