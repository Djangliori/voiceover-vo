#!/bin/bash

# Start Celery worker with proper user configuration
# This script ensures the worker doesn't run as root

# Set PATH to include ffmpeg
export PATH=/nix/var/nix/profiles/default/bin:/usr/bin:$PATH

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

    # Switch to non-root user and run celery with better error handling
    echo "Starting Celery as non-root user (uid=1001)..."
    exec su celeryuser -c "python -c 'import sys; print(\"Python:\", sys.version)' && celery -A celery_app worker --loglevel=info --concurrency=1 --pool=solo"
else
    echo "Already running as non-root user (uid=$EUID)"
    python -c 'import sys; print("Python:", sys.version)'
    exec celery -A celery_app worker --loglevel=info --concurrency=1 --pool=solo
fi