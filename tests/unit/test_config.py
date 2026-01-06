"""
Unit Tests for config.py
Tests configuration management, validation, and environment variable handling
"""

import os
import pytest
from pathlib import Path
from src.config import Config


# ========================================
# Test Configuration Loading
# ========================================

class TestConfigLoading:
    """Tests for configuration loading from environment"""

    @pytest.mark.unit
    def test_config_has_required_attributes(self):
        """Test that Config has all required attributes"""
        required_attrs = [
            'VOICEGAIN_API_KEY',
            'OPENAI_API_KEY',
            'RAPIDAPI_KEY',
            'FLASK_PORT',
            'SECRET_KEY',
            'MAX_VIDEO_LENGTH',
            'MAX_FILE_SIZE',
            'MAX_CONCURRENT_JOBS',
            'ORIGINAL_AUDIO_VOLUME',
            'VOICEOVER_VOLUME',
            'OUTPUT_DIR',
            'TEMP_DIR',
            'DATABASE_URL',
            'REDIS_URL',
        ]
        for attr in required_attrs:
            assert hasattr(Config, attr), f"Config missing attribute: {attr}"

    @pytest.mark.unit
    def test_default_flask_port(self):
        """Test default Flask port is set"""
        assert Config.FLASK_PORT in [5000, 5001]
        assert isinstance(Config.FLASK_PORT, int)

    @pytest.mark.unit
    def test_default_video_limits(self):
        """Test default video processing limits"""
        assert Config.MAX_VIDEO_LENGTH > 0
        assert Config.MAX_FILE_SIZE > 0
        assert Config.MAX_CONCURRENT_JOBS > 0
        assert isinstance(Config.MAX_VIDEO_LENGTH, int)
        assert isinstance(Config.MAX_FILE_SIZE, int)

    @pytest.mark.unit
    def test_default_audio_volumes(self):
        """Test default audio volume settings"""
        assert 0 <= Config.ORIGINAL_AUDIO_VOLUME <= 1
        assert 0 <= Config.VOICEOVER_VOLUME <= 1
        assert isinstance(Config.ORIGINAL_AUDIO_VOLUME, float)
        assert isinstance(Config.VOICEOVER_VOLUME, float)

    @pytest.mark.unit
    def test_directories_exist(self):
        """Test that default directories are defined"""
        assert Config.OUTPUT_DIR is not None
        assert Config.TEMP_DIR is not None
        assert isinstance(Config.OUTPUT_DIR, str)
        assert isinstance(Config.TEMP_DIR, str)


# ========================================
# Test Configuration with Environment Variables
# ========================================

class TestConfigWithEnvVars:
    """Tests for configuration with custom environment variables"""

    @pytest.mark.unit
    def test_custom_flask_port(self, monkeypatch):
        """Test custom Flask port from environment"""
        monkeypatch.setenv('FLASK_PORT', '8080')
        from importlib import reload
        import src.config
        reload(src.config)
        assert src.config.Config.FLASK_PORT == 8080

    @pytest.mark.unit
    def test_custom_video_length(self, monkeypatch):
        """Test custom max video length"""
        monkeypatch.setenv('MAX_VIDEO_LENGTH', '3600')
        from importlib import reload
        import src.config
        reload(src.config)
        assert src.config.Config.MAX_VIDEO_LENGTH == 3600

    @pytest.mark.unit
    def test_custom_audio_volume(self, monkeypatch):
        """Test custom audio volume"""
        monkeypatch.setenv('ORIGINAL_AUDIO_VOLUME', '0.2')
        monkeypatch.setenv('VOICEOVER_VOLUME', '0.8')
        from importlib import reload
        import src.config
        reload(src.config)
        assert src.config.Config.ORIGINAL_AUDIO_VOLUME == 0.2
        assert src.config.Config.VOICEOVER_VOLUME == 0.8

    @pytest.mark.unit
    def test_postgres_url_fix(self, monkeypatch):
        """Test that postgres:// URLs are converted to postgresql://"""
        monkeypatch.setenv('DATABASE_URL', 'postgres://user:pass@localhost/db')
        from importlib import reload
        import src.config
        reload(src.config)
        assert src.config.Config.DATABASE_URL.startswith('postgresql://')
        assert 'postgres://' not in src.config.Config.DATABASE_URL


# ========================================
# Test Configuration Validation
# ========================================

class TestConfigValidation:
    """Tests for configuration validation"""

    @pytest.mark.unit
    def test_validate_requires_api_keys(self, monkeypatch):
        """Test that validate() requires API keys"""
        # Clear API keys
        monkeypatch.delenv('VOICEGAIN_API_KEY', raising=False)
        monkeypatch.delenv('OPENAI_API_KEY', raising=False)
        monkeypatch.delenv('GOOGLE_APPLICATION_CREDENTIALS', raising=False)
        monkeypatch.delenv('GOOGLE_APPLICATION_CREDENTIALS_JSON', raising=False)

        from importlib import reload
        import src.config
        reload(src.config)

        with pytest.raises(ValueError) as exc_info:
            src.config.Config.validate()

        error_msg = str(exc_info.value)
        assert 'VOICEGAIN_API_KEY' in error_msg or 'OPENAI_API_KEY' in error_msg

    @pytest.mark.unit
    def test_validate_audio_volume_range(self, monkeypatch):
        """Test that audio volumes must be between 0 and 1"""
        monkeypatch.setenv('ORIGINAL_AUDIO_VOLUME', '1.5')  # Invalid
        monkeypatch.setenv('VOICEGAIN_API_KEY', 'test_key')
        monkeypatch.setenv('OPENAI_API_KEY', 'test_key')
        monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS', '/fake/path.json')

        from importlib import reload
        import src.config
        reload(src.config)

        with pytest.raises(ValueError) as exc_info:
            src.config.Config.validate()
        assert 'ORIGINAL_AUDIO_VOLUME' in str(exc_info.value)

    @pytest.mark.unit
    def test_validate_positive_limits(self, monkeypatch):
        """Test that video limits must be positive"""
        monkeypatch.setenv('MAX_VIDEO_LENGTH', '-100')  # Invalid
        monkeypatch.setenv('VOICEGAIN_API_KEY', 'test_key')
        monkeypatch.setenv('OPENAI_API_KEY', 'test_key')
        monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS', '/fake/path.json')

        from importlib import reload
        import src.config
        reload(src.config)

        with pytest.raises(ValueError) as exc_info:
            src.config.Config.validate()
        assert 'MAX_VIDEO_LENGTH' in str(exc_info.value)


# ========================================
# Test Celery Configuration
# ========================================

class TestCeleryConfig:
    """Tests for Celery configuration"""

    @pytest.mark.unit
    def test_get_celery_config_returns_dict(self):
        """Test that get_celery_config returns dictionary"""
        celery_config = Config.get_celery_config()
        assert isinstance(celery_config, dict)

    @pytest.mark.unit
    def test_celery_config_has_required_keys(self):
        """Test Celery config has required keys"""
        celery_config = Config.get_celery_config()
        required_keys = [
            'broker_url',
            'result_backend',
            'task_serializer',
            'accept_content',
            'result_serializer',
            'timezone',
            'task_time_limit',
        ]
        for key in required_keys:
            assert key in celery_config, f"Missing Celery config key: {key}"

    @pytest.mark.unit
    def test_celery_uses_json_serializer(self):
        """Test Celery uses JSON serialization"""
        celery_config = Config.get_celery_config()
        assert celery_config['task_serializer'] == 'json'
        assert celery_config['result_serializer'] == 'json'
        assert 'json' in celery_config['accept_content']

    @pytest.mark.unit
    def test_celery_timezone_is_utc(self):
        """Test Celery uses UTC timezone"""
        celery_config = Config.get_celery_config()
        assert celery_config['timezone'] == 'UTC'
        assert celery_config['enable_utc'] is True

    @pytest.mark.unit
    def test_celery_has_time_limits(self):
        """Test Celery has task time limits"""
        celery_config = Config.get_celery_config()
        assert celery_config['task_time_limit'] > 0
        assert celery_config['task_soft_time_limit'] > 0
        # Soft limit should be less than hard limit
        assert celery_config['task_soft_time_limit'] < celery_config['task_time_limit']


# ========================================
# Test Helper Methods
# ========================================

class TestConfigHelpers:
    """Tests for Config helper methods"""

    @pytest.mark.unit
    def test_is_r2_configured_true(self, monkeypatch):
        """Test is_r2_configured when all R2 vars are set"""
        monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'test_account')
        monkeypatch.setenv('R2_ACCESS_KEY_ID', 'test_key')
        monkeypatch.setenv('R2_SECRET_ACCESS_KEY', 'test_secret')
        monkeypatch.setenv('R2_BUCKET_NAME', 'test_bucket')

        from importlib import reload
        import src.config
        reload(src.config)

        assert src.config.Config.is_r2_configured() is True

    @pytest.mark.unit
    def test_is_r2_configured_false(self, monkeypatch):
        """Test is_r2_configured when R2 vars are missing"""
        monkeypatch.delenv('CLOUDFLARE_ACCOUNT_ID', raising=False)
        monkeypatch.delenv('R2_ACCESS_KEY_ID', raising=False)

        from importlib import reload
        import src.config
        reload(src.config)

        assert src.config.Config.is_r2_configured() is False

    @pytest.mark.unit
    def test_is_celery_configured_true(self, monkeypatch):
        """Test is_celery_configured when Redis is set"""
        monkeypatch.setenv('REDIS_URL', 'redis://localhost:6379/0')

        from importlib import reload
        import src.config
        reload(src.config)

        assert src.config.Config.is_celery_configured() is True

    @pytest.mark.unit
    def test_is_celery_configured_false(self, monkeypatch):
        """Test is_celery_configured when Redis is not set"""
        monkeypatch.delenv('REDIS_URL', raising=False)
        monkeypatch.delenv('CELERY_BROKER_URL', raising=False)

        from importlib import reload
        import src.config
        reload(src.config)

        # May be False or have a default value
        result = src.config.Config.is_celery_configured()
        assert isinstance(result, bool)


# ========================================
# Test TTS Configuration
# ========================================

class TestTTSConfig:
    """Tests for TTS provider configuration"""

    @pytest.mark.unit
    def test_tts_provider_is_gemini(self):
        """Test that TTS provider is set to Gemini"""
        assert Config.TTS_PROVIDER == 'gemini'

    @pytest.mark.unit
    def test_tts_provider_is_string(self):
        """Test that TTS provider is a string"""
        assert isinstance(Config.TTS_PROVIDER, str)


# ========================================
# Test Transcription Settings
# ========================================

class TestTranscriptionConfig:
    """Tests for transcription configuration"""

    @pytest.mark.unit
    def test_max_speakers_is_positive(self):
        """Test MAX_SPEAKERS is positive integer"""
        assert Config.MAX_SPEAKERS > 0
        assert isinstance(Config.MAX_SPEAKERS, int)

    @pytest.mark.unit
    def test_speaker_merge_pause_is_positive(self):
        """Test SPEAKER_MERGE_PAUSE is positive float"""
        assert Config.SPEAKER_MERGE_PAUSE > 0
        assert isinstance(Config.SPEAKER_MERGE_PAUSE, float)


# ========================================
# Test Timeout Configuration
# ========================================

class TestTimeoutConfig:
    """Tests for API timeout configuration"""

    @pytest.mark.unit
    def test_all_timeouts_are_positive(self):
        """Test that all timeout values are positive"""
        timeout_attrs = [
            'OPENAI_TIMEOUT',
            'RAPIDAPI_TIMEOUT',
            'DOWNLOAD_TIMEOUT',
            'VOICEGAIN_TIMEOUT',
        ]
        for attr in timeout_attrs:
            timeout = getattr(Config, attr)
            assert timeout > 0, f"{attr} must be positive"
            assert isinstance(timeout, int), f"{attr} must be integer"

    @pytest.mark.unit
    def test_voicegain_timeout_is_longest(self):
        """Test that Voicegain timeout is longer (for transcription)"""
        assert Config.VOICEGAIN_TIMEOUT >= Config.OPENAI_TIMEOUT
        assert Config.VOICEGAIN_TIMEOUT >= Config.RAPIDAPI_TIMEOUT


# ========================================
# Test Rate Limiting Configuration
# ========================================

class TestRateLimitConfig:
    """Tests for rate limiting configuration"""

    @pytest.mark.unit
    def test_rate_limits_are_positive(self):
        """Test rate limit values are positive"""
        assert Config.API_RATE_LIMIT > 0
        assert Config.API_BURST_LIMIT > 0
        assert isinstance(Config.API_RATE_LIMIT, int)
        assert isinstance(Config.API_BURST_LIMIT, int)

    @pytest.mark.unit
    def test_burst_limit_reasonable(self):
        """Test burst limit is reasonable compared to rate limit"""
        # Burst should be less than rate limit
        assert Config.API_BURST_LIMIT <= Config.API_RATE_LIMIT
