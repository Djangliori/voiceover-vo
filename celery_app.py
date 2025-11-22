"""
Celery Configuration
Task queue for background video processing
"""

import os
import sys
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Redis configuration helper
from src.redis_config import get_redis_url

# Redis configuration - handles Railway's various formats
REDIS_URL = get_redis_url()
if not REDIS_URL:
    print("WARNING: No Redis configuration found, using fallback")
    REDIS_URL = 'redis://localhost:6379/0'

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

# Log the Redis URL for debugging (hide password)
import re
safe_url = re.sub(r':([^:@]+)@', ':****@', REDIS_URL) if REDIS_URL else 'None'
print(f"Celery using Redis URL: {safe_url}")

# Create Celery app
celery_app = Celery(
    'georgian_voiceover',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['src.tasks']
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Broker connection settings (Celery 6.0+)
    broker_connection_retry_on_startup=True,

    # Task execution settings
    task_acks_late=True,  # Acknowledge tasks after execution
    task_reject_on_worker_lost=True,  # Retry if worker crashes
    worker_prefetch_multiplier=1,  # One task at a time (video processing is memory intensive)

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to Redis

    # Task retry settings
    task_default_retry_delay=60,  # Retry after 60 seconds
    task_max_retries=3,  # Max 3 retries

    # Worker settings
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks (prevent memory leaks)
    worker_disable_rate_limits=True,  # No rate limiting (we'll use Flask-Limiter)

    # Monitoring
    worker_send_task_events=True,  # Send task events for Flower monitoring
    task_send_sent_event=True,
)

if __name__ == '__main__':
    celery_app.start()
