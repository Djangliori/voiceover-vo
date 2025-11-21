#!/usr/bin/env python3
"""
Celery/Redis Debug Script
Diagnoses why Celery tasks are stuck in "processing" and not being picked up

Run this script to check:
1. Redis connection and queue status
2. Celery app configuration
3. Task registration
4. Pending tasks in the queue
5. Common misconfiguration issues

Usage:
    python debug_celery.py

Prerequisites:
    pip install redis celery python-dotenv
"""

import os
import sys
import json
from datetime import datetime

# Try to load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[WARNING] python-dotenv not installed. Environment variables must be set manually.")

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("CELERY/REDIS DEBUG SCRIPT")
print(f"Timestamp: {datetime.now().isoformat()}")
print("=" * 70)


# ==============================================================================
# 1. ENVIRONMENT VARIABLES CHECK
# ==============================================================================
print("\n" + "=" * 70)
print("1. ENVIRONMENT VARIABLES CHECK")
print("=" * 70)

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
celery_broker_url = os.getenv('CELERY_BROKER_URL', redis_url)
celery_result_backend = os.getenv('CELERY_RESULT_BACKEND', redis_url)

print(f"\nREDIS_URL:             {redis_url}")
print(f"CELERY_BROKER_URL:     {celery_broker_url}")
print(f"CELERY_RESULT_BACKEND: {celery_result_backend}")

# Check if Redis URLs match
if redis_url != celery_broker_url or redis_url != celery_result_backend:
    print("\n[WARNING] Redis URLs don't match! This could cause task routing issues.")
    print("  - Ensure all Celery-related environment variables point to the same Redis instance.")
else:
    print("\n[OK] All Redis URLs match.")


# ==============================================================================
# 2. REDIS CONNECTION CHECK
# ==============================================================================
print("\n" + "=" * 70)
print("2. REDIS CONNECTION CHECK")
print("=" * 70)

r = None  # Will be set if Redis connection succeeds

try:
    import redis as redis_lib
    r = redis_lib.from_url(redis_url, socket_connect_timeout=5)
    ping = r.ping()
    print(f"\n[OK] Redis connection successful: {ping}")

    # Get Redis info
    info = r.info()
    print(f"  - Redis version: {info.get('redis_version', 'unknown')}")
    print(f"  - Connected clients: {info.get('connected_clients', 'unknown')}")
    print(f"  - Used memory: {info.get('used_memory_human', 'unknown')}")

except ImportError:
    print(f"\n[WARNING] 'redis' package not installed!")
    print("  - Install with: pip install redis")
    print("  - Skipping Redis connection checks...")
except Exception as e:
    print(f"\n[ERROR] Redis connection error: {e}")
    print("  - Make sure Redis is running")
    print("  - Check REDIS_URL environment variable")
    print("  - Some checks will be skipped...")


# ==============================================================================
# 3. CELERY CONFIGURATION CHECK
# ==============================================================================
print("\n" + "=" * 70)
print("3. CELERY CONFIGURATION CHECK")
print("=" * 70)

try:
    from celery_app import celery_app
    print(f"\n[OK] Celery app imported successfully")
    print(f"  - App name: {celery_app.main}")
    print(f"  - Broker URL: {celery_app.conf.broker_url}")
    print(f"  - Result backend: {celery_app.conf.result_backend}")
    print(f"  - Include modules: {celery_app.conf.include}")
    print(f"  - Task serializer: {celery_app.conf.task_serializer}")
    print(f"  - Accept content: {celery_app.conf.accept_content}")

except ImportError as e:
    print(f"\n[ERROR] Cannot import celery_app: {e}")
    print("  - Check celery_app.py exists and has no syntax errors")
except Exception as e:
    print(f"\n[ERROR] Error loading Celery config: {e}")


# ==============================================================================
# 4. TASK REGISTRATION CHECK
# ==============================================================================
print("\n" + "=" * 70)
print("4. TASK REGISTRATION CHECK")
print("=" * 70)

try:
    # Force task discovery
    celery_app.loader.import_default_modules()

    # Get registered tasks
    tasks = list(celery_app.tasks.keys())

    # Filter out built-in Celery tasks
    builtin_prefixes = ['celery.']
    custom_tasks = [t for t in tasks if not any(t.startswith(p) for p in builtin_prefixes)]

    print(f"\n[INFO] Total registered tasks: {len(tasks)}")
    print(f"[INFO] Custom registered tasks: {len(custom_tasks)}")

    if custom_tasks:
        print("\nRegistered custom tasks:")
        for task_name in sorted(custom_tasks):
            task = celery_app.tasks.get(task_name)
            print(f"  - {task_name}")
            if task:
                print(f"      max_retries: {getattr(task, 'max_retries', 'N/A')}")
    else:
        print("\n[WARNING] No custom tasks registered!")
        print("  - Check that src.tasks is in celery_app.conf.include")
        print("  - Check import statements in tasks.py")

    # Specifically check for process_video_task
    expected_task = 'src.tasks.process_video_task'
    if expected_task in tasks:
        print(f"\n[OK] Expected task '{expected_task}' is registered")
    else:
        print(f"\n[WARNING] Expected task '{expected_task}' NOT found!")
        print("  - The task may be registered under a different name")
        print("  - Check the @celery_app.task decorator in src/tasks.py")

        # Check for similar task names
        similar = [t for t in tasks if 'process_video' in t.lower()]
        if similar:
            print(f"  - Similar tasks found: {similar}")

except Exception as e:
    print(f"\n[ERROR] Error checking task registration: {e}")
    import traceback
    traceback.print_exc()


# ==============================================================================
# 5. REDIS QUEUE STATUS (CELERY QUEUES)
# ==============================================================================
print("\n" + "=" * 70)
print("5. REDIS QUEUE STATUS (CELERY QUEUES)")
print("=" * 70)

queue_len = 0  # Default value

if r is None:
    print("\n[SKIPPED] Redis not connected - cannot check queue status")
else:
    try:
        # Celery uses several keys in Redis
        # Default queue name is 'celery'
        default_queue = 'celery'

        # Check queue length
        queue_len = r.llen(default_queue)
        print(f"\n[INFO] Default queue '{default_queue}' length: {queue_len}")

        if queue_len > 0:
            print(f"\n[WARNING] There are {queue_len} pending tasks in the queue!")
            print("  - Tasks are being sent but not picked up by workers")
            print("  - This indicates the worker is not consuming from this queue")

            # Peek at first few tasks
            print("\nPeeking at pending tasks (first 5):")
            pending_tasks = r.lrange(default_queue, 0, 4)
            for i, task_data in enumerate(pending_tasks):
                try:
                    task_json = json.loads(task_data)
                    task_name = task_json.get('headers', {}).get('task', 'unknown')
                    task_id = task_json.get('headers', {}).get('id', 'unknown')
                    task_args = task_json.get('body', '')

                    # Try to decode body if it's base64 encoded
                    try:
                        import base64
                        body_decoded = base64.b64decode(task_args).decode('utf-8')
                        body_json = json.loads(body_decoded)
                        args = body_json[0] if body_json else []
                    except:
                        args = 'encoded'

                    print(f"\n  Task {i+1}:")
                    print(f"    - Task name: {task_name}")
                    print(f"    - Task ID: {task_id}")
                    print(f"    - Arguments: {args}")
                except json.JSONDecodeError:
                    print(f"\n  Task {i+1}: Could not decode task data")
                except Exception as ex:
                    print(f"\n  Task {i+1}: Error parsing - {ex}")
        else:
            print("  - Queue is empty (no pending tasks)")

        # Check other potential queues
        print("\nSearching for other Celery-related keys in Redis:")
        celery_keys = r.keys('celery*') + r.keys('_kombu*') + r.keys('unacked*')
        if celery_keys:
            for key in celery_keys[:20]:  # Limit to first 20
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                key_type = r.type(key)
                key_type_str = key_type.decode('utf-8') if isinstance(key_type, bytes) else key_type

                if key_type_str == 'list':
                    size = r.llen(key)
                elif key_type_str == 'set':
                    size = r.scard(key)
                elif key_type_str == 'hash':
                    size = r.hlen(key)
                elif key_type_str == 'zset':
                    size = r.zcard(key)
                else:
                    size = 'N/A'

                print(f"  - {key_str}: type={key_type_str}, size={size}")
        else:
            print("  - No Celery-related keys found in Redis")

    except Exception as e:
        print(f"\n[ERROR] Error checking Redis queues: {e}")
        import traceback
        traceback.print_exc()


# ==============================================================================
# 6. CHECK CELERY WORKER STATUS
# ==============================================================================
print("\n" + "=" * 70)
print("6. CELERY WORKER STATUS")
print("=" * 70)

active = None  # Initialize for later use in summary

try:
    # Try to inspect workers
    i = celery_app.control.inspect()

    # Check for active workers
    active = i.active()
    registered = i.registered()
    stats = i.stats()

    if active is None and registered is None:
        print("\n[WARNING] No Celery workers are responding!")
        print("  - The worker may not be running")
        print("  - The worker may be connected to a different Redis instance")
        print("  - The worker may be using a different Celery app")
        print("\nTo start a worker locally:")
        print("  celery -A celery_app worker --loglevel=info")
    else:
        print("\n[OK] Workers are responding")

        if active:
            print("\nActive tasks per worker:")
            for worker, tasks in active.items():
                print(f"  - {worker}: {len(tasks)} active tasks")
                for task in tasks:
                    print(f"      - {task.get('name', 'unknown')} (id: {task.get('id', 'unknown')[:8]}...)")

        if registered:
            print("\nRegistered tasks per worker:")
            for worker, tasks in registered.items():
                print(f"  - {worker}:")
                for task in tasks[:10]:  # Limit output
                    print(f"      - {task}")
                if len(tasks) > 10:
                    print(f"      ... and {len(tasks) - 10} more")

        if stats:
            print("\nWorker stats:")
            for worker, stat in stats.items():
                print(f"  - {worker}:")
                print(f"      - Pool: {stat.get('pool', {}).get('implementation', 'unknown')}")
                print(f"      - Concurrency: {stat.get('pool', {}).get('max-concurrency', 'unknown')}")
                print(f"      - PID: {stat.get('pid', 'unknown')}")

except Exception as e:
    print(f"\n[ERROR] Error checking worker status: {e}")
    print("  - Workers may not be running or may be unreachable")


# ==============================================================================
# 7. DATABASE CHECK (Videos in 'processing' status)
# ==============================================================================
print("\n" + "=" * 70)
print("7. DATABASE CHECK (Stuck videos)")
print("=" * 70)

try:
    from src.database import Database, Video
    db = Database()
    session = db.get_session()

    # Find videos stuck in 'processing'
    processing_videos = session.query(Video).filter_by(processing_status='processing').all()

    if processing_videos:
        print(f"\n[WARNING] Found {len(processing_videos)} videos stuck in 'processing' status:")
        for video in processing_videos[:10]:  # Limit output
            print(f"\n  Video ID: {video.video_id}")
            print(f"    - Title: {video.title}")
            print(f"    - Status: {video.processing_status}")
            print(f"    - Progress: {video.progress}%")
            print(f"    - Status Message: {video.status_message}")
            print(f"    - Created: {video.created_at}")
            print(f"    - Updated: {video.updated_at}")
    else:
        print("\n[OK] No videos stuck in 'processing' status")

    # Also check failed videos
    failed_videos = session.query(Video).filter_by(processing_status='failed').order_by(Video.updated_at.desc()).limit(5).all()
    if failed_videos:
        print(f"\n[INFO] Recent failed videos ({len(failed_videos)} shown):")
        for video in failed_videos:
            print(f"  - {video.video_id}: {video.error_message}")

    db.close_session(session)

except Exception as e:
    print(f"\n[ERROR] Error checking database: {e}")
    import traceback
    traceback.print_exc()


# ==============================================================================
# 8. IMPORT PATH ANALYSIS
# ==============================================================================
print("\n" + "=" * 70)
print("8. IMPORT PATH ANALYSIS")
print("=" * 70)

print(f"\nPython executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"\nCurrent working directory: {os.getcwd()}")
print(f"\nPython path:")
for path in sys.path[:10]:
    print(f"  - {path}")

# Check if we can import the task directly
print("\nTesting task import:")
try:
    from src.tasks import process_video_task
    print(f"  [OK] Can import process_video_task from src.tasks")
    print(f"       Task name: {process_video_task.name}")
    print(f"       Bound to app: {process_video_task.app.main}")
except ImportError as e:
    print(f"  [ERROR] Cannot import process_video_task: {e}")
except Exception as e:
    print(f"  [ERROR] Error importing: {e}")


# ==============================================================================
# 9. CONFIGURATION COMPARISON (App vs Worker)
# ==============================================================================
print("\n" + "=" * 70)
print("9. CONFIGURATION COMPARISON ANALYSIS")
print("=" * 70)

print("\nPotential issues to check:")
print("""
1. IMPORT MISMATCH:
   - celery_app.py sets include=['src.tasks']
   - tasks.py imports 'from celery_app import celery_app' (not 'from src.celery_app')
   - This could cause different task registration in different contexts

2. REDIS URL MISSING FROM .env:
   - Your .env file may be missing REDIS_URL
   - Default falls back to redis://localhost:6379/0
   - Worker and app must use the same Redis URL

3. WORKER NOT RUNNING:
   - Worker needs to be started separately
   - Command: celery -A celery_app worker --loglevel=info

4. QUEUE NAME MISMATCH:
   - Default queue is 'celery'
   - Make sure worker is consuming from the same queue
""")


# ==============================================================================
# 10. RECOMMENDED FIXES
# ==============================================================================
print("\n" + "=" * 70)
print("10. RECOMMENDED FIXES")
print("=" * 70)

print("""
Based on the analysis, here are the recommended fixes:

1. ADD REDIS_URL TO .env:
   REDIS_URL=redis://localhost:6379/0
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0

2. CHECK WORKER IS RUNNING:
   Start worker: celery -A celery_app worker --loglevel=info

3. VERIFY QUEUE CONSUMPTION:
   Worker should show: "celery exchange=celery(direct) key=celery"

4. CHECK TASK NAME CONSISTENCY:
   Task should be registered as 'src.tasks.process_video_task'

5. TEST TASK DIRECTLY:
   from src.tasks import process_video_task
   result = process_video_task.delay('test_id', 'https://youtube.com/watch?v=test')
   print(result.id)

6. CHECK WORKER LOGS:
   Look for: "celery@... ready" message
   Look for: "Received task: src.tasks.process_video_task" when task is sent
""")

# ==============================================================================
# SUMMARY
# ==============================================================================
print("\n" + "=" * 70)
print("DEBUG SUMMARY")
print("=" * 70)

summary = []
if queue_len > 0:
    summary.append(f"[ISSUE] {queue_len} tasks pending in queue - worker not consuming")
try:
    if active is None:
        summary.append("[ISSUE] No workers responding")
except:
    summary.append("[ISSUE] Could not check worker status")

if not summary:
    summary.append("[OK] No obvious issues found")

print("\n" + "\n".join(summary))
print("\n" + "=" * 70)
print("End of debug report")
print("=" * 70)
