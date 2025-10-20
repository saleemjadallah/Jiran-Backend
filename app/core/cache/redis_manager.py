"""Redis cache manager for Souk Loop.

Provides async Redis operations with automatic JSON serialization/deserialization.
Supports all Redis data structures: String, Hash, Set, Sorted Set, List.
Includes compression support for large objects.
"""

import base64
import json
import zlib
from typing import Any, Optional, List, Set, Dict

import redis.asyncio as redis

from app.config import settings


class RedisManager:
    """Async Redis manager with JSON serialization support.

    Usage:
        redis_manager = RedisManager()
        await redis_manager.set("key", {"data": "value"}, ttl=300)
        data = await redis_manager.get("key")
    """

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis manager.

        Args:
            redis_url: Redis connection URL (defaults to settings.REDIS_URL)
        """
        url = redis_url or str(settings.REDIS_URL)
        self.redis = redis.from_url(url, decode_responses=True)

    async def close(self):
        """Close Redis connection."""
        await self.redis.close()

    # ========== String Operations ==========

    async def get(self, key: str) -> Optional[Any]:
        """Get string value, deserialize JSON.

        Args:
            key: Redis key

        Returns:
            Deserialized value or None if key doesn't exist
        """
        value = await self.redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set string value, serialize to JSON.

        Args:
            key: Redis key
            value: Value to store (will be JSON-serialized)
            ttl: Time-to-live in seconds (optional)
        """
        serialized = json.dumps(value) if not isinstance(value, str) else value
        if ttl:
            await self.redis.setex(key, ttl, serialized)
        else:
            await self.redis.set(key, serialized)

    async def delete(self, key: str) -> int:
        """Delete key.

        Args:
            key: Redis key

        Returns:
            Number of keys deleted (0 or 1)
        """
        return await self.redis.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern (e.g., 'feed:*').

        Args:
            pattern: Redis key pattern with wildcards

        Returns:
            Number of keys deleted
        """
        keys = await self.redis.keys(pattern)
        if not keys:
            return 0
        return await self.redis.delete(*keys)

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Redis key

        Returns:
            True if key exists
        """
        return await self.redis.exists(key) > 0

    # ========== Counter Operations ==========

    async def increment(self, key: str, amount: int = 1) -> int:
        """Atomic increment (for counters).

        Args:
            key: Redis key
            amount: Amount to increment by (default: 1)

        Returns:
            New value after increment
        """
        return await self.redis.incrby(key, amount)

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Atomic decrement.

        Args:
            key: Redis key
            amount: Amount to decrement by (default: 1)

        Returns:
            New value after decrement
        """
        return await self.redis.decrby(key, amount)

    # ========== Hash Operations ==========

    async def hset(self, key: str, field: str, value: Any) -> None:
        """Set hash field.

        Args:
            key: Redis key
            field: Hash field name
            value: Value to store (will be JSON-serialized)
        """
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await self.redis.hset(key, field, serialized)

    async def hget(self, key: str, field: str) -> Optional[Any]:
        """Get hash field.

        Args:
            key: Redis key
            field: Hash field name

        Returns:
            Deserialized value or None
        """
        value = await self.redis.hget(key, field)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Get all hash fields.

        Args:
            key: Redis key

        Returns:
            Dictionary of field:value pairs
        """
        data = await self.redis.hgetall(key)
        result = {}
        for field, value in data.items():
            try:
                result[field] = json.loads(value)
            except json.JSONDecodeError:
                result[field] = value
        return result

    async def hmset(
        self, key: str, mapping: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        """Set multiple hash fields.

        Args:
            key: Redis key
            mapping: Dictionary of field:value pairs
            ttl: Time-to-live in seconds (optional)
        """
        serialized = {
            k: json.dumps(v) if not isinstance(v, str) else v for k, v in mapping.items()
        }
        await self.redis.hset(key, mapping=serialized)
        if ttl:
            await self.redis.expire(key, ttl)

    # ========== Set Operations ==========

    async def sadd(self, key: str, *values: str) -> None:
        """Add to set.

        Args:
            key: Redis key
            *values: Values to add to set
        """
        await self.redis.sadd(key, *values)

    async def srem(self, key: str, *values: str) -> None:
        """Remove from set.

        Args:
            key: Redis key
            *values: Values to remove from set
        """
        await self.redis.srem(key, *values)

    async def smembers(self, key: str) -> Set[str]:
        """Get all set members.

        Args:
            key: Redis key

        Returns:
            Set of member values
        """
        return await self.redis.smembers(key)

    async def sismember(self, key: str, value: str) -> bool:
        """Check set membership.

        Args:
            key: Redis key
            value: Value to check

        Returns:
            True if value is in set
        """
        return await self.redis.sismember(key, value)

    async def scard(self, key: str) -> int:
        """Get set size.

        Args:
            key: Redis key

        Returns:
            Number of members in set
        """
        return await self.redis.scard(key)

    # ========== Sorted Set Operations ==========

    async def zadd(
        self, key: str, mapping: Dict[str, float], ttl: Optional[int] = None
    ) -> None:
        """Add to sorted set with scores.

        Args:
            key: Redis key
            mapping: Dictionary of member:score pairs
            ttl: Time-to-live in seconds (optional)
        """
        await self.redis.zadd(key, mapping)
        if ttl:
            await self.redis.expire(key, ttl)

    async def zincrby(self, key: str, amount: float, member: str) -> float:
        """Increment sorted set member score.

        Args:
            key: Redis key
            amount: Amount to increment by
            member: Member to increment

        Returns:
            New score
        """
        return await self.redis.zincrby(key, amount, member)

    async def zrem(self, key: str, *members: str) -> None:
        """Remove from sorted set.

        Args:
            key: Redis key
            *members: Members to remove
        """
        await self.redis.zrem(key, *members)

    async def zcard(self, key: str) -> int:
        """Get sorted set size.

        Args:
            key: Redis key

        Returns:
            Number of members in sorted set
        """
        return await self.redis.zcard(key)

    async def zrevrange(
        self, key: str, start: int, end: int, withscores: bool = False
    ) -> List:
        """Get sorted set members in reverse order (highest score first).

        Args:
            key: Redis key
            start: Start index
            end: End index
            withscores: Include scores in result

        Returns:
            List of members (and scores if withscores=True)
        """
        return await self.redis.zrevrange(key, start, end, withscores=withscores)

    async def zrange(
        self, key: str, start: int, end: int, withscores: bool = False
    ) -> List:
        """Get sorted set members in order (lowest score first).

        Args:
            key: Redis key
            start: Start index
            end: End index
            withscores: Include scores in result

        Returns:
            List of members (and scores if withscores=True)
        """
        return await self.redis.zrange(key, start, end, withscores=withscores)

    async def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        """Remove sorted set members by score range.

        Args:
            key: Redis key
            min_score: Minimum score
            max_score: Maximum score

        Returns:
            Number of members removed
        """
        return await self.redis.zremrangebyscore(key, min_score, max_score)

    async def zrangebyscore(
        self, key: str, min_score: float, max_score: float
    ) -> List[str]:
        """Get sorted set members by score range.

        Args:
            key: Redis key
            min_score: Minimum score
            max_score: Maximum score

        Returns:
            List of members in score range
        """
        return await self.redis.zrangebyscore(key, min_score, max_score)

    # ========== List Operations ==========

    async def lpush(self, key: str, *values: str) -> None:
        """Push to list (left/head).

        Args:
            key: Redis key
            *values: Values to push
        """
        serialized = [json.dumps(v) if not isinstance(v, str) else v for v in values]
        await self.redis.lpush(key, *serialized)

    async def rpush(self, key: str, *values: str) -> None:
        """Push to list (right/tail).

        Args:
            key: Redis key
            *values: Values to push
        """
        serialized = [json.dumps(v) if not isinstance(v, str) else v for v in values]
        await self.redis.rpush(key, *serialized)

    async def lrange(self, key: str, start: int, end: int) -> List[Any]:
        """Get list range.

        Args:
            key: Redis key
            start: Start index
            end: End index

        Returns:
            List of values in range
        """
        values = await self.redis.lrange(key, start, end)
        result = []
        for v in values:
            try:
                result.append(json.loads(v))
            except json.JSONDecodeError:
                result.append(v)
        return result

    async def llen(self, key: str) -> int:
        """Get list length.

        Args:
            key: Redis key

        Returns:
            Length of list
        """
        return await self.redis.llen(key)

    # ========== Pub/Sub Operations ==========

    async def publish(self, channel: str, message: Any) -> None:
        """Publish message to channel.

        Args:
            channel: Channel name
            message: Message to publish (will be JSON-serialized)
        """
        serialized = json.dumps(message) if not isinstance(message, str) else message
        await self.redis.publish(channel, serialized)

    # ========== TTL Operations ==========

    async def expire(self, key: str, seconds: int) -> None:
        """Set key expiration.

        Args:
            key: Redis key
            seconds: Time-to-live in seconds
        """
        await self.redis.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """Get key TTL.

        Args:
            key: Redis key

        Returns:
            TTL in seconds (-1 if no expiration, -2 if key doesn't exist)
        """
        return await self.redis.ttl(key)

    # ========== Batch Operations ==========

    async def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """Get multiple keys.

        Args:
            keys: List of Redis keys

        Returns:
            List of values (None for missing keys)
        """
        values = await self.redis.mget(keys)
        result = []
        for v in values:
            if v is None:
                result.append(None)
            else:
                try:
                    result.append(json.loads(v))
                except json.JSONDecodeError:
                    result.append(v)
        return result

    async def mset(self, mapping: Dict[str, Any]) -> None:
        """Set multiple keys.

        Args:
            mapping: Dictionary of key:value pairs
        """
        serialized = {
            k: json.dumps(v) if not isinstance(v, str) else v for k, v in mapping.items()
        }
        await self.redis.mset(serialized)

    # ========== Compression Operations ==========

    async def set_compressed(
        self, key: str, value: Any, ttl: Optional[int] = None, threshold: int = 1024
    ) -> None:
        """Set value with automatic compression for large objects.

        Compresses objects larger than threshold size to save memory.

        Args:
            key: Redis key
            value: Value to store
            ttl: Time-to-live in seconds (optional)
            threshold: Size threshold in bytes for compression (default: 1KB)
        """
        # Serialize to JSON
        json_str = json.dumps(value)

        # Compress if size exceeds threshold
        if len(json_str) > threshold:
            # Compress and encode as base64 string (for decode_responses=True)
            compressed = zlib.compress(json_str.encode())
            compressed_b64 = base64.b64encode(compressed).decode('utf-8')

            # Store compressed data
            if ttl:
                await self.redis.setex(f"{key}:compressed", ttl, compressed_b64)
                await self.redis.setex(f"{key}:is_compressed", ttl, "1")
            else:
                await self.redis.set(f"{key}:compressed", compressed_b64)
                await self.redis.set(f"{key}:is_compressed", "1")
        else:
            # Store uncompressed (normal set)
            await self.set(key, value, ttl=ttl)

    async def get_compressed(self, key: str) -> Optional[Any]:
        """Get value with automatic decompression.

        Args:
            key: Redis key

        Returns:
            Decompressed value or None if key doesn't exist
        """
        # Check if compressed
        is_compressed = await self.redis.get(f"{key}:is_compressed")

        if is_compressed:
            # Get compressed data (base64 string)
            compressed_b64 = await self.redis.get(f"{key}:compressed")
            if compressed_b64:
                try:
                    # Decode base64 and decompress
                    compressed = base64.b64decode(compressed_b64)
                    decompressed = zlib.decompress(compressed).decode('utf-8')
                    return json.loads(decompressed)
                except Exception:
                    # Fallback to regular get if decompression fails
                    return await self.get(key)
        else:
            # Get uncompressed (normal get)
            return await self.get(key)

        return None

    async def delete_compressed(self, key: str) -> int:
        """Delete compressed value and all related keys.

        Args:
            key: Redis key

        Returns:
            Number of keys deleted
        """
        count = 0
        count += await self.redis.delete(key)
        count += await self.redis.delete(f"{key}:compressed")
        count += await self.redis.delete(f"{key}:is_compressed")
        return count


# Global Redis manager instance (initialized in app startup)
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """Get global Redis manager instance.

    Returns:
        RedisManager instance

    Raises:
        RuntimeError: If Redis manager not initialized
    """
    if _redis_manager is None:
        raise RuntimeError(
            "Redis manager not initialized. Call init_redis_manager() first."
        )
    return _redis_manager


async def init_redis_manager() -> RedisManager:
    """Initialize global Redis manager.

    Returns:
        Initialized RedisManager instance
    """
    global _redis_manager
    _redis_manager = RedisManager()
    return _redis_manager


async def close_redis_manager() -> None:
    """Close global Redis manager."""
    global _redis_manager
    if _redis_manager:
        await _redis_manager.close()
        _redis_manager = None
