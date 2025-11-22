#!/usr/bin/env python3
"""Debug script to check environment variables"""

import os
import json

# Check all Redis-related variables
redis_vars = {
    'REDIS_URL': os.getenv('REDIS_URL'),
    'REDIS_PRIVATE_URL': os.getenv('REDIS_PRIVATE_URL'),
    'REDISHOST': os.getenv('REDISHOST'),
    'REDIS_HOST': os.getenv('REDIS_HOST'),
    'REDISPORT': os.getenv('REDISPORT'),
    'REDIS_PORT': os.getenv('REDIS_PORT'),
    'REDISPASSWORD': os.getenv('REDISPASSWORD'),
    'REDIS_PASSWORD': os.getenv('REDIS_PASSWORD'),
}

print("=== Redis Environment Variables ===")
for key, value in redis_vars.items():
    if value:
        # Hide password in output
        if 'PASSWORD' in key:
            print(f"{key}: [SET - HIDDEN]")
        else:
            print(f"{key}: {value[:50]}..." if len(str(value)) > 50 else f"{key}: {value}")
    else:
        print(f"{key}: NOT SET")

print("\n=== All Environment Variables ===")
all_vars = os.environ
redis_related = [k for k in all_vars.keys() if 'REDIS' in k.upper()]
for var in redis_related:
    print(f"Found: {var}")