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
            audio_format = audio_path.split('.')[-1].upper()

            logger.info("="*60)
            logger.info("VOICEGAIN TRANSCRIPTION START")
            logger.info(f"Audio file: {audio_path}")
            logger.info(f"Format: {audio_format}")
            logger.info(f"Size: {file_size_mb:.2f} MB")
            logger.info("="*60)

            # Use async for all files - it supports MP3/M4A directly
            # No need to convert to WAV!
            if progress_callback:
                progress_callback(f"Processing {audio_format} audio with Voicegain...")

            # Always use async - it handles all formats via ffmpeg
            result = self._async_transcribe(audio_path, progress_callback)

            # Log results
            segments, speakers = result
            logger.info("="*60)
            logger.info("VOICEGAIN TRANSCRIPTION RESULTS")
            logger.info(f"Total segments: {len(segments)}")
            logger.info(f"Total speakers: {len(speakers)}")

            # Log first few segments for debugging
            for i, segment in enumerate(segments[:3]):
                logger.info(f"Segment {i}: [{segment.get('start', 0):.1f}s - {segment.get('end', 0):.1f}s] Speaker: {segment.get('speaker', 'unknown')}")
                logger.info(f"  Text: {segment.get('text', '')[:100]}...")

            if len(segments) > 3:
                logger.info(f"... and {len(segments) - 3} more segments")

            # Log speaker info
            for speaker in speakers:
                logger.info(f"Speaker {speaker.get('id')}: {speaker.get('gender', 'unknown')} / {speaker.get('age', 'unknown')}")

            logger.info("="*60)

            return result

        except Exception as e:
            logger.error(f"Voicegain transcription failed: {e}")
            # Return empty results on failure
            return [], []

    def _convert_to_wav(self, audio_path: str) -> str:
        """
        Convert any audio format to WAV that Voicegain sync API supports
        Uses ffmpeg to convert to 16kHz mono WAV
        Works with MP3, M4A, AAC, and other formats
        """
        try:
            # Create temporary WAV file
            wav_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            wav_path = wav_file.name
            wav_file.close()

            # Convert audio to WAV using ffmpeg
            # 16kHz, mono, 16-bit PCM which Voicegain supports
            cmd = [
                'ffmpeg', '-i', audio_path,
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',       # mono
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-y',             # overwrite output
                wav_path
            ]

            logger.info(f"Converting audio with ffmpeg: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"ffmpeg conversion failed: {result.stderr}")
                raise Exception(f"Audio conversion failed: {result.stderr}")

            # Check output file size to ensure conversion worked
            import os as os_module
            output_size = os_module.path.getsize(wav_path)
            logger.info(f"Converted audio size: {output_size / (1024*1024):.2f} MB")

            return wav_path

        except Exception as e:
            logger.error(f"Error converting audio to WAV: {e}")
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
            logger.info(f"Sending async request to {self.base_url}/asr/transcribe/async")
            logger.info(f"Audio size being sent: {len(audio_base64)} bytes (base64)")

            response = requests.post(
                f"{self.base_url}/asr/transcribe/async",  # Changed to transcribe/async
                headers=self.headers,
                json=request_body
            )

            logger.info(f"Voicegain response status: {response.status_code}")

            if response.status_code not in [200, 201, 202]:
                logger.error(f"Async start failed: {response.status_code}")
                logger.error(f"Response body: {response.text[:500]}")
                return [], []

            result = response.json()
            logger.info(f"Async request accepted: {json.dumps(result, indent=2)[:500]}")

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
                    logger.debug(f"Poll {i}: Not ready yet")
                    continue  # Not ready yet

                if response.status_code != 200:
                    logger.warning(f"Poll {i}: Status {response.status_code}")
                    continue

                result = response.json()

                # Check if done
                if result.get("result", {}).get("final", False):
                    logger.info(f"Transcription complete after {i} polls")
                    logger.info(f"Result structure: {json.dumps(result, indent=2)[:1000]}")
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
                    # Check for words array first (more detailed)
                    words = alternatives[0].get("words", [])
                    if words:
                        # Build segments from words
                        current_segment = None
                        segment_duration = 5.0  # 5 second segments

                        for word in words:
                            word_text = word.get("word", "")
                            word_start = word.get("start", 0) / 1000.0  # Convert ms to seconds
                            word_end = word.get("end", word_start + 0.5) / 1000.0

                            # Start new segment if needed
                            if current_segment is None or word_start - current_segment['start'] > segment_duration:
                                if current_segment:
                                    segments.append(current_segment)
                                current_segment = {
                                    'text': word_text,
                                    'start': word_start,
                                    'end': word_end,
                                    'speaker': 'speaker_0'
                                }
                            else:
                                current_segment['text'] += ' ' + word_text
                                current_segment['end'] = word_end

                        if current_segment:
                            segments.append(current_segment)
                    else:
                        # Fallback: split transcript into chunks
                        transcript = alternatives[0].get("utterance", "")
                        if transcript:
                            # Split into sentences or chunks
                            sentences = transcript.replace('!', '.').replace('?', '.').split('.')
                            time_per_sentence = 3.0  # Estimate 3 seconds per sentence
                            current_time = 0

                            for sentence in sentences:
                                sentence = sentence.strip()
                                if sentence:
                                    segments.append({
                                        'text': sentence,
                                        'start': current_time,
                                        'end': current_time + time_per_sentence,
                                        'speaker': 'speaker_0'
                                    })
                                    current_time += time_per_sentence

                    # Create default speaker
                    if segments:
                        speakers['speaker_0'] = {
                            'id': 'speaker_0',
                            'label': 'Speaker 1',
                            'gender': 'unknown',
                            'age': 'unknown'
                        }

            logger.info(f"Parsed {len(segments)} segments from sync results")

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

