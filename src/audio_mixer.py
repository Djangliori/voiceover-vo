"""
Audio Mixing Module
Mixes original audio with Georgian voiceover, lowering original volume during speech
Uses ffmpeg for reliable audio processing
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

    def _get_ffmpeg_path(self):
        """Find ffmpeg binary"""
        import shutil

        # Check for Nix path first (Railway)
        nix_ffmpeg = '/nix/var/nix/profiles/default/bin/ffmpeg'
        if os.path.exists(nix_ffmpeg):
            return nix_ffmpeg

        # Try system PATH
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path

        # Try common locations
        for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']:
            if os.path.exists(path):
                return path

        raise Exception("ffmpeg not found")

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

        temp_dir = Path(output_path).parent
        ffmpeg_path = self._get_ffmpeg_path()

        if not voiceover_segments:
            # No voiceover, just export lowered original
            if progress_callback:
                progress_callback("Exporting audio...")

            cmd = [
                ffmpeg_path,
                '-i', original_audio_path,
                '-af', f'volume={self.original_volume}',
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-y',
                output_path
            ]
            subprocess.run(cmd, capture_output=True, check=True)

            if progress_callback:
                progress_callback("Audio mixing complete!")
            return output_path

        if progress_callback:
            progress_callback(f"Mixing {len(voiceover_segments)} voiceover segments...")

        # Strategy: Create a combined voiceover track first, then mix with original
        # This avoids the amix volume reduction issue by only using 2 inputs at final mix

        voiceover_track = temp_dir / f"voiceover_combined_{os.getpid()}.wav"

        try:
            # Step 1: Create combined voiceover track
            # We'll use Sox-style concatenation with silence padding
            # But since we have ffmpeg, we'll use a reliable approach:
            # Create each segment as a full-duration track with silence, then sum

            if progress_callback:
                progress_callback("Building voiceover timeline...")

            # For each segment, create a padded version and save it
            padded_segments = []
            for i, segment in enumerate(voiceover_segments):
                start_time = segment['start']
                segment_path = segment['audio_path']
                padded_path = temp_dir / f"padded_{os.getpid()}_{i}.wav"

                # Create a track that is: [silence for start_time] + [voiceover] + [silence to fill duration]
                # Using adelay to add silence at the start, then pad to full duration
                delay_ms = int(start_time * 1000)

                cmd = [
                    ffmpeg_path,
                    '-i', segment_path,
                    '-af', f'adelay={delay_ms}|{delay_ms},apad=whole_dur={duration}',
                    '-acodec', 'pcm_s16le',
                    '-ar', '44100',
                    '-ac', '1',
                    '-y',
                    str(padded_path)
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Failed to pad segment {i}: {result.stderr}")

                padded_segments.append(str(padded_path))

                if progress_callback and (i + 1) % 5 == 0:
                    progress_callback(f"Prepared {i + 1}/{len(voiceover_segments)} segments")

            if progress_callback:
                progress_callback("Combining voiceover segments...")

            # Step 2: Sum all padded segments together
            # Since they don't overlap (mostly), we can just add them
            # We'll do this by summing waveforms directly using ffmpeg's 'amix'
            # BUT with a key insight: use volume compensation

            # Build input args
            input_args = []
            for seg_path in padded_segments:
                input_args.extend(['-i', seg_path])

            # For N non-overlapping inputs, amix won't reduce volume much
            # But to be safe, we'll amplify by sqrt(N) after mixing
            num_segments = len(padded_segments)

            # Apply volume boost after amix to compensate
            # amix with normalize=0 should work, but as backup we boost
            volume_boost = 1.0  # Start with no boost, amix normalize=0 should preserve

            cmd = [
                ffmpeg_path,
                *input_args,
                '-filter_complex',
                f'amix=inputs={num_segments}:duration=longest:dropout_transition=0:normalize=0,volume={volume_boost}',
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-y',
                str(voiceover_track)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                # If amix fails, try alternative: sequential mixing
                if progress_callback:
                    progress_callback("Using alternative mixing method...")
                self._mix_sequential(padded_segments, str(voiceover_track), ffmpeg_path)

            # Clean up padded segments
            for seg_path in padded_segments:
                try:
                    Path(seg_path).unlink()
                except:
                    pass

            if progress_callback:
                progress_callback("Mixing with original audio...")

            # Step 3: Mix original (lowered) with voiceover track
            # Just 2 inputs = no volume issues!
            cmd = [
                ffmpeg_path,
                '-i', original_audio_path,
                '-i', str(voiceover_track),
                '-filter_complex',
                f'[0:a]volume={self.original_volume}[orig];[orig][1:a]amix=inputs=2:duration=longest:normalize=0',
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to mix audio: {result.stderr}")

            if progress_callback:
                progress_callback("Audio mixing complete!")

        finally:
            # Clean up
            if voiceover_track.exists():
                try:
                    voiceover_track.unlink()
                except:
                    pass

        return output_path

    def _mix_sequential(self, segment_paths, output_path, ffmpeg_path):
        """
        Alternative mixing method: mix segments two at a time
        This is slower but guaranteed to preserve volume
        """
        if len(segment_paths) == 0:
            return

        if len(segment_paths) == 1:
            # Just copy
            import shutil
            shutil.copy(segment_paths[0], output_path)
            return

        temp_dir = Path(output_path).parent
        current = segment_paths[0]

        for i, next_seg in enumerate(segment_paths[1:]):
            is_last = (i == len(segment_paths) - 2)
            out_path = output_path if is_last else str(temp_dir / f"mix_temp_{os.getpid()}_{i}.wav")

            cmd = [
                ffmpeg_path,
                '-i', current,
                '-i', next_seg,
                '-filter_complex', 'amix=inputs=2:duration=longest:normalize=0',
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-y',
                out_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Sequential mix failed at step {i}: {result.stderr}")

            # Clean up previous temp
            if i > 0 and Path(current).name.startswith('mix_temp_'):
                try:
                    Path(current).unlink()
                except:
                    pass

            current = out_path
