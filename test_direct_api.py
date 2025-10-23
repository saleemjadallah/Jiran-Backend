"""
Test registration directly using FastAPI TestClient to see actual errors.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from datetime import datetime


def test_registration():
    """Test registration with TestClient."""
    print("\n🔍 Testing Registration with TestClient...")

    client = TestClient(app)

    # Generate unique test data
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_user = {
        "email": f"test.direct.{timestamp}@jiran.app",
        "username": f"testdirect{timestamp}",
        "password": "SecurePass123!",
        "phone": f"+9715{timestamp[-8:]}",
        "full_name": "Test Direct User",
        "role": "buyer"
    }

    print(f"\n   📝 Test Data:")
    for key, value in test_user.items():
        display_value = "***" if key == "password" else value
        print(f"      • {key:15s} = {display_value}")

    print(f"\n   🚀 Sending request...")

    try:
        response = client.post(
            "/api/v1/auth/register",
            json=test_user,
        )

        print(f"   📡 Status: {response.status_code}")

        if response.status_code == 201:
            print(f"   ✅ Registration successful!")
            data = response.json()
            print(f"\n   📦 Response:")
            print(f"      • access_token: {data.get('access_token', 'N/A')[:50]}...")
            print(f"      • user.id: {data.get('user', {}).get('id', 'N/A')}")
            print(f"      • user.email: {data.get('user', {}).get('email', 'N/A')}")
            return True

        else:
            print(f"   ❌ Registration failed!")
            print(f"\n   Response Body:")
            print(f"      {response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("  Direct API Test - FastAPI TestClient")
    print("=" * 70)

    success = test_registration()

    print("\n" + "=" * 70)
    if success:
        print("  ✅ Test Passed!")
    else:
        print("  ❌ Test Failed - Check errors above")
    print("=" * 70)
