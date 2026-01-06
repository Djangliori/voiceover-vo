"""
Processing Status Tracker Module
Tracks video processing status with Redis for distributed environments
Version: 2.0.0 - Redis-based with in-memory fallback
"""

import os
import json
import threading
from typing import Dict, Any, Optional
from src.logging_config import get_logger

logger = get_logger(__name__)

# Try to import Redis - optional dependency
try:
    import redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - falling back to in-memory status tracking")


class RedisStatusTracker:
    """
    Redis-based processing status tracker for distributed environments.
    Provides atomic operations and shared state across workers.
    """

    def __init__(self, redis_client: 'redis.Redis'):
        self.redis = redis_client
        self.key_prefix = "processing_status:"
        self.default_ttl = 86400  # 24 hours

    def _get_key(self, video_id: str) -> str:
        """Get Redis key for video status"""
        return f"{self.key_prefix}{video_id}"

    def get_status(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get processing status for a video.

        Args:
            video_id: The video ID

        Returns:
            Status dict or None if not found
        """
        try:
            key = self._get_key(video_id)
            data = self.redis.get(key)

            if data:
                return json.loads(data)
            return None

        except RedisError as e:
            logger.error(f"Redis error in get_status for {video_id}: {e}")
            return None

    def update_status(self, video_id: str, status_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Update processing status for a video.

        Args:
            video_id: The video ID
            status_data: Status dictionary to store
            ttl: Time to live in seconds (default: 24 hours)

        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_key(video_id)
            data = json.dumps(status_data)

            # Set with TTL to automatically expire old statuses
            self.redis.setex(
                key,
                ttl or self.default_ttl,
                data
            )

            logger.debug(f"Updated status for {video_id}: {status_data.get('status', 'unknown')}")
            return True

        except RedisError as e:
            logger.error(f"Redis error in update_status for {video_id}: {e}")
            return False

    def merge_status(self, video_id: str, updates: Dict[str, Any]) -> bool:
        """
        Merge updates into existing status (atomic operation).

        Args:
            video_id: The video ID
            updates: Dictionary of updates to merge

        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_key(video_id)

            # Use WATCH for optimistic locking
            with self.redis.pipeline() as pipe:
                while True:
                    try:
                        pipe.watch(key)

                        # Get current data
                        current_data = pipe.get(key)
                        if current_data:
                            status_data = json.loads(current_data)
                        else:
                            status_data = {'video_id': video_id}

                        # Merge updates
                        status_data.update(updates)

                        # Start transaction
                        pipe.multi()
                        pipe.setex(key, self.default_ttl, json.dumps(status_data))
                        pipe.execute()

                        logger.debug(f"Merged status for {video_id}: {updates}")
                        return True

                    except redis.WatchError:
                        # Retry if data changed during transaction
                        logger.debug(f"Retrying merge_status for {video_id} due to concurrent modification")
                        continue
                    finally:
                        pipe.reset()

        except RedisError as e:
            logger.error(f"Redis error in merge_status for {video_id}: {e}")
            return False

    def delete_status(self, video_id: str) -> bool:
        """
        Delete processing status for a video.

        Args:
            video_id: The video ID

        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_key(video_id)
            self.redis.delete(key)
            logger.debug(f"Deleted status for {video_id}")
            return True

        except RedisError as e:
            logger.error(f"Redis error in delete_status for {video_id}: {e}")
            return False

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all processing statuses (for debugging).
        WARNING: Can be slow with many videos.

        Returns:
            Dictionary mapping video_id -> status_data
        """
        try:
            pattern = f"{self.key_prefix}*"
            statuses = {}

            for key in self.redis.scan_iter(match=pattern, count=100):
                video_id = key.decode('utf-8').replace(self.key_prefix, '')
                data = self.redis.get(key)
                if data:
                    statuses[video_id] = json.loads(data)

            return statuses

        except RedisError as e:
            logger.error(f"Redis error in get_all_statuses: {e}")
            return {}


class InMemoryStatusTracker:
    """
    In-memory processing status tracker (fallback for development).
    Thread-safe but not distributed across workers.
    """

    def __init__(self):
        self.statuses: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def get_status(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get processing status for a video"""
        with self.lock:
            return self.statuses.get(video_id)

    def update_status(self, video_id: str, status_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Update processing status for a video"""
        with self.lock:
            self.statuses[video_id] = dict(status_data)  # Copy to avoid mutations
            logger.debug(f"Updated in-memory status for {video_id}: {status_data.get('status', 'unknown')}")
            return True

    def merge_status(self, video_id: str, updates: Dict[str, Any]) -> bool:
        """Merge updates into existing status"""
        with self.lock:
            if video_id not in self.statuses:
                self.statuses[video_id] = {'video_id': video_id}

            self.statuses[video_id].update(updates)
            logger.debug(f"Merged in-memory status for {video_id}: {updates}")
            return True

    def delete_status(self, video_id: str) -> bool:
        """Delete processing status for a video"""
        with self.lock:
            if video_id in self.statuses:
                del self.statuses[video_id]
                logger.debug(f"Deleted in-memory status for {video_id}")
            return True

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get all processing statuses"""
        with self.lock:
            return dict(self.statuses)  # Return copy


def create_status_tracker():
    """
    Factory function to create the appropriate status tracker.
    Uses Redis if available, otherwise falls back to in-memory.
    """
    redis_url = os.getenv('REDIS_URL')

    if REDIS_AVAILABLE and redis_url:
        try:
            # Try to connect to Redis
            redis_client = redis.from_url(
                redis_url,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )

            # Test connection
            redis_client.ping()

            logger.info("✅ Using Redis-based status tracker (distributed mode)")
            return RedisStatusTracker(redis_client)

        except (RedisConnectionError, RedisError) as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to in-memory status tracker.")

    # Fallback to in-memory tracker
    logger.info("⚠️  Using in-memory status tracker (development mode)")
    logger.warning("In-memory tracker not shared across workers - use Redis for production")
    return InMemoryStatusTracker()


# Global status tracker instance
status_tracker = create_status_tracker()
