# Backend Authentication Setup - Souk Loop

## Overview

The Souk Loop backend has a complete authentication system with JWT tokens, email OTP verification, password reset, and session management. This document provides a comprehensive guide to the authentication infrastructure.

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# Required: Secure secret key (32+ characters)
SECRET_KEY="your-secure-32-character-random-string-here"

# Email Service (choose one provider)
# Option 1: ZeptoMail (recommended)
SMTP_HOST=smtp.zeptomail.com
SMTP_PORT=587
SMTP_USERNAME=emailappsmtp
SMTP_PASSWORD=your-zepto-send-mail-token
SMTP_FROM_EMAIL=Souk Loop <noreply@soukloop.com>

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/soukloop

# Redis
REDIS_URL=redis://localhost:6379/0
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Start Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

---

## 📋 Authentication Endpoints

Base URL: `http://localhost:8080/api/v1/auth`

### 1. Register User

**POST** `/auth/register`

Create a new user account and send OTP verification email.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "phone": "+971501234567",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "role": "buyer"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Flow:**
1. Validates email, username, phone uniqueness
2. Hashes password with Argon2
3. Creates user record (is_verified=False)
4. Generates 6-digit OTP
5. Stores OTP in Redis (10-minute expiry)
6. Sends OTP email (or SMS if phone provided)
7. Returns JWT tokens

---

### 2. Login User

**POST** `/auth/login`

Authenticate with email/username and password.

**Request Body:**
```json
{
  "identifier": "user@example.com",  // or username
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Notes:**
- Identifier can be email OR username
- Case-insensitive lookup
- Updates last_login_at timestamp

---

### 3. Send OTP

**POST** `/auth/send-otp`

Send a new OTP code for verification.

**Request Body:**
```json
{
  "email": "user@example.com"
  // OR
  "phone": "+971501234567"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent"
}
```

**Rate Limiting:**
- Max 3 OTP requests per hour per identifier
- Returns 429 Too Many Requests if exceeded

---

### 4. Verify OTP

**POST** `/auth/verify-otp`

Verify OTP code and mark user as verified.

**Request Body:**
```json
{
  "email": "user@example.com",
  "otp_code": "123456"
}
```

**Response:**
```json
{
  "success": true
}
```

**Effects:**
- Sets user.is_verified = True
- Deletes OTP from Redis
- Sends welcome email

---

### 5. Verify Email Link

**GET** `/auth/verify-email?code=123456&email=user@example.com`

One-click email verification via email link.

**Query Parameters:**
- `code`: 6-digit OTP code
- `email`: User's email address

**Response:**
```json
{
  "success": true,
  "message": "Email verified successfully",
  "redirect_url": "soukloop://verified"
}
```

**Flow:**
1. Validates OTP from Redis
2. Marks user as verified
3. Sends welcome email
4. Returns deep link for mobile app redirect

---

### 6. Refresh Token

**POST** `/auth/refresh`

Get a new access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### 7. Forgot Password

**POST** `/auth/forgot-password`

Request a password reset email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Password reset instructions sent"
}
```

**Flow:**
1. Generates secure reset token
2. Stores token in Redis (1-hour expiry)
3. Sends password reset email with link
4. Email contains: `soukloop://reset-password?token=...`

---

### 8. Reset Password

**POST** `/auth/reset-password`

Reset password using token from email.

**Request Body:**
```json
{
  "token": "secure-reset-token-from-email",
  "new_password": "NewSecurePass123!"
}
```

**Response:**
```json
{
  "success": true
}
```

**Flow:**
1. Validates token from Redis
2. Hashes new password with Argon2
3. Updates user.password_hash
4. Deletes token from Redis

---

### 9. Get Current User

**GET** `/auth/me`

Get authenticated user's profile.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "uuid",
  "username": "johndoe",
  "email": "user@example.com",
  "phone": "+971501234567",
  "full_name": "John Doe",
  "role": "buyer",
  "avatar_url": "https://...",
  "bio": "...",
  "location": {
    "latitude": 25.276987,
    "longitude": 55.296249,
    "neighborhood": "Dubai Marina",
    "building_name": "..."
  },
  "is_verified": true,
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z",
  "stats": {}
}
```

---

### 10. Logout

**POST** `/auth/logout`

Logout user by invalidating current session.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

**Note:** Token blacklisting is prepared but requires token injection in dependencies.

---

## 🔐 Security Features

### Password Hashing

- **Algorithm**: Argon2 (industry best practice)
- **Fallback**: BCrypt (via Passlib)
- **Configuration**: Default secure parameters

```python
from app.utils.jwt import hash_password, verify_password

hashed = hash_password("SecurePass123!")
is_valid = verify_password("SecurePass123!", hashed)
```

### JWT Tokens

**Access Token:**
- Expiry: 15 minutes (configurable)
- Payload:
  ```json
  {
    "sub": "user_id",
    "role": "buyer|seller|both|admin",
    "type": "access",
    "exp": 1234567890
  }
  ```

**Refresh Token:**
- Expiry: 7 days (configurable)
- Payload:
  ```json
  {
    "sub": "user_id",
    "role": "buyer|seller|both|admin",
    "type": "refresh",
    "exp": 1234567890
  }
  ```

**Signing:**
- Algorithm: HS256 (HMAC SHA-256)
- Secret: 32+ character random string

### OTP Security

- **Generation**: Cryptographically secure (secrets module)
- **Length**: 6 digits
- **TTL**: 10 minutes (600 seconds)
- **Rate Limiting**: 3 requests per hour per identifier
- **Storage**: Redis with automatic expiry
- **Verification**: Constant-time comparison (secrets.compare_digest)

### Rate Limiting

```python
# OTP rate limit
await store_otp(email, otp, redis)
# Raises ValueError if > 3 requests in past hour

# Rate limit key
f"otp:rate:{identifier}"  # TTL: 1 hour, Type: Counter
```

---

## 📧 Email Service

### Configuration

**Location**: `app/services/email_service.py`

**Supported Providers:**
- ZeptoMail (recommended for transactional emails)
- Mailgun
- AWS SES (via boto3, already installed)
- SendGrid
- Gmail SMTP

### Email Templates

**Location**: `email_templates/`

1. **OTP Verification** (`otp_verification.html`)
   - Variables: `{{OTP_CODE}}`, `{{USER_EMAIL}}`, `{{VERIFICATION_LINK}}`
   - Features: Monospace code display, 10-minute timer, mobile-responsive

2. **Welcome Email** (`welcome.html`)
   - Variables: `{{USER_NAME}}`, `{{APP_LINK}}`, `{{SUPPORT_EMAIL}}`
   - Features: Sunset gradient, feature cards, app download buttons

3. **Password Reset** (inline in email_service.py)
   - Variables: `reset_token`, `user_name`
   - Features: Secure link, 1-hour expiry warning

### Email Service API

```python
from app.services.email_service import email_service

# Send OTP email
await email_service.send_otp_email(
    email="user@example.com",
    otp="123456",
    user_name="John Doe"  # optional
)

# Send welcome email
await email_service.send_welcome_email(
    email="user@example.com",
    name="John Doe"
)

# Send password reset
await email_service.send_password_reset_email(
    email="user@example.com",
    reset_token="secure-token",
    user_name="John Doe"  # optional
)
```

### Graceful Degradation

If SMTP is not configured, the email service:
- Logs email content to console
- Returns success (doesn't block development)
- Shows warning on startup

---

## 💾 Redis Cache Strategy

### Authentication Keys

```python
from app.core.cache.cache_keys import CacheKeys

# OTP storage
key = CacheKeys.otp_code(email)  # "otp:{email}"
await redis.set(key, "123456", ex=600)

# OTP rate limiting
key = f"otp:rate:{email}"
await redis.incr(key)

# Password reset token
key = f"password-reset:{token}"
await redis.set(key, user_id, ex=3600)

# Token blacklist (logout)
key = CacheKeys.blacklisted_token(token)
await redis.set(key, "revoked", ex=ttl_remaining)

# User session
key = CacheKeys.user_session(user_id)
await redis.hset(key, "device", request.headers.get("User-Agent"))

# User profile cache
key = CacheKeys.user_profile(user_id)
await redis.set(key, json.dumps(profile), ex=3600)
```

### Cache TTLs

| Key Pattern | TTL | Type | Purpose |
|-------------|-----|------|---------|
| `otp:{identifier}` | 10 min | String | OTP code |
| `otp:rate:{identifier}` | 1 hour | Counter | Rate limiting |
| `password-reset:{token}` | 1 hour | String | Reset token |
| `token:blacklist:{token}` | 15 min | String | Logout |
| `session:{user_id}` | 7 days | Hash | User session |
| `user:profile:{user_id}` | 1 hour | JSON | Profile cache |

---

## 🗄️ Database Schema

### User Model

**Table**: `users`

```python
class User(Base):
    __tablename__ = "users"

    # Primary Key
    id: UUID                    # Auto-generated

    # Authentication (unique + indexed)
    email: str                  # Unique, indexed
    username: str               # Unique, indexed
    phone: str                  # Unique, indexed
    password_hash: str          # Argon2 hash

    # Profile
    full_name: str
    avatar_url: str | None
    bio: str | None

    # Role & Status
    role: UserRole              # buyer|seller|both|admin
    is_verified: bool           # OTP verification status
    is_active: bool

    # Location (PostGIS POINT)
    location: Geometry | None   # SRID=4326 (WGS84)
    neighborhood: str | None
    building_name: str | None

    # Activity
    last_login_at: datetime | None

    # Timestamps (auto-managed)
    created_at: datetime
    updated_at: datetime
```

**Indexes:**
- `email` (unique B-tree)
- `username` (unique B-tree)
- `phone` (unique B-tree)
- `location` (GIST spatial index)

---

## 🔄 Authentication Flows

### Registration Flow

```
1. POST /auth/register
   ↓
2. Validate uniqueness (email, username, phone)
   ↓
3. Hash password (Argon2)
   ↓
4. Create User (is_verified=False)
   ↓
5. Generate 6-digit OTP
   ↓
6. Store OTP in Redis (10-min TTL)
   ↓
7. Send OTP email
   ↓
8. Return JWT tokens
   ↓
9. User verifies OTP
   ↓
10. POST /auth/verify-otp → Set is_verified=True
   ↓
11. Send welcome email
```

### Login Flow

```
1. POST /auth/login (email/username + password)
   ↓
2. Query user by identifier (case-insensitive)
   ↓
3. Verify password hash
   ↓
4. Update last_login_at
   ↓
5. Generate JWT tokens
   ↓
6. Return tokens
```

### Password Reset Flow

```
1. POST /auth/forgot-password (email)
   ↓
2. Generate secure token (secrets.token_urlsafe(32))
   ↓
3. Store token in Redis (1-hour TTL)
   ↓
4. Send reset email with link
   ↓
5. User clicks link → Opens app with token
   ↓
6. POST /auth/reset-password (token + new_password)
   ↓
7. Validate token from Redis
   ↓
8. Hash new password
   ↓
9. Update user.password_hash
   ↓
10. Delete token from Redis
```

### Email Verification Flow

```
Option 1: Manual OTP Entry
1. User receives OTP email (123456)
2. POST /auth/verify-otp (otp_code="123456")
3. Verify OTP from Redis
4. Set is_verified=True
5. Send welcome email

Option 2: One-Click Link
1. User receives email with verification link
2. User taps link (opens app via deep link)
3. GET /auth/verify-email?code=123456&email=...
4. Verify OTP from Redis
5. Set is_verified=True
6. Send welcome email
7. Redirect to app: soukloop://verified
```

---

## 🧪 Testing Authentication

### Test OTP Email

```python
# Create test script: test_otp.py
import asyncio
from app.services.email_service import email_service

async def test():
    result = await email_service.send_otp_email(
        email="your-email@example.com",
        otp="123456",
        user_name="Test User"
    )
    print(f"Email sent: {result}")

asyncio.run(test())
```

### Test API with cURL

```bash
# 1. Register
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "phone": "+971501234567",
    "password": "Test123!",
    "full_name": "Test User",
    "role": "buyer"
  }'

# 2. Check email for OTP (or check Redis)
redis-cli
> GET otp:test@example.com
"123456"

# 3. Verify OTP
curl -X POST http://localhost:8080/api/v1/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "otp_code": "123456"
  }'

# 4. Login
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "test@example.com",
    "password": "Test123!"
  }'

# 5. Get current user (use access_token from login response)
curl -X GET http://localhost:8080/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

## 🚨 Error Handling

### Common Error Responses

```json
// 400 Bad Request - Invalid OTP
{
  "detail": "Invalid or expired OTP"
}

// 400 Bad Request - User exists
{
  "detail": "User already exists"
}

// 401 Unauthorized - Invalid credentials
{
  "detail": "Invalid credentials"
}

// 404 Not Found - User not found
{
  "detail": "User not found"
}

// 429 Too Many Requests - Rate limit
{
  "detail": "OTP request limit reached. Please try again later."
}
```

---

## 📝 Next Steps

### Frontend Integration

1. **Create Auth Service** (Dart/Flutter)
   - Token storage (secure_storage)
   - API client with interceptors
   - Automatic token refresh
   - Token expiry handling

2. **Auth Screens**
   - Login screen
   - Register screen
   - OTP verification screen
   - Password reset screens

3. **Deep Link Handling**
   - `soukloop://verified` → Success screen
   - `soukloop://reset-password?token=...` → Reset screen

### Backend Enhancements

1. **Token Blacklisting**
   - Update dependencies to pass token to logout endpoint
   - Check blacklist in auth dependency

2. **SMS Support**
   - Integrate Twilio for OTP SMS
   - Update send_otp_sms() function

3. **Social Login**
   - Google Sign-In (OAuth2)
   - Apple Sign-In (required for iOS)

4. **Two-Factor Authentication**
   - Optional 2FA for enhanced security
   - TOTP support (authenticator apps)

---

## 📚 References

- **FastAPI Docs**: https://fastapi.tiangolo.com
- **JWT**: https://jwt.io
- **Argon2**: https://en.wikipedia.org/wiki/Argon2
- **Redis**: https://redis.io/docs
- **Passlib**: https://passlib.readthedocs.io
- **aiosmtplib**: https://aiosmtplib.readthedocs.io
