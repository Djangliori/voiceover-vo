"""
Audio Mixing Module
Mixes original audio with Georgian voiceover, lowering original volume during speech
Uses ffmpeg-python for efficient, Python-version-independent audio processing
"""

import os
import ffmpeg
from pathlib import Path
import subprocess


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
        Mix original audio with Georgian voiceover using ffmpeg

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

        # Get original audio duration
        probe = ffmpeg.probe(original_audio_path)
        duration = float(probe['streams'][0]['duration'])

        if progress_callback:
            progress_callback("Lowering original audio volume...")

        # Start with original audio with lowered volume
        original = ffmpeg.input(original_audio_path)
        # Apply volume filter to lower original audio
        original_lowered = original.audio.filter('volume', self.original_volume)

        if not voiceover_segments:
            # No voiceover, just export lowered original
            if progress_callback:
                progress_callback("Exporting audio...")

            output = ffmpeg.output(original_lowered, output_path, acodec='pcm_s16le', ar='44100')
            ffmpeg.run(output, overwrite_output=True, quiet=True)

            if progress_callback:
                progress_callback("Audio mixing complete!")
            return output_path

        if progress_callback:
            progress_callback(f"Mixing {len(voiceover_segments)} voiceover segments...")

        # Create temp file for intermediate mixing
        temp_dir = Path(output_path).parent
        temp_mixed = temp_dir / f"temp_mixed_{os.getpid()}.wav"

        try:
            # Build complex filter for overlaying all voiceover segments
            # Strategy: overlay segments one by one using amerge and amix

            current_audio = original_lowered

            for i, segment in enumerate(voiceover_segments):
                start_time = segment['start']
                voiceover_path = segment['audio_path']

                # Load voiceover segment
                voiceover = ffmpeg.input(voiceover_path)

                # Apply volume to voiceover if needed
                if self.voiceover_volume != 1.0:
                    voiceover_audio = voiceover.audio.filter('volume', self.voiceover_volume)
                else:
                    voiceover_audio = voiceover.audio

                # Add delay to voiceover to position it at correct timestamp
                voiceover_delayed = voiceover_audio.filter('adelay', f'{int(start_time * 1000)}|{int(start_time * 1000)}')

                # Mix current audio with this voiceover segment
                # Use amix to overlay the voiceover on top of current audio
                current_audio = ffmpeg.filter([current_audio, voiceover_delayed], 'amix', inputs=2, duration='longest')

                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(f"Mixed {i + 1}/{len(voiceover_segments)} segments")

            if progress_callback:
                progress_callback("Exporting mixed audio...")

            # Output final mixed audio
            output = ffmpeg.output(current_audio, output_path, acodec='pcm_s16le', ar='44100')
            ffmpeg.run(output, overwrite_output=True, quiet=True)

        finally:
            # Clean up temp file if it exists
            if temp_mixed.exists():
                temp_mixed.unlink()

        if progress_callback:
            progress_callback("Audio mixing complete!")

        return output_path
