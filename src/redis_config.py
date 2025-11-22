"""
Redis Configuration Helper for Railway
Handles various Redis URL formats and Railway's environment variables
"""

import os
import logging

logger = logging.getLogger(__name__)

def get_redis_url():
    """
    Get Redis URL from various possible Railway environment variables
    Railway can provide Redis in different formats
    """

    # Try direct Redis URLs first
    redis_url = (
        os.getenv('REDIS_URL') or
        os.getenv('REDIS_PRIVATE_URL') or
        os.getenv('REDISCLOUD_URL') or
        os.getenv('REDIS_TLS_URL')
    )

    if redis_url:
        logger.info(f"Found Redis URL from environment")
        return redis_url

    # Try building from components (Railway sometimes provides these)
    redis_host = os.getenv('REDISHOST') or os.getenv('REDIS_HOST')
    redis_port = os.getenv('REDISPORT') or os.getenv('REDIS_PORT') or '6379'
    redis_password = os.getenv('REDISPASSWORD') or os.getenv('REDIS_PASSWORD')
    redis_user = os.getenv('REDISUSER') or os.getenv('REDIS_USER') or 'default'

    if redis_host:
        if redis_password:
            redis_url = f"redis://{redis_user}:{redis_password}@{redis_host}:{redis_port}/0"
        else:
            redis_url = f"redis://{redis_host}:{redis_port}/0"
        logger.info(f"Built Redis URL from components")
        return redis_url

    # No Redis found
    logger.warning("No Redis configuration found in environment")
    return None

def test_redis_connection(redis_url):
    """Test if Redis is actually reachable"""
    if not redis_url:
        return False

    try:
        import redis
        r = redis.from_url(redis_url, socket_connect_timeout=5)
        r.ping()
        logger.info("Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False