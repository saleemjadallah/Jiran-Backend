"""
Test user registration with different roles: buyer, seller, both.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from datetime import datetime


def test_role_registration(role_type):
    """Test registration with specific role."""
    print(f"\n🔍 Testing Registration with Role: '{role_type}'")

    client = TestClient(app)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    test_user = {
        "email": f"test.{role_type}.{timestamp}@jiran.app",
        "username": f"test{role_type}{timestamp[:10]}",
        "password": "SecurePass123!",
        "phone": f"+9715{timestamp[-8:]}",
        "full_name": f"Test {role_type.title()} User",
        "role": role_type
    }

    print(f"   📝 Registration Data:")
    print(f"      • email: {test_user['email']}")
    print(f"      • username: {test_user['username']}")
    print(f"      • role: {test_user['role']}")

    try:
        response = client.post(
            "/api/v1/auth/register",
            json=test_user,
        )

        print(f"   📡 Status: {response.status_code}")

        if response.status_code == 201:
            print(f"   ✅ Registration successful!")
            data = response.json()
            user_data = data.get('user', {})
            print(f"   👤 User Created:")
            print(f"      • ID: {user_data.get('id')}")
            print(f"      • Role: {user_data.get('role')}")
            print(f"      • Is Verified: {user_data.get('is_verified')}")
            return True
        else:
            print(f"   ❌ Registration failed!")
            print(f"   Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False


def main():
    print("=" * 70)
    print("  User Role Registration Test")
    print("=" * 70)
    print("\n  Testing all role types: buyer, seller, both")

    roles = ["buyer", "seller", "both"]
    results = {}

    for role in roles:
        results[role] = test_role_registration(role)

    print("\n" + "=" * 70)
    print("  Test Results Summary")
    print("=" * 70)

    all_passed = all(results.values())

    for role, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {role.upper():10s} role registration")

    print("\n" + "=" * 70)
    if all_passed:
        print("  ✅ All Role Types Work Correctly!")
        print("=" * 70)
        print("\n  Users can register as:")
        print("   • Buyer (default) - Can purchase items")
        print("   • Seller - Can list and sell items")
        print("   • Both - Can both buy and sell")
        print("\n  Your app can now support all user types! 🎉")
    else:
        print("  ⚠️  Some Role Types Failed")
        print("=" * 70)
        print("\n  Check the errors above for details")

    print()

    # Verify in database
    print("\n🔍 Verifying Roles in Database...")
    import asyncio
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def verify_db():
        engine = create_async_engine('postgresql+asyncpg://jiran:jiran@localhost:5432/jiran', echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT role, COUNT(*) as count
                FROM users
                GROUP BY role
                ORDER BY role;
            """))
            print("\n   📊 Users by Role:")
            for row in result.fetchall():
                print(f"      • {row[0]:10s}: {row[1]} users")
        await engine.dispose()

    asyncio.run(verify_db())
    print()


if __name__ == "__main__":
    main()
