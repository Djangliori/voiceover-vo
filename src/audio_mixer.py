"""
Audio Mixing Module
Mixes original audio with Georgian voiceover, lowering original volume during speech
Uses pydub for audio processing - with manual sample mixing to avoid overlay issues
"""

import os
import math
import array
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
        Mix original audio with Georgian voiceover.

        Process:
        1. Build ONE voiceover track by concatenating segments with silence gaps
        2. Mix the two tracks by adding their samples together (no pydub overlay)
        """

        # ============================================================
        # STEP 1: Load and prepare original audio
        # ============================================================

        if progress_callback:
            progress_callback("Loading original audio...")

        original = AudioSegment.from_wav(original_audio_path)
        original = original.set_frame_rate(44100).set_channels(1)
        duration_ms = len(original)

        logger.info(f"Original audio: {duration_ms}ms")

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
        # STEP 2: Build ONE voiceover track (no mixing, just placement)
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
        # STEP 3: Mix by adding samples directly (NOT using pydub overlay)
        # ============================================================

        if progress_callback:
            progress_callback("Mixing audio tracks...")

        final_mix = self._mix_two_tracks(original_lowered, voiceover_track)

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
        NO overlay, NO mixing - just concatenation.
        """

        logger.info(f"Building voiceover track from {len(voiceover_segments)} segments")

        # Sort by start time
        sorted_segments = sorted(voiceover_segments, key=lambda s: s['start'])

        # Build the track by concatenation
        pieces = []
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

            # Add silence gap before this segment
            if start_ms > current_time_ms:
                gap_duration = start_ms - current_time_ms
                silence = AudioSegment.silent(duration=gap_duration, frame_rate=44100)
                silence = silence.set_channels(1)
                pieces.append(silence)
                current_time_ms = start_ms

            # Add the voiceover clip
            pieces.append(clip)
            current_time_ms += len(clip)

            if progress_callback and (i + 1) % 5 == 0:
                progress_callback(f"Placed {i + 1}/{len(sorted_segments)} segments")

        # Add silence padding at the end
        if current_time_ms < total_duration_ms:
            end_padding = total_duration_ms - current_time_ms
            silence = AudioSegment.silent(duration=end_padding, frame_rate=44100)
            silence = silence.set_channels(1)
            pieces.append(silence)

        # Concatenate all pieces by joining raw bytes
        # This is the most direct way - no pydub operations that could affect volume
        logger.info(f"Concatenating {len(pieces)} pieces")

        # Collect all raw bytes
        all_bytes = b''
        for piece in pieces:
            all_bytes += piece.raw_data

        # Create single AudioSegment from concatenated bytes
        voiceover_track = AudioSegment(
            data=all_bytes,
            sample_width=2,  # 16-bit
            frame_rate=44100,
            channels=1
        )

        logger.info(f"Voiceover track complete: {len(voiceover_track)}ms")

        return voiceover_track

    def _mix_two_tracks(self, track1, track2):
        """
        Mix two audio tracks by directly adding their samples.
        This avoids any potential issues with pydub's overlay() method.

        Both tracks must have the same sample rate and channels.
        """

        # Ensure same length
        len1 = len(track1)
        len2 = len(track2)

        if len1 > len2:
            # Pad track2
            padding = AudioSegment.silent(duration=len1 - len2, frame_rate=44100)
            padding = padding.set_channels(1)
            track2 = track2 + padding
        elif len2 > len1:
            # Pad track1
            padding = AudioSegment.silent(duration=len2 - len1, frame_rate=44100)
            padding = padding.set_channels(1)
            track1 = track1 + padding

        # Get raw sample data
        samples1 = array.array('h', track1.raw_data)
        samples2 = array.array('h', track2.raw_data)

        # Add samples together with clipping
        mixed_samples = array.array('h')
        for s1, s2 in zip(samples1, samples2):
            mixed = s1 + s2
            # Clip to 16-bit range
            if mixed > 32767:
                mixed = 32767
            elif mixed < -32768:
                mixed = -32768
            mixed_samples.append(mixed)

        # Create new AudioSegment from mixed samples
        mixed_audio = AudioSegment(
            data=mixed_samples.tobytes(),
            sample_width=2,  # 16-bit = 2 bytes
            frame_rate=44100,
            channels=1
        )

        logger.info(f"Mixed two tracks: {len(mixed_audio)}ms")

        return mixed_audio
