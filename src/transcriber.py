"""
Speech-to-Text Transcription Module
Uses AssemblyAI (with speaker diarization) or OpenAI Whisper API for transcription
Supports automatic fallback from AssemblyAI to Whisper
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import openai
from src.config import Config
from src.logging_config import get_logger

logger = get_logger(__name__)


class Transcriber:
    def __init__(self):
        """
        Initialize transcriber with configured provider (AssemblyAI or Whisper)
        """
        # Set OpenAI API key for v0.28.1 compatibility
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        openai.api_key = api_key

        # Initialize AssemblyAI if configured
        self.provider = Config.TRANSCRIPTION_PROVIDER
        self.enable_diarization = Config.ENABLE_SPEAKER_DIARIZATION
        self.assemblyai_transcriber = None

        if self.provider == 'assemblyai' and Config.ASSEMBLYAI_API_KEY:
            try:
                from src.assemblyai_transcriber import AssemblyAITranscriber
                self.assemblyai_transcriber = AssemblyAITranscriber()
                logger.info("AssemblyAI transcriber initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize AssemblyAI, will fallback to Whisper: {e}")
                self.provider = 'whisper'

    def transcribe(self, audio_path, progress_callback=None):
        """
        Transcribe audio file with timestamps and optional speaker diarization

        Args:
            audio_path: Path to audio file (WAV format)
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with text, start_time, end_time, and optional speaker info
        """
        # Store speaker information (will be None for Whisper)
        self.speakers = None

        # Try AssemblyAI first if configured and available
        if self.provider == 'assemblyai' and self.assemblyai_transcriber:
            try:
                logger.info("Using AssemblyAI for transcription with speaker diarization")
                segments, speakers = self.assemblyai_transcriber.transcribe_with_speakers(
                    audio_path,
                    progress_callback=progress_callback
                )
                self.speakers = speakers  # Store speaker info for later use
                return segments
            except Exception as e:
                logger.warning(f"AssemblyAI transcription failed, falling back to Whisper: {e}")
                if progress_callback:
                    progress_callback("Falling back to Whisper transcription...")

        # Use Whisper (either as primary or fallback)
        return self._transcribe_with_whisper(audio_path, progress_callback)

    def _transcribe_with_whisper(self, audio_path, progress_callback=None):
        """
        Transcribe using OpenAI Whisper API

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with text, start_time, end_time
        """
        if progress_callback:
            progress_callback("Starting Whisper API transcription...")

        # Retry logic for transient OpenAI errors
        max_retries = 3
        retry_delay = 5  # seconds
        last_error = None

        for attempt in range(max_retries):
            try:
                # OpenAI Whisper API v0.28.1 usage
                with open(audio_path, 'rb') as audio_file:
                    response = openai.Audio.transcribe(
                        model="whisper-1",
                        file=audio_file,
                        language='en',  # Source language
                        response_format='verbose_json',  # Get timestamps
                        timestamp_granularities=['segment']  # Get segment-level timestamps
                    )
                # Success - break out of retry loop
                break
            except openai.error.ServiceUnavailableError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"OpenAI server overloaded, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    if progress_callback:
                        progress_callback(f"Server busy, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"OpenAI transcription failed after {max_retries} attempts")
                    raise
            except openai.error.RateLimitError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"OpenAI rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    if progress_callback:
                        progress_callback(f"Rate limited, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"OpenAI transcription failed after {max_retries} attempts due to rate limiting")
                    raise

        # Extract segments with timestamps from API response
        segments = []
        if hasattr(response, 'segments') and response.segments:
            for segment in response.segments:
                segments.append({
                    'text': segment['text'].strip(),
                    'start': segment['start'],
                    'end': segment['end']
                })
        else:
            # Fallback: if no segments, create one segment with full text
            segments.append({
                'text': response.get('text', '').strip(),
                'start': 0.0,
                'end': 0.0  # Unknown duration
            })

        if progress_callback:
            progress_callback(f"Transcription complete: {len(segments)} segments")

        return segments

    def merge_short_segments(self, segments, min_duration=3.0):
        """
        Merge very short segments together for better voiceover pacing

        Args:
            segments: List of transcription segments
            min_duration: Minimum segment duration in seconds

        Returns:
            List of merged segments
        """
        if not segments:
            return []

        merged = []
        current = segments[0].copy()

        for segment in segments[1:]:
            current_duration = current['end'] - current['start']

            if current_duration < min_duration:
                # Merge with next segment
                current['text'] += ' ' + segment['text']
                current['end'] = segment['end']
            else:
                merged.append(current)
                current = segment.copy()

        # Add last segment
        merged.append(current)

        return merged

    def get_speakers(self) -> Optional[List[Dict]]:
        """
        Get speaker information from the last transcription

        Returns:
            List of speaker profiles if available, None otherwise
        """
        return self.speakers

    def has_speaker_diarization(self) -> bool:
        """
        Check if speaker diarization was used in the last transcription

        Returns:
            True if speaker information is available
        """
        return self.speakers is not None and len(self.speakers) > 0
