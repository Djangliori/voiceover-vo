"""
Audio Mixing Module
Mixes original audio with Georgian voiceover, lowering original volume during speech
Uses pydub for reliable audio overlay at specific timestamps
"""

import os
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

        Args:
            original_audio_path: Path to original audio WAV file
            voiceover_segments: List of segments with 'audio_path', 'start', 'end'
            output_path: Path for output mixed audio file
            progress_callback: Optional callback for progress updates

        Returns:
            Path to mixed audio file
        """
        if progress_callback:
            progress_callback("Loading original audio...")

        # Load original audio and normalize to 44.1kHz mono for consistency
        original = AudioSegment.from_wav(original_audio_path)

        # Ensure consistent format: 44.1kHz mono
        original = original.set_frame_rate(44100).set_channels(1)
        duration_ms = len(original)

        logger.info(f"Original audio duration: {duration_ms}ms")

        if progress_callback:
            progress_callback("Lowering original audio volume...")

        # Lower the original audio volume
        # pydub uses dB, so convert ratio to dB: dB = 20 * log10(ratio)
        import math
        if self.original_volume > 0:
            volume_db = 20 * math.log10(self.original_volume)
        else:
            volume_db = -60  # Effectively silent

        original_lowered = original + volume_db
        logger.info(f"Lowered original audio by {volume_db:.1f}dB")

        if not voiceover_segments:
            # No voiceover, just export lowered original
            if progress_callback:
                progress_callback("Exporting audio...")

            original_lowered.export(output_path, format="wav")

            if progress_callback:
                progress_callback("Audio mixing complete!")
            return output_path

        if progress_callback:
            progress_callback(f"Mixing {len(voiceover_segments)} voiceover segments...")

        # Build the voiceover track by placing each segment at its timestamp
        # We'll construct this by concatenating: silence + segment + silence + segment...
        # This avoids any overlay operations that might affect volume

        logger.info(f"Building voiceover track from {len(voiceover_segments)} segments")

        # Sort segments by start time to ensure correct order
        sorted_segments = sorted(voiceover_segments, key=lambda s: s['start'])

        # Build the voiceover track piece by piece
        # Use consistent format: 44.1kHz mono
        voiceover_track = AudioSegment.silent(duration=0, frame_rate=44100)
        voiceover_track = voiceover_track.set_channels(1)
        current_position_ms = 0

        for i, segment in enumerate(sorted_segments):
            start_time = segment['start']
            segment_path = segment['audio_path']
            start_ms = int(start_time * 1000)

            try:
                # Load the voiceover segment and normalize format
                voiceover_clip = AudioSegment.from_wav(segment_path)
                voiceover_clip = voiceover_clip.set_frame_rate(44100).set_channels(1)

                # Apply volume adjustment if needed
                if self.voiceover_volume != 1.0 and self.voiceover_volume > 0:
                    vo_volume_db = 20 * math.log10(self.voiceover_volume)
                    voiceover_clip = voiceover_clip + vo_volume_db

                # Add silence from current position to this segment's start
                if start_ms > current_position_ms:
                    silence_duration = start_ms - current_position_ms
                    silence = AudioSegment.silent(duration=silence_duration, frame_rate=44100)
                    silence = silence.set_channels(1)
                    voiceover_track += silence
                    current_position_ms = start_ms

                # Add the voiceover segment
                voiceover_track += voiceover_clip
                current_position_ms += len(voiceover_clip)

                logger.debug(f"Added segment {i} at {start_ms}ms (duration: {len(voiceover_clip)}ms)")

            except Exception as e:
                logger.error(f"Failed to add segment {i}: {e}")
                raise

            if progress_callback and (i + 1) % 5 == 0:
                progress_callback(f"Positioned {i + 1}/{len(voiceover_segments)} voiceover segments")

        # Pad with silence to match original duration if needed
        if len(voiceover_track) < duration_ms:
            padding = AudioSegment.silent(duration=duration_ms - len(voiceover_track), frame_rate=44100)
            padding = padding.set_channels(1)
            voiceover_track += padding

        logger.info(f"Voiceover track built: {len(voiceover_track)}ms")

        if progress_callback:
            progress_callback("Combining audio tracks...")

        # Now mix the lowered original with the voiceover track
        # This is just ONE overlay operation - no volume reduction issue
        final_mix = original_lowered.overlay(voiceover_track)

        if progress_callback:
            progress_callback("Exporting mixed audio...")

        # Export the final mix
        final_mix.export(output_path, format="wav")

        logger.info(f"Audio mixing complete: {output_path}")

        if progress_callback:
            progress_callback("Audio mixing complete!")

        return output_path
