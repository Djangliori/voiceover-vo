#!/bin/bash

# Start Celery worker with proper user configuration
# This script ensures the worker doesn't run as root

# Set PATH to include ffmpeg
export PATH=/nix/var/nix/profiles/default/bin:/usr/bin:$PATH

# Set default TTS_PROVIDER if not set (fixes Config import error)
export TTS_PROVIDER="${TTS_PROVIDER:-elevenlabs}"

# Check if Redis is configured
if [ -z "$REDIS_URL" ] && [ -z "$REDIS_PRIVATE_URL" ]; then
    echo "================================================================"
    echo "Redis not configured - Celery worker not needed"
    echo "The main app is using threading mode for video processing"
    echo "This is perfectly fine for moderate traffic"
    echo "================================================================"

    # Just keep the process alive
    while true; do
        sleep 3600
        echo "Worker placeholder - $(date) - Redis not configured"
    done
    exit 0
fi

# Check if running as root and create user if needed
if [ "$EUID" -eq 0 ]; then
    echo "Running as root, creating non-root user..."

    # Create a non-root user if it doesn't exist
    if ! id -u celeryuser > /dev/null 2>&1; then
        useradd -m -u 1001 -s /bin/bash celeryuser
    fi

    # Ensure temp directory has proper permissions
    mkdir -p /app/temp
    chown -R celeryuser:celeryuser /app/temp

    # Switch to non-root user and run celery
    echo "Starting Celery as non-root user (uid=1001)..."
    # Export TTS_PROVIDER for the su session as well
    exec su celeryuser -c "export TTS_PROVIDER=${TTS_PROVIDER:-elevenlabs} && celery -A celery_app worker --loglevel=info --concurrency=1"
else
    echo "Already running as non-root user (uid=$EUID)"
    exec celery -A celery_app worker --loglevel=info --concurrency=1
fi