# Solution: Add Debug Logging to Diagnose 401 Error

## Problem
Video upload succeeds (200 OK) but product creation fails (401 Unauthorized) even though:
- User has BOTH role (includes seller permissions)
- Token expiry increased to 15 minutes
- Same client session (same IP)

## Root Cause Investigation

We need to determine if the problem is:
1. **Token not being sent** in the product creation request
2. **Token validation failing** for some reason
3. **Database lookup failing** (user not found)

## Solution: Add Temporary Debug Logging

### Step 1: Add logging to `app/dependencies.py`

Replace the `get_current_user()` function with this version:

```python
import logging

logger = logging.getLogger(__name__)

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    logger.info(f"🔑 [AUTH] Token received: {token[:40]}...")

    try:
        payload = decode_access_token(token)
        logger.info(f"✅ [AUTH] Token decoded. User ID: {payload.get('sub')}, Exp: {payload.get('exp')}")
    except ValueError as exc:
        logger.error(f"❌ [AUTH] Token decode FAILED: {exc}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from exc

    user_id = payload.get("sub")
    if not user_id:
        logger.error("❌ [AUTH] No 'sub' in token payload!")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    logger.info(f"🔍 [AUTH] Looking up user: {user_id}")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.error(f"❌ [AUTH] User NOT FOUND in database: {user_id}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    logger.info(f"✅ [AUTH] User authenticated: {user.email}, role={user.role}, active={user.is_active}")
    return user
```

### Step 2: Add logging to `require_seller_role()`

```python
async def require_seller_role(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    logger.info(f"🔐 [SELLER CHECK] User: {current_user.email}, Role: {current_user.role}")

    if current_user.role not in {UserRole.SELLER, UserRole.BOTH, UserRole.ADMIN}:
        logger.error(f"❌ [SELLER CHECK] FORBIDDEN - User role '{current_user.role}' not allowed")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seller permissions required")

    logger.info(f"✅ [SELLER CHECK] Access granted for role: {current_user.role}")
    return current_user
```

### Step 3: Deploy and Test

```bash
# Commit changes
git add app/dependencies.py
git commit -m "Add debug logging to auth dependencies"
git push

# Wait for Railway deploy (auto-deploy enabled)
railway logs --service "Jiran-Backend"

# Try video upload + product creation from app
# Then check logs for the [AUTH] and [SELLER CHECK] messages
railway logs --tail 200 | grep "\[AUTH\]\|\[SELLER CHECK\]"
```

### Step 4: Analyze Output

Look for this pattern in logs:

**Successful video upload:**
```
✅ [AUTH] Token decoded. User ID: xxx
✅ [AUTH] User authenticated: test@jiran.app, role=BOTH, active=True
```

**Failed product creation:**
- If you see `🔑 [AUTH] Token received` → Token IS being sent
- If you DON'T see it → **Frontend not sending token**
- If you see `❌ [AUTH] Token decode FAILED` → **Token expired or invalid**
- If you see `❌ [AUTH] User NOT FOUND` → **Database issue**
- If you see `❌ [SELLER CHECK] FORBIDDEN` → **Role issue**

## Alternative Quick Fix

If logging shows the token IS being sent and IS valid, but still failing, try this:

### Make product creation less restrictive temporarily

Change `app/api/v1/products.py` line 104:

```python
# BEFORE (requires seller role)
current_user: Annotated[User, Depends(require_seller_role)],

# AFTER (only requires active user - FOR TESTING ONLY)
current_user: Annotated[User, Depends(get_current_active_user)],
```

If this works, the problem is in the role checking logic.
If this STILL fails with 401, the problem is in token extraction/validation.

## Most Likely Causes (In Order)

1. **Frontend not sending Authorization header** in product POST request
2. **Token expiring** during video upload (15 min might not be enough if upload is slow)
3. **Different token** being used for video vs product request
4. **CORS preflight** stripping headers (unlikely for native app)
5. **Database connection issue** during user lookup

## Next Steps

1. Add the logging above
2. Redeploy
3. Try uploading video + creating product
4. Share the `[AUTH]` and `[SELLER CHECK]` log output
5. We'll pinpoint the exact failure point
