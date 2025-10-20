from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.redis_manager import RedisManager
from app.core.redis import get_redis
from app.database import get_db_session
from app.db.repositories.stream_repository import StreamRepository
from app.models.user import User, UserRole
from app.services.cache.feed_cache_service import FeedCacheService
from app.utils.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


async def require_seller_role(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if current_user.role not in {UserRole.SELLER, UserRole.BOTH, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seller permissions required")
    return current_user


async def require_admin_role(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required")
    return current_user


async def get_redis_client() -> Redis:
    return await get_redis()


async def get_redis_manager() -> RedisManager:
    """Get RedisManager instance.

    Returns:
        RedisManager instance for cache operations
    """
    redis = await get_redis()
    return RedisManager(redis)


async def get_feed_cache_service(
    redis_manager: Annotated[RedisManager, Depends(get_redis_manager)],
) -> FeedCacheService:
    """Get FeedCacheService instance.

    Args:
        redis_manager: Redis manager dependency

    Returns:
        FeedCacheService instance for feed caching
    """
    return FeedCacheService(redis_manager)


async def get_stream_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_manager: Annotated[RedisManager, Depends(get_redis_manager)],
) -> StreamRepository:
    """Get StreamRepository instance.

    Args:
        db: Database session
        redis_manager: Redis manager dependency

    Returns:
        StreamRepository instance with cache integration
    """
    return StreamRepository(db, redis_manager)
