"""Cache decorators for automatic caching and invalidation.

Provides decorators to add caching behavior to repository methods:
- @cached: Automatically cache function results
- @invalidate_cache: Clear cache after function execution
- @stale_while_revalidate: Return stale data while refreshing in background
"""

import asyncio
import hashlib
import inspect
import json
from functools import wraps
from typing import Any, Callable, Optional

from app.core.cache.redis_manager import get_redis_manager


def cached(
    key_prefix: str,
    ttl: int = 300,  # 5 minutes default
    key_builder: Optional[Callable] = None,
) -> Callable:
    """Decorator for automatic caching of async function results.

    Usage:
        @cached(key_prefix="product", ttl=900)
        async def get_product(self, product_id: str):
            return await self.db.query(...)

    Args:
        key_prefix: Prefix for cache key (e.g., "product", "feed:discover")
        ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        key_builder: Optional custom function to build cache key

    Returns:
        Decorated function with caching behavior
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get RedisManager from DI
            try:
                redis_manager = get_redis_manager()
            except RuntimeError:
                # Redis not initialized, skip caching
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default: use function args as key
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                key_parts = [key_prefix]
                for param_name, param_value in bound_args.arguments.items():
                    if param_name != "self":  # Skip self for class methods
                        key_parts.append(f"{param_name}:{param_value}")

                cache_key = ":".join(key_parts)

            # Check cache
            cached_result = await redis_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Cache miss - execute function
            result = await func(*args, **kwargs)

            # Store in cache (only if result is not None)
            if result is not None:
                await redis_manager.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


def invalidate_cache(*patterns: str) -> Callable:
    """Decorator to invalidate cache after function execution.

    Usage:
        @invalidate_cache("feed:*", "product:{product_id}")
        async def update_product(self, product_id: str, data: dict):
            return await self.db.update(...)

    Args:
        *patterns: Cache key patterns to invalidate (supports {arg_name} placeholders)

    Returns:
        Decorated function with cache invalidation
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Execute function first
            result = await func(*args, **kwargs)

            # Get RedisManager
            try:
                redis_manager = get_redis_manager()
            except RuntimeError:
                # Redis not initialized, skip invalidation
                return result

            # Invalidate cache patterns
            for pattern in patterns:
                # Replace placeholders with actual values
                resolved_pattern = pattern

                # Try to replace {arg_name} with actual arg values
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                for param_name, param_value in bound_args.arguments.items():
                    resolved_pattern = resolved_pattern.replace(
                        f"{{{param_name}}}", str(param_value)
                    )

                # Delete matching keys
                await redis_manager.delete_pattern(resolved_pattern)

            return result

        return wrapper

    return decorator


def stale_while_revalidate(
    key_prefix: str,
    ttl: int = 300,
    key_builder: Optional[Callable] = None,
) -> Callable:
    """Decorator for stale-while-revalidate caching pattern.

    Returns cached data immediately, then refreshes in background.

    Usage:
        @stale_while_revalidate(key_prefix="product", ttl=900)
        async def get_product(self, product_id: str):
            return await self.db.query(...)

    Args:
        key_prefix: Prefix for cache key
        ttl: Time-to-live in seconds
        key_builder: Optional custom function to build cache key

    Returns:
        Decorated function with SWR behavior
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get RedisManager
            try:
                redis_manager = get_redis_manager()
            except RuntimeError:
                # Redis not initialized, skip caching
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default: use function args as key
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                key_parts = [key_prefix]
                for param_name, param_value in bound_args.arguments.items():
                    if param_name != "self":  # Skip self for class methods
                        key_parts.append(f"{param_name}:{param_value}")

                cache_key = ":".join(key_parts)

            # Check cache
            cached_result = await redis_manager.get(cache_key)

            if cached_result is not None:
                # Return cached immediately
                # Revalidate in background (fire and forget)
                asyncio.create_task(_revalidate(cache_key, func, args, kwargs, ttl))
                return cached_result

            # Cache miss - fetch fresh
            result = await func(*args, **kwargs)
            if result is not None:
                await redis_manager.set(cache_key, result, ttl=ttl)
            return result

        async def _revalidate(
            key: str, func: Callable, args: tuple, kwargs: dict, ttl: int
        ) -> None:
            """Background task to revalidate cache."""
            try:
                redis_manager = get_redis_manager()
                # Fetch fresh data
                fresh_data = await func(*args, **kwargs)

                # Update cache
                if fresh_data is not None:
                    await redis_manager.set(key, fresh_data, ttl=ttl)
            except Exception:
                # Silently fail (don't affect user experience)
                pass

        return wrapper

    return decorator


def cache_key_from_filters(key_prefix: str, filters: dict, **extras) -> str:
    """Generate cache key from filter dictionary.

    Useful for list/search endpoints with complex filter parameters.

    Args:
        key_prefix: Key prefix (e.g., "search:results")
        filters: Dictionary of filter parameters
        **extras: Additional key components (e.g., page, limit)

    Returns:
        Cache key string

    Example:
        >>> cache_key_from_filters(
        ...     "search:results",
        ...     {"category": "sneakers", "min_price": 100},
        ...     page=1,
        ...     limit=20
        ... )
        'search:results:a3f2b1c4:page:1:limit:20'
    """
    # Create hash from filters for uniqueness
    filters_str = json.dumps(filters or {}, sort_keys=True)
    filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:8]

    # Build key parts
    key_parts = [key_prefix, filters_hash]

    # Add extras
    for key, value in sorted(extras.items()):
        key_parts.extend([key, str(value)])

    return ":".join(key_parts)
