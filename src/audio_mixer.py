"""
Audio Mixing Module
Mixes original audio with Georgian voiceover, lowering original volume during speech
"""

import os
from pydub import AudioSegment
from pathlib import Path


class AudioMixer:
    def __init__(self, original_volume=0.3, voiceover_volume=1.0):
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
        Mix original audio with Georgian voiceover

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

        # Load original audio
        original_audio = AudioSegment.from_wav(original_audio_path)
        original_duration_ms = len(original_audio)

        if progress_callback:
            progress_callback("Lowering original audio volume...")

        # Lower the volume of original audio
        original_audio_lowered = original_audio + (20 * (self.original_volume - 1))  # dB adjustment

        # Start with the lowered original audio
        mixed_audio = original_audio_lowered

        if progress_callback:
            progress_callback(f"Mixing {len(voiceover_segments)} voiceover segments...")

        # Overlay each voiceover segment at its timestamp
        for i, segment in enumerate(voiceover_segments):
            start_time_ms = int(segment['start'] * 1000)

            # Load voiceover audio
            voiceover_audio = AudioSegment.from_wav(segment['audio_path'])

            # Adjust voiceover volume
            if self.voiceover_volume != 1.0:
                voiceover_audio = voiceover_audio + (20 * (self.voiceover_volume - 1))

            # Check if we're within bounds
            if start_time_ms < original_duration_ms:
                # Overlay voiceover on top of original audio
                mixed_audio = mixed_audio.overlay(voiceover_audio, position=start_time_ms)

            if progress_callback and (i + 1) % 10 == 0:
                progress_callback(f"Mixed {i + 1}/{len(voiceover_segments)} segments")

        if progress_callback:
            progress_callback("Exporting mixed audio...")

        # Export mixed audio
        mixed_audio.export(output_path, format='wav')

        if progress_callback:
            progress_callback("Audio mixing complete!")

        return output_path

    def create_voiceover_only(self, voiceover_segments, output_path, progress_callback=None):
        """
        Create a single audio file with all voiceover segments at their correct timestamps
        (Alternative approach - voiceover only without original audio)

        Args:
            voiceover_segments: List of segments with 'audio_path', 'start', 'end'
            output_path: Path for output audio file
            progress_callback: Optional callback for progress updates

        Returns:
            Path to voiceover-only audio file
        """
        if not voiceover_segments:
            raise ValueError("No voiceover segments provided")

        if progress_callback:
            progress_callback("Creating voiceover-only audio...")

        # Find total duration needed
        last_segment = max(voiceover_segments, key=lambda x: x['end'])
        total_duration_ms = int(last_segment['end'] * 1000) + 5000  # Add 5 seconds padding

        # Create silent audio
        silent_audio = AudioSegment.silent(duration=total_duration_ms)

        # Overlay each voiceover segment
        for i, segment in enumerate(voiceover_segments):
            start_time_ms = int(segment['start'] * 1000)
            voiceover_audio = AudioSegment.from_wav(segment['audio_path'])

            # Adjust volume
            if self.voiceover_volume != 1.0:
                voiceover_audio = voiceover_audio + (20 * (self.voiceover_volume - 1))

            silent_audio = silent_audio.overlay(voiceover_audio, position=start_time_ms)

            if progress_callback and (i + 1) % 10 == 0:
                progress_callback(f"Added {i + 1}/{len(voiceover_segments)} segments")

        # Export
        silent_audio.export(output_path, format='wav')

        if progress_callback:
            progress_callback("Voiceover-only audio complete!")

        return output_path
