"""
Test B2 using bucket ID approach
"""
import os
from dotenv import load_dotenv
import boto3

load_dotenv()

key_id = os.getenv('B2_ACCESS_KEY_ID')
app_key = os.getenv('B2_SECRET_ACCESS_KEY')
endpoint = os.getenv('B2_ENDPOINT_URL')

# Try with bucket ID
bucket_id = "ffb771481d6102289baa0a19"

print("=" * 60)
print("Testing with Bucket ID")
print("=" * 60)

print(f"\nTrying to access bucket using ID: {bucket_id}")

try:
    s3 = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=key_id,
        aws_secret_access_key=app_key,
        region_name='us-east-1'
    )

    # Try to list objects in bucket using bucket ID
    print("\nAttempting to list objects using bucket ID...")
    try:
        response = s3.list_objects_v2(Bucket=bucket_id, MaxKeys=1)
        print(f"✅ SUCCESS using bucket ID!")
        print(f"   Bucket contents: {response.get('KeyCount', 0)} objects")
    except Exception as e:
        print(f"❌ Failed with bucket ID: {e}")

    # Try with bucket name
    print("\nAttempting to list objects using bucket name 'jiranapp'...")
    try:
        response = s3.list_objects_v2(Bucket='jiranapp', MaxKeys=1)
        print(f"✅ SUCCESS using bucket name!")
        print(f"   Bucket contents: {response.get('KeyCount', 0)} objects")
    except Exception as e:
        print(f"❌ Failed with bucket name: {e}")

except Exception as e:
    print(f"\n❌ Client creation failed: {e}")

print("\n" + "=" * 60)
print("\nPlease check your Backblaze B2 dashboard:")
print("1. Go to 'Account' → 'App Keys'")
print("2. Look for 'Account ID' at the top of the page")
print("3. Send me that Account ID")
print("=" * 60)
