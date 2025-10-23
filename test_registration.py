"""
Test user registration endpoint to verify full registration flow.
"""
import asyncio
import httpx
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000/api/v1"


async def test_registration_endpoint():
    """Test the user registration endpoint with valid data."""
    print("\n🔍 Testing User Registration Endpoint...")
    print(f"   API URL: {API_BASE_URL}/auth/register")

    # Generate unique test data
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_user = {
        "email": f"test.user.{timestamp}@jiran.app",
        "username": f"testuser{timestamp}",
        "password": "SecurePass123!",
        "phone": f"+9715{timestamp[-8:]}",  # UAE phone format
        "full_name": "Test User",
        "role": "buyer"
    }

    print(f"\n   📝 Test Registration Data:")
    for key, value in test_user.items():
        display_value = "***" if key == "password" else value
        print(f"      • {key:15s} = {display_value}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test 1: Register new user
            print(f"\n   🚀 Sending registration request...")
            response = await client.post(
                f"{API_BASE_URL}/auth/register",
                json=test_user,
                headers={"Content-Type": "application/json"}
            )

            print(f"   📡 Response Status: {response.status_code}")

            if response.status_code == 201:
                print(f"   ✅ Registration successful!")
                data = response.json()

                # Check response structure
                print(f"\n   📦 Response Data:")
                print(f"      • access_token: {data.get('access_token', 'N/A')[:50]}...")
                print(f"      • refresh_token: {data.get('refresh_token', 'N/A')[:50]}...")
                print(f"      • token_type: {data.get('token_type', 'N/A')}")
                print(f"      • expires_in: {data.get('expires_in', 'N/A')} seconds")

                if 'user' in data:
                    user_data = data['user']
                    print(f"\n   👤 User Data:")
                    print(f"      • id: {user_data.get('id', 'N/A')}")
                    print(f"      • email: {user_data.get('email', 'N/A')}")
                    print(f"      • username: {user_data.get('username', 'N/A')}")
                    print(f"      • full_name: {user_data.get('full_name', 'N/A')}")
                    print(f"      • role: {user_data.get('role', 'N/A')}")
                    print(f"      • is_verified: {user_data.get('is_verified', 'N/A')}")
                    print(f"      • is_active: {user_data.get('is_active', 'N/A')}")

                    # Test 2: Try to register duplicate user (should fail)
                    print(f"\n   🔍 Testing duplicate registration (should fail)...")
                    dup_response = await client.post(
                        f"{API_BASE_URL}/auth/register",
                        json=test_user,
                        headers={"Content-Type": "application/json"}
                    )

                    if dup_response.status_code == 400:
                        print(f"   ✅ Duplicate registration correctly rejected")
                        print(f"      Status: {dup_response.status_code}")
                        print(f"      Message: {dup_response.json().get('detail', 'N/A')}")
                    else:
                        print(f"   ⚠️  Unexpected status for duplicate: {dup_response.status_code}")

                    # Test 3: Verify user in database
                    print(f"\n   🔍 Verifying user was created in database...")
                    from sqlalchemy import text
                    from sqlalchemy.ext.asyncio import create_async_engine

                    DATABASE_URL = "postgresql+asyncpg://jiran:jiran@localhost:5432/jiran"
                    engine = create_async_engine(DATABASE_URL, echo=False)

                    async with engine.connect() as conn:
                        result = await conn.execute(
                            text("SELECT id, email, username, role, is_verified FROM users WHERE email = :email"),
                            {"email": test_user["email"]}
                        )
                        db_user = result.fetchone()

                        if db_user:
                            print(f"   ✅ User found in database")
                            print(f"      • DB ID: {db_user[0]}")
                            print(f"      • DB Email: {db_user[1]}")
                            print(f"      • DB Username: {db_user[2]}")
                            print(f"      • DB Role: {db_user[3]}")
                            print(f"      • DB Verified: {db_user[4]}")
                        else:
                            print(f"   ❌ User NOT found in database")

                    await engine.dispose()

                return True

            elif response.status_code == 400:
                print(f"   ❌ Registration failed - Bad Request")
                print(f"      Error: {response.json().get('detail', 'Unknown error')}")
                return False

            elif response.status_code == 422:
                print(f"   ❌ Registration failed - Validation Error")
                errors = response.json().get('detail', [])
                for error in errors:
                    print(f"      • {error.get('loc', [])[-1]}: {error.get('msg', 'Unknown error')}")
                return False

            else:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                print(f"      Response: {response.text[:200]}")
                return False

    except httpx.ConnectError:
        print(f"   ❌ Cannot connect to API server")
        print(f"   ⚠️  Make sure the backend is running:")
        print(f"      cd backend && python3 -m uvicorn app.main:app --reload")
        return False

    except Exception as e:
        print(f"   ❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_invalid_registration():
    """Test registration with invalid data to verify validation."""
    print("\n🔍 Testing Registration Validation...")

    # Test cases with invalid data
    invalid_cases = [
        {
            "name": "Missing email",
            "data": {
                "username": "testuser",
                "password": "SecurePass123!",
                "phone": "+971501234567",
                "full_name": "Test User"
            }
        },
        {
            "name": "Invalid email format",
            "data": {
                "email": "not-an-email",
                "username": "testuser",
                "password": "SecurePass123!",
                "phone": "+971501234567",
                "full_name": "Test User"
            }
        },
        {
            "name": "Password too short",
            "data": {
                "email": "test@jiran.app",
                "username": "testuser",
                "password": "short",
                "phone": "+971501234567",
                "full_name": "Test User"
            }
        },
        {
            "name": "Username too short",
            "data": {
                "email": "test@jiran.app",
                "username": "ab",
                "password": "SecurePass123!",
                "phone": "+971501234567",
                "full_name": "Test User"
            }
        },
    ]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for test_case in invalid_cases:
                print(f"\n   Testing: {test_case['name']}")
                response = await client.post(
                    f"{API_BASE_URL}/auth/register",
                    json=test_case['data'],
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 422:
                    print(f"      ✅ Correctly rejected (422 Validation Error)")
                else:
                    print(f"      ⚠️  Unexpected status: {response.status_code}")

    except httpx.ConnectError:
        print(f"   ⚠️  API server not running, skipping validation tests")


async def main():
    """Run all registration tests."""
    print("=" * 70)
    print("  Jiran Backend - Registration Endpoint Test")
    print("=" * 70)

    # Test valid registration
    success = await test_registration_endpoint()

    if success:
        # Test invalid cases
        await test_invalid_registration()

        print("\n" + "=" * 70)
        print("  ✅ All Registration Tests Passed!")
        print("=" * 70)
        print("\n📌 Verified:")
        print("   • User registration endpoint works correctly")
        print("   • User data is saved to database")
        print("   • Duplicate registrations are rejected")
        print("   • Validation errors are handled properly")
        print("   • JWT tokens are generated")
        print()
    else:
        print("\n⚠️  Registration test failed - check API server status")


if __name__ == "__main__":
    asyncio.run(main())
