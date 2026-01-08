"""
Speech Transcription Module - Uses Local Whisper
Provides accurate transcription using local Whisper (free, no API key needed)
"""

from src.local_whisper_transcriber import LocalWhisperTranscriber
from src.logging_config import get_logger

logger = get_logger(__name__)


class Transcriber:
    """Main transcriber using Local Whisper"""

    def __init__(self):
        """Initialize Local Whisper transcriber"""
        try:
            # Use "base" model for good balance of speed/accuracy
            # Options: "tiny", "base", "small", "medium", "large"
            self.transcriber = LocalWhisperTranscriber(model_size="base")
            self.provider = 'local_whisper'
            self.speakers = []
            logger.info("Transcriber initialized with Local Whisper (base model)")
        except Exception as e:
            logger.error(f"Failed to initialize Local Whisper transcriber: {e}")
            raise ValueError(f"Local Whisper initialization failed: {e}")

    def transcribe(self, audio_path, progress_callback=None):
        """
        Transcribe audio using Local Whisper

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with timestamps and text
        """
        # Use Local Whisper transcription
        segments = self.transcriber.transcribe(
            audio_path,
            progress_callback
        )

        # Get speaker info
        self.speakers = self.transcriber.get_speakers()

        logger.info(f"Local Whisper transcription complete: {len(segments)} segments")

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