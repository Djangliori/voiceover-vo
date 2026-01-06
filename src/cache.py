"""
Redis Caching Module
Provides decorators and utilities for caching expensive database queries and API calls
"""

import os
import json
import hashlib
import functools
from typing import Any, Callable, Optional
from src.logging_config import get_logger

logger = get_logger(__name__)

# Try to import Redis - optional dependency
try:
    import redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - caching disabled")


class RedisCache:
    """Redis-based caching with automatic serialization/deserialization"""

    def __init__(self, redis_client: 'redis.Redis', key_prefix: str = "cache"):
        self.redis = redis_client
        self.key_prefix = key_prefix

    def _make_key(self, namespace: str, *args, **kwargs) -> str:
        """
        Generate cache key from function arguments.

        Args:
            namespace: Function or cache namespace
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Create a consistent hash of arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())  # Sort for consistency
        }
        key_hash = hashlib.md5(json.dumps(key_data, sort_keys=True, default=str).encode()).hexdigest()
        return f"{self.key_prefix}:{namespace}:{key_hash}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except RedisError as e:
            logger.error(f"Redis cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        try:
            data = json.dumps(value, default=str)
            self.redis.setex(key, ttl, data)
            return True
        except (RedisError, TypeError, ValueError) as e:
            logger.error(f"Redis cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            self.redis.delete(key)
            return True
        except RedisError as e:
            logger.error(f"Redis cache delete error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Redis key pattern (e.g., "cache:videos:*")

        Returns:
            Number of keys deleted
        """
        try:
            deleted = 0
            for key in self.redis.scan_iter(match=pattern, count=100):
                self.redis.delete(key)
                deleted += 1
            return deleted
        except RedisError as e:
            logger.error(f"Redis cache delete_pattern error: {e}")
            return 0

    def clear_namespace(self, namespace: str) -> int:
        """Clear all cache entries for a namespace"""
        pattern = f"{self.key_prefix}:{namespace}:*"
        return self.delete_pattern(pattern)


class NoOpCache:
    """No-op cache implementation for when Redis is unavailable"""

    def _make_key(self, namespace: str, *args, **kwargs) -> str:
        return ""

    def get(self, key: str) -> None:
        return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        return False

    def delete(self, key: str) -> bool:
        return False

    def delete_pattern(self, pattern: str) -> int:
        return 0

    def clear_namespace(self, namespace: str) -> int:
        return 0


def create_cache() -> RedisCache:
    """
    Factory function to create cache instance.
    Uses Redis if available, otherwise returns no-op cache.
    """
    redis_url = os.getenv('REDIS_URL')

    if REDIS_AVAILABLE and redis_url:
        try:
            redis_client = redis.from_url(
                redis_url,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            redis_client.ping()

            logger.info("✅ Redis cache enabled")
            return RedisCache(redis_client)

        except (RedisConnectionError, RedisError) as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")

    logger.info("⚠️  Redis cache disabled - using no-op cache")
    return NoOpCache()


# Global cache instance
cache = create_cache()


def cached(ttl: int = 300, namespace: Optional[str] = None):
    """
    Decorator to cache function results in Redis.

    Usage:
        @cached(ttl=600, namespace="videos")
        def get_expensive_data(video_id):
            return expensive_database_query(video_id)

    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        namespace: Cache namespace (defaults to function name)

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Use function name as namespace if not specified
            ns = namespace or f"{func.__module__}.{func.__name__}"

            # Generate cache key
            cache_key = cache._make_key(ns, *args, **kwargs)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache HIT: {ns}")
                return cached_result

            # Cache miss - call function
            logger.debug(f"Cache MISS: {ns}")
            result = func(*args, **kwargs)

            # Store in cache (only if result is not None)
            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        # Add cache control methods to the wrapped function
        wrapper.cache_clear = lambda: cache.clear_namespace(namespace or f"{func.__module__}.{func.__name__}")
        wrapper.cache_key = lambda *a, **kw: cache._make_key(namespace or f"{func.__module__}.{func.__name__}", *a, **kw)

        return wrapper
    return decorator


def invalidate_cache(namespace: str) -> int:
    """
    Invalidate all cache entries for a namespace.

    Usage:
        invalidate_cache("videos")  # Clear all video-related cache

    Args:
        namespace: Cache namespace to invalidate

    Returns:
        Number of keys deleted
    """
    return cache.clear_namespace(namespace)
