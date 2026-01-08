# Speaker Detection Service with pyannote.audio
# Runs in separate container to avoid torch version conflicts

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    pyannote.audio==4.0.3 \
    torch==2.8.0 \
    torchaudio==2.8.0 \
    python-dotenv==1.0.0

# Copy service code
COPY speaker_service.py /app/

# Expose port
EXPOSE 5002

# Set environment
ENV PYTHONUNBUFFERED=1

# Run service
CMD ["python", "speaker_service.py"]
