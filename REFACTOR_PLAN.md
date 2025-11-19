# Production-Grade Refactor Plan

## Timeline: 2-3 Days
## Goal: Scalable, Robust, Production-Ready System

---

## Phase 1: Foundation (Critical) - 8 hours

### Task 1.1: Replace pydub with ffmpeg-python ✅ PRIORITY 1
**Why:** Eliminates Python version dependency issues permanently

**Changes:**
- `src/audio_mixer.py`: Rewrite using ffmpeg-python
- `src/tts.py`: Output directly to required format
- Remove `pydub` from requirements.txt
- Add `ffmpeg-python==0.2.0`

**Impact:** Fixes deployment issues, more efficient audio processing

---

### Task 1.2: Add Celery + Redis ✅ PRIORITY 1
**Why:** Proper task queue for scalability

**New Files:**
- `celery_app.py`: Celery configuration
- `src/tasks.py`: Task definitions
- `docker-compose.yml`: Local Redis for development

**Changes:**
- `app.py`: Replace threading with Celery tasks
- `requirements.txt`: Add celery, redis, flower

**Environment Variables:**
```
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

**Railway Setup:**
- Add Redis plugin
- Add Celery worker service (separate from web)

---

### Task 1.3: Structured Logging ✅ PRIORITY 1
**Why:** Can't debug production without proper logging

**Changes:**
- Replace ALL `print()` statements
- Add `structlog` configuration
- Add log levels (DEBUG, INFO, WARNING, ERROR)
- Add request ID tracking

**New File:**
- `src/logging_config.py`

```python
import structlog

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

---

## Phase 2: Security & Reliability - 6 hours

### Task 2.1: Input Validation ✅ PRIORITY 1

**New File:**
- `src/validators.py`

```python
import re
from functools import wraps
from flask import request, jsonify

def validate_video_id(video_id: str) -> str:
    """Validate YouTube video ID format"""
    if not video_id or not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        raise ValueError(f"Invalid video ID: {video_id}")
    return video_id

def validate_request(schema):
    """Decorator for request validation"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Validate request against schema
            return f(*args, **kwargs)
        return wrapper
    return decorator
```

---

### Task 2.2: Rate Limiting ✅ PRIORITY 1

**Changes:**
- Add `Flask-Limiter`
- Configure rate limits per endpoint
- Add Redis backing store

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/watch')
@limiter.limit("10 per minute")
def watch():
    ...
```

---

### Task 2.3: Error Tracking (Sentry)

**Changes:**
- Add `sentry-sdk[flask]`
- Configure Sentry DSN
- Add custom error handlers

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[FlaskIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv('ENVIRONMENT', 'production')
)
```

---

## Phase 3: Observability - 4 hours

### Task 3.1: Health Checks ✅ PRIORITY 1

**New Endpoints:**
```python
@app.route('/health')
def health():
    """Liveness probe"""
    return {"status": "healthy"}, 200

@app.route('/ready')
def ready():
    """Readiness probe - checks dependencies"""
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "r2": check_r2()
    }
    all_healthy = all(checks.values())
    return checks, 200 if all_healthy else 503

@app.route('/version')
def version():
    return {
        "version": os.getenv('APP_VERSION', '1.0.0'),
        "commit": os.getenv('GIT_COMMIT', 'unknown'),
        "build_time": os.getenv('BUILD_TIME', 'unknown')
    }
```

---

### Task 3.2: Metrics (Prometheus)

**New File:**
- `src/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge

# Counters
videos_processed_total = Counter('videos_processed_total', 'Total videos processed')
videos_failed_total = Counter('videos_failed_total', 'Total videos failed')

# Histograms
video_processing_duration = Histogram(
    'video_processing_duration_seconds',
    'Video processing duration',
    buckets=[10, 30, 60, 120, 300, 600, 1800]
)

transcription_duration = Histogram(
    'transcription_duration_seconds',
    'Transcription duration'
)

# Gauges
active_processing_jobs = Gauge('active_processing_jobs', 'Currently processing videos')
```

**Endpoint:**
```python
from prometheus_client import generate_latest

@app.route('/metrics')
def metrics():
    return generate_latest()
```

---

## Phase 4: Performance - 4 hours

### Task 4.1: Whisper Model Singleton

**Changes to `src/transcriber.py`:**
```python
class Transcriber:
    _model = None
    _model_lock = threading.Lock()

    @classmethod
    def get_model(cls, model_size='base'):
        if cls._model is None:
            with cls._model_lock:
                if cls._model is None:  # Double-check
                    logger.info("Loading Whisper model", model_size=model_size)
                    cls._model = whisper.load_model(model_size)
        return cls._model
```

---

### Task 4.2: Temp File Management

**New File:**
- `src/temp_manager.py`

```python
import tempfile
import shutil
import atexit
from pathlib import Path

class TempFileManager:
    def __init__(self):
        self.temp_dirs = set()
        self.temp_files = set()
        atexit.register(self.cleanup_all)

    def create_temp_dir(self):
        temp_dir = Path(tempfile.mkdtemp())
        self.temp_dirs.add(temp_dir)
        return temp_dir

    def create_temp_file(self, suffix=''):
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        self.temp_files.add(Path(path))
        return path

    def cleanup_dir(self, temp_dir):
        try:
            shutil.rmtree(temp_dir)
            self.temp_dirs.discard(temp_dir)
        except Exception as e:
            logger.error("Failed to cleanup temp dir", path=temp_dir, error=str(e))

    def cleanup_all(self):
        for temp_dir in list(self.temp_dirs):
            self.cleanup_dir(temp_dir)
        for temp_file in list(self.temp_files):
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass
```

---

### Task 4.3: Database Schema Improvements

**Migration File:**
- `migrations/001_add_tracking_fields.sql`

```sql
-- Add missing fields for production
ALTER TABLE videos ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE videos ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE videos ADD COLUMN processing_started_at TIMESTAMP;
ALTER TABLE videos ADD COLUMN processing_completed_at TIMESTAMP;
ALTER TABLE videos ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE videos ADD COLUMN file_size_bytes BIGINT;
ALTER TABLE videos ADD COLUMN processing_duration_seconds INTEGER;
ALTER TABLE videos ADD COLUMN error_details JSONB;
ALTER TABLE videos ADD COLUMN last_error_at TIMESTAMP;

-- Add indexes for common queries
CREATE INDEX idx_videos_created_at ON videos(created_at DESC);
CREATE INDEX idx_videos_processing_status ON videos(processing_status);
CREATE INDEX idx_videos_video_id ON videos(video_id);

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_videos_updated_at BEFORE UPDATE ON videos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

---

## Phase 5: Configuration & Deployment - 2 hours

### Task 5.1: Configuration Management

**New File:**
- `config.py`

```python
import os
from dataclasses import dataclass

@dataclass
class Config:
    # App
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'production')
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    PORT: int = int(os.getenv('PORT', 5001))

    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL')

    # Redis
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL: str = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)

    # API Keys
    ELEVENLABS_API_KEY: str = os.getenv('ELEVENLABS_API_KEY')
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY')

    # R2
    R2_ACCESS_KEY_ID: str = os.getenv('R2_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY: str = os.getenv('R2_SECRET_ACCESS_KEY')
    R2_BUCKET_NAME: str = os.getenv('R2_BUCKET_NAME')
    R2_PUBLIC_URL: str = os.getenv('R2_PUBLIC_URL')

    # Processing
    MAX_VIDEO_LENGTH: int = int(os.getenv('MAX_VIDEO_LENGTH', 1800))
    WHISPER_MODEL: str = os.getenv('WHISPER_MODEL', 'base')

    # Monitoring
    SENTRY_DSN: str = os.getenv('SENTRY_DSN', '')

    def validate(self):
        """Validate required config"""
        required = ['DATABASE_URL', 'ELEVENLABS_API_KEY', 'OPENAI_API_KEY']
        missing = [k for k in required if not getattr(self, k)]
        if missing:
            raise ValueError(f"Missing required config: {missing}")

config = Config()
config.validate()
```

---

### Task 5.2: Updated Requirements

**requirements.txt:**
```python
# Web Framework
flask==3.0.0
flask-cors==4.0.0
flask-limiter==3.5.0

# Task Queue
celery==5.3.4
redis==5.0.1
flower==2.0.1

# OpenAI API
openai>=1.0.0

# ElevenLabs API
elevenlabs==2.23.0

# YouTube Download
yt-dlp==2024.10.7

# Audio/Video Processing (NO MORE PYDUB!)
ffmpeg-python==0.2.0
# Speech Recognition
git+https://github.com/openai/whisper.git

# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.13.0  # For migrations

# Cloud Storage
boto3==1.34.0

# Production Server
gunicorn==21.2.0

# Logging & Monitoring
structlog==23.2.0
python-json-logger==2.0.7
sentry-sdk[flask]==1.39.2
prometheus-client==0.19.0

# Utilities
python-dotenv==1.0.0
tqdm==4.66.1
```

---

### Task 5.3: Railway Configuration

**New Services Needed:**
1. **Web Service** (existing)
2. **Worker Service** (new) - Celery workers
3. **Redis** (Railway plugin)

**Procfile.web:**
```
web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 600 app:app
```

**Procfile.worker** (new file):
```
worker: celery -A celery_app worker --loglevel=info --concurrency=2
```

---

## Phase 6: Testing - 4 hours

### Task 6.1: Unit Tests

**New Directory:**
- `tests/`
  - `test_audio_mixer.py`
  - `test_transcriber.py`
  - `test_validators.py`
  - `test_tasks.py`

---

### Task 6.2: Integration Tests

**Test scenarios:**
1. End-to-end video processing
2. Error handling
3. Rate limiting
4. Health checks
5. Metrics collection

---

## Total Estimated Time

| Phase | Hours |
|-------|-------|
| Foundation | 8 |
| Security | 6 |
| Observability | 4 |
| Performance | 4 |
| Configuration | 2 |
| Testing | 4 |
| **Total** | **28 hours (~3.5 days)** |

---

## Deployment Strategy

### Step 1: Feature Branch
```bash
git checkout -b refactor/production-grade
```

### Step 2: Incremental Commits
- Commit after each task
- Keep main branch working

### Step 3: Testing
- Test locally with Docker Compose
- Test on Railway staging environment

### Step 4: Gradual Rollout
- Deploy to staging
- Run for 24 hours
- Monitor metrics
- Deploy to production

---

## Success Criteria

- [ ] No Python version issues
- [ ] Handles 50+ concurrent users
- [ ] All requests logged
- [ ] Health checks passing
- [ ] Metrics exported
- [ ] Error rate < 1%
- [ ] P95 latency < 60s for processing
- [ ] Zero memory leaks
- [ ] Proper error tracking
- [ ] Rate limiting working

---

## Risk Mitigation

**Risk:** Breaking existing functionality
**Mitigation:** Comprehensive tests, feature flags

**Risk:** Deployment downtime
**Mitigation:** Blue-green deployment, rollback plan

**Risk:** Data loss
**Mitigation:** Database migration testing, backups

---

## Next Steps

1. Review this plan
2. Get approval
3. Start Phase 1, Task 1.1
4. Commit frequently
5. Test continuously
6. Deploy incrementally
