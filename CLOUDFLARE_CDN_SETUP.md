# Cloudflare CDN Setup for Backblaze B2

## Why Cloudflare + B2?

- **FREE bandwidth** (Backblaze waives egress fees)
- **10x faster** video delivery
- **Global CDN** with 200+ locations
- **DDoS protection** included
- **Easy setup** (5-10 minutes)

---

## Step-by-Step Setup Guide

### Prerequisites
- ✅ Backblaze B2 account (you have this)
- ✅ B2 bucket with videos (you have this: `jiranapp`)
- ⚠️ A domain name (e.g., `cdn.jiran.app` or `videos.jiran.app`)

---

### Step 1: Create Cloudflare Account (If You Don't Have One)

1. Go to: https://dash.cloudflare.com/sign-up
2. Sign up with your email
3. **Free plan is perfect** for this use case

---

### Step 2: Add Your Domain to Cloudflare

**If you already have `jiran.app` domain:**

1. Log in to Cloudflare Dashboard
2. Click **"Add a Site"**
3. Enter: `jiran.app`
4. Select **Free Plan**
5. Cloudflare will scan your DNS records
6. Update your domain's nameservers to Cloudflare's nameservers
   - Go to your domain registrar (GoDaddy, Namecheap, etc.)
   - Replace existing nameservers with Cloudflare's (they'll provide these)
   - Wait 5-60 minutes for DNS propagation

**If you don't have a domain yet:**
- You can buy one from Namecheap, GoDaddy, or Cloudflare itself
- Recommended: `cdn.jiran.app` or use a subdomain

---

### Step 3: Create a CNAME Record for B2

Once your domain is on Cloudflare:

1. In Cloudflare Dashboard, go to **DNS** tab
2. Click **"Add Record"**
3. Fill in:
   ```
   Type: CNAME
   Name: cdn (or videos, or media - your choice)
   Target: s3.us-east-005.backblazeb2.com
   Proxy status: ✅ Proxied (orange cloud)
   TTL: Auto
   ```
4. Click **Save**

**Result**: You'll have `cdn.jiran.app` pointing to your B2 bucket through Cloudflare's CDN

---

### Step 4: Configure Cloudflare Page Rules (Important!)

This ensures proper caching of videos:

1. Go to **Rules** → **Page Rules**
2. Click **"Create Page Rule"**
3. Fill in:
   ```
   URL: cdn.jiran.app/*
   Settings:
   - Cache Level: Cache Everything
   - Edge Cache TTL: 1 month (2592000 seconds)
   - Browser Cache TTL: 4 hours
   ```
4. Click **Save and Deploy**

---

### Step 5: Update Your Backend .env File

Open `/Users/saleemjadallah/Desktop/Soukloop/backend/.env` and update:

```bash
# Before
B2_CDN_URL=

# After
B2_CDN_URL=https://cdn.jiran.app/jiranapp
```

**Explanation**:
- `cdn.jiran.app` = Your Cloudflare CNAME
- `/jiranapp` = Your B2 bucket name

---

### Step 6: Update Video URL Generation in Backend

Your backend should use `B2_CDN_URL` instead of `B2_ENDPOINT_URL` when serving video URLs to the frontend.

**Example**:
```python
# Instead of:
video_url = f"{B2_ENDPOINT_URL}/{bucket_name}/{file_key}"
# https://s3.us-east-005.backblazeb2.com/jiranapp/recorded/...

# Use:
video_url = f"{B2_CDN_URL}/{file_key}"
# https://cdn.jiran.app/jiranapp/recorded/...
```

This way:
- Videos are served through Cloudflare CDN
- Faster delivery
- No B2 bandwidth charges
- Better user experience

---

### Step 7: Test the CDN URL

Once set up, test your video URL:

**Before (Direct B2)**:
```
https://s3.us-east-005.backblazeb2.com/jiranapp/recorded/c798c6e9-2dc4-4ffc-8dfe-58c0e3e56ce8/20251023_051058_e49c3118.mp4
```

**After (Cloudflare CDN)**:
```
https://cdn.jiran.app/jiranapp/recorded/c798c6e9-2dc4-4ffc-8dfe-58c0e3e56ce8/20251023_051058_e49c3118.mp4
```

Open the CDN URL in your browser - it should load the video faster!

---

## Alternative: If You Don't Have a Domain

### Option A: Use Backblaze's Built-in CDN Domain

Backblaze provides a free CDN-friendly URL:

```
https://f005.backblazeb2.com/file/jiranapp/recorded/...
```

Update your .env:
```bash
B2_CDN_URL=https://f005.backblazeb2.com/file/jiranapp
```

**Pros**: Easy, no domain needed
**Cons**: Less control, slower than Cloudflare

### Option B: Use Cloudflare without Custom Domain

You can use Cloudflare Workers to proxy B2 without a custom domain (more advanced).

---

## Performance Comparison

| Metric | Direct B2 | With Cloudflare CDN |
|--------|-----------|---------------------|
| **First Load** | 3-5 seconds | 0.5-1 second |
| **Cached Load** | 3-5 seconds | 0.2-0.5 seconds |
| **Bandwidth Cost** | $0.01/GB | $0 (FREE) |
| **Global Speed** | Slow in some regions | Fast everywhere |

---

## Verification Checklist

After setup, verify:

- [ ] CDN URL loads video in browser
- [ ] Video plays smoothly
- [ ] Check Cloudflare Analytics (should show requests)
- [ ] Test from different locations (use VPN or ask friends)
- [ ] Backend returns CDN URLs instead of direct B2 URLs

---

## Security Considerations

### Option 1: Keep It Simple (Current)
- Anyone with the URL can view videos
- Good for public content

### Option 2: Signed URLs (Advanced)
- Generate time-limited URLs
- Better for private/premium content
- Requires backend changes

For now, Option 1 is fine for testing!

---

## Troubleshooting

### Video returns 404 or 403
- Check CNAME record is correct
- Verify bucket name in URL
- Ensure B2 bucket is public

### Video loads slowly
- Check Cloudflare proxy is enabled (orange cloud)
- Verify Page Rules are set up correctly
- Clear Cloudflare cache: Dashboard → Caching → Purge Everything

### CORS errors
- CORS is already configured on B2
- Cloudflare passes through CORS headers automatically
- No additional configuration needed

---

## Next Steps After CDN Setup

1. Update backend to use B2_CDN_URL
2. Regenerate video URLs for existing products
3. Test video playback in Flutter app
4. Monitor Cloudflare analytics
5. Enjoy faster videos and no bandwidth costs! 🚀

---

## Cost Breakdown

**Without CDN** (1000 users watching 1 video):
- Storage: $0.005/GB
- Bandwidth: $0.01/GB × 1.3MB × 1000 = **$13/month**

**With Cloudflare CDN**:
- Storage: $0.005/GB
- Bandwidth: **$0 (FREE)**
- Total: **$0.005/month** 💰

**Savings**: ~$12.995/month per 1000 views!
