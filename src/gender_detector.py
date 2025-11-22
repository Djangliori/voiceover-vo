"""
Simple gender detection based on voice pitch analysis
Uses fundamental frequency (F0) to estimate speaker gender
"""

import numpy as np
import librosa
from typing import Dict, Optional
from src.logging_config import get_logger

logger = get_logger(__name__)


class GenderDetector:
    """Detect gender from voice using pitch analysis"""

    def __init__(self):
        # Typical fundamental frequency ranges (Hz)
        self.male_f0_range = (85, 180)
        self.female_f0_range = (165, 255)
        # Overlap zone: 165-180 Hz

    def detect_gender_from_audio(self, audio_path: str, start_time: float = 0, end_time: float = None) -> Optional[str]:
        """
        Detect gender from audio segment using pitch analysis

        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds
            end_time: End time in seconds (None for entire file)

        Returns:
            'male', 'female', or None if uncertain
        """
        try:
            # Load audio segment
            y, sr = librosa.load(audio_path, offset=start_time, duration=(end_time - start_time) if end_time else None)

            # Extract pitch using fundamental frequency
            f0, voiced_flag, voiced_probs = librosa.pyin(
                y,
                fmin=librosa.note_to_hz('C2'),  # ~65 Hz
                fmax=librosa.note_to_hz('C6'),  # ~1047 Hz
                sr=sr
            )

            # Remove NaN values and get median pitch
            f0_valid = f0[~np.isnan(f0)]

            if len(f0_valid) == 0:
                logger.warning("No valid pitch detected in audio segment")
                return None

            median_f0 = np.median(f0_valid)
            mean_f0 = np.mean(f0_valid)

            logger.info(f"Pitch analysis: median={median_f0:.1f}Hz, mean={mean_f0:.1f}Hz")

            # Classify based on median pitch
            if median_f0 < 140:  # Clearly male
                return 'male'
            elif median_f0 > 200:  # Clearly female
                return 'female'
            else:
                # Ambiguous range, use additional heuristics
                if mean_f0 < 160:
                    return 'male'
                elif mean_f0 > 180:
                    return 'female'
                else:
                    logger.info(f"Ambiguous pitch range: {median_f0}Hz")
                    return None

        except Exception as e:
            logger.error(f"Gender detection failed: {e}")
            return None

    def detect_speakers_gender(self, audio_path: str, segments: list) -> Dict[str, str]:
        """
        Detect gender for multiple speakers from segments

        Args:
            audio_path: Path to audio file
            segments: List of segments with speaker IDs and timestamps

        Returns:
            Dict mapping speaker IDs to detected gender
        """
        speaker_genders = {}
        speaker_segments = {}

        # Group segments by speaker
        for segment in segments:
            speaker = segment.get('speaker', 'unknown')
            if speaker not in speaker_segments:
                speaker_segments[speaker] = []
            speaker_segments[speaker].append(segment)

        # Analyze each speaker's segments
        for speaker_id, segs in speaker_segments.items():
            # Analyze multiple segments for more reliable detection
            gender_votes = []

            for seg in segs[:5]:  # Analyze up to 5 segments per speaker
                gender = self.detect_gender_from_audio(
                    audio_path,
                    seg['start'],
                    seg['end']
                )
                if gender:
                    gender_votes.append(gender)

            # Majority vote
            if gender_votes:
                male_votes = gender_votes.count('male')
                female_votes = gender_votes.count('female')

                if male_votes > female_votes:
                    speaker_genders[speaker_id] = 'male'
                elif female_votes > male_votes:
                    speaker_genders[speaker_id] = 'female'
                else:
                    speaker_genders[speaker_id] = 'unknown'

                logger.info(f"Speaker {speaker_id}: {male_votes} male, {female_votes} female votes -> {speaker_genders[speaker_id]}")
            else:
                speaker_genders[speaker_id] = 'unknown'

        return speaker_genders