"""
Voicegain Transcriber with Speaker Diarization, Gender, and Age Detection
Uses Voicegain API with proper JWT authentication
"""

import os
import time
import json
import requests
from typing import List, Dict, Optional, Tuple
from src.logging_config import get_logger

logger = get_logger(__name__)


class VoicegainTranscriber:
    """Transcriber using Voicegain API for complete speech analytics"""

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

        logger.info("Voicegain transcriber initialized with JWT authentication")

    def transcribe_with_analytics(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Transcribe audio with speaker diarization, gender, and age detection

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (segments, speakers) where:
                - segments: List of transcript segments with speaker labels
                - speakers: List of speaker profiles with gender and age
        """
        try:
            if progress_callback:
                progress_callback("Uploading audio to Voicegain...")

            # Step 1: Upload audio file using presigned URL method
            audio_url = self._upload_audio_presigned(audio_path)

            if progress_callback:
                progress_callback("Starting transcription with speaker analytics...")

            # Step 2: Start transcription with analytics
            session_id = self._start_transcription(audio_url, audio_path)

            # Step 3: Poll for results
            result = self._poll_for_results(session_id, progress_callback)

            # Step 4: Parse results
            segments, speakers = self._parse_results(result)

            if progress_callback:
                progress_callback(f"Transcription complete: {len(segments)} segments, {len(speakers)} speakers")

            return segments, speakers

        except Exception as e:
            logger.error(f"Voicegain transcription failed: {e}")
            raise

    def _upload_audio_presigned(self, audio_path: str) -> str:
        """Upload audio file using presigned URL method"""
        try:
            file_size = os.path.getsize(audio_path)
            file_name = os.path.basename(audio_path)

            # Request a presigned upload URL
            upload_request = {
                "name": file_name,
                "description": "Georgian voiceover transcription",
                "contentType": "audio/mpeg",
                "sizeBytes": file_size
            }

            response = requests.post(
                f"{self.base_url}/data/file",
                headers=self.headers,
                json=upload_request
            )

            if response.status_code != 200:
                logger.error(f"Failed to get upload URL: {response.status_code} - {response.text}")
                raise Exception(f"Failed to get upload URL: {response.status_code}")

            upload_data = response.json()

            # Use the presigned URL to upload the file
            with open(audio_path, 'rb') as f:
                upload_headers = {
                    "Content-Type": "audio/mpeg"
                }
                upload_response = requests.put(
                    upload_data.get("url", upload_data.get("signedUrl")),
                    data=f,
                    headers=upload_headers
                )

                if upload_response.status_code not in [200, 204]:
                    logger.error(f"Failed to upload file: {upload_response.status_code}")
                    raise Exception(f"Failed to upload file: {upload_response.status_code}")

            # Return the audio URL for transcription
            return upload_data.get("url", upload_data.get("signedUrl"))

        except Exception as e:
            logger.error(f"Failed to upload audio: {e}")
            raise

    def _start_transcription(self, audio_url: str, audio_path: str) -> str:
        """Start transcription with analytics"""
        try:
            # Create transcription request with audio URL
            transcribe_request = {
                "audio": {
                    "source": {
                        "fromUrl": {
                            "url": audio_url
                        }
                    }
                },
                "settings": {
                    "asr": {
                        "languages": ["en-US"],
                        "acousticModel": "VoiceGain-omega",
                        "noInputTimeout": 60000,
                        "completeTimeout": 3600000
                    },
                    "speaker": {
                        "diarization": {
                            "enable": True,
                            "minSpeakers": 1,
                            "maxSpeakers": 10
                        }
                    }
                },
                "output": {
                    "format": "json-mc"
                }
            }

            response = requests.post(
                f"{self.base_url}/asr/transcribe/async",
                headers=self.headers,
                json=transcribe_request
            )

            if response.status_code != 200:
                logger.error(f"Failed to start transcription: {response.status_code} - {response.text}")
                raise Exception(f"Failed to start transcription: {response.status_code}")

            result = response.json()
            session_id = result.get("sessionId")

            if not session_id:
                logger.error(f"No session ID in response: {result}")
                raise Exception("No session ID returned from transcription request")

            logger.info(f"Transcription started: session_id={session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to start transcription: {e}")
            raise

    def _poll_for_results(self, session_id: str, progress_callback: Optional[callable] = None) -> Dict:
        """Poll for transcription results"""
        poll_url = f"{self.base_url}/asr/transcribe/{session_id}"
        max_polls = 300  # 5 minutes max
        poll_interval = 1  # Start with 1 second

        for i in range(max_polls):
            try:
                response = requests.get(poll_url, headers=self.headers)

                if response.status_code == 404:
                    # Session not ready yet
                    time.sleep(poll_interval)
                    continue

                if response.status_code != 200:
                    logger.error(f"Poll error: {response.status_code} - {response.text}")
                    time.sleep(poll_interval)
                    continue

                result = response.json()
                status = result.get("status", result.get("progress", {}).get("status"))

                if status == "COMPLETED" or status == "done":
                    return result
                elif status == "FAILED" or status == "error":
                    raise Exception(f"Transcription failed: {result.get('error', 'Unknown error')}")

                if progress_callback and i % 5 == 0:
                    percent = result.get("progress", {}).get("percent", 0)
                    progress_callback(f"Processing... {percent}%")

                time.sleep(poll_interval)
                # Increase poll interval over time
                if i > 10:
                    poll_interval = 2
                if i > 30:
                    poll_interval = 5

            except requests.exceptions.RequestException as e:
                logger.warning(f"Poll request failed: {e}, retrying...")
                time.sleep(poll_interval)
                continue

        raise Exception("Transcription timed out")

    def _parse_results(self, result: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse Voicegain results into our format with speaker analytics

        Returns:
            Tuple of (segments, speakers)
        """
        segments = []
        speakers = {}

        # Parse alternatives or result structure
        alternatives = result.get("alternatives", [result])
        if alternatives and len(alternatives) > 0:
            alternative = alternatives[0]

            # Get words with speaker labels
            words = alternative.get("words", [])

            # Extract unique speakers
            speaker_ids = set()
            for word in words:
                if "speakerTag" in word:
                    speaker_ids.add(word["speakerTag"])
                elif "speaker" in word:
                    speaker_ids.add(word["speaker"])

            # Create speaker profiles (gender/age detection would be in metadata if available)
            metadata = result.get("metadata", {})
            speaker_info = metadata.get("speakers", [])

            if speaker_info:
                # If we have speaker metadata with gender/age
                for sp_data in speaker_info:
                    sp_id = sp_data.get("speakerTag", sp_data.get("id"))
                    speakers[sp_id] = {
                        'id': sp_id,
                        'label': sp_data.get("label", f"Speaker {sp_id}"),
                        'gender': sp_data.get("gender", "unknown"),
                        'age': sp_data.get("age", "unknown")
                    }
            else:
                # Create default speakers without gender/age
                for sp_id in speaker_ids:
                    speakers[sp_id] = {
                        'id': sp_id,
                        'label': f"Speaker {sp_id}",
                        'gender': 'unknown',
                        'age': 'unknown'
                    }

            # Group words into segments by speaker
            current_segment = None
            for word in words:
                speaker = word.get("speakerTag", word.get("speaker", 0))
                start_time = word.get("start", 0) / 1000.0  # Convert ms to seconds
                end_time = word.get("end", 0) / 1000.0
                text = word.get("word", word.get("text", ""))

                # Start new segment if speaker changes or significant pause
                if (current_segment is None or
                    current_segment['speaker'] != speaker or
                    start_time - current_segment['end'] > 1.5):

                    if current_segment:
                        segments.append(current_segment)

                    current_segment = {
                        'text': text,
                        'start': start_time,
                        'end': end_time,
                        'speaker': speaker
                    }
                else:
                    # Continue current segment
                    current_segment['text'] += ' ' + text
                    current_segment['end'] = end_time

            # Add last segment
            if current_segment:
                segments.append(current_segment)

        # If no segments parsed, try alternative format
        if not segments:
            # Try to get transcript directly
            transcript = result.get("transcript", alternative.get("transcript", ""))
            if transcript:
                # Create a single segment with the full transcript
                segments.append({
                    'text': transcript,
                    'start': 0,
                    'end': result.get("duration", 0) / 1000.0,
                    'speaker': 'speaker_0'
                })
                speakers['speaker_0'] = {
                    'id': 'speaker_0',
                    'label': 'Speaker 1',
                    'gender': 'unknown',
                    'age': 'unknown'
                }

        logger.info(f"Parsed {len(segments)} segments and {len(speakers)} speakers")

        # Ensure we return list of speaker values
        return segments, list(speakers.values())