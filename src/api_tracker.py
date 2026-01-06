"""
API Usage Tracker Module
Tracks and limits API calls to prevent quota exhaustion
Version: 2.0.0 - Redis-based with file fallback
"""

import time
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any
from src.logging_config import get_logger

logger = get_logger(__name__)

# Try to import Redis - optional dependency
try:
    import redis
    from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - falling back to file-based API tracking")


class RedisAPITracker:
    """
    Redis-based API usage tracker for distributed environments.
    Provides atomic operations and distributed locking.
    """

    def __init__(self, redis_client: 'redis.Redis'):
        self.redis = redis_client
        self.key_prefix = "api_tracker:"

        # Daily limits (adjust based on your RapidAPI plan)
        self.daily_limit = int(os.getenv('RAPIDAPI_DAILY_LIMIT', 100))
        self.hourly_limit = int(os.getenv('RAPIDAPI_HOURLY_LIMIT', 20))

        # Rate limiting
        self.min_request_interval = 2  # Minimum seconds between requests

    def _get_day_key(self) -> str:
        """Get Redis key for daily counter"""
        day = datetime.now().strftime('%Y-%m-%d')
        return f"{self.key_prefix}daily:{day}"

    def _get_hour_key(self) -> str:
        """Get Redis key for hourly counter"""
        hour = datetime.now().strftime('%Y-%m-%d:%H')
        return f"{self.key_prefix}hourly:{hour}"

    def _get_stats_key(self) -> str:
        """Get Redis key for total stats"""
        return f"{self.key_prefix}stats"

    def _get_rate_limit_key(self) -> str:
        """Get Redis key for rate limiting"""
        return f"{self.key_prefix}last_request"

    def can_make_request(self) -> Tuple[bool, str]:
        """Check if we can make an API request without exceeding limits"""
        try:
            # Get current counts atomically
            pipe = self.redis.pipeline()
            pipe.get(self._get_day_key())
            pipe.get(self._get_hour_key())
            daily_count, hourly_count = pipe.execute()

            daily_count = int(daily_count) if daily_count else 0
            hourly_count = int(hourly_count) if hourly_count else 0

            # Check daily limit
            if daily_count >= self.daily_limit:
                logger.warning(f"Daily API limit reached: {daily_count}/{self.daily_limit}")
                return False, "Daily API limit reached. Please try again tomorrow."

            # Check hourly limit
            if hourly_count >= self.hourly_limit:
                logger.warning(f"Hourly API limit reached: {hourly_count}/{self.hourly_limit}")
                return False, "Hourly API limit reached. Please try again in the next hour."

            # Check rate limiting using Redis timestamp
            last_request = self.redis.get(self._get_rate_limit_key())
            if last_request:
                last_request_time = float(last_request)
                current_time = time.time()
                time_since_last = current_time - last_request_time

                if time_since_last < self.min_request_interval:
                    wait_time = self.min_request_interval - time_since_last
                    logger.info(f"Rate limiting: waiting {wait_time:.1f}s")
                    time.sleep(wait_time)

            return True, "OK"

        except RedisError as e:
            logger.error(f"Redis error in can_make_request: {e}")
            # Fail open - allow request if Redis is down
            return True, "OK (Redis unavailable)"

    def record_request(self, success: bool = True) -> None:
        """Record that an API request was made"""
        try:
            current_time = time.time()

            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Increment daily counter (expires at end of day)
            day_key = self._get_day_key()
            pipe.incr(day_key)
            # Set expiry to end of day + 1 hour buffer
            tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1, hours=1)
            ttl_seconds = int((tomorrow - datetime.now()).total_seconds())
            pipe.expire(day_key, ttl_seconds)

            # Increment hourly counter (expires after 2 hours)
            hour_key = self._get_hour_key()
            pipe.incr(hour_key)
            pipe.expire(hour_key, 7200)  # 2 hours

            # Update total stats (hash)
            stats_key = self._get_stats_key()
            pipe.hincrby(stats_key, 'total_requests', 1)
            if not success:
                pipe.hincrby(stats_key, 'failed_requests', 1)

            # Update last request timestamp
            pipe.set(self._get_rate_limit_key(), str(current_time), ex=60)

            # Execute all atomically
            daily_count, _, hourly_count, _, total_requests, *_ = pipe.execute()

            logger.info(
                f"API request recorded. "
                f"Daily: {daily_count}/{self.daily_limit}, "
                f"Hourly: {hourly_count}/{self.hourly_limit}, "
                f"Total: {total_requests}"
            )

        except RedisError as e:
            logger.error(f"Redis error in record_request: {e}")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        try:
            pipe = self.redis.pipeline()
            pipe.get(self._get_day_key())
            pipe.get(self._get_hour_key())
            pipe.hgetall(self._get_stats_key())

            daily_count, hourly_count, stats = pipe.execute()

            daily_count = int(daily_count) if daily_count else 0
            hourly_count = int(hourly_count) if hourly_count else 0

            # Decode stats hash
            total_requests = int(stats.get(b'total_requests', 0))
            failed_requests = int(stats.get(b'failed_requests', 0))

            return {
                'daily': {
                    'used': daily_count,
                    'limit': self.daily_limit,
                    'remaining': max(0, self.daily_limit - daily_count)
                },
                'hourly': {
                    'used': hourly_count,
                    'limit': self.hourly_limit,
                    'remaining': max(0, self.hourly_limit - hourly_count)
                },
                'total_requests': total_requests,
                'failed_requests': failed_requests,
                'success_rate': (
                    ((total_requests - failed_requests) / total_requests * 100)
                    if total_requests > 0 else 0
                )
            }

        except RedisError as e:
            logger.error(f"Redis error in get_usage_stats: {e}")
            return {
                'daily': {'used': 0, 'limit': self.daily_limit, 'remaining': self.daily_limit},
                'hourly': {'used': 0, 'limit': self.hourly_limit, 'remaining': self.hourly_limit},
                'total_requests': 0,
                'failed_requests': 0,
                'success_rate': 0
            }


class FileAPITracker:
    """
    File-based API usage tracker (fallback for development).
    Not recommended for production with multiple workers.
    """

    def __init__(self, tracker_file: str = "api_usage.json"):
        self.tracker_file = Path(tracker_file)
        self.usage_data = self._load_usage_data()

        # Daily limits (adjust based on your RapidAPI plan)
        self.daily_limit = int(os.getenv('RAPIDAPI_DAILY_LIMIT', 100))
        self.hourly_limit = int(os.getenv('RAPIDAPI_HOURLY_LIMIT', 20))

        # Rate limiting
        self.min_request_interval = 2  # Minimum seconds between requests
        self.last_request_time = 0

    def _load_usage_data(self) -> Dict[str, Any]:
        """Load usage data from file"""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load usage data: {e}")

        return {
            'daily_count': 0,
            'hourly_count': 0,
            'last_reset_day': datetime.now().strftime('%Y-%m-%d'),
            'last_reset_hour': datetime.now().strftime('%Y-%m-%d %H'),
            'total_requests': 0,
            'failed_requests': 0
        }

    def _save_usage_data(self) -> None:
        """Save usage data to file"""
        try:
            with open(self.tracker_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save API usage data: {e}")

    def _reset_counters_if_needed(self) -> None:
        """Reset daily/hourly counters if time period has passed"""
        now = datetime.now()
        current_day = now.strftime('%Y-%m-%d')
        current_hour = now.strftime('%Y-%m-%d %H')

        # Reset daily counter
        if self.usage_data['last_reset_day'] != current_day:
            logger.info(f"Resetting daily API counter. Previous: {self.usage_data['daily_count']}")
            self.usage_data['daily_count'] = 0
            self.usage_data['last_reset_day'] = current_day

        # Reset hourly counter
        if self.usage_data['last_reset_hour'] != current_hour:
            logger.info(f"Resetting hourly API counter. Previous: {self.usage_data['hourly_count']}")
            self.usage_data['hourly_count'] = 0
            self.usage_data['last_reset_hour'] = current_hour

        self._save_usage_data()

    def can_make_request(self) -> Tuple[bool, str]:
        """Check if we can make an API request without exceeding limits"""
        self._reset_counters_if_needed()

        # Check daily limit
        if self.usage_data['daily_count'] >= self.daily_limit:
            logger.warning(f"Daily API limit reached: {self.usage_data['daily_count']}/{self.daily_limit}")
            return False, "Daily API limit reached. Please try again tomorrow."

        # Check hourly limit
        if self.usage_data['hourly_count'] >= self.hourly_limit:
            logger.warning(f"Hourly API limit reached: {self.usage_data['hourly_count']}/{self.hourly_limit}")
            return False, "Hourly API limit reached. Please try again in the next hour."

        # Check rate limiting (minimum interval between requests)
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            logger.info(f"Rate limiting: waiting {wait_time:.1f}s")
            time.sleep(wait_time)

        return True, "OK"

    def record_request(self, success: bool = True) -> None:
        """Record that an API request was made"""
        self._reset_counters_if_needed()

        self.usage_data['daily_count'] += 1
        self.usage_data['hourly_count'] += 1
        self.usage_data['total_requests'] += 1

        if not success:
            self.usage_data['failed_requests'] += 1

        self.last_request_time = time.time()
        self._save_usage_data()

        logger.info(
            f"API request recorded. "
            f"Daily: {self.usage_data['daily_count']}/{self.daily_limit}, "
            f"Hourly: {self.usage_data['hourly_count']}/{self.hourly_limit}, "
            f"Total: {self.usage_data['total_requests']}"
        )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        self._reset_counters_if_needed()
        return {
            'daily': {
                'used': self.usage_data['daily_count'],
                'limit': self.daily_limit,
                'remaining': max(0, self.daily_limit - self.usage_data['daily_count'])
            },
            'hourly': {
                'used': self.usage_data['hourly_count'],
                'limit': self.hourly_limit,
                'remaining': max(0, self.hourly_limit - self.usage_data['hourly_count'])
            },
            'total_requests': self.usage_data['total_requests'],
            'failed_requests': self.usage_data['failed_requests'],
            'success_rate': (
                ((self.usage_data['total_requests'] - self.usage_data['failed_requests']) /
                 self.usage_data['total_requests'] * 100)
                if self.usage_data['total_requests'] > 0 else 0
            )
        }


def create_api_tracker():
    """
    Factory function to create the appropriate API tracker.
    Uses Redis if available, otherwise falls back to file-based.
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

            logger.info("✅ Using Redis-based API tracker (distributed mode)")
            return RedisAPITracker(redis_client)

        except (RedisConnectionError, RedisError) as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to file-based tracker.")

    # Fallback to file-based tracker
    logger.info("⚠️  Using file-based API tracker (development mode)")
    logger.warning("File-based tracker not recommended for production with multiple workers")
    return FileAPITracker()


# Global tracker instance
api_tracker = create_api_tracker()
