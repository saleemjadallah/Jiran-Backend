"""
Add temporary debug logging to auth dependencies to diagnose 401 error
"""

LOGGING_CODE = '''
import logging

logger = logging.getLogger(__name__)

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    logger.info(f"[AUTH DEBUG] Validating token: {token[:30]}...")
    try:
        payload = decode_access_token(token)
        logger.info(f"[AUTH DEBUG] Token decoded successfully. Payload sub: {payload.get('sub')}")
    except ValueError as exc:
        logger.error(f"[AUTH DEBUG] Token decode failed: {exc}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from exc

    user_id = payload.get("sub")
    if not user_id:
        logger.error("[AUTH DEBUG] No 'sub' in token payload")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    logger.info(f"[AUTH DEBUG] Looking up user_id: {user_id}")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.error(f"[AUTH DEBUG] User not found: {user_id}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    logger.info(f"[AUTH DEBUG] User found: {user.email}, role: {user.role}, active: {user.is_active}")
    return user
'''

print("=" * 70)
print("ADD THIS LOGGING TO app/dependencies.py")
print("=" * 70)
print(LOGGING_CODE)
print("\n" + "=" * 70)
print("After adding this, redeploy and check the logs for:")
print("  - [AUTH DEBUG] messages")
print("  - Which step is failing for product creation")
print("=" * 70)
