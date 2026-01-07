"""
Speech Transcription Module - Uses OpenAI Whisper
Provides accurate transcription using OpenAI's Whisper model
"""

from src.whisper_transcriber import WhisperTranscriber
from src.logging_config import get_logger

logger = get_logger(__name__)


class Transcriber:
    """Main transcriber using OpenAI Whisper"""

    def __init__(self):
        """Initialize OpenAI Whisper transcriber"""
        try:
            self.transcriber = WhisperTranscriber()
            self.provider = 'whisper'
            self.speakers = []
            logger.info("Transcriber initialized with OpenAI Whisper")
        except Exception as e:
            logger.error(f"Failed to initialize Whisper transcriber: {e}")
            raise ValueError(f"Whisper initialization failed: {e}")

    def transcribe(self, audio_path, progress_callback=None):
        """
        Transcribe audio using OpenAI Whisper

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with timestamps and text
        """
        # Use Whisper transcription
        segments = self.transcriber.transcribe(
            audio_path,
            progress_callback
        )

        # Get speaker info (Whisper provides default single speaker)
        self.speakers = self.transcriber.get_speakers()

        logger.info(f"Whisper transcription complete: {len(segments)} segments")

        return segments

    def has_speaker_diarization(self):
        """Check if provider supports speaker diarization"""
        return self.transcriber.has_speaker_diarization()

    def get_speakers(self):
        """Get speaker profiles"""
        return self.speakers if hasattr(self, 'speakers') else []

    def merge_short_segments(self, segments):
        """Merge short segments - pass through for now"""
        return segments