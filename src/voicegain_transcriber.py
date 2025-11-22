"""
Voicegain Transcriber with Speaker Diarization, Gender, and Age Detection
Replaces AssemblyAI and Whisper with a single unified solution
"""

import os
import time
import requests
from typing import List, Dict, Optional, Tuple
from src.logging_config import get_logger

logger = get_logger(__name__)


class VoicegainTranscriber:
    """Transcriber using Voicegain API for complete speech analytics"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Voicegain transcriber

        Args:
            api_key: Voicegain API key (or from environment)
        """
        self.api_key = api_key or os.getenv('VOICEGAIN_API_KEY')
        if not self.api_key:
            raise ValueError("VOICEGAIN_API_KEY not found in environment variables")

        self.base_url = "https://api.voicegain.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info("Voicegain transcriber initialized successfully")

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
            - segments: List of transcript segments with speaker IDs
            - speakers: List of speaker profiles with gender and age
        """
        try:
            if progress_callback:
                progress_callback("Uploading audio to Voicegain...")

            # Step 1: Upload audio file
            upload_url = self._upload_audio(audio_path)

            if progress_callback:
                progress_callback("Starting Voicegain transcription with analytics...")

            # Step 2: Start transcription with analytics
            session_id = self._start_transcription(upload_url)

            if progress_callback:
                progress_callback("Processing speech analytics (gender, age, diarization)...")

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

    def _upload_audio(self, audio_path: str) -> str:
        """Upload audio file to Voicegain and get URL"""
        # First, get upload URL
        upload_request = {
            "name": os.path.basename(audio_path),
            "description": "Georgian voiceover transcription"
        }

        response = requests.post(
            f"{self.base_url}/data/file",
            headers=self.headers,
            json=upload_request
        )
        response.raise_for_status()

        upload_data = response.json()
        upload_url = upload_data["url"]

        # Upload the actual file
        with open(audio_path, 'rb') as f:
            upload_response = requests.put(upload_url, data=f)
            upload_response.raise_for_status()

        return upload_data["objectId"]

    def _start_transcription(self, audio_object_id: str) -> str:
        """Start transcription with analytics enabled"""
        transcription_request = {
            "audio": {
                "source": {
                    "dataStore": {
                        "objectId": audio_object_id
                    }
                }
            },
            "settings": {
                "asr": {
                    "languages": ["en-US"],  # Will auto-detect if needed
                    "acousticModel": "latest",
                    "noInputTimeout": 60000,
                    "completeTimeout": 3600000
                },
                "speaker": {
                    "diarization": {
                        "enable": True,
                        "minSpeakers": 1,
                        "maxSpeakers": 10
                    }
                },
                "analytics": {
                    "enable": True,
                    "gender": True,
                    "age": True,
                    "emotion": False  # We don't need emotion for now
                }
            },
            "output": {
                "format": "json"
            }
        }

        response = requests.post(
            f"{self.base_url}/asr/transcribe/async",
            headers=self.headers,
            json=transcription_request
        )
        response.raise_for_status()

        return response.json()["sessionId"]

    def _poll_for_results(self, session_id: str, progress_callback: Optional[callable] = None) -> Dict:
        """Poll for transcription results"""
        poll_url = f"{self.base_url}/asr/transcribe/{session_id}"
        max_polls = 300  # 5 minutes max
        poll_interval = 1  # Start with 1 second

        for i in range(max_polls):
            response = requests.get(poll_url, headers=self.headers)
            response.raise_for_status()

            result = response.json()
            status = result.get("status")

            if status == "COMPLETED":
                return result
            elif status == "FAILED":
                raise Exception(f"Transcription failed: {result.get('error', 'Unknown error')}")

            if progress_callback and i % 5 == 0:
                progress_callback(f"Processing... ({i}/{max_polls})")

            time.sleep(poll_interval)
            # Increase poll interval over time
            if i > 10:
                poll_interval = 2
            if i > 30:
                poll_interval = 5

        raise Exception("Transcription timed out")

    def _parse_results(self, result: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse Voicegain results into our format

        Returns:
            Tuple of (segments, speakers)
        """
        segments = []
        speakers_data = {}

        # Parse transcript with speaker labels
        transcript_data = result.get("transcript", {})
        words = transcript_data.get("words", [])

        current_segment = None
        segment_text = []

        for word_data in words:
            word = word_data.get("word", "")
            start_time = word_data.get("start", 0) / 1000.0  # Convert ms to seconds
            end_time = word_data.get("end", 0) / 1000.0
            speaker_id = word_data.get("speakerId", "SPEAKER_00")

            # Collect speaker analytics
            if speaker_id not in speakers_data:
                speakers_data[speaker_id] = {
                    "id": speaker_id,
                    "label": f"Speaker {len(speakers_data) + 1}",
                    "gender": word_data.get("gender", "unknown"),
                    "age": word_data.get("age", "unknown")
                }

            # Group words into segments by speaker
            if current_segment is None or current_segment["speaker"] != speaker_id:
                # Save previous segment
                if current_segment and segment_text:
                    current_segment["text"] = " ".join(segment_text)
                    segments.append(current_segment)

                # Start new segment
                current_segment = {
                    "start": start_time,
                    "end": end_time,
                    "speaker": speaker_id,
                    "gender": speakers_data[speaker_id]["gender"],
                    "age": speakers_data[speaker_id]["age"]
                }
                segment_text = [word]
            else:
                # Continue current segment
                current_segment["end"] = end_time
                segment_text.append(word)

        # Save last segment
        if current_segment and segment_text:
            current_segment["text"] = " ".join(segment_text)
            segments.append(current_segment)

        # Get aggregated speaker analytics if available
        analytics = result.get("analytics", {})
        speaker_analytics = analytics.get("speaker", {})

        for speaker_id, speaker_info in speaker_analytics.items():
            if speaker_id in speakers_data:
                # Update with aggregated analytics
                speakers_data[speaker_id]["gender"] = speaker_info.get("gender", speakers_data[speaker_id]["gender"])
                speakers_data[speaker_id]["age"] = speaker_info.get("age", speakers_data[speaker_id]["age"])
                speakers_data[speaker_id]["speaking_time"] = speaker_info.get("talkTime", 0)

        # Convert speakers dict to list
        speakers = list(speakers_data.values())

        # Log speaker information
        for speaker in speakers:
            logger.info(f"Speaker {speaker['label']}: {speaker['gender']}, {speaker['age']}")

        # Merge short segments from same speaker
        segments = self._merge_short_segments(segments)

        return segments, speakers

    def _merge_short_segments(self, segments: List[Dict], min_duration: float = 2.0) -> List[Dict]:
        """Merge very short segments from the same speaker"""
        if not segments:
            return segments

        merged = []
        current = segments[0].copy()

        for next_segment in segments[1:]:
            # Check if we should merge
            same_speaker = current["speaker"] == next_segment["speaker"]
            short_gap = (next_segment["start"] - current["end"]) < 1.0
            current_short = (current["end"] - current["start"]) < min_duration

            if same_speaker and short_gap and current_short:
                # Merge segments
                current["text"] = current["text"] + " " + next_segment["text"]
                current["end"] = next_segment["end"]
            else:
                # Save current and start new
                merged.append(current)
                current = next_segment.copy()

        # Don't forget the last segment
        merged.append(current)

        return merged