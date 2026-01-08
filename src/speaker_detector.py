"""
Speaker Detection Client
Communicates with speaker-detection microservice
"""

import os
import requests
from typing import List, Dict, Optional
from src.logging_config import get_logger

logger = get_logger(__name__)


class SpeakerDetector:
    """Client for speaker detection microservice"""

    def __init__(self, service_url: str = None):
        """
        Initialize speaker detector client

        Args:
            service_url: URL of speaker detection service
                        Default: http://localhost:5002
        """
        self.service_url = service_url or os.getenv(
            'SPEAKER_DETECTION_URL',
            'http://localhost:5002'
        )
        self.enabled = self._check_service_health()

    def _check_service_health(self) -> bool:
        """Check if speaker detection service is available"""
        try:
            response = requests.get(
                f"{self.service_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                logger.info(f"Speaker detection service available at {self.service_url}")
                return True
        except Exception as e:
            logger.warning(f"Speaker detection service not available: {e}")
        return False

    def detect_speakers(self, audio_path: str) -> Optional[Dict]:
        """
        Detect speakers in audio file

        Args:
            audio_path: Path to audio file

        Returns:
            {
                'speakers': [{'start': 0, 'end': 10, 'speaker': 'SPEAKER_00'}, ...],
                'num_speakers': 2,
                'speaker_labels': ['SPEAKER_00', 'SPEAKER_01']
            }
            or None if service unavailable
        """
        if not self.enabled:
            logger.warning("Speaker detection service not available")
            return None

        try:
            response = requests.post(
                f"{self.service_url}/detect-speakers",
                json={'audio_path': audio_path},
                timeout=300  # 5 minutes for long audio
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Detected {result['num_speakers']} speakers in {len(result['speakers'])} segments")
                return result
            else:
                logger.error(f"Speaker detection failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error calling speaker detection service: {e}")
            return None

    def assign_voices_to_segments(
        self,
        transcription_segments: List[Dict],
        speaker_segments: List[Dict],
        voice_mapping: Dict[str, str] = None
    ) -> List[Dict]:
        """
        Assign speaker/voice to each transcription segment

        Args:
            transcription_segments: [{'start': 0, 'end': 5, 'text': '...'}, ...]
            speaker_segments: [{'start': 0, 'end': 10, 'speaker': 'SPEAKER_00'}, ...]
            voice_mapping: {'SPEAKER_00': 'male', 'SPEAKER_01': 'female'}

        Returns:
            Segments with 'speaker' and 'voice' fields added
        """
        if not speaker_segments:
            # No speaker detection - assign default voice to all
            for seg in transcription_segments:
                seg['speaker'] = 'SPEAKER_00'
                seg['voice'] = 'male'
            return transcription_segments

        # Default voice mapping: alternate male/female
        if not voice_mapping:
            voice_mapping = {
                'SPEAKER_00': 'male',
                'SPEAKER_01': 'female',
                'SPEAKER_02': 'male',
                'SPEAKER_03': 'female',
            }

        # Assign speaker to each transcription segment
        for trans_seg in transcription_segments:
            start = trans_seg['start']
            end = trans_seg['end']
            midpoint = (start + end) / 2

            # Find which speaker is talking at the midpoint
            speaker = None
            for spk_seg in speaker_segments:
                if spk_seg['start'] <= midpoint <= spk_seg['end']:
                    speaker = spk_seg['speaker']
                    break

            # If no match, find closest speaker segment
            if not speaker:
                closest_distance = float('inf')
                for spk_seg in speaker_segments:
                    distance = min(
                        abs(spk_seg['start'] - midpoint),
                        abs(spk_seg['end'] - midpoint)
                    )
                    if distance < closest_distance:
                        closest_distance = distance
                        speaker = spk_seg['speaker']

            # Assign speaker and voice
            trans_seg['speaker'] = speaker or 'SPEAKER_00'
            trans_seg['voice'] = voice_mapping.get(
                trans_seg['speaker'],
                'male'  # Default
            )

        logger.info(f"Assigned voices to {len(transcription_segments)} segments")
        return transcription_segments

    def is_available(self) -> bool:
        """Check if service is available"""
        return self.enabled
