"""
Pytest Configuration and Shared Fixtures
Provides reusable test fixtures for all test modules
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Base, Database, Video, User, Tier
from src.config import Config


# ========================================
# Application Fixtures
# ========================================

@pytest.fixture(scope='session')
def app() -> Generator[Flask, None, None]:
    """
    Create Flask application for testing
    Uses in-memory SQLite database and disables external services
    """
    # Set testing environment variables
    os.environ['TESTING'] = '1'
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['SECRET_KEY'] = 'test-secret-key-not-for-production'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    # Import app after setting environment
    from app import app as flask_app

    # Configure for testing
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    flask_app.config['DEBUG'] = False

    yield flask_app


@pytest.fixture(scope='function')
def client(app):
    """Flask test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Flask CLI test runner"""
    return app.test_cli_runner()


# ========================================
# Database Fixtures
# ========================================

@pytest.fixture(scope='session')
def db_engine():
    """Create in-memory SQLite engine for testing"""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope='function')
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Create a new database session for each test
    Automatically rolls back after test completion
    """
    connection = db_engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope='function')
def db(db_session):
    """Database instance with test session"""
    database = Database()
    database._session = db_session
    yield database


# ========================================
# Model Fixtures
# ========================================

@pytest.fixture
def sample_tier(db_session) -> Tier:
    """Create a sample tier for testing"""
    tier = Tier(
        name='free',
        display_name='Free Tier',
        minutes_per_month=30,
        price_monthly=0.0,
        description='Free tier for testing',
        is_active=True
    )
    db_session.add(tier)
    db_session.commit()
    return tier


@pytest.fixture
def sample_user(db_session, sample_tier) -> User:
    """Create a sample user for testing"""
    user = User(
        email='test@example.com',
        name='Test User',
        tier_id=sample_tier.id,
        is_admin=False,
        is_active=True
    )
    user.set_password('testpassword123')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_user(db_session, sample_tier) -> User:
    """Create an admin user for testing"""
    user = User(
        email='admin@example.com',
        name='Admin User',
        tier_id=sample_tier.id,
        is_admin=True,
        is_active=True
    )
    user.set_password('adminpassword123')
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_video(db_session) -> Video:
    """Create a sample video record for testing"""
    video = Video(
        video_id='dQw4w9WgXcQ',
        title='Test Video Title',
        original_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        r2_url='https://videos.example.com/test.mp4',
        duration=180,
        processing_status='completed',
        progress=100,
        status_message='Processing complete',
        view_count=0
    )
    db_session.add(video)
    db_session.commit()
    return video


@pytest.fixture
def processing_video(db_session) -> Video:
    """Create a video in processing state"""
    video = Video(
        video_id='test123456',
        title='Processing Video',
        original_url='https://www.youtube.com/watch?v=test123456',
        processing_status='processing',
        progress=50,
        status_message='Transcribing audio...',
    )
    db_session.add(video)
    db_session.commit()
    return video


# ========================================
# File System Fixtures
# ========================================

@pytest.fixture(scope='function')
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope='function')
def temp_video_file(temp_dir) -> Path:
    """Create a fake video file for testing"""
    video_path = temp_dir / 'test_video.mp4'
    video_path.write_bytes(b'fake video content')
    return video_path


@pytest.fixture(scope='function')
def temp_audio_file(temp_dir) -> Path:
    """Create a fake audio file for testing"""
    audio_path = temp_dir / 'test_audio.wav'
    audio_path.write_bytes(b'fake audio content')
    return audio_path


# ========================================
# Mock Data Fixtures
# ========================================

@pytest.fixture
def youtube_urls():
    """Sample YouTube URLs for testing"""
    return {
        'standard': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'short': 'https://youtu.be/dQw4w9WgXcQ',
        'embed': 'https://www.youtube.com/embed/dQw4w9WgXcQ',
        'shorts': 'https://www.youtube.com/shorts/dQw4w9WgXcQ',
        'voyoutube': 'https://voyoutube.com/watch?v=dQw4w9WgXcQ',
        'voyoutube_shorts': 'https://voyoutube.com/shorts/dQw4w9WgXcQ',
        'invalid': 'https://example.com/not-a-youtube-url',
        'malformed': 'not-even-a-url',
    }


@pytest.fixture
def sample_segments():
    """Sample transcription segments for testing"""
    return [
        {
            'text': 'Hello world',
            'start': 0.0,
            'end': 2.5,
            'speaker': 'SPEAKER_1'
        },
        {
            'text': 'This is a test',
            'start': 2.5,
            'end': 5.0,
            'speaker': 'SPEAKER_1'
        },
        {
            'text': 'Testing translation',
            'start': 5.0,
            'end': 7.5,
            'speaker': 'SPEAKER_2'
        }
    ]


@pytest.fixture
def sample_translated_segments():
    """Sample translated segments for testing"""
    return [
        {
            'original_text': 'Hello world',
            'translated_text': 'გამარჯობა მსოფლიო',
            'start': 0.0,
            'end': 2.5,
            'speaker': 'SPEAKER_1'
        },
        {
            'original_text': 'This is a test',
            'translated_text': 'ეს არის ტესტი',
            'start': 2.5,
            'end': 5.0,
            'speaker': 'SPEAKER_1'
        }
    ]


# ========================================
# Environment Fixtures
# ========================================

@pytest.fixture(scope='function', autouse=True)
def reset_env_vars():
    """Reset environment variables after each test"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration for testing"""
    monkeypatch.setenv('VOICEGAIN_API_KEY', 'test_voicegain_key')
    monkeypatch.setenv('OPENAI_API_KEY', 'test_openai_key')
    monkeypatch.setenv('RAPIDAPI_KEY', 'test_rapidapi_key')
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379/15')  # Use test DB 15
    monkeypatch.setenv('TESTING', '1')

    # Reload config with new env vars
    from importlib import reload
    import src.config
    reload(src.config)

    return Config


# ========================================
# Cleanup Fixtures
# ========================================

@pytest.fixture(scope='function', autouse=True)
def cleanup_temp_files(temp_dir):
    """Automatically cleanup temporary files after tests"""
    yield
    # Cleanup is automatic with tempfile.TemporaryDirectory
    pass
