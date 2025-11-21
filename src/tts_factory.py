"""
TTS Factory Module
Creates the appropriate Text-to-Speech provider based on configuration
Supports: ElevenLabs, Google Gemini TTS
"""

import os
from src.logging_config import get_logger

logger = get_logger(__name__)


def get_tts_provider():
    """
    Get the configured TTS provider instance

    Environment variables:
        TTS_PROVIDER: 'elevenlabs' or 'gemini' (default: 'elevenlabs')

    Returns:
        TextToSpeech instance (either ElevenLabs or Gemini)

    Raises:
        ValueError: If provider is not configured correctly
    """
    provider = os.getenv('TTS_PROVIDER', 'elevenlabs').lower()

    logger.info(f"Initializing TTS provider: {provider}")

    if provider == 'gemini':
        return _get_gemini_provider()
    elif provider == 'elevenlabs':
        return _get_elevenlabs_provider()
    else:
        logger.warning(f"Unknown TTS provider '{provider}', falling back to ElevenLabs")
        return _get_elevenlabs_provider()


def _get_elevenlabs_provider():
    """Initialize ElevenLabs TTS provider"""
    try:
        from src.tts import TextToSpeech
        provider = TextToSpeech()
        logger.info("ElevenLabs TTS provider initialized successfully")
        return provider
    except Exception as e:
        logger.error(f"Failed to initialize ElevenLabs TTS: {e}")
        raise ValueError(f"ElevenLabs TTS initialization failed: {e}")


def _get_gemini_provider():
    """Initialize Google Gemini TTS provider"""
    try:
        from src.tts_gemini import GeminiTextToSpeech
        provider = GeminiTextToSpeech()
        logger.info("Gemini TTS provider initialized successfully")
        return provider
    except ImportError as e:
        logger.error(f"Gemini TTS import failed. Install google-cloud-texttospeech>=2.29.0: {e}")
        raise ValueError(
            "Gemini TTS requires google-cloud-texttospeech>=2.29.0. "
            "Install with: pip install google-cloud-texttospeech>=2.29.0"
        )
    except Exception as e:
        logger.error(f"Failed to initialize Gemini TTS: {e}")
        raise ValueError(f"Gemini TTS initialization failed: {e}")


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
