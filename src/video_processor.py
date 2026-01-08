"""
Video Processing Module
Combines mixed audio with original video to create final output
"""

import subprocess
from pathlib import Path
from src.ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path


class VideoProcessor:
    def __init__(self, output_dir="output"):
        """Initialize video processor"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def combine_video_audio(self, video_path, audio_path, output_filename, progress_callback=None):
        """
        Combine video with new audio track

        Args:
            video_path: Path to original video file
            audio_path: Path to mixed audio file
            output_filename: Desired output filename
            progress_callback: Optional callback for progress updates

        Returns:
            Path to final video file
        """
        if progress_callback:
            progress_callback("Combining video with Georgian voiceover...")

        output_path = self.output_dir / output_filename

        # Use ffmpeg to replace audio track
        cmd = [
            get_ffmpeg_path(),
            '-i', str(video_path),
            '-i', str(audio_path),
            '-c:v', 'copy',  # Copy video stream (no re-encoding)
            '-c:a', 'aac',   # Encode audio to AAC
            '-b:a', '192k',  # Audio bitrate
            '-map', '0:v:0', # Use video from first input
            '-map', '1:a:0', # Use audio from second input
            '-shortest',     # Match shortest stream duration
            '-y',            # Overwrite output file
            str(output_path)
        ]

        if progress_callback:
            progress_callback("Running ffmpeg (this may take a minute)...")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"Failed to combine video and audio: {result.stderr}")

        if progress_callback:
            progress_callback(f"Video processing complete! Saved to: {output_path}")

        return str(output_path)

    def get_video_info(self, video_path):
        """
        Get video information using ffprobe

        Args:
            video_path: Path to video file

        Returns:
            Dict with video duration, resolution, etc.
        """
        cmd = [
            get_ffprobe_path(),
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(video_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"Failed to get video info: {result.stderr}")

        import json
        return json.loads(result.stdout)
