# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies (ffmpeg for audio processing)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better Docker caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default command (will be overridden by Railway for different services)
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--workers", "2", "--threads", "4", "--timeout", "600", "app:app"]
