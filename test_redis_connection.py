#!/usr/bin/env python3
"""
Test Redis connection with Railway's internal URL
This will show exactly why the Flask app can't connect
"""

import os
import sys

# The Railway Redis URL
REDIS_URL = "redis://default:ULdlroSysIzTTNvnaSKBarHcKYTyxNCR@redis.railway.internal:6379"

print("=" * 60)
print("TESTING RAILWAY REDIS CONNECTION")
print("=" * 60)
print(f"\nRedis URL: {REDIS_URL}")

# Test 1: DNS Resolution
print("\n1. DNS RESOLUTION TEST:")
try:
    import socket
    hostname = "redis.railway.internal"
    ip = socket.gethostbyname(hostname)
    print(f"  ✅ {hostname} resolves to {ip}")
except socket.gaierror as e:
    print(f"  ❌ Cannot resolve {hostname}: {e}")
    print("  This means the Flask app can't find Redis on Railway's internal network!")
except Exception as e:
    print(f"  ❌ DNS error: {e}")

# Test 2: Network connectivity
print("\n2. NETWORK CONNECTIVITY TEST:")
try:
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    # Try to connect to Redis port
    result = s.connect_ex(("redis.railway.internal", 6379))
    if result == 0:
        print(f"  ✅ Port 6379 is reachable")
    else:
        print(f"  ❌ Cannot reach port 6379 (error code: {result})")
    s.close()
except Exception as e:
    print(f"  ❌ Network error: {e}")

# Test 3: Redis connection
print("\n3. REDIS CONNECTION TEST:")
try:
    import redis

    # Try different connection methods
    print("  Testing standard connection...")
    try:
        r = redis.from_url(REDIS_URL, socket_connect_timeout=10, socket_keepalive=True)
        r.ping()
        print("  ✅ Standard connection works!")
    except Exception as e:
        print(f"  ❌ Standard connection failed: {e}")

        # Try with decode_responses
        print("\n  Testing with decode_responses=True...")
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=10)
            r.ping()
            print("  ✅ Connection with decode_responses works!")
        except Exception as e2:
            print(f"  ❌ Also failed: {e2}")

        # Try StrictRedis
        print("\n  Testing with StrictRedis...")
        try:
            r = redis.StrictRedis.from_url(REDIS_URL, socket_connect_timeout=10)
            r.ping()
            print("  ✅ StrictRedis connection works!")
        except Exception as e3:
            print(f"  ❌ StrictRedis also failed: {e3}")

except ImportError:
    print("  ❌ redis package not installed")
except Exception as e:
    print(f"  ❌ Unexpected error: {e}")

# Test 4: Check if we're on Railway
print("\n4. ENVIRONMENT CHECK:")
if os.getenv('RAILWAY_ENVIRONMENT'):
    print(f"  ✅ Running on Railway (environment: {os.getenv('RAILWAY_ENVIRONMENT')})")
    print(f"  Service: {os.getenv('RAILWAY_SERVICE_NAME', 'unknown')}")
    print(f"  Deployment: {os.getenv('RAILWAY_DEPLOYMENT_ID', 'unknown')}")
else:
    print("  ⚠️  Not running on Railway")
    print("  The internal URL only works within Railway's network!")

print("\n" + "=" * 60)
print("DIAGNOSIS SUMMARY")
print("=" * 60)

print("""
If DNS resolution fails:
- The Flask app service might not have access to Railway's internal network
- Try using the public Redis URL instead of the internal one

If network connectivity fails:
- There might be a firewall or network policy issue
- Check if Redis service is running and healthy

If Redis connection fails but network works:
- Password might be wrong
- Redis might be configured differently
""")