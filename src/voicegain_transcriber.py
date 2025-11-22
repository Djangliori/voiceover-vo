"""
Voicegain Transcriber - Speech Analytics API Version
Uses /sa endpoint for transcription with speaker diarization, gender, and age detection
Falls back to /asr/transcribe if SA config is not available
"""

import os
import time
import json
import requests
from typing import List, Dict, Optional, Tuple
from src.logging_config import get_logger

try:
    from src.console_logger import console, log_api_call
    CONSOLE_AVAILABLE = True
except ImportError:
    CONSOLE_AVAILABLE = False
    class DummyConsole:
        def log(self, *args, **kwargs):
            pass
    console = DummyConsole()
    def log_api_call(*args, **kwargs):
        pass

logger = get_logger(__name__)


class VoicegainTranscriber:
    """Voicegain transcriber using Speech Analytics API for speaker/gender detection"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Voicegain transcriber with JWT authentication

        Args:
            api_key: Voicegain JWT token (or from environment)
        """
        self.api_key = api_key or os.getenv('VOICEGAIN_API_KEY')
        if not self.api_key:
            raise ValueError("VOICEGAIN_API_KEY not found in environment variables")

        self.base_url = "https://api.voicegain.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Speech Analytics config ID (create in Voicegain console)
        self.sa_config_id = os.getenv('VOICEGAIN_SA_CONFIG_ID')

        # Store speakers for multi-voice support
        self._speakers = []
        self._segments = []

        if self.sa_config_id:
            logger.info(f"Voicegain transcriber initialized with Speech Analytics (config: {self.sa_config_id})")
        else:
            logger.info("Voicegain transcriber initialized (Speech Analytics disabled - no SA config)")

    def transcribe(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Main transcribe method called by tasks.py
        Uses Speech Analytics API if configured, otherwise falls back to basic transcription
        """
        segments, speakers = self.transcribe_with_analytics(audio_path, progress_callback)

        self._segments = segments
        self._speakers = speakers
        return segments

    def has_speaker_diarization(self) -> bool:
        """Check if multiple speakers were detected"""
        return len(self._speakers) > 1

    def get_speakers(self) -> List[Dict]:
        """Get detected speakers"""
        return self._speakers

    def merge_short_segments(self, segments: List[Dict], min_duration: float = 2.0) -> List[Dict]:
        """Merge segments shorter than min_duration with adjacent segments"""
        if not segments:
            return segments

        merged = []
        current = None

        for seg in segments:
            duration = seg.get('end', 0) - seg.get('start', 0)

            if current is None:
                current = seg.copy()
            elif duration < min_duration:
                current['text'] = current.get('text', '') + ' ' + seg.get('text', '')
                current['end'] = seg.get('end', current.get('end', 0))
            else:
                merged.append(current)
                current = seg.copy()

        if current:
            merged.append(current)

        return merged

    def transcribe_with_analytics(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Transcribe audio with speaker diarization and gender detection

        Uses Speech Analytics API (/sa) if SA config is available,
        otherwise falls back to basic transcription (/asr/transcribe/async)
        """
        try:
            if progress_callback:
                progress_callback("Preparing audio for Voicegain...")

            # Check file exists
            if not os.path.exists(audio_path):
                raise Exception(f"Audio file not found: {audio_path}")

            file_size = os.path.getsize(audio_path)
            file_size_mb = file_size / (1024 * 1024)

            logger.info("=" * 60)
            logger.info("VOICEGAIN TRANSCRIPTION START")
            logger.info(f"Audio file: {audio_path}")
            logger.info(f"Size: {file_size_mb:.2f} MB")
            logger.info(f"Using Speech Analytics: {bool(self.sa_config_id)}")
            logger.info("=" * 60)

            session_id = audio_path.split('/')[-1].split('_')[0] if '/' in audio_path else 'unknown'

            # Upload audio first
            if progress_callback:
                progress_callback("Uploading audio to Voicegain...")

            audio_id = self._upload_audio(audio_path, session_id)
            if not audio_id:
                raise Exception("Failed to upload audio to Voicegain")

            logger.info(f"Audio uploaded, ID: {audio_id}")

            # Use Speech Analytics API if configured
            if self.sa_config_id:
                if progress_callback:
                    progress_callback("Starting Speech Analytics (with speaker/gender detection)...")
                result = self._speech_analytics_transcribe(audio_id, progress_callback, session_id)
            else:
                if progress_callback:
                    progress_callback("Starting transcription...")
                result = self._basic_transcribe(audio_id, progress_callback, session_id)

            segments, speakers = result

            logger.info("=" * 60)
            logger.info("VOICEGAIN TRANSCRIPTION RESULTS")
            logger.info(f"Total segments: {len(segments)}")
            logger.info(f"Total speakers: {len(speakers)}")

            for speaker in speakers:
                logger.info(f"Speaker {speaker.get('id')}: gender={speaker.get('gender', 'unknown')}, age={speaker.get('age', 'unknown')}")

            logger.info("=" * 60)

            return result

        except Exception as e:
            logger.error(f"Voicegain transcription failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return [], []

    def _upload_audio(self, audio_path: str, session_id: str = None) -> Optional[str]:
        """Upload audio file to Voicegain data store"""
        try:
            file_size = os.path.getsize(audio_path)
            logger.info(f"Uploading audio: {audio_path} ({file_size / (1024*1024):.2f} MB)")

            upload_headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            filename = os.path.basename(audio_path)
            with open(audio_path, 'rb') as audio_file:
                files = {
                    'file': (filename, audio_file, 'audio/mpeg')
                }
                response = requests.post(
                    f"{self.base_url}/data/file",
                    headers=upload_headers,
                    files=files
                )

            if response.status_code not in [200, 201]:
                logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return None

            result = response.json()
            audio_id = result.get("objectId") or result.get("uuid")

            logger.info(f"Audio uploaded successfully, ID: {audio_id}")
            return audio_id

        except Exception as e:
            logger.error(f"Error uploading audio: {e}")
            return None

    def _speech_analytics_transcribe(
        self,
        audio_id: str,
        progress_callback: Optional[callable] = None,
        session_id: str = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Transcribe using Speech Analytics API (/sa)
        Returns transcript with speaker diarization and gender detection
        """
        try:
            # Create SA session
            request_body = {
                "asyncMode": "OFF-LINE",
                "metadata": [
                    {"name": "source", "value": "gva-app"}
                ],
                "audio": {
                    "source": {
                        "dataStore": {
                            "uuid": audio_id
                        }
                    }
                },
                "virtualDualChannelEnabled": True,  # Enable diarization for mono audio
                "speakerChannels": [
                    {"audioChannelSelector": "mix"}
                ],
                "asr": {
                    "acousticModelNonRealTime": "VoiceGain-omega-x",
                    "noInputTimeout": 60000,
                    "completeTimeout": 5000,
                    "sensitivity": 0.5,
                    "speedVsAccuracy": 0.5,
                    "languages": ["en"]
                },
                "saConfig": self.sa_config_id
            }

            logger.info(f"Creating SA session with config: {self.sa_config_id}")

            response = requests.post(
                f"{self.base_url}/sa",
                headers=self.headers,
                json=request_body
            )

            if response.status_code not in [200, 201, 202]:
                logger.error(f"SA request failed: {response.status_code} - {response.text}")
                # Fall back to basic transcription
                logger.info("Falling back to basic transcription...")
                return self._basic_transcribe(audio_id, progress_callback, session_id)

            result = response.json()
            sa_session_id = result.get("saSessionId")
            poll_url = result.get("poll", {}).get("url")

            if not sa_session_id:
                logger.error(f"No SA session ID in response: {result}")
                return self._basic_transcribe(audio_id, progress_callback, session_id)

            logger.info(f"SA session started: {sa_session_id}")

            # Poll for completion
            return self._poll_sa_results(sa_session_id, poll_url, progress_callback, session_id)

        except Exception as e:
            logger.error(f"Speech Analytics error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fall back to basic transcription
            return self._basic_transcribe(audio_id, progress_callback, session_id)

    def _poll_sa_results(
        self,
        sa_session_id: str,
        poll_url: str,
        progress_callback: Optional[callable] = None,
        session_id: str = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """Poll for Speech Analytics results"""
        max_attempts = 120

        for i in range(max_attempts):
            try:
                time.sleep(5 if i > 0 else 1)

                response = requests.get(poll_url, headers=self.headers)

                if response.status_code != 200:
                    logger.debug(f"Poll {i}: status {response.status_code}")
                    continue

                result = response.json()
                status = result.get("status", "")

                if progress_callback and i % 5 == 0:
                    progress_callback(f"Processing... ({i}/{max_attempts})")

                if status == "done" or status == "completed":
                    logger.info(f"SA session completed after {i} polls")
                    return self._fetch_sa_data(sa_session_id, session_id)

                if status == "error" or status == "failed":
                    logger.error(f"SA session failed: {result}")
                    return [], []

            except Exception as e:
                logger.warning(f"Poll error: {e}")
                continue

        logger.error("SA session timed out")
        return [], []

    def _fetch_sa_data(
        self,
        sa_session_id: str,
        session_id: str = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """Fetch Speech Analytics data with transcript, speakers, and gender"""
        try:
            # Fetch full SA data
            data_url = f"{self.base_url}/sa/{sa_session_id}/data?summary=true&emotion=true&keywords=true"

            response = requests.get(data_url, headers=self.headers)

            if response.status_code != 200:
                logger.error(f"Failed to fetch SA data: {response.status_code} - {response.text}")
                return [], []

            data = response.json()

            logger.info(f"SA data keys: {data.keys()}")
            logger.info(f"SA data: {json.dumps(data, indent=2)[:3000]}")

            segments = []
            speakers = {}

            # Extract channel info (speaker, gender, age)
            channels = data.get("channels", [])
            for i, channel in enumerate(channels):
                speaker_id = channel.get("spk", str(i))
                speaker_key = f"speaker_{speaker_id}"

                gender = channel.get("gender", "unknown")
                age = channel.get("age", "unknown")

                speakers[speaker_key] = {
                    "id": speaker_key,
                    "label": f"Speaker {i + 1}",
                    "gender": gender.lower() if gender else "unknown",
                    "age": age.lower() if age else "unknown"
                }

                logger.info(f"Channel {i}: speaker={speaker_id}, gender={gender}, age={age}")

            # Extract transcript with timing and speaker info
            multi_channel_words = data.get("multiChannelWords", [])

            for section in multi_channel_words:
                words = section.get("words", [])
                channel_idx = section.get("channel", 0)

                if not words:
                    continue

                # Build segment from words
                text_parts = []
                start_time = None
                end_time = None

                for word in words:
                    utterance = word.get("utterance", "")
                    word_start = word.get("start", 0) / 1000.0  # ms to seconds
                    word_duration = word.get("duration", 100) / 1000.0
                    word_end = word_start + word_duration

                    if utterance:
                        text_parts.append(utterance)
                        if start_time is None:
                            start_time = word_start
                        end_time = word_end

                if text_parts:
                    # Determine speaker from channel
                    speaker_key = f"speaker_{channel_idx}"
                    if speaker_key not in speakers:
                        speaker_key = list(speakers.keys())[0] if speakers else "speaker_0"

                    segments.append({
                        "text": " ".join(text_parts),
                        "start": start_time or 0,
                        "end": end_time or 0,
                        "speaker": speaker_key
                    })

            # Sort segments by start time
            segments.sort(key=lambda x: x.get("start", 0))

            logger.info(f"Parsed {len(segments)} segments from SA data")
            logger.info(f"Detected {len(speakers)} speakers with gender info")

            # Log first few segments
            for i, seg in enumerate(segments[:3]):
                logger.info(f"Segment {i}: [{seg.get('start'):.1f}s-{seg.get('end'):.1f}s] "
                           f"speaker={seg.get('speaker')} text='{seg.get('text', '')[:50]}...'")

            return segments, list(speakers.values())

        except Exception as e:
            logger.error(f"Error parsing SA data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return [], []

    def _basic_transcribe(
        self,
        audio_id: str,
        progress_callback: Optional[callable] = None,
        session_id: str = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Basic transcription using /asr/transcribe/async
        Fallback when Speech Analytics is not available
        """
        try:
            request_body = {
                "sessions": [{
                    "asyncMode": "OFF-LINE",
                    "audioChannelSelector": "mix",
                    "content": {
                        "full": ["transcript", "words"],
                        "incremental": []
                    },
                    "diarization": {
                        "minSpeakers": 1,
                        "maxSpeakers": 6
                    },
                    "poll": {
                        "persist": 600000
                    }
                }],
                "audio": {
                    "source": {
                        "dataStore": {
                            "uuid": audio_id
                        }
                    }
                },
                "settings": {
                    "asr": {
                        "noInputTimeout": -1,
                        "completeTimeout": -1,
                        "sensitivity": 0.5,
                        "speedVsAccuracy": 0.5,
                        "languages": ["en"]
                    }
                }
            }

            logger.info("Starting basic transcription (no SA config)")

            response = requests.post(
                f"{self.base_url}/asr/transcribe/async",
                headers=self.headers,
                json=request_body
            )

            if response.status_code not in [200, 201, 202]:
                logger.error(f"Transcription request failed: {response.status_code} - {response.text}")
                return [], []

            result = response.json()

            if "sessions" not in result or len(result["sessions"]) == 0:
                logger.error(f"No sessions in response: {result}")
                return [], []

            session_data = result["sessions"][0]
            poll_url = session_data.get("poll", {}).get("url")

            if not poll_url:
                logger.error(f"No poll URL in response: {result}")
                return [], []

            logger.info(f"Transcription started, polling: {poll_url}")

            return self._poll_basic_results(poll_url, progress_callback, session_id)

        except Exception as e:
            logger.error(f"Basic transcription error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return [], []

    def _poll_basic_results(
        self,
        poll_url: str,
        progress_callback: Optional[callable] = None,
        session_id: str = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """Poll for basic transcription results"""
        max_attempts = 120

        for i in range(max_attempts):
            try:
                time.sleep(5 if i > 0 else 1)

                response = requests.get(f"{poll_url}?full=false", headers=self.headers)

                if response.status_code == 404:
                    continue

                if response.status_code != 200:
                    continue

                result = response.json()
                is_final = result.get("result", {}).get("final", False)

                if progress_callback and i % 5 == 0:
                    progress_callback(f"Processing... ({i}/{max_attempts})")

                if is_final:
                    logger.info(f"Transcription completed after {i} polls")

                    # Fetch transcript with format=json for word details
                    session_id_from_url = poll_url.split('/asr/transcribe/')[1].split('/')[0]
                    transcript_url = f"{self.base_url}/asr/transcribe/{session_id_from_url}/transcript?format=json"

                    json_response = requests.get(transcript_url, headers=self.headers)

                    if json_response.status_code == 200:
                        return self._parse_basic_transcript(json_response.json())
                    else:
                        # Fallback to poll response
                        full_response = requests.get(f"{poll_url}?full=true", headers=self.headers)
                        if full_response.status_code == 200:
                            return self._parse_poll_response(full_response.json())

                    return [], []

            except Exception as e:
                logger.warning(f"Poll error: {e}")
                continue

        logger.error("Transcription timed out")
        return [], []

    def _parse_basic_transcript(self, data: Dict) -> Tuple[List[Dict], List[Dict]]:
        """Parse basic transcript JSON format"""
        segments = []
        speakers = {}

        try:
            logger.info(f"Parsing basic transcript: {json.dumps(data, indent=2)[:2000]}")

            # Handle array of phrases
            phrases = data if isinstance(data, list) else data.get("words", [])

            for phrase in phrases:
                if not isinstance(phrase, dict):
                    continue

                phrase_speaker = phrase.get("spk", "0")
                speaker_key = f"speaker_{phrase_speaker}"

                # Get nested words
                words = phrase.get("words", [])

                if words:
                    text_parts = []
                    start_time = None
                    end_time = None

                    for word in words:
                        utterance = word.get("utterance", "")
                        word_start = word.get("start", 0) / 1000.0
                        word_duration = word.get("duration", 100) / 1000.0

                        if utterance:
                            text_parts.append(utterance)
                            if start_time is None:
                                start_time = word_start
                            end_time = word_start + word_duration

                    if text_parts:
                        segments.append({
                            "text": " ".join(text_parts),
                            "start": start_time or 0,
                            "end": end_time or 0,
                            "speaker": speaker_key
                        })

                        if speaker_key not in speakers:
                            speakers[speaker_key] = {
                                "id": speaker_key,
                                "label": f"Speaker {len(speakers) + 1}",
                                "gender": "unknown",
                                "age": "unknown"
                            }

            logger.info(f"Parsed {len(segments)} segments, {len(speakers)} speakers")

            # Apply pitch-based gender detection since basic API doesn't provide it
            if speakers:
                # Note: Gender detection will be applied in transcribe() method
                pass

            return segments, list(speakers.values())

        except Exception as e:
            logger.error(f"Error parsing basic transcript: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return [], []

    def _parse_poll_response(self, data: Dict) -> Tuple[List[Dict], List[Dict]]:
        """Parse poll response format (fallback)"""
        segments = []
        speakers = {}

        try:
            inner_result = data.get("result", {})
            words = inner_result.get("words", [])
            transcript = inner_result.get("transcript", "")

            if words:
                current_segment = None

                for word in words:
                    text = word.get("utterance") or word.get("word", "")
                    start_ms = word.get("start", 0)
                    end_ms = word.get("end", start_ms + 500)

                    start = start_ms / 1000.0
                    end = end_ms / 1000.0

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

            elif transcript:
                sentences = transcript.replace('!', '.').replace('?', '.').split('.')
                current_time = 0

                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        segments.append({
                            'text': sentence,
                            'start': current_time,
                            'end': current_time + 3.0,
                            'speaker': 'speaker_0'
                        })
                        current_time += 3.0

            if segments:
                speakers['speaker_0'] = {
                    'id': 'speaker_0',
                    'label': 'Speaker 1',
                    'gender': 'unknown',
                    'age': 'unknown'
                }

            return segments, list(speakers.values())

        except Exception as e:
            logger.error(f"Error parsing poll response: {e}")
            return [], []


# For backwards compatibility
Transcriber = VoicegainTranscriber
