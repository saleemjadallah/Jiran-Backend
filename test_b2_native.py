"""
Test B2 with different authentication approaches
"""
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

# Get credentials
key_id = os.getenv('B2_ACCESS_KEY_ID')
app_key = os.getenv('B2_SECRET_ACCESS_KEY')
endpoint = os.getenv('B2_ENDPOINT_URL')
region = os.getenv('B2_REGION')

print("=" * 60)
print("B2 Connection Test - Different Approaches")
print("=" * 60)

print(f"\nCredentials:")
print(f"  Key ID: {key_id}")
print(f"  App Key: {app_key[:10]}...{app_key[-10:]}")
print(f"  Endpoint: {endpoint}")
print(f"  Region: {region}")

# Try different configurations
configs = [
    {
        "name": "Original configuration",
        "endpoint": endpoint,
        "region": region
    },
    {
        "name": "Without region",
        "endpoint": endpoint,
        "region": None
    },
    {
        "name": "Generic us-east-1 region",
        "endpoint": endpoint,
        "region": "us-east-1"
    }
]

for i, config in enumerate(configs, 1):
    print(f"\n{i}. Testing: {config['name']}")
    print(f"   Endpoint: {config['endpoint']}")
    print(f"   Region: {config['region']}")

    try:
        s3 = boto3.client(
            's3',
            endpoint_url=config['endpoint'],
            aws_access_key_id=key_id,
            aws_secret_access_key=app_key,
            region_name=config['region']
        )

        # Try to list buckets
        response = s3.list_buckets()
        buckets = response.get('Buckets', [])

        print(f"   ✅ SUCCESS! Found {len(buckets)} bucket(s):")
        for bucket in buckets:
            print(f"      - {bucket['Name']}")

        # If successful, try to access our bucket
        try:
            s3.head_bucket(Bucket='jiranapp')
            print(f"   ✅ Can access 'jiranapp' bucket!")
        except ClientError as e:
            print(f"   ⚠️  Cannot access 'jiranapp': {e}")

        break  # Stop if successful

    except ClientError as e:
        print(f"   ❌ Failed: {e}")
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
