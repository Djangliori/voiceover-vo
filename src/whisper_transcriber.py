"""
OpenAI Whisper Transcriber
Uses OpenAI Whisper API for speech-to-text transcription
"""

import os
import openai
from typing import List, Dict, Optional
from src.logging_config import get_logger

logger = get_logger(__name__)


class WhisperTranscriber:
    """OpenAI Whisper transcriber for accurate speech-to-text"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Whisper transcriber

        Args:
            api_key: OpenAI API key (or from environment)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Set OpenAI API key
        openai.api_key = self.api_key

        logger.info("OpenAI Whisper transcriber initialized")

    def transcribe(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Transcribe audio file using OpenAI Whisper API

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            List of segment dictionaries with start, end, text, speaker
        """
        try:
            if progress_callback:
                progress_callback("Preparing audio for Whisper...")

            # Check file exists
            if not os.path.exists(audio_path):
                raise Exception(f"Audio file not found: {audio_path}")

            file_size = os.path.getsize(audio_path)
            file_size_mb = file_size / (1024 * 1024)

            logger.info("=" * 60)
            logger.info("OPENAI WHISPER TRANSCRIPTION START")
            logger.info(f"Audio file: {audio_path}")
            logger.info(f"Size: {file_size_mb:.2f} MB")
            logger.info("=" * 60)

            if progress_callback:
                progress_callback("Uploading to OpenAI Whisper...")

            # Open audio file and transcribe with timestamps
            with open(audio_path, 'rb') as audio_file:
                logger.info("Calling OpenAI Whisper API...")

                # Using openai 0.28.0 syntax
                transcript = openai.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )

            if progress_callback:
                progress_callback("Processing Whisper results...")

            # Parse response
            segments = self._parse_whisper_response(transcript)

            logger.info("=" * 60)
            logger.info("OPENAI WHISPER TRANSCRIPTION RESULTS")
            logger.info(f"Total segments: {len(segments)}")
            # OpenAI 0.28.0 returns dict
            language = transcript.get('language', 'unknown') if isinstance(transcript, dict) else getattr(transcript, 'language', 'unknown')
            logger.info(f"Language detected: {language}")
            logger.info("=" * 60)

            return segments

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _parse_whisper_response(self, transcript) -> List[Dict]:
        """
        Parse Whisper API response into our segment format

        Args:
            transcript: Whisper API response (dict from openai 0.28.0)

        Returns:
            List of segment dictionaries
        """
        segments = []

        # OpenAI 0.28.0 returns a dict, not an object
        if isinstance(transcript, dict):
            transcript_segments = transcript.get('segments', [])
        else:
            # Fallback for object format
            transcript_segments = getattr(transcript, 'segments', [])

        if not transcript_segments:
            logger.warning("No segments found in Whisper response")
            logger.info(f"Response keys: {transcript.keys() if isinstance(transcript, dict) else 'N/A'}")
            return segments

        logger.info(f"Parsing {len(transcript_segments)} segments from Whisper")

        for idx, seg in enumerate(transcript_segments):
            segment = {
                'start': seg.get('start', 0.0),
                'end': seg.get('end', 0.0),
                'text': seg.get('text', '').strip(),
                'speaker': 0,  # Whisper doesn't provide speaker info, default to speaker 0
                'confidence': 0.95  # Whisper is generally high confidence
            }

            # Skip empty segments
            if not segment['text']:
                continue

            segments.append(segment)
            logger.info(f"Segment {idx}: [{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['text'][:50]}...")

        return segments

    def has_speaker_diarization(self) -> bool:
        """
        Check if multiple speakers were detected
        Note: Whisper doesn't provide speaker diarization
        """
        return False

    def get_speakers(self) -> List[Dict]:
        """
        Get detected speakers
        Note: Whisper doesn't provide speaker info, return default single speaker
        """
        return [
            {
                'id': 0,
                'gender': 'unknown',
                'age': 'unknown'
            }
        ]
