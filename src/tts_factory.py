"""
TTS Factory Module
Creates the appropriate Text-to-Speech provider based on configuration
Supports: ElevenLabs, Google Gemini TTS
Includes automatic fallback if primary provider fails
"""

import os
from src.logging_config import get_logger

logger = get_logger(__name__)


def get_tts_provider():
    """
    Get the configured TTS provider instance with automatic fallback

    Environment variables:
        TTS_PROVIDER: 'elevenlabs' or 'gemini' (default: 'elevenlabs')

    Returns:
        TTSWithFallback wrapper that handles automatic fallback

    Raises:
        ValueError: If no provider can be initialized
    """
    primary = os.getenv('TTS_PROVIDER', 'elevenlabs').lower()

    logger.info(f"Initializing TTS with primary provider: {primary}")

    # Return wrapper with fallback support
    return TTSWithFallback(primary)


class TTSWithFallback:
    """TTS wrapper that automatically falls back to alternate provider on failure"""

    def __init__(self, primary_provider):
        self.primary_provider = primary_provider
        self.fallback_provider = 'elevenlabs' if primary_provider == 'gemini' else 'gemini'

        # Try to initialize both providers
        self._primary = None
        self._fallback = None
        self._primary_error = None
        self._fallback_error = None

        # Initialize primary
        try:
            self._primary = self._init_provider(self.primary_provider)
            logger.info(f"Primary TTS provider ({self.primary_provider}) initialized successfully")
        except Exception as e:
            self._primary_error = str(e)
            logger.warning(f"Primary TTS provider ({self.primary_provider}) failed to initialize: {e}")

        # Initialize fallback
        try:
            self._fallback = self._init_provider(self.fallback_provider)
            logger.info(f"Fallback TTS provider ({self.fallback_provider}) initialized successfully")
        except Exception as e:
            self._fallback_error = str(e)
            logger.warning(f"Fallback TTS provider ({self.fallback_provider}) failed to initialize: {e}")

        # Ensure at least one provider is available
        if self._primary is None and self._fallback is None:
            raise ValueError(
                f"No TTS provider available. "
                f"Primary ({self.primary_provider}): {self._primary_error}. "
                f"Fallback ({self.fallback_provider}): {self._fallback_error}"
            )

    def _init_provider(self, provider_name):
        """Initialize a specific provider"""
        if provider_name == 'gemini':
            from src.tts_gemini import GeminiTextToSpeech
            return GeminiTextToSpeech()
        elif provider_name == 'elevenlabs':
            from src.tts import TextToSpeech
            return TextToSpeech()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def generate_voiceover(self, segments, temp_dir="temp", progress_callback=None):
        """
        Generate voiceover with automatic fallback

        First tries primary provider, falls back to secondary on failure
        """
        # Try primary provider first
        if self._primary is not None:
            try:
                logger.info(f"Generating voiceover with primary provider: {self.primary_provider}")
                if progress_callback:
                    progress_callback(f"Using {self.primary_provider.title()} TTS...")
                return self._primary.generate_voiceover(segments, temp_dir, progress_callback)
            except Exception as e:
                logger.error(f"Primary provider ({self.primary_provider}) failed: {e}")
                if self._fallback is None:
                    raise  # No fallback available, re-raise

                logger.info(f"Falling back to {self.fallback_provider}")
                if progress_callback:
                    progress_callback(f"Switching to {self.fallback_provider.title()} TTS (fallback)...")

        # Try fallback provider
        if self._fallback is not None:
            try:
                logger.info(f"Generating voiceover with fallback provider: {self.fallback_provider}")
                return self._fallback.generate_voiceover(segments, temp_dir, progress_callback)
            except Exception as e:
                logger.error(f"Fallback provider ({self.fallback_provider}) also failed: {e}")
                raise ValueError(
                    f"All TTS providers failed. "
                    f"Primary ({self.primary_provider}): failed during generation. "
                    f"Fallback ({self.fallback_provider}): {e}"
                )

        raise ValueError("No TTS provider available")

    def set_voice(self, voice_id):
        """Set voice on both providers if available"""
        if self._primary and hasattr(self._primary, 'set_voice'):
            self._primary.set_voice(voice_id)
        if self._fallback and hasattr(self._fallback, 'set_voice'):
            self._fallback.set_voice(voice_id)


def get_available_providers():
    """
    Get list of available TTS providers

    Returns:
        dict: Provider names mapped to their availability status
    """
    providers = {}

    # Check ElevenLabs
    try:
        elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
        providers['elevenlabs'] = {
            'available': bool(elevenlabs_key),
            'reason': 'Ready' if elevenlabs_key else 'ELEVENLABS_API_KEY not set'
        }
    except Exception as e:
        providers['elevenlabs'] = {'available': False, 'reason': str(e)}

    # Check Gemini
    try:
        google_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        google_project = os.getenv('GOOGLE_CLOUD_PROJECT')
        has_google = bool(google_creds or google_project)
        providers['gemini'] = {
            'available': has_google,
            'reason': 'Ready' if has_google else 'Google Cloud credentials not configured'
        }
    except Exception as e:
        providers['gemini'] = {'available': False, 'reason': str(e)}

    return providers
