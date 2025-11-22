"""
Voicegain Transcriber - Simplified Minimal Version
Start with basic transcription, add features once it works
"""

import os
import time
import json
import base64
import requests
import tempfile
import subprocess
from typing import List, Dict, Optional, Tuple
from src.logging_config import get_logger

logger = get_logger(__name__)


class VoicegainTranscriber:
    """Simplified Voicegain transcriber - start with basics"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Voicegain transcriber with JWT authentication

        Args:
            api_key: Voicegain JWT token (or from environment)
        """
        self.api_key = api_key or os.getenv('VOICEGAIN_API_KEY')
        if not self.api_key:
            raise ValueError("VOICEGAIN_API_KEY not found in environment variables")

        # Use the JWT token directly for authentication
        self.base_url = "https://api.voicegain.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info("Voicegain transcriber initialized (simplified version)")

    def transcribe_with_analytics(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Transcribe audio - simplified version

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (segments, speakers)
        """
        try:
            if progress_callback:
                progress_callback("Preparing audio for Voicegain...")

            # Check file exists and get size
            import os as os_module
            if not os_module.path.exists(audio_path):
                raise Exception(f"Audio file not found: {audio_path}")

            file_size = os_module.path.getsize(audio_path)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"Audio file size: {file_size_mb:.2f} MB")

            # Convert MP3 to WAV for sync transcription
            # YouTube downloads are MP3, but sync API needs WAV
            if audio_path.lower().endswith('.mp3'):
                if progress_callback:
                    progress_callback("Converting MP3 to WAV format...")
                audio_path = self._convert_to_wav(audio_path)
                logger.info("Converted MP3 to WAV for Voicegain")

            # For WAV files under 10MB, use sync transcribe
            if file_size_mb < 10:
                return self._sync_transcribe(audio_path, progress_callback)
            else:
                # For larger files, use async
                return self._async_transcribe(audio_path, progress_callback)

        except Exception as e:
            logger.error(f"Voicegain transcription failed: {e}")
            # Return empty results on failure
            return [], []

    def _convert_to_wav(self, mp3_path: str) -> str:
        """
        Convert MP3 to WAV format that Voicegain sync API supports
        Uses ffmpeg to convert to 16kHz mono WAV
        """
        try:
            # Create temporary WAV file
            wav_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            wav_path = wav_file.name
            wav_file.close()

            # Convert MP3 to WAV using ffmpeg
            # 16kHz, mono, 16-bit PCM which Voicegain supports
            cmd = [
                'ffmpeg', '-i', mp3_path,
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',       # mono
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-y',             # overwrite output
                wav_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"ffmpeg conversion failed: {result.stderr}")
                raise Exception(f"Audio conversion failed: {result.stderr}")

            return wav_path

        except Exception as e:
            logger.error(f"Error converting MP3 to WAV: {e}")
            raise

    def _sync_transcribe(self, audio_path: str, progress_callback: Optional[callable] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Synchronous transcription for smaller files
        """
        try:
            if progress_callback:
                progress_callback("Using synchronous transcription...")

            # Read and encode audio
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # Request with proper format specification for WAV
            # L16 = Linear PCM 16-bit (standard WAV format)
            request_body = {
                "audio": {
                    "source": {
                        "inline": {
                            "data": audio_base64
                        }
                    },
                    "format": "L16",
                    "rate": 16000,
                    "channels": "mono"
                }
            }

            # Send synchronous request
            response = requests.post(
                f"{self.base_url}/asr/transcribe",  # Sync endpoint
                headers=self.headers,
                json=request_body
            )

            if response.status_code != 200:
                logger.error(f"Sync transcription failed: {response.status_code} - {response.text}")
                return [], []

            result = response.json()
            return self._parse_sync_results(result)

        except Exception as e:
            logger.error(f"Sync transcription error: {e}")
            return [], []

    def _async_transcribe(self, audio_path: str, progress_callback: Optional[callable] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Async transcription for larger files - uses /asr/transcribe/async
        Supports MP3 and other formats via ffmpeg
        """
        try:
            if progress_callback:
                progress_callback("Using async transcription...")

            # Read and encode audio
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # Async request structure according to OpenAPI spec
            # OFF-LINE mode for batch transcription
            request_body = {
                "sessions": [{
                    "asyncMode": "OFF-LINE",
                    "poll": {
                        "persist": 600000  # 10 minutes
                    }
                }],
                "audio": {
                    "source": {
                        "inline": {
                            "data": audio_base64
                        }
                    }
                    # No format specification needed for async - it uses ffmpeg
                }
            }

            # Send async request to correct endpoint
            response = requests.post(
                f"{self.base_url}/asr/transcribe/async",  # Changed to transcribe/async
                headers=self.headers,
                json=request_body
            )

            if response.status_code not in [200, 201, 202]:
                logger.error(f"Async start failed: {response.status_code} - {response.text}")
                return [], []

            result = response.json()

            # Get session ID
            if "sessions" in result and len(result["sessions"]) > 0:
                session_id = result["sessions"][0].get("sessionId")
            else:
                session_id = result.get("sessionId")

            if not session_id:
                logger.error(f"No session ID in response: {result}")
                return [], []

            logger.info(f"Started async transcription: {session_id}")

            # Poll for results
            return self._poll_and_parse(session_id, progress_callback)

        except Exception as e:
            logger.error(f"Async transcription error: {e}")
            return [], []


    def _poll_and_parse(self, session_id: str, progress_callback: Optional[callable] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Poll for async results and parse them
        """
        poll_url = f"{self.base_url}/asr/transcribe/{session_id}"
        max_attempts = 120

        for i in range(max_attempts):
            try:
                time.sleep(2 if i > 0 else 0)  # Wait before polling

                response = requests.get(poll_url, headers=self.headers)

                if response.status_code == 404:
                    continue  # Not ready yet

                if response.status_code != 200:
                    logger.warning(f"Poll status {response.status_code}")
                    continue

                result = response.json()

                # Check if done
                if result.get("result", {}).get("final", False):
                    return self._parse_async_results(result)

                if progress_callback and i % 5 == 0:
                    progress_callback(f"Processing... ({i}/{max_attempts})")

            except Exception as e:
                logger.warning(f"Poll error: {e}")
                continue

        logger.error("Transcription timed out")
        return [], []

    def _parse_sync_results(self, result: Dict) -> Tuple[List[Dict], List[Dict]]:
        """Parse synchronous transcription results"""
        segments = []
        speakers = {}

        try:
            # Get the transcript
            if "result" in result:
                alternatives = result["result"].get("alternatives", [])
                if alternatives:
                    transcript = alternatives[0].get("utterance", "")
                    if transcript:
                        segments.append({
                            'text': transcript,
                            'start': 0,
                            'end': 10,
                            'speaker': 'speaker_0'
                        })
                        speakers['speaker_0'] = {
                            'id': 'speaker_0',
                            'label': 'Speaker 1',
                            'gender': 'unknown',
                            'age': 'unknown'
                        }
        except Exception as e:
            logger.error(f"Error parsing sync results: {e}")

        return segments, list(speakers.values())

    def _parse_async_results(self, result: Dict) -> Tuple[List[Dict], List[Dict]]:
        """Parse async transcription results"""
        segments = []
        speakers = {}

        try:
            # Try to get alternatives
            if "result" in result:
                alternatives = result["result"].get("alternatives", [])
                if alternatives:
                    # Get words if available
                    words = alternatives[0].get("words", [])
                    if words:
                        # Group words into segments
                        current_segment = None
                        for word in words:
                            text = word.get("word", "")
                            start = word.get("start", 0) / 1000.0
                            end = word.get("end", start + 0.5) / 1000.0

                            if current_segment is None or start - current_segment['end'] > 1.0:
                                if current_segment:
                                    segments.append(current_segment)
                                current_segment = {
                                    'text': text,
                                    'start': start,
                                    'end': end,
                                    'speaker': 'speaker_0'
                                }
                            else:
                                current_segment['text'] += ' ' + text
                                current_segment['end'] = end

                        if current_segment:
                            segments.append(current_segment)
                    else:
                        # Just get the full transcript
                        utterance = alternatives[0].get("utterance", "")
                        if utterance:
                            segments.append({
                                'text': utterance,
                                'start': 0,
                                'end': 10,
                                'speaker': 'speaker_0'
                            })

            # Create a default speaker
            if segments:
                speakers['speaker_0'] = {
                    'id': 'speaker_0',
                    'label': 'Speaker 1',
                    'gender': 'unknown',
                    'age': 'unknown'
                }

        except Exception as e:
            logger.error(f"Error parsing async results: {e}")

        logger.info(f"Parsed {len(segments)} segments")
        return segments, list(speakers.values())

