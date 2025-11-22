"""
Gender Detector Module
Detects speaker gender from audio using pitch analysis (F0 frequency)

Male voices typically have F0: 85-180 Hz
Female voices typically have F0: 165-255 Hz
"""

import os
from typing import Dict, List, Optional, Tuple
from pydub import AudioSegment
from src.logging_config import get_logger

logger = get_logger(__name__)

# Pitch thresholds for gender classification
# Male F0: 85-180 Hz, Female F0: 165-255 Hz
# Using 165 Hz as the boundary (average of upper male and lower female)
MALE_FEMALE_THRESHOLD_HZ = 165


class GenderDetector:
    """Detects speaker gender from audio using pitch analysis"""

    def __init__(self):
        self._librosa_available = None

    def _check_librosa(self) -> bool:
        """Check if librosa is available for pitch detection"""
        if self._librosa_available is None:
            try:
                import librosa
                self._librosa_available = True
                logger.info("librosa available for pitch-based gender detection")
            except ImportError:
                self._librosa_available = False
                logger.warning("librosa not available - gender detection will be basic")
        return self._librosa_available

    def detect_gender_from_audio(
        self,
        audio_path: str,
        segments: List[Dict],
        speakers: List[Dict]
    ) -> List[Dict]:
        """
        Analyze speaker segments and detect gender based on pitch

        Args:
            audio_path: Path to the audio file
            segments: List of transcript segments with speaker info
            speakers: List of speaker dictionaries to update

        Returns:
            Updated speakers list with gender detection
        """
        if not speakers:
            return speakers

        if not self._check_librosa():
            logger.warning("Skipping pitch-based gender detection (librosa not installed)")
            return speakers

        try:
            # Load audio file
            logger.info(f"Loading audio for gender detection: {audio_path}")
            audio = AudioSegment.from_file(audio_path)

            # Analyze each speaker's segments
            for speaker in speakers:
                speaker_id = speaker.get('id')
                if speaker.get('gender', 'unknown') != 'unknown':
                    # Already has gender from API, skip
                    continue

                # Get all segments for this speaker
                speaker_segments = [
                    seg for seg in segments
                    if seg.get('speaker') == speaker_id
                ]

                if not speaker_segments:
                    continue

                # Analyze pitch for this speaker
                gender, avg_f0 = self._analyze_speaker_pitch(
                    audio, speaker_segments
                )

                if gender:
                    speaker['gender'] = gender
                    speaker['detected_f0'] = avg_f0
                    logger.info(
                        f"Detected {speaker_id} as {gender} "
                        f"(avg F0: {avg_f0:.1f} Hz)"
                    )

        except Exception as e:
            logger.error(f"Gender detection failed: {e}")

        return speakers

    def _analyze_speaker_pitch(
        self,
        audio: AudioSegment,
        segments: List[Dict]
    ) -> Tuple[Optional[str], float]:
        """
        Analyze pitch from speaker's audio segments

        Args:
            audio: Full audio file as AudioSegment
            segments: Speaker's transcript segments with timing

        Returns:
            Tuple of (gender, average_f0)
        """
        import librosa
        import numpy as np

        f0_values = []

        # Sample up to 5 segments (max 30 seconds total)
        sample_segments = segments[:5]
        total_duration = 0
        max_duration = 30.0

        for seg in sample_segments:
            if total_duration >= max_duration:
                break

            start_ms = int(seg.get('start', 0) * 1000)
            end_ms = int(seg.get('end', start_ms + 1000) * 1000)

            # Limit segment duration
            duration = (end_ms - start_ms) / 1000
            if duration > 10:
                end_ms = start_ms + 10000
                duration = 10

            total_duration += duration

            try:
                # Extract segment audio
                segment_audio = audio[start_ms:end_ms]

                # Convert to numpy array for librosa
                samples = np.array(segment_audio.get_array_of_samples())
                samples = samples.astype(np.float32) / 32768.0  # Normalize to [-1, 1]

                # Handle stereo
                if segment_audio.channels == 2:
                    samples = samples.reshape((-1, 2)).mean(axis=1)

                sr = segment_audio.frame_rate

                # Extract F0 using pyin (probabilistic YIN)
                f0, voiced_flag, _ = librosa.pyin(
                    samples,
                    fmin=60,  # Minimum expected F0
                    fmax=300,  # Maximum expected F0
                    sr=sr
                )

                # Get voiced F0 values
                voiced_f0 = f0[voiced_flag]
                if len(voiced_f0) > 0:
                    f0_values.extend(voiced_f0)

            except Exception as e:
                logger.debug(f"Failed to analyze segment: {e}")
                continue

        if not f0_values:
            logger.warning("No F0 values detected for speaker")
            return None, 0.0

        # Calculate median F0 (more robust than mean)
        avg_f0 = float(np.median(f0_values))

        # Classify gender based on F0
        if avg_f0 < MALE_FEMALE_THRESHOLD_HZ:
            gender = 'male'
        else:
            gender = 'female'

        return gender, avg_f0


# Singleton instance
_detector = None


def get_gender_detector() -> GenderDetector:
    """Get singleton gender detector instance"""
    global _detector
    if _detector is None:
        _detector = GenderDetector()
    return _detector


def detect_speaker_genders(
    audio_path: str,
    segments: List[Dict],
    speakers: List[Dict]
) -> List[Dict]:
    """
    Convenience function to detect speaker genders

    Args:
        audio_path: Path to audio file
        segments: Transcript segments
        speakers: Speaker list to update

    Returns:
        Updated speakers with gender detection
    """
    detector = get_gender_detector()
    return detector.detect_gender_from_audio(audio_path, segments, speakers)
