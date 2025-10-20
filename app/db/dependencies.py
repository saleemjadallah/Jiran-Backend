"""Dependency injection for database and repositories.

Provides FastAPI dependencies for:
- Database sessions
- Redis manager
- Repository instances with automatic cache integration
"""

from typing import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.redis_manager import RedisManager, get_redis_manager
from app.database import get_db_session
from app.db.repositories.product_repository import ProductRepository


# ========== Core Dependencies ==========


async def get_db() -> AsyncIterator[AsyncSession]:
    """Get database session dependency.

    Yields:
        AsyncSession instance
    """
    async for session in get_db_session():
        yield session


async def get_redis() -> RedisManager:
    """Get Redis manager dependency.

    Returns:
        RedisManager instance
    """
    return get_redis_manager()


# ========== Repository Dependencies ==========


async def get_product_repository(
    db: AsyncSession = Depends(get_db), redis: RedisManager = Depends(get_redis)
) -> ProductRepository:
    """Get ProductRepository with cache integration.

    Args:
        db: Database session (injected)
        redis: Redis manager (injected)

    Returns:
        ProductRepository instance
    """
    return ProductRepository(db=db, redis=redis)


# Add more repository dependencies as needed:
# async def get_user_repository(
#     db: AsyncSession = Depends(get_db),
#     redis: RedisManager = Depends(get_redis)
# ) -> UserRepository:
#     return UserRepository(db=db, redis=redis)
