"""
Central Configuration Management
Consolidates all application configuration with validation
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Central configuration class with validation"""

    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
    RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
    ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')

    # Flask Configuration
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5001))
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Video Processing Limits
    MAX_VIDEO_LENGTH = int(os.getenv('MAX_VIDEO_LENGTH', 1800))  # 30 minutes
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 500 * 1024 * 1024))  # 500MB
    MAX_CONCURRENT_JOBS = int(os.getenv('MAX_CONCURRENT_JOBS', 3))
    MAX_MEMORY_PER_JOB = int(os.getenv('MAX_MEMORY_PER_JOB', 2048))  # 2GB in MB

    # Audio Settings
    ORIGINAL_AUDIO_VOLUME = float(os.getenv('ORIGINAL_AUDIO_VOLUME', 0.05))
    VOICEOVER_VOLUME = float(os.getenv('VOICEOVER_VOLUME', 1.0))
    WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')

    # Transcription Settings
    TRANSCRIPTION_PROVIDER = os.getenv('TRANSCRIPTION_PROVIDER', 'assemblyai')  # 'assemblyai' or 'whisper'
    ENABLE_SPEAKER_DIARIZATION = os.getenv('ENABLE_SPEAKER_DIARIZATION', 'true').lower() == 'true'
    MAX_SPEAKERS = int(os.getenv('MAX_SPEAKERS', 10))  # Maximum speakers to detect
    SPEAKER_MERGE_PAUSE = float(os.getenv('SPEAKER_MERGE_PAUSE', 1.5))  # Seconds between segments to merge

    # Directories
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
    TEMP_DIR = os.getenv('TEMP_DIR', 'temp')

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        # Fix for SQLAlchemy 1.4+ compatibility
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    # Redis/Celery
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

    # Cloudflare R2 Storage
    CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')
    R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
    R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME', 'geyoutube-videos')
    R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL', 'https://videos.geyoutube.com')

    # API Timeouts (in seconds)
    OPENAI_TIMEOUT = int(os.getenv('OPENAI_TIMEOUT', 60))
    ELEVENLABS_TIMEOUT = int(os.getenv('ELEVENLABS_TIMEOUT', 30))
    RAPIDAPI_TIMEOUT = int(os.getenv('RAPIDAPI_TIMEOUT', 30))
    DOWNLOAD_TIMEOUT = int(os.getenv('DOWNLOAD_TIMEOUT', 60))
    ASSEMBLYAI_TIMEOUT = int(os.getenv('ASSEMBLYAI_TIMEOUT', 300))  # 5 minutes for long transcriptions

    # Rate Limiting
    API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', 100))  # requests per minute
    API_BURST_LIMIT = int(os.getenv('API_BURST_LIMIT', 10))  # burst allowance

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []

        # Check required API keys
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required")
        if not cls.ELEVENLABS_API_KEY:
            errors.append("ELEVENLABS_API_KEY is required")

        # Check transcription provider API key
        if cls.TRANSCRIPTION_PROVIDER == 'assemblyai' and not cls.ASSEMBLYAI_API_KEY:
            errors.append("ASSEMBLYAI_API_KEY is required when using AssemblyAI transcription")

        # Validate numeric ranges
        if not 0 <= cls.ORIGINAL_AUDIO_VOLUME <= 1:
            errors.append("ORIGINAL_AUDIO_VOLUME must be between 0 and 1")
        if not 0 <= cls.VOICEOVER_VOLUME <= 1:
            errors.append("VOICEOVER_VOLUME must be between 0 and 1")
        if cls.MAX_VIDEO_LENGTH <= 0:
            errors.append("MAX_VIDEO_LENGTH must be positive")
        if cls.MAX_FILE_SIZE <= 0:
            errors.append("MAX_FILE_SIZE must be positive")

        # Create required directories
        for dir_path in [cls.OUTPUT_DIR, cls.TEMP_DIR]:
            Path(dir_path).mkdir(exist_ok=True)

        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")

    @classmethod
    def get_celery_config(cls):
        """Get Celery-specific configuration"""
        return {
            'broker_url': cls.CELERY_BROKER_URL,
            'result_backend': cls.CELERY_RESULT_BACKEND,
            'task_serializer': 'json',
            'accept_content': ['json'],
            'result_serializer': 'json',
            'timezone': 'UTC',
            'enable_utc': True,
            'worker_prefetch_multiplier': 1,
            'task_acks_late': True,
            'task_track_started': True,
            'task_time_limit': 3600,  # 1 hour
            'task_soft_time_limit': 3300,  # 55 minutes
        }

    @classmethod
    def is_r2_configured(cls):
        """Check if R2 storage is properly configured"""
        return all([
            cls.CLOUDFLARE_ACCOUNT_ID,
            cls.R2_ACCESS_KEY_ID,
            cls.R2_SECRET_ACCESS_KEY,
            cls.R2_BUCKET_NAME
        ])

    @classmethod
    def is_celery_configured(cls):
        """Check if Celery is properly configured"""
        return bool(cls.REDIS_URL and cls.CELERY_BROKER_URL)


# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    print(f"Warning: {e}")