#!/usr/bin/env python3
"""Test script for ZeptoMail email configuration."""

import asyncio
import sys
from app.services.email_service import email_service


async def test_otp_email():
    """Test OTP verification email."""
    print("🧪 Testing OTP Email...")
    print("-" * 50)

    test_email = input("Enter your email address to test: ").strip()
    test_otp = "123456"
    test_name = "Test User"

    print(f"\n📧 Sending OTP email to: {test_email}")
    print(f"🔢 OTP Code: {test_otp}")

    result = await email_service.send_otp_email(
        email=test_email,
        otp=test_otp,
        user_name=test_name
    )

    if result:
        print("✅ OTP email sent successfully!")
        print(f"📬 Check your inbox at {test_email}")
    else:
        print("❌ Failed to send OTP email")
        print("Check SMTP configuration in .env")

    return result


async def test_welcome_email():
    """Test welcome email."""
    print("\n\n🧪 Testing Welcome Email...")
    print("-" * 50)

    test_email = input("Enter your email address to test: ").strip()
    test_name = "Test User"

    print(f"\n📧 Sending welcome email to: {test_email}")

    result = await email_service.send_welcome_email(
        email=test_email,
        name=test_name
    )

    if result:
        print("✅ Welcome email sent successfully!")
        print(f"📬 Check your inbox at {test_email}")
    else:
        print("❌ Failed to send welcome email")
        print("Check SMTP configuration in .env")

    return result


async def test_password_reset_email():
    """Test password reset email."""
    print("\n\n🧪 Testing Password Reset Email...")
    print("-" * 50)

    test_email = input("Enter your email address to test: ").strip()
    test_token = "test-reset-token-abc123xyz"
    test_name = "Test User"

    print(f"\n📧 Sending password reset email to: {test_email}")
    print(f"🔑 Reset Token: {test_token}")

    result = await email_service.send_password_reset_email(
        email=test_email,
        reset_token=test_token,
        user_name=test_name
    )

    if result:
        print("✅ Password reset email sent successfully!")
        print(f"📬 Check your inbox at {test_email}")
    else:
        print("❌ Failed to send password reset email")
        print("Check SMTP configuration in .env")

    return result


async def main():
    """Run all email tests."""
    print("\n" + "=" * 50)
    print("📮 Souk Loop Email Service Test")
    print("=" * 50)
    print(f"\n📡 SMTP Configuration:")
    print(f"   Host: {email_service.smtp_host}")
    print(f"   Port: {email_service.smtp_port}")
    print(f"   From: {email_service.from_email}")
    print(f"   Configured: {'✅ Yes' if email_service.is_configured else '❌ No'}")

    if not email_service.is_configured:
        print("\n❌ SMTP is not configured!")
        print("Please check your .env file and ensure:")
        print("  - SMTP_HOST is set")
        print("  - SMTP_USERNAME is set")
        print("  - SMTP_PASSWORD is set")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("Select test to run:")
    print("1. OTP Email")
    print("2. Welcome Email")
    print("3. Password Reset Email")
    print("4. All Tests")
    print("=" * 50)

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == "1":
        await test_otp_email()
    elif choice == "2":
        await test_welcome_email()
    elif choice == "3":
        await test_password_reset_email()
    elif choice == "4":
        print("\n🚀 Running all tests...")
        results = []
        results.append(await test_otp_email())
        results.append(await test_welcome_email())
        results.append(await test_password_reset_email())

        print("\n\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        print(f"OTP Email: {'✅ Passed' if results[0] else '❌ Failed'}")
        print(f"Welcome Email: {'✅ Passed' if results[1] else '❌ Failed'}")
        print(f"Password Reset Email: {'✅ Passed' if results[2] else '❌ Failed'}")
        print(f"\nTotal: {sum(results)}/3 passed")
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)

    print("\n✨ Test complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
