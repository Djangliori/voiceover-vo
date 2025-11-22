"""
Voicegain Transcriber with Speaker Diarization
Uses Voicegain API with JWT authentication and base64 audio encoding
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
    """Transcriber using Voicegain API for speech analytics with speaker diarization"""

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
        Transcribe audio with speaker diarization

        Args:
            audio_path: Path to audio file
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (segments, speakers) where:
                - segments: List of transcript segments with speaker labels
                - speakers: List of speaker profiles
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
            logger.info(f"Audio file size: {file_size_mb:.2f} MB ({file_size} bytes)")

            # Read and encode audio file to base64
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            base64_size_mb = len(audio_base64) / (1024 * 1024)
            logger.info(f"Base64 encoded size: {base64_size_mb:.2f} MB")

            if progress_callback:
                progress_callback("Starting transcription with speaker diarization...")

            # Start async transcription with speaker diarization
            session_id = self._start_async_transcription(audio_base64, progress_callback)

            # Poll for results
            result = self._poll_for_results(session_id, progress_callback)

            # Parse results
            segments, speakers = self._parse_results(result)

            if progress_callback:
                progress_callback(f"Transcription complete: {len(segments)} segments, {len(speakers)} speakers")

            return segments, speakers

        except Exception as e:
            logger.error(f"Voicegain transcription failed: {e}")
            # Return empty results on failure
            return [], []

    def _start_async_transcription(self, audio_base64: str, progress_callback: Optional[callable] = None) -> str:
        """Start async transcription with speaker diarization"""
        try:
            # Create transcription request with inline base64 audio
            transcribe_request = {
                "sessions": [{
                    "asyncMode": "OFF-LINE",
                    "audioChannelSelector": "mix",
                    "vadMode": "strict",
                    "content": {
                        "incremental": ["words"],
                        "full": ["words", "transcript"]
                    }
                }],
                "audio": {
                    "source": {
                        "inline": {
                            "data": audio_base64
                        }
                    }
                },
                "settings": {
                    "asr": {
                        "acousticModel": "VoiceGain-omega-x",
                        "languages": ["en-US"],
                        "sensitivity": 0.5,
                        "speedVsAccuracy": 0.5
                    },
                    "formatters": [{
                        "type": "basic",
                        "parameters": {
                            "enabled": True
                        }
                    }],
                    "diarization": {
                        "enable": True,
                        "speakerCount": None  # Auto-detect number of speakers
                    }
                }
            }

            # Send request
            response = requests.post(
                f"{self.base_url}/asr/recognize/async",
                headers=self.headers,
                json=transcribe_request
            )

            if response.status_code not in [200, 201, 202]:
                error_msg = f"Failed to start transcription: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

            result = response.json()

            # Get session ID from response
            if "sessions" in result and len(result["sessions"]) > 0:
                session_id = result["sessions"][0].get("sessionId")
            else:
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
        poll_url = f"{self.base_url}/asr/session/{session_id}"
        max_polls = 600  # 10 minutes max
        poll_interval = 1  # Start with 1 second

        for i in range(max_polls):
            try:
                response = requests.get(poll_url, headers=self.headers)

                if response.status_code == 404:
                    # Session not ready yet
                    time.sleep(poll_interval)
                    continue

                if response.status_code != 200:
                    logger.warning(f"Poll error: {response.status_code}")
                    time.sleep(poll_interval)
                    continue

                result = response.json()

                # Check if transcription is complete
                if "audio" in result and "status" in result["audio"]:
                    status = result["audio"]["status"]

                    if status == "DONE":
                        # Get the final transcript
                        return self._get_final_transcript(session_id)
                    elif status == "ERROR":
                        raise Exception(f"Transcription failed: {result.get('audio', {}).get('errorMessage', 'Unknown error')}")

                # Also check session status
                if "status" in result:
                    if result["status"] == "DONE":
                        return self._get_final_transcript(session_id)
                    elif result["status"] == "ERROR":
                        raise Exception(f"Transcription failed")

                if progress_callback and i % 10 == 0:
                    progress = result.get("progress", {})
                    if progress:
                        percent = progress.get("audioPercentDone", 0)
                        progress_callback(f"Processing... {percent}%")
                    else:
                        progress_callback(f"Processing...")

                time.sleep(poll_interval)
                # Increase poll interval over time
                if i > 30:
                    poll_interval = 2
                if i > 60:
                    poll_interval = 3

            except requests.exceptions.RequestException as e:
                logger.warning(f"Poll request failed: {e}, retrying...")
                time.sleep(poll_interval)
                continue

        raise Exception("Transcription timed out")

    def _get_final_transcript(self, session_id: str) -> Dict:
        """Get the final transcript with all details"""
        try:
            # Get full transcript
            transcript_url = f"{self.base_url}/asr/session/{session_id}/transcript"
            response = requests.get(transcript_url, headers=self.headers)

            if response.status_code == 200:
                return response.json()
            else:
                # Fallback to session data
                session_url = f"{self.base_url}/asr/session/{session_id}"
                response = requests.get(session_url, headers=self.headers)
                if response.status_code == 200:
                    return response.json()

            raise Exception(f"Failed to get transcript: {response.status_code}")

        except Exception as e:
            logger.error(f"Failed to get final transcript: {e}")
            raise

    def _parse_results(self, result: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse Voicegain results into our format

        Returns:
            Tuple of (segments, speakers)
        """
        segments = []
        speakers = {}

        try:
            # Handle different response formats
            words = []

            # Try to get words from different possible locations
            if "words" in result:
                words = result["words"]
            elif "transcript" in result and isinstance(result["transcript"], dict):
                if "words" in result["transcript"]:
                    words = result["transcript"]["words"]
            elif "results" in result:
                for res in result["results"]:
                    if "words" in res:
                        words.extend(res["words"])

            # If we have words with speaker tags, process them
            if words:
                # Extract unique speakers
                speaker_ids = set()
                for word in words:
                    speaker_tag = word.get("speaker", word.get("speakerTag", 0))
                    speaker_ids.add(speaker_tag)

                # Create speaker profiles
                for sp_id in speaker_ids:
                    speakers[sp_id] = {
                        'id': f"speaker_{sp_id}",
                        'label': f"Speaker {sp_id + 1}",
                        'gender': 'unknown',
                        'age': 'unknown'
                    }

                # Group words into segments by speaker
                current_segment = None
                for word in words:
                    speaker_tag = word.get("speaker", word.get("speakerTag", 0))
                    speaker_id = f"speaker_{speaker_tag}"

                    # Get timing (Voicegain uses seconds, not milliseconds)
                    start_time = word.get("start", 0)
                    end_time = word.get("end", start_time + 0.5)
                    text = word.get("word", word.get("text", ""))

                    # Start new segment if speaker changes or significant pause
                    if (current_segment is None or
                        current_segment['speaker'] != speaker_id or
                        start_time - current_segment['end'] > 1.5):

                        if current_segment:
                            segments.append(current_segment)

                        current_segment = {
                            'text': text,
                            'start': start_time,
                            'end': end_time,
                            'speaker': speaker_id
                        }
                    else:
                        # Continue current segment
                        current_segment['text'] += ' ' + text
                        current_segment['end'] = end_time

                # Add last segment
                if current_segment:
                    segments.append(current_segment)

            # If no word-level data, try to get utterances or plain transcript
            if not segments:
                # Try utterances
                if "utterances" in result:
                    for idx, utterance in enumerate(result["utterances"]):
                        speaker_id = f"speaker_{utterance.get('speaker', 0)}"
                        segment = {
                            'text': utterance.get('text', ''),
                            'start': utterance.get('start', idx * 5),
                            'end': utterance.get('end', (idx + 1) * 5),
                            'speaker': speaker_id
                        }
                        segments.append(segment)

                        if speaker_id not in speakers:
                            speakers[speaker_id] = {
                                'id': speaker_id,
                                'label': f"Speaker {len(speakers) + 1}",
                                'gender': 'unknown',
                                'age': 'unknown'
                            }

                # Last resort - just get the transcript as a single segment
                elif "transcript" in result:
                    transcript_text = result["transcript"]
                    if isinstance(transcript_text, str) and transcript_text:
                        segments.append({
                            'text': transcript_text,
                            'start': 0,
                            'end': 10,  # Default duration
                            'speaker': 'speaker_0'
                        })
                        speakers['speaker_0'] = {
                            'id': 'speaker_0',
                            'label': 'Speaker 1',
                            'gender': 'unknown',
                            'age': 'unknown'
                        }

        except Exception as e:
            logger.error(f"Error parsing results: {e}")
            # Return at least something if parsing fails
            if not segments and "transcript" in result:
                segments.append({
                    'text': str(result.get("transcript", "Transcription failed")),
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

        logger.info(f"Parsed {len(segments)} segments and {len(speakers)} speakers")

        # Ensure we return list of speaker values
        return segments, list(speakers.values())