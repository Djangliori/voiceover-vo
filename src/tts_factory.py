"""
TTS Factory Module
Creates the Text-to-Speech provider (Gemini only)
"""

import os
from src.logging_config import get_logger

logger = get_logger(__name__)


def get_tts_provider(provider='edge'):
    """
    Get the TTS provider instance

    Args:
        provider: TTS provider to use ('edge', 'gemini', 'gtts')
                 Default: 'edge' (free, unlimited, multi-voice)

    Returns:
        TTS provider instance

    Raises:
        ValueError: If provider cannot be initialized
    """
    # Default to Edge TTS from environment or 'edge' as fallback
    provider = os.getenv('TTS_PROVIDER', provider).lower()

    # Try Edge TTS (FREE, unlimited, multi-voice)
    if provider == 'edge':
        logger.info("Initializing Edge TTS provider (free, unlimited)")
        try:
            from src.tts_edge import EdgeTTSProvider
            tts = EdgeTTSProvider()
            logger.info("Edge TTS provider initialized successfully")
            return tts
        except Exception as e:
            logger.error(f"Failed to initialize Edge TTS: {e}")
            raise ValueError(f"Edge TTS initialization failed: {e}")

    # Gemini TTS (requires Google Cloud credentials, has content filter)
    elif provider == 'gemini':
        logger.info("Initializing Gemini TTS provider")
        try:
            from src.tts_gemini import GeminiTextToSpeech
            tts = GeminiTextToSpeech()
            logger.info("Gemini TTS provider initialized successfully")
            return tts
        except Exception as e:
            logger.error(f"Failed to initialize Gemini TTS: {e}")
            raise ValueError(f"Gemini TTS initialization failed: {e}")

    # gTTS (free, simple, single voice only)
    elif provider == 'gtts':
        logger.info("Initializing gTTS provider")
        try:
            from src.tts_gtts import GTTSProvider
            tts = GTTSProvider()
            logger.info("gTTS provider initialized successfully")
            return tts
        except Exception as e:
            logger.error(f"Failed to initialize gTTS: {e}")
            raise ValueError(f"gTTS initialization failed: {e}")

    else:
        raise ValueError(f"Unknown TTS provider: {provider}")


def get_available_providers():
    """
    Get list of available TTS providers

    Returns:
        dict: Provider names mapped to their availability status
    """
    providers = {}

    # Check Gemini
    try:
        google_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        google_creds_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        has_google = bool(google_creds or google_creds_json)
        providers['gemini'] = {
            'available': has_google,
            'reason': 'Ready' if has_google else 'Google Cloud credentials not configured'
        }
    except Exception as e:
        providers['gemini'] = {'available': False, 'reason': str(e)}

    return providers
