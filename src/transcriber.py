"""
Speech Transcription Module - Uses Voicegain Only
Provides transcription with speaker diarization, gender, and age detection
"""

from src.voicegain_transcriber import VoicegainTranscriber
from src.logging_config import get_logger

logger = get_logger(__name__)


class Transcriber:
    """Main transcriber using Voicegain for everything"""

    def __init__(self):
        """Initialize Voicegain transcriber"""
        try:
            self.transcriber = VoicegainTranscriber()
            self.provider = 'voicegain'
            logger.info("Transcriber initialized with Voicegain (includes gender/age detection)")
        except Exception as e:
            logger.error(f"Failed to initialize Voicegain transcriber: {e}")
            raise ValueError(f"Voicegain initialization failed: {e}")

    def transcribe(self, audio_path, progress_callback=None):
        """
        Transcribe audio using Voicegain

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with speaker, gender, and age information
        """
        # Use Voicegain with full analytics
        segments, self.speakers = self.transcriber.transcribe_with_analytics(
            audio_path,
            progress_callback
        )

        # Log speaker information
        if self.speakers:
            logger.info(f"Detected {len(self.speakers)} speakers:")
            for speaker in self.speakers:
                logger.info(f"  - {speaker['label']}: {speaker['gender']}, {speaker['age']}")

        return segments

    def has_speaker_diarization(self):
        """Check if provider supports speaker diarization"""
        return True  # Voicegain always has diarization

    def get_speakers(self):
        """Get speaker profiles with gender and age"""
        return self.speakers if hasattr(self, 'speakers') else []

    def merge_short_segments(self, segments):
        """Merge short segments (already done by Voicegain transcriber)"""
        return segments  # Voicegain already handles this