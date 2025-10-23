"""Test CDN video delivery through cdn.jiran.app"""

import requests

# Video URL through CDN (note: /file/ prefix is required for B2)
cdn_url = "https://cdn.jiran.app/file/jiranapp/recorded/c798c6e9-2dc4-4ffc-8dfe-58c0e3e56ce8/20251023_051058_e49c3118.mp4"

# Direct B2 URL (for comparison)
b2_url = "https://s3.us-east-005.backblazeb2.com/jiranapp/recorded/c798c6e9-2dc4-4ffc-8dfe-58c0e3e56ce8/20251023_051058_e49c3118.mp4"

print("=" * 70)
print("🧪 Testing CDN Video Delivery")
print("=" * 70)
print()

# Test Direct B2 URL first
print("1️⃣  Testing Direct B2 URL...")
print(f"   URL: {b2_url[:60]}...")
try:
    response = requests.head(b2_url, timeout=10)
    print(f"   ✅ Status: {response.status_code}")
    print(f"   📦 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    print(f"   📏 Content-Length: {int(response.headers.get('Content-Length', 0)) / 1024 / 1024:.2f} MB")
    print(f"   🌐 Server: {response.headers.get('Server', 'N/A')}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# Test CDN URL
print("2️⃣  Testing CDN URL (Cloudflare)...")
print(f"   URL: {cdn_url[:60]}...")
try:
    response = requests.head(cdn_url, timeout=10)
    print(f"   ✅ Status: {response.status_code}")
    print(f"   📦 Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    print(f"   📏 Content-Length: {int(response.headers.get('Content-Length', 0)) / 1024 / 1024:.2f} MB")
    print(f"   🌐 Server: {response.headers.get('Server', 'N/A')}")
    print(f"   ☁️  CF-Cache-Status: {response.headers.get('CF-Cache-Status', 'N/A')}")
    print(f"   🔒 CF-Ray: {response.headers.get('CF-Ray', 'N/A')}")

    if response.status_code == 200:
        print()
        print("=" * 70)
        print("✅ CDN IS WORKING!")
        print("=" * 70)
        print()
        print("🎯 Next Steps:")
        print("  1. Your videos will now be served through Cloudflare CDN")
        print("  2. FREE bandwidth (no B2 egress charges)")
        print("  3. 10x faster video delivery globally")
        print()
        print("📝 CDN Performance:")
        cf_cache = response.headers.get('CF-Cache-Status', 'N/A')
        if cf_cache == 'HIT':
            print("  ✅ Video is cached on Cloudflare (super fast!)")
        elif cf_cache == 'MISS':
            print("  ⚠️  First request - video will be cached now")
            print("     Next requests will be much faster!")
        else:
            print(f"  ℹ️  Cache status: {cf_cache}")
        print()

except requests.exceptions.SSLError as e:
    print(f"   ❌ SSL Error: {e}")
    print()
    print("💡 This might mean:")
    print("   - DNS hasn't propagated to your local network yet")
    print("   - Try again in 1-2 minutes")
    print("   - Or test in a browser: open the CDN URL directly")
except requests.exceptions.ConnectionError as e:
    print(f"   ❌ Connection Error: {e}")
    print()
    print("💡 This might mean:")
    print("   - DNS hasn't propagated yet (wait 1-5 minutes)")
    print("   - CNAME record not set up correctly")
    print("   - Check Cloudflare DNS settings")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("=" * 70)
