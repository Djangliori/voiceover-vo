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
try:
    from src.console_logger import console, log_api_call
    CONSOLE_AVAILABLE = True
except ImportError:
    # Console logger not available yet
    CONSOLE_AVAILABLE = False
    class DummyConsole:
        def log(self, *args, **kwargs):
            pass
    console = DummyConsole()
    def log_api_call(*args, **kwargs):
        pass

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

        logger.info("Voicegain transcriber initialized (unlimited size version)")

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

            # Also log to console
            session_id = audio_path.split('/')[-1].split('_')[0] if '/' in audio_path else 'unknown'
            console.log("="*60, session_id=session_id)
            console.log("VOICEGAIN TRANSCRIPTION START", level="INFO", session_id=session_id)
            console.log(f"Audio: {audio_path}", session_id=session_id)
            console.log(f"Format: {audio_format}, Size: {file_size_mb:.2f} MB", session_id=session_id)

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

    def _upload_audio_to_voicegain(self, audio_path: str, session_id: str = None) -> Optional[str]:
        """
        Upload audio file to Voicegain's data store using POST /data/file.
        Returns the data UUID that can be used for transcription.
        This allows transcribing files of ANY size.
        """
        try:
            file_size = os.path.getsize(audio_path)
            logger.info(f"Uploading audio to Voicegain: {audio_path} ({file_size / (1024*1024):.2f} MB)")
            console.log(f"Uploading {file_size / (1024*1024):.2f} MB audio to Voicegain...", session_id=session_id)

            # Use POST /data/file to upload audio directly
            # This is the documented way per Voicegain API docs
            upload_headers = {
                "Authorization": f"Bearer {self.api_key}"
                # Don't set Content-Type - requests will set it for multipart
            }

            filename = os.path.basename(audio_path)
            with open(audio_path, 'rb') as audio_file:
                files = {
                    'file': (filename, audio_file, 'audio/mpeg')
                }
                upload_response = requests.post(
                    f"{self.base_url}/data/file",
                    headers=upload_headers,
                    files=files
                )

            logger.info(f"Upload response: {upload_response.status_code} - {upload_response.text[:500]}")

            if upload_response.status_code not in [200, 201]:
                logger.error(f"Failed to upload audio file: {upload_response.status_code} - {upload_response.text}")
                console.log(f"Audio upload failed: {upload_response.status_code}", level="ERROR", session_id=session_id)
                return None

            # Get the UUID from the response
            result = upload_response.json()
            data_uuid = result.get("objectId") or result.get("uuid") or result.get("dataObjectId")

            if not data_uuid:
                logger.error(f"No UUID in upload response: {result}")
                console.log(f"No UUID in response", level="ERROR", session_id=session_id)
                return None

            logger.info(f"Audio uploaded successfully, UUID: {data_uuid}")
            console.log(f"Audio uploaded to Voicegain data store", level="SUCCESS", session_id=session_id)

            return data_uuid

        except Exception as e:
            logger.error(f"Error uploading audio to Voicegain: {e}")
            console.log(f"Upload error: {e}", level="ERROR", session_id=session_id)
            return None

    def _async_transcribe(self, audio_path: str, progress_callback: Optional[callable] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Async transcription using /asr/transcribe/async
        Uses Voicegain's audio upload endpoint for large files
        """
        try:
            if progress_callback:
                progress_callback("Uploading audio to Voicegain...")

            session_id = audio_path.split('/')[-1].split('_')[0] if '/' in audio_path else 'unknown'

            # First, upload the audio file to Voicegain's data endpoint
            # This returns a data ID that we can use in the transcription request
            audio_id = self._upload_audio_to_voicegain(audio_path, session_id)
            if not audio_id:
                logger.error("Failed to upload audio to Voicegain")
                return [], []

            logger.info(f"Audio uploaded successfully, ID: {audio_id}")
            console.log(f"Audio uploaded, ID: {audio_id}", level="SUCCESS", session_id=session_id)

            if progress_callback:
                progress_callback("Starting transcription...")

            # Determine audio format
            audio_format = audio_path.split('.')[-1].lower()

            # Request structure using uploaded audio ID
            request_body = {
                "sessions": [{
                    "asyncMode": "OFF-LINE",  # Offline processing mode
                    "audioChannelSelector": "mix",  # Mix stereo to mono if needed
                    "content": {
                        "full": ["transcript", "words"],  # Get full transcript and word timings
                        "incremental": []
                    },
                    "poll": {
                        "afterlife": 300000,  # Keep results for 5 minutes after completion
                        "persist": 0  # Don't persist to storage
                    }
                }],
                "audio": {
                    "source": {
                        "dataStore": {
                            "uuid": audio_id  # Use the uploaded audio ID
                        }
                    }
                },
                "settings": {
                    "asr": {
                        "noInputTimeout": -1,  # No timeout
                        "completeTimeout": -1,  # No timeout
                        "sensitivity": 0.5,
                        "speedVsAccuracy": 0.5,
                        "languages": ["en"]  # English (not en-US for async)
                    }
                }
            }

            # Send async request to correct endpoint
            logger.info(f"Sending async request to {self.base_url}/asr/transcribe/async")
            logger.info(f"Using dataStore audio ID: {audio_id}")

            # Log to console
            console.log(f"Starting transcription with uploaded audio", session_id=session_id)

            response = requests.post(
                f"{self.base_url}/asr/transcribe/async",
                headers=self.headers,
                json=request_body
            )

            logger.info(f"Voicegain response status: {response.status_code}")
            console.log(f"Voicegain API response: {response.status_code}",
                       level="SUCCESS" if response.status_code in [200, 201, 202] else "ERROR",
                       session_id=session_id)

            if response.status_code not in [200, 201, 202]:
                error_msg = f"Async start failed: {response.status_code} - {response.text[:500]}"
                logger.error(error_msg)
                console.log(error_msg, level="ERROR", session_id=session_id)
                return [], []

            result = response.json()
            logger.info(f"Async request accepted: {json.dumps(result, indent=2)[:500]}")
            console.log("Async transcription started successfully", level="SUCCESS", session_id=session_id)

            # Get session ID
            transcription_session_id = None
            if "sessions" in result and len(result["sessions"]) > 0:
                transcription_session_id = result["sessions"][0].get("sessionId")
            else:
                transcription_session_id = result.get("sessionId")

            if not transcription_session_id:
                error_msg = f"No session ID in response: {json.dumps(result, indent=2)}"
                logger.error(error_msg)
                console.log("No session ID received from Voicegain", level="ERROR", session_id=session_id)
                console.log(f"Response: {json.dumps(result)[:200]}", level="DEBUG", session_id=session_id)
                return [], []

            logger.info(f"Started async transcription: {transcription_session_id}")
            console.log(f"Polling session: {transcription_session_id}", session_id=session_id)

            # Poll for results
            return self._poll_and_parse(transcription_session_id, progress_callback, session_id)

        except Exception as e:
            logger.error(f"Async transcription error: {e}")
            return [], []


    def _poll_and_parse(self, transcription_session_id: str, progress_callback: Optional[callable] = None,
                        console_session_id: str = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Poll for async results and parse them.

        Voicegain async API requires two-phase polling:
        1. Poll without ?full=true to check progress
        2. When session.final=true, poll with ?full=true to get transcript
        """
        poll_url = f"{self.base_url}/asr/transcribe/{transcription_session_id}"
        max_attempts = 120

        for i in range(max_attempts):
            try:
                time.sleep(2 if i > 0 else 0)  # Wait before polling

                # First poll for progress (without ?full=true)
                response = requests.get(poll_url, headers=self.headers)

                if response.status_code == 404:
                    if i % 10 == 0:  # Log every 10th attempt
                        logger.debug(f"Poll {i}: Not ready yet")
                        if console_session_id:
                            console.log(f"Polling... attempt {i}/120", level="DEBUG", session_id=console_session_id)
                    continue  # Not ready yet

                if response.status_code != 200:
                    logger.warning(f"Poll {i}: Status {response.status_code} - {response.text[:500]}")
                    continue

                result = response.json()

                # Log poll response for debugging (first poll and every 10th)
                if i == 0 or i % 10 == 0:
                    logger.info(f"Poll {i} response keys: {result.keys()}")
                    if "session" in result:
                        logger.info(f"Poll {i} session: {result['session']}")

                # Check if done - NOTE: 'final' is under 'session', not 'result'!
                session_final = result.get("session", {}).get("final", False)

                if session_final:
                    logger.info(f"Session marked as final after {i} polls, fetching full transcript...")

                    # NOW fetch with ?full=true to get the actual transcript
                    full_response = requests.get(f"{poll_url}?full=true", headers=self.headers)

                    if full_response.status_code != 200:
                        logger.error(f"Failed to fetch full transcript: {full_response.status_code}")
                        return [], []

                    full_result = full_response.json()
                    logger.info(f"Full result keys: {full_result.keys()}")
                    logger.info(f"Full result structure: {json.dumps(full_result, indent=2)[:2000]}")

                    if console_session_id:
                        console.log(f"Transcription complete after {i} polls", level="SUCCESS", session_id=console_session_id)

                        # Log transcript preview
                        transcript = full_result.get("result", {}).get("transcript", "")
                        if transcript:
                            preview = transcript[:200]
                            console.log(f"Transcript preview: {preview}...", session_id=console_session_id)

                    return self._parse_async_results(full_result, console_session_id)

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

    def _parse_async_results(self, result: Dict, console_session_id: str = None) -> Tuple[List[Dict], List[Dict]]:
        """Parse async transcription results.

        Voicegain async API returns data in result.result with:
        - 'words': array of word objects with timing
        - 'transcript': plain text transcript
        NOT in 'alternatives' (which is for sync API)
        """
        segments = []
        speakers = {}

        try:
            # Log full result structure for debugging
            logger.info(f"Full result keys: {result.keys() if result else 'None'}")

            inner_result = result.get("result", {})
            if inner_result:
                logger.info(f"result.result keys: {inner_result.keys()}")

            # For async API, words and transcript are directly under result.result
            words = inner_result.get("words", [])
            transcript = inner_result.get("transcript", "")

            logger.info(f"Found {len(words)} words in result.result")
            logger.info(f"Transcript length: {len(transcript)} chars")

            if words:
                # Log first few words for debugging
                logger.info(f"First word sample: {words[0] if words else 'None'}")

                # Group words into segments based on gaps/pauses
                current_segment = None
                for word_data in words:
                    # Word structure: {"word": "text", "start": ms, "end": ms, "confidence": float}
                    text = word_data.get("word", word_data.get("text", ""))
                    start = word_data.get("start", 0) / 1000.0  # Convert ms to seconds
                    end = word_data.get("end", start * 1000 + 500) / 1000.0

                    # Start new segment if gap > 1 second or first word
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

                logger.info(f"Created {len(segments)} segments from {len(words)} words")

            elif transcript:
                # No word-level data, but we have transcript text
                # Split into sentences for segments
                logger.info(f"Using plain transcript (no words): {transcript[:200]}...")

                sentences = transcript.replace('!', '.').replace('?', '.').split('.')
                time_per_sentence = 3.0
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

                logger.info(f"Created {len(segments)} segments from transcript text")

            else:
                # Try alternatives as fallback (sync API structure)
                alternatives = inner_result.get("alternatives", [])
                if alternatives:
                    logger.info(f"Using alternatives fallback: {len(alternatives)} alternatives")
                    words = alternatives[0].get("words", [])
                    if words:
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
                        utterance = alternatives[0].get("utterance", "")
                        if utterance:
                            segments.append({
                                'text': utterance,
                                'start': 0,
                                'end': 10,
                                'speaker': 'speaker_0'
                            })
                else:
                    logger.warning("No words, transcript, or alternatives found in result!")

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
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        logger.info(f"Parsed {len(segments)} segments")
        return segments, list(speakers.values())

