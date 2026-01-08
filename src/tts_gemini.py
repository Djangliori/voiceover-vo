"""
Text-to-Speech Module using Google Gemini TTS
Generates Georgian voiceover using Google Cloud Text-to-Speech API with Gemini models
Supports parallel requests for faster processing
"""

import os
import json
import subprocess
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Google Cloud TTS imports
from google.cloud import texttospeech
from google.oauth2 import service_account

from src.logging_config import get_logger
from src.ffmpeg_utils import get_ffprobe_path

logger = get_logger(__name__)


class GeminiTextToSpeech:
    """Text-to-Speech using Google Gemini TTS API"""

    def __init__(self):
        """Initialize Google Cloud Text-to-Speech client with Gemini model"""
        # Try to get credentials from various sources
        credentials = self._get_credentials()

        if credentials:
            self.client = texttospeech.TextToSpeechClient(credentials=credentials)
        else:
            # Fall back to default credentials (ADC)
            self.client = texttospeech.TextToSpeechClient()

        # Gemini TTS configuration for Georgian
        self.language_code = "ka-GE"  # Georgian (Georgia)
        self.model_name = os.getenv('GEMINI_TTS_MODEL', 'gemini-2.5-pro-tts')

        # Voice selection - Charon is a good default male voice for Georgian
        # (Most YouTube content has male speakers, so male default is safer)
        self.voice_name = os.getenv('GEMINI_TTS_VOICE', 'Charon')

        # Default prompt for consistent tone
        self.default_prompt = os.getenv(
            'GEMINI_TTS_PROMPT',
            'Read aloud in a clear, natural voice with good pacing.'
        )

        # Parallel processing settings
        self.max_workers = int(os.getenv('GEMINI_TTS_MAX_CONCURRENT', '5'))

    def _get_credentials(self):
        """Get Google Cloud credentials from environment"""
        logger.info("=== Google Credentials Debug ===")

        # Option 1: JSON credentials stored directly in env var
        creds_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        logger.info(f"GOOGLE_APPLICATION_CREDENTIALS_JSON: {'SET' if creds_json else 'NOT SET'}")
        if creds_json:
            try:
                creds_dict = json.loads(creds_json)
                logger.info("Using credentials from JSON environment variable")
                return service_account.Credentials.from_service_account_info(creds_dict)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")

        # Option 2: Path to credentials file
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        logger.info(f"GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")

        # Try to find the file in multiple locations
        possible_paths = []
        if creds_path:
            possible_paths.append(creds_path)

        # Always check for file in project root
        project_root = Path(__file__).parent.parent
        possible_paths.append(str(project_root / 'google-credentials.json'))

        for path in possible_paths:
            logger.info(f"Checking path: {path}")
            if path and os.path.exists(path):
                logger.info(f"Found credentials file: {path}")
                # Also set the environment variable for subprocess calls
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = path
                return service_account.Credentials.from_service_account_file(path)
            else:
                logger.warning(f"Credentials file not found: {path}")

        # Option 3: Return None to use Application Default Credentials
        logger.warning("No credentials found, falling back to Application Default Credentials")
        return None

    def generate_voiceover(self, segments, temp_dir="temp", progress_callback=None):
        """
        Generate Georgian voiceover for all segments using parallel requests

        Args:
            segments: List of segments with 'translated_text', 'start', 'end'
            temp_dir: Directory for temporary audio files
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with 'audio_path' added
        """
        temp_path = Path(temp_dir)
        temp_path.mkdir(exist_ok=True)

        # Filter out segments with empty text
        valid_segments = []
        skipped_indices = []
        for i, seg in enumerate(segments):
            text = seg.get('translated_text', '').strip()
            if text:
                valid_segments.append((i, seg))
            else:
                skipped_indices.append(i)
                logger.warning(f"Skipping segment {i} - empty translated text")

        if skipped_indices:
            logger.info(f"Skipped {len(skipped_indices)} segments with empty text: {skipped_indices}")

        if progress_callback:
            progress_callback(f"Generating Georgian voiceover with Gemini TTS ({len(valid_segments)} segments)...")

        if not valid_segments:
            logger.warning("No valid segments to process")
            return []

        # Process segments in parallel
        results = {}
        completed_count = 0
        total_segments = len(valid_segments)

        def process_segment(args):
            """Process a single segment - runs in thread pool"""
            idx, segment = args
            return idx, self._process_single_segment(segment, idx, temp_path)

        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks for valid segments only
            futures = {
                executor.submit(process_segment, (idx, seg)): idx
                for idx, seg in valid_segments
            }

            # Process completed tasks as they finish
            for future in as_completed(futures):
                try:
                    idx, result = future.result()
                    results[idx] = result
                    completed_count += 1

                    if progress_callback:
                        progress_callback(f"Generated {completed_count}/{total_segments} voiceover segments")
                except Exception as e:
                    # Log error but continue with other segments
                    idx = futures[future]
                    raise Exception(f"Failed to generate segment {idx}: {str(e)}")

        # Return only the results we have (valid segments), sorted by original index
        voiceover_segments = [results[idx] for idx, _ in valid_segments if idx in results]

        if progress_callback:
            progress_callback(f"Voiceover generation complete: {len(voiceover_segments)} segments")

        return voiceover_segments

    def _process_single_segment(self, segment, index, temp_path):
        """
        Process a single segment: synthesize speech with Gemini TTS

        Args:
            segment: Segment dict with 'translated_text', 'start', 'end'
            index: Segment index for filename
            temp_path: Path object for temp directory

        Returns:
            Updated segment dict with 'audio_path' and 'audio_duration'
        """
        text = segment['translated_text']
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # Synthesize speech using Gemini TTS
                audio_content = self._synthesize_speech(text)
                break  # Success
            except Exception as e:
                error_str = str(e).lower()
                last_error = e

                # Check if this is a content blocked error - don't retry, use silence
                if 'sensitive' in error_str or 'harmful' in error_str or 'content' in error_str:
                    logger.warning(f"Segment {index} blocked by content filter, generating silence: {text[:50]}...")
                    duration = segment.get('end', 0) - segment.get('start', 0)
                    if duration <= 0:
                        duration = 2.0
                    audio_content = self._generate_silence(duration)
                    break

                # Check if this is a transient error (500, 499, cancelled, timeout) - retry
                if ('500' in error_str or '499' in error_str or
                    'unable to generate' in error_str or 'try again' in error_str or
                    'cancelled' in error_str or 'timeout' in error_str):
                    if attempt < max_retries - 1:
                        import time
                        wait_time = (attempt + 1) * 2  # 2, 4, 6 seconds
                        logger.warning(f"Segment {index} got transient error ({str(e)[:100]}), retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        # All retries failed, generate silence instead of failing
                        logger.warning(f"Segment {index} failed after {max_retries} retries, generating silence: {text[:50]}...")
                        duration = segment.get('end', 0) - segment.get('start', 0)
                        if duration <= 0:
                            duration = 2.0
                        audio_content = self._generate_silence(duration)
                        break

                # Other errors - re-raise
                raise

        # Save to WAV file (Gemini outputs LINEAR16 which is WAV-compatible)
        wav_filename = f"segment_{index:04d}.wav"
        wav_path = temp_path / wav_filename

        with open(wav_path, 'wb') as f:
            f.write(audio_content)

        # Get audio duration using ffprobe
        duration = self._get_audio_duration(wav_path)

        # Create result segment
        voiceover_segment = segment.copy()
        voiceover_segment['audio_path'] = str(wav_path)
        voiceover_segment['audio_duration'] = duration

        return voiceover_segment

    def _generate_silence(self, duration_seconds):
        """
        Generate silent WAV audio for the specified duration

        Args:
            duration_seconds: Duration in seconds

        Returns:
            bytes: WAV audio content
        """
        import struct

        sample_rate = 44100
        num_samples = int(sample_rate * duration_seconds)

        # WAV header for 16-bit mono PCM
        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + num_samples * 2,  # File size - 8
            b'WAVE',
            b'fmt ',
            16,  # Subchunk1 size
            1,   # Audio format (PCM)
            1,   # Num channels (mono)
            sample_rate,
            sample_rate * 2,  # Byte rate
            2,   # Block align
            16,  # Bits per sample
            b'data',
            num_samples * 2  # Data size
        )

        # Generate silence (all zeros)
        silence_data = b'\x00' * (num_samples * 2)

        return wav_header + silence_data

    def _synthesize_speech(self, text, prompt=None):
        """
        Synthesize speech for a text segment using Gemini TTS

        Args:
            text: Text to synthesize (in Georgian)
            prompt: Optional style prompt (uses default if not provided)

        Returns:
            Audio content bytes (LINEAR16/WAV format)
        """
        try:
            # Build synthesis input with optional prompt
            synthesis_input = texttospeech.SynthesisInput(
                text=text,
                prompt=prompt or self.default_prompt
            )

            # Configure voice parameters for Gemini TTS
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                name=self.voice_name,
                model_name=self.model_name
            )

            # Audio config - LINEAR16 for WAV output at 44.1kHz
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=44100,
                speaking_rate=1.0,
                pitch=0.0
            )

            # Make the API request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            return response.audio_content

        except Exception as e:
            raise Exception(f"Gemini TTS error: {str(e)}")

    def _get_audio_duration(self, audio_path):
        """Get audio duration using ffprobe"""
        ffprobe_path = self._get_ffprobe_path()

        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        return 0.0

    def _get_ffprobe_path(self):
        """Get ffprobe path"""
        return get_ffprobe_path()

    def set_voice(self, voice_name):
        """
        Change the voice dynamically for multi-speaker support

        Args:
            voice_name: Gemini voice name (e.g., 'Achernar', 'Charon', 'Kore')
        """
        from src.voice_profiles import GEMINI_VOICES, GEMINI_ALL_VOICES

        # Validate voice name exists
        valid_voice = False

        # Check if it's in our curated list
        for voice in GEMINI_VOICES.values():
            if voice.id == voice_name:
                valid_voice = True
                break

        # Also check against complete list
        if not valid_voice:
            all_voices = GEMINI_ALL_VOICES.get('male', []) + GEMINI_ALL_VOICES.get('female', [])
            if voice_name in all_voices:
                valid_voice = True

        if valid_voice:
            self.voice_name = voice_name
            logger.info(f"Gemini TTS voice switched to: {voice_name}")
        else:
            logger.warning(f"Unknown Gemini voice name: {voice_name}, using current: {self.voice_name}")
            # Keep current voice_name unchanged

    def set_prompt(self, prompt):
        """
        Change the default style prompt

        Args:
            prompt: Natural language prompt for voice style
        """
        self.default_prompt = prompt
