"""
Rate Limiting Configuration
Centralized rate limiting setup for the application
"""

import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create limiter instance (will be initialized by app)
limiter = None


def init_rate_limiter(app):
    """
    Initialize rate limiter with Flask app.

    Args:
        app: Flask application instance

    Returns:
        Limiter: Configured rate limiter instance
    """
    global limiter

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=os.getenv('REDIS_URL', 'memory://'),
        storage_options={"socket_connect_timeout": 30},
        strategy="fixed-window",
        headers_enabled=True,  # Add X-RateLimit-* headers to responses
    )

    return limiter


# Rate limit decorators for common use cases
def auth_rate_limit():
    """Rate limit for authentication endpoints (stricter)"""
    return limiter.limit("5 per hour", override_defaults=False)


def api_rate_limit():
    """Rate limit for API endpoints (moderate)"""
    return limiter.limit("30 per minute", override_defaults=False)


def download_rate_limit():
    """Rate limit for download endpoints (lenient)"""
    return limiter.limit("10 per minute", override_defaults=False)
