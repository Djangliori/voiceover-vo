"""
Local Whisper Transcriber
Uses local Whisper model (no API key needed, completely free)
"""

import os
import whisper
from typing import List, Dict, Optional
from src.logging_config import get_logger

logger = get_logger(__name__)


class LocalWhisperTranscriber:
    """Local Whisper transcriber - completely free, no API needed"""

    def __init__(self, model_size: str = "base"):
        """
        Initialize local Whisper transcriber

        Args:
            model_size: Model size - "tiny", "base", "small", "medium", "large"
                       (base is good balance of speed/accuracy)
        """
        self.model_size = model_size

        logger.info(f"Loading Whisper {model_size} model (this may take a moment)...")
        try:
            self.model = whisper.load_model(model_size)
            logger.info(f"Local Whisper {model_size} model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise ValueError(f"Whisper model loading failed: {e}")

    def transcribe(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Transcribe audio file using local Whisper model

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            List of segment dictionaries with start, end, text, speaker
        """
        try:
            if progress_callback:
                progress_callback("Preparing audio for local Whisper...")

            # Check file exists
            if not os.path.exists(audio_path):
                raise Exception(f"Audio file not found: {audio_path}")

            file_size = os.path.getsize(audio_path)
            file_size_mb = file_size / (1024 * 1024)

            logger.info("=" * 60)
            logger.info("LOCAL WHISPER TRANSCRIPTION START")
            logger.info(f"Audio file: {audio_path}")
            logger.info(f"Size: {file_size_mb:.2f} MB")
            logger.info(f"Model: {self.model_size}")
            logger.info("=" * 60)

            if progress_callback:
                progress_callback(f"Transcribing with local Whisper {self.model_size} model...")

            # Transcribe with local Whisper
            logger.info("Starting local Whisper transcription...")
            result = self.model.transcribe(
                audio_path,
                language="en",  # Auto-detect, but hint English
                task="transcribe",
                verbose=False
            )

            if progress_callback:
                progress_callback("Processing Whisper results...")

            # Convert to our format
            segments = []
            for segment in result.get("segments", []):
                segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "speaker": "Speaker 1"  # Local Whisper doesn't do speaker diarization
                })

            logger.info(f"Local Whisper transcription complete: {len(segments)} segments")
            logger.info("=" * 60)

            return segments

        except Exception as e:
            logger.error(f"Local Whisper transcription failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def has_speaker_diarization(self):
        """Check if provider supports speaker diarization"""
        return False  # Local Whisper doesn't support speaker diarization

    def get_speakers(self):
        """Get speaker profiles"""
        return [{"id": "Speaker 1", "label": "Speaker 1"}]
