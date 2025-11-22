#!/bin/bash

# Simple worker that just sleeps to prevent Railway from restarting
# The main app is already handling video processing via threading

echo "Celery worker disabled - main app using threading mode"
echo "Video processing is handled by the main Flask app"
echo "To enable Celery, ensure Redis is properly configured"

# Keep the process alive
while true; do
    sleep 3600
    echo "Worker heartbeat - $(date)"
done