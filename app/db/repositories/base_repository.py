"""Base repository with automatic cache integration.

Provides CRUD operations with built-in Redis caching to reduce database load.
All repositories should inherit from this base class.
"""

import json
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.cache_keys import CacheKeys
from app.core.cache.redis_manager import RedisManager

# Type variable for model
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with automatic cache integration.

    Provides:
    - CRUD operations (Create, Read, Update, Delete)
    - Automatic Redis caching
    - Cache invalidation on writes
    - Batch operations with MGET optimization

    Usage:
        class ProductRepository(BaseRepository[Product]):
            def __init__(self, db: AsyncSession, redis: RedisManager):
                super().__init__(
                    db=db,
                    redis=redis,
                    model=Product,
                    cache_prefix="product",
                    default_ttl=900  # 15 minutes
                )
    """

    def __init__(
        self,
        db: AsyncSession,
        redis: RedisManager,
        model: type[T],
        cache_prefix: str,
        default_ttl: int = 300,  # 5 minutes default
    ):
        """Initialize repository.

        Args:
            db: SQLAlchemy async session
            redis: Redis manager instance
            model: SQLAlchemy model class
            cache_prefix: Cache key prefix (e.g., "product", "user")
            default_ttl: Default TTL in seconds (default: 300 = 5 min)
        """
        self.db = db
        self.redis = redis
        self.model = model
        self.cache_prefix = cache_prefix
        self.default_ttl = default_ttl

    # ========== Read Operations ==========

    async def get_by_id(
        self, id: str, use_cache: bool = True
    ) -> Optional[T]:
        """Get entity by ID with cache check.

        Flow:
        1. Check Redis cache
        2. If miss, query database
        3. Store in cache for future requests

        Args:
            id: Entity ID (UUID string)
            use_cache: Whether to use cache (default: True)

        Returns:
            Entity instance or None if not found
        """
        cache_key = f"{self.cache_prefix}:{id}"

        # Check cache first
        if use_cache:
            cached = await self.redis.get(cache_key)
            if cached:
                return self._deserialize(cached)

        # Query database
        result = await self.db.execute(select(self.model).filter(self.model.id == id))
        entity = result.scalar_one_or_none()

        # Populate cache
        if entity and use_cache:
            await self.redis.set(
                cache_key, self._serialize(entity), ttl=self.default_ttl
            )

        return entity

    async def get_many(
        self, ids: List[str], use_cache: bool = True
    ) -> List[T]:
        """Batch get entities by IDs.

        Optimized with MGET:
        1. Fetch all IDs from cache with single MGET
        2. Query DB only for cache misses
        3. Backfill cache with missing entities

        Args:
            ids: List of entity IDs
            use_cache: Whether to use cache (default: True)

        Returns:
            List of entity instances
        """
        if not use_cache:
            # Direct DB query
            result = await self.db.execute(
                select(self.model).filter(self.model.id.in_(ids))
            )
            return list(result.scalars().all())

        # Build cache keys
        cache_keys = [f"{self.cache_prefix}:{id}" for id in ids]

        # Batch fetch from cache
        cached_values = await self.redis.mget(cache_keys)

        # Track hits and misses
        entities = []
        missing_ids = []

        for id, cached in zip(ids, cached_values):
            if cached:
                entities.append(self._deserialize(cached))
            else:
                missing_ids.append(id)

        # Fetch missing from DB
        if missing_ids:
            result = await self.db.execute(
                select(self.model).filter(self.model.id.in_(missing_ids))
            )
            db_entities = list(result.scalars().all())

            # Backfill cache
            cache_mapping = {}
            for entity in db_entities:
                cache_key = f"{self.cache_prefix}:{entity.id}"
                cache_mapping[cache_key] = self._serialize(entity)
                entities.append(entity)

            if cache_mapping:
                await self.redis.mset(cache_mapping)
                # Set TTLs individually
                for key in cache_mapping.keys():
                    await self.redis.expire(key, self.default_ttl)

        return entities

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 20,
        use_cache: bool = True,
    ) -> List[T]:
        """List entities with pagination and filtering.

        Cache key includes filters hash for uniqueness.

        Args:
            filters: Dictionary of filter conditions (e.g., {"status": "active"})
            offset: Pagination offset (default: 0)
            limit: Page size (default: 20)
            use_cache: Whether to use cache (default: True)

        Returns:
            List of entity instances
        """
        # Build query
        query = select(self.model)

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

        query = query.offset(offset).limit(limit)

        # Generate cache key from filters
        if use_cache:
            import hashlib

            filters_str = json.dumps(filters or {}, sort_keys=True)
            filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:8]
            cache_key = (
                f"{self.cache_prefix}:list:{filters_hash}:offset:{offset}:limit:{limit}"
            )

            # Check cache
            cached = await self.redis.get(cache_key)
            if cached:
                return [self._deserialize(item) for item in cached]

        # Execute query
        result = await self.db.execute(query)
        entities = list(result.scalars().all())

        # Cache results
        if use_cache:
            serialized = [self._serialize(e) for e in entities]
            await self.redis.set(cache_key, serialized, ttl=self.default_ttl)

        return entities

    # ========== Write Operations ==========

    async def create(self, data: Dict[str, Any]) -> T:
        """Create entity with cache invalidation.

        Flow:
        1. Insert into database
        2. Commit transaction
        3. Invalidate related cache patterns
        4. Optionally warm cache with new entity

        Args:
            data: Dictionary of entity attributes

        Returns:
            Created entity instance
        """
        # Create instance
        entity = self.model(**data)
        self.db.add(entity)

        # Commit to DB
        await self.db.commit()
        await self.db.refresh(entity)

        # Invalidate related caches
        await self._invalidate_related_caches(entity)

        # Optionally warm cache
        cache_key = f"{self.cache_prefix}:{entity.id}"
        await self.redis.set(cache_key, self._serialize(entity), ttl=self.default_ttl)

        return entity

    async def update(self, id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update entity with cache invalidation.

        Flow:
        1. Fetch from DB
        2. Update fields
        3. Commit transaction
        4. Invalidate cache

        Args:
            id: Entity ID
            data: Dictionary of fields to update

        Returns:
            Updated entity instance or None if not found
        """
        # Fetch entity
        result = await self.db.execute(select(self.model).filter(self.model.id == id))
        entity = result.scalar_one_or_none()

        if not entity:
            return None

        # Update fields
        for field, value in data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

        # Commit
        await self.db.commit()
        await self.db.refresh(entity)

        # Invalidate caches
        await self._invalidate_related_caches(entity)

        # Update cache with new data
        cache_key = f"{self.cache_prefix}:{entity.id}"
        await self.redis.set(cache_key, self._serialize(entity), ttl=self.default_ttl)

        return entity

    async def delete(self, id: str) -> bool:
        """Delete entity with cache invalidation.

        Flow:
        1. Delete from DB
        2. Commit transaction
        3. Remove from cache
        4. Invalidate related caches

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(select(self.model).filter(self.model.id == id))
        entity = result.scalar_one_or_none()

        if not entity:
            return False

        # Delete from DB
        await self.db.delete(entity)
        await self.db.commit()

        # Remove from cache
        cache_key = f"{self.cache_prefix}:{id}"
        await self.redis.delete(cache_key)

        # Invalidate related caches
        await self._invalidate_related_caches(entity)

        return True

    # ========== Cache Management ==========

    async def _invalidate_related_caches(self, entity: T) -> None:
        """Invalidate related caches.

        Override in subclasses to invalidate feature-specific caches.

        Example for ProductRepository:
            await self.redis.delete_pattern("feed:*")
            await self.redis.delete_pattern(f"seller:{entity.seller_id}:*")
            await self.redis.delete_pattern("search:*")

        Args:
            entity: Entity instance
        """
        # Default: invalidate list caches
        await self.redis.delete_pattern(f"{self.cache_prefix}:list:*")

    def _serialize(self, entity: T) -> Dict[str, Any]:
        """Serialize entity for caching.

        Converts SQLAlchemy model to JSON-serializable dict, handling:
        - UUID → str
        - Decimal → str
        - datetime → ISO format str
        - Enum → value
        - bytes → None (skip binary data)

        Override in subclasses for custom serialization.

        Args:
            entity: Entity instance

        Returns:
            JSON-serializable dictionary representation
        """
        if hasattr(entity, "__dict__"):
            result = {}
            for k, v in entity.__dict__.items():
                # Skip SQLAlchemy internal attributes
                if k.startswith("_"):
                    continue

                # Convert non-JSON-serializable types
                if isinstance(v, UUID):
                    result[k] = str(v)
                elif isinstance(v, Decimal):
                    result[k] = str(v)
                elif isinstance(v, datetime):
                    result[k] = v.isoformat()
                elif isinstance(v, Enum):
                    result[k] = v.value
                elif isinstance(v, bytes):
                    # Skip binary data (e.g., PostGIS geometry)
                    continue
                else:
                    result[k] = v

            return result
        return {}

    def _deserialize(self, data: Dict[str, Any]) -> T:
        """Deserialize cached data to entity.

        Converts serialized strings back to original types:
        - str → UUID (for id fields)
        - str → Decimal (for price/amount fields)
        - ISO str → datetime
        - str → Enum value

        Override in subclasses for custom deserialization.

        Args:
            data: Cached dictionary

        Returns:
            Entity instance
        """
        # Create entity directly from cached data
        # SQLAlchemy will handle type conversion for most fields
        entity = self.model()

        # Set attributes manually to preserve types
        for key, value in data.items():
            if value is not None:
                # Get the model column type
                column = getattr(self.model, key, None)
                if column is not None and hasattr(column, "type"):
                    column_type = type(column.type).__name__

                    # Convert strings back to proper types
                    if "UUID" in str(type(column.type)) and isinstance(value, str):
                        value = UUID(value)
                    elif "Numeric" in column_type and isinstance(value, str):
                        value = Decimal(value)
                    elif "DateTime" in column_type and isinstance(value, str):
                        value = datetime.fromisoformat(value)

            setattr(entity, key, value)

        return entity

    async def clear_cache(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries.

        Args:
            pattern: Optional pattern to match (default: all entries for this prefix)

        Returns:
            Number of keys deleted
        """
        if pattern:
            return await self.redis.delete_pattern(pattern)
        return await self.redis.delete_pattern(f"{self.cache_prefix}:*")
