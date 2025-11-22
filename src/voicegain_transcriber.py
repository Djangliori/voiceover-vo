"""
Voicegain Transcriber - Simplified Minimal Version
Start with basic transcription, add features once it works
"""

import os
import time
import json
import base64
import requests
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

            # Try the simplest endpoint first (/asr/recognize)
            result = self._simple_recognize(audio_path, progress_callback)
            if result[0]:  # If we got segments
                return result

            # If that fails, try sync transcribe
            if file_size_mb < 10:  # If less than 10MB, use sync
                return self._sync_transcribe(audio_path, progress_callback)
            else:
                return self._async_transcribe(audio_path, progress_callback)

        except Exception as e:
            logger.error(f"Voicegain transcription failed: {e}")
            # Return empty results on failure
            return [], []

    def _simple_recognize(self, audio_path: str, progress_callback: Optional[callable] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Simplest possible recognition - just audio, no settings
        """
        try:
            if progress_callback:
                progress_callback("Using simple recognition...")

            # Read and encode audio
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # ABSOLUTELY MINIMAL request - just audio
            request_body = {
                "audio": {
                    "source": {
                        "inline": {
                            "data": audio_base64
                        }
                    }
                }
            }

            # Send to simplest endpoint
            response = requests.post(
                f"{self.base_url}/asr/recognize",
                headers=self.headers,
                json=request_body
            )

            if response.status_code != 200:
                logger.warning(f"Simple recognize returned {response.status_code}")
                return [], []

            result = response.json()
            return self._parse_recognize_results(result)

        except Exception as e:
            logger.warning(f"Simple recognize error: {e}")
            return [], []

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

            # ABSOLUTELY MINIMAL request - just audio, no settings at all
            request_body = {
                "audio": {
                    "source": {
                        "inline": {
                            "data": audio_base64
                        }
                    }
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
        Async transcription for larger files - MINIMAL version
        """
        try:
            if progress_callback:
                progress_callback("Using async transcription...")

            # Read and encode audio
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # ULTRA MINIMAL async request - just audio, no sessions config
            request_body = {
                "audio": {
                    "source": {
                        "inline": {
                            "data": audio_base64
                        }
                    }
                }
            }

            # Send async request
            response = requests.post(
                f"{self.base_url}/asr/recognize/async",
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
        poll_url = f"{self.base_url}/asr/recognize/async/{session_id}"
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

    def _parse_recognize_results(self, result: Dict) -> Tuple[List[Dict], List[Dict]]:
        """Parse recognize endpoint results"""
        segments = []
        speakers = {}

        try:
            # Get alternatives
            alternatives = result.get("alternatives", [])
            if alternatives:
                transcript = alternatives[0].get("transcript", "")
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
            logger.error(f"Error parsing recognize results: {e}")

        return segments, list(speakers.values())