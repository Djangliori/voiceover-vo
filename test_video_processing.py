#!/usr/bin/env python3
"""
Test video processing pipeline
"""

import requests
import time
import sys

# Server URL
BASE_URL = "http://localhost:5001"

# Test with a SHORT video (important for testing!)
# Using a short demo video - replace with any short YouTube video
TEST_VIDEO_ID = "jNQXAC9IVRw"  # "Me at the zoo" - first YouTube video (18 seconds)

print("=" * 70)
print("  Testing Georgian Voiceover Video Processing")
print("=" * 70)
print()

# Step 1: Check server is running
print("1. Checking server status...")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    if response.status_code == 200:
        print("   SUCCESS: Server is running")
    else:
        print(f"   ERROR: Server returned status {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"   ERROR: Cannot connect to server: {e}")
    print("   Make sure the server is running at http://localhost:5001")
    sys.exit(1)

print()

# Step 2: Login
print("2. Logging in...")
try:
    session = requests.Session()  # Use session to maintain cookies
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": "admin@test.com", "password": "testpassword123"},
        timeout=10
    )

    if response.status_code == 200:
        print("   SUCCESS: Logged in as admin")
    else:
        print(f"   ERROR: Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)
except Exception as e:
    print(f"   ERROR: Login error: {e}")
    sys.exit(1)

print()

# Step 3: Submit video for processing
print(f"3. Submitting video for processing: {TEST_VIDEO_ID}")
print(f"   YouTube URL: https://youtube.com/watch?v={TEST_VIDEO_ID}")

try:
    response = session.post(
        f"{BASE_URL}/process",
        json={"url": f"https://youtube.com/watch?v={TEST_VIDEO_ID}"},
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        job_id = data.get('job_id')
        print(f"   SUCCESS: Video submitted successfully!")
        print(f"   Job ID: {job_id}")
    else:
        print(f"   ERROR: Failed to submit video: {response.status_code}")
        print(f"   Response: {response.text}")
        sys.exit(1)
except Exception as e:
    print(f"   ERROR: Error submitting video: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Step 4: Monitor processing status
print("4. Monitoring processing status...")
print("   (This may take a few minutes)")
print()

max_wait = 300  # 5 minutes max
start_time = time.time()
last_status = None

while time.time() - start_time < max_wait:
    try:
        response = session.get(f"{BASE_URL}/status/{job_id}", timeout=10)

        if response.status_code == 200:
            data = response.json()
            status = data.get('status')
            message = data.get('message', '')
            progress = data.get('progress', 0)

            # Only print if status changed
            if status != last_status:
                elapsed = int(time.time() - start_time)
                print(f"   [{elapsed}s] Status: {status}")
                if message:
                    print(f"          {message}")
                last_status = status

            # Check if completed
            if status == 'completed':
                print()
                print("   SUCCESS: Processing completed successfully!")
                output_file = data.get('output_file')
                if output_file:
                    print(f"   Output file: {output_file}")
                print()
                print("=" * 70)
                print("  Video processing test PASSED!")
                print("=" * 70)
                print()
                print(f"  Watch at: http://localhost:5001/watch?v={TEST_VIDEO_ID}")
                print()
                sys.exit(0)

            # Check if failed
            if status == 'failed':
                print()
                print(f"   ERROR: Processing failed: {message}")
                error = data.get('error')
                if error:
                    print(f"   Error: {error}")
                sys.exit(1)

        time.sleep(2)  # Poll every 2 seconds

    except Exception as e:
        print(f"   ERROR: Error checking status: {e}")
        time.sleep(2)
        continue

# Timeout
print()
print(f"   TIMEOUT: Processing took longer than {max_wait} seconds")
print("   Check the server logs for details")
sys.exit(1)
