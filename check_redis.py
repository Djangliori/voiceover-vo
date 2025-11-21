#!/usr/bin/env python3
"""
Check Redis connection on Railway
Shows why Flask app can't connect to Redis
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("REDIS CONNECTION CHECK")
print("=" * 60)

# Check environment variables
print("\n1. ENVIRONMENT VARIABLES:")
redis_url = os.getenv('REDIS_URL')
celery_broker = os.getenv('CELERY_BROKER_URL')
redis_host = os.getenv('REDIS_HOST')
redishost = os.getenv('REDISHOST')  # Railway sometimes uses this
redis_private_url = os.getenv('REDIS_PRIVATE_URL')  # Railway private URL

print(f"  REDIS_URL: {redis_url or 'NOT SET'}")
print(f"  CELERY_BROKER_URL: {celery_broker or 'NOT SET'}")
print(f"  REDIS_HOST: {redis_host or 'NOT SET'}")
print(f"  REDISHOST: {redishost or 'NOT SET'}")
print(f"  REDIS_PRIVATE_URL: {redis_private_url or 'NOT SET'}")

# Try to find the correct Redis URL
if not redis_url:
    # Railway patterns
    if redishost:
        redis_url = f"redis://default:{os.getenv('REDISPASSWORD', '')}@{redishost}:{os.getenv('REDISPORT', '6379')}"
        print(f"\n  Constructed from REDISHOST: {redis_url}")
    elif redis_private_url:
        redis_url = redis_private_url
        print(f"\n  Using REDIS_PRIVATE_URL")
    else:
        redis_url = 'redis://localhost:6379/0'
        print(f"\n  Using default localhost (will fail on Railway!)")

# Test connection
print("\n2. CONNECTION TEST:")
try:
    import redis
    print(f"  Connecting to: {redis_url}")

    # Try with different timeouts
    for timeout in [1, 5, 10]:
        try:
            r = redis.from_url(redis_url, socket_connect_timeout=timeout, socket_keepalive=True)
            r.ping()
            print(f"  ✅ SUCCESS with timeout={timeout}s")

            # Test basic operations
            r.set('test_key', 'test_value', ex=10)
            value = r.get('test_key')
            print(f"  ✅ Read/Write test passed: {value}")

            # Check Celery queue
            queue_length = r.llen('celery')
            print(f"  📊 Celery queue length: {queue_length}")

            break
        except redis.TimeoutError:
            print(f"  ⏱️ Timeout with {timeout}s")
            if timeout == 10:
                print("  ❌ Connection timed out even with 10s timeout")
        except Exception as e:
            print(f"  ❌ Error with timeout={timeout}s: {e}")
            if timeout == 10:
                raise

except ImportError:
    print("  ❌ redis package not installed")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ Connection failed: {e}")
    print("\n  This is why Flask falls back to threading mode!")

# Show what Railway expects
print("\n3. RAILWAY CONFIGURATION:")
print("  On Railway, you should have these environment variables:")
print("  - For Flask app service: Set REDIS_URL to your Redis internal URL")
print("  - For Celery worker: Same REDIS_URL")
print("  - Format: redis://default:<password>@<service>.railway.internal:6379")
print("\n  Example for Railway:")
print("  REDIS_URL=redis://default:yourpassword@redis.railway.internal:6379")

# Check if running on Railway
if os.getenv('RAILWAY_ENVIRONMENT'):
    print(f"\n  ✅ Running on Railway (environment: {os.getenv('RAILWAY_ENVIRONMENT')})")
    print("  Make sure REDIS_URL is set in your service variables!")
else:
    print("\n  ℹ️ Not running on Railway (local environment)")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)