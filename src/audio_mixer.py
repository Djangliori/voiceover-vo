"""
Audio Mixing Module
Mixes original audio with Georgian voiceover, lowering original volume during speech
Uses pydub for reliable audio processing
"""

import os
import math
from pathlib import Path
from pydub import AudioSegment
from src.logging_config import get_logger

logger = get_logger(__name__)


class AudioMixer:
    def __init__(self, original_volume=0.05, voiceover_volume=1.0):
        """
        Initialize audio mixer

        Args:
            original_volume: Volume level for original audio (0.0 to 1.0)
            voiceover_volume: Volume level for voiceover (0.0 to 1.0)
        """
        self.original_volume = original_volume
        self.voiceover_volume = voiceover_volume

    def mix_audio(self, original_audio_path, voiceover_segments, output_path, progress_callback=None):
        """
        Mix original audio with Georgian voiceover using pydub

        Two-step process:
        1. Build a single voiceover track by placing segments at their timestamps
           (NO overlay, NO mixing - just concatenation with silence gaps)
        2. Overlay the complete voiceover track onto the lowered original audio
           (ONE single overlay operation)

        Args:
            original_audio_path: Path to original audio WAV file
            voiceover_segments: List of segments with 'audio_path', 'start', 'end'
            output_path: Path for output mixed audio file
            progress_callback: Optional callback for progress updates

        Returns:
            Path to mixed audio file
        """

        # ============================================================
        # STEP 1: Load and prepare original audio
        # ============================================================

        if progress_callback:
            progress_callback("Loading original audio...")

        original = AudioSegment.from_wav(original_audio_path)
        original = original.set_frame_rate(44100).set_channels(1)
        duration_ms = len(original)

        logger.info(f"Original audio: {duration_ms}ms, {original.frame_rate}Hz, {original.channels} channels")

        # Lower the original audio volume
        if self.original_volume > 0:
            volume_db = 20 * math.log10(self.original_volume)
        else:
            volume_db = -60

        original_lowered = original + volume_db
        logger.info(f"Lowered original audio by {volume_db:.1f}dB")

        if not voiceover_segments:
            if progress_callback:
                progress_callback("No voiceover segments, exporting original...")
            original_lowered.export(output_path, format="wav")
            return output_path

        # ============================================================
        # STEP 2: Build ONE voiceover track
        #         NO overlay, NO mixing here - just place audio on timeline
        # ============================================================

        if progress_callback:
            progress_callback("Building voiceover track...")

        voiceover_track = self._build_voiceover_track(
            voiceover_segments,
            duration_ms,
            progress_callback
        )

        logger.info(f"Voiceover track: {len(voiceover_track)}ms")

        # ============================================================
        # STEP 3: ONE overlay operation - voiceover onto original
        # ============================================================

        if progress_callback:
            progress_callback("Overlaying voiceover onto original...")

        final_mix = original_lowered.overlay(voiceover_track)

        if progress_callback:
            progress_callback("Exporting final mix...")

        final_mix.export(output_path, format="wav")

        logger.info(f"Audio mixing complete: {output_path}")

        if progress_callback:
            progress_callback("Audio mixing complete!")

        return output_path

    def _build_voiceover_track(self, voiceover_segments, total_duration_ms, progress_callback=None):
        """
        Build a single voiceover track by placing segments at their timestamps.

        This method does NOT use overlay or mixing. It simply:
        1. Creates silence for the gap before each segment
        2. Appends the voiceover segment
        3. Repeats until all segments are placed
        4. Pads with silence at the end

        The result is ONE audio track with all voiceovers placed at correct times.

        Args:
            voiceover_segments: List of segments with 'audio_path' and 'start'
            total_duration_ms: Total duration the track should be
            progress_callback: Optional callback for progress updates

        Returns:
            AudioSegment containing all voiceovers placed on timeline
        """

        logger.info(f"Building voiceover track from {len(voiceover_segments)} segments")

        # Sort by start time
        sorted_segments = sorted(voiceover_segments, key=lambda s: s['start'])

        # We'll build the track by simple concatenation:
        # [silence][segment1][silence][segment2][silence]...[padding]

        pieces = []  # List of AudioSegment pieces to concatenate at the end
        current_time_ms = 0

        for i, segment in enumerate(sorted_segments):
            start_ms = int(segment['start'] * 1000)
            segment_path = segment['audio_path']

            # Load the voiceover clip
            clip = AudioSegment.from_wav(segment_path)
            clip = clip.set_frame_rate(44100).set_channels(1)

            # Apply volume adjustment if needed
            if self.voiceover_volume != 1.0 and self.voiceover_volume > 0:
                vo_volume_db = 20 * math.log10(self.voiceover_volume)
                clip = clip + vo_volume_db

            # Add silence gap before this segment (if needed)
            if start_ms > current_time_ms:
                gap_duration = start_ms - current_time_ms
                silence = AudioSegment.silent(duration=gap_duration, frame_rate=44100)
                silence = silence.set_channels(1)
                pieces.append(silence)
                current_time_ms = start_ms
                logger.debug(f"Added {gap_duration}ms silence gap before segment {i}")

            # Add the voiceover clip
            pieces.append(clip)
            current_time_ms += len(clip)
            logger.debug(f"Added segment {i} at {start_ms}ms (duration: {len(clip)}ms)")

            if progress_callback and (i + 1) % 5 == 0:
                progress_callback(f"Placed {i + 1}/{len(sorted_segments)} voiceover segments")

        # Add silence padding at the end if needed
        if current_time_ms < total_duration_ms:
            end_padding = total_duration_ms - current_time_ms
            silence = AudioSegment.silent(duration=end_padding, frame_rate=44100)
            silence = silence.set_channels(1)
            pieces.append(silence)
            logger.debug(f"Added {end_padding}ms silence padding at end")

        # Now concatenate all pieces into one track
        # This is a simple sum operation, no mixing
        logger.info(f"Concatenating {len(pieces)} pieces into voiceover track")

        voiceover_track = AudioSegment.empty()
        for piece in pieces:
            voiceover_track = voiceover_track + piece

        logger.info(f"Voiceover track complete: {len(voiceover_track)}ms")

        return voiceover_track
