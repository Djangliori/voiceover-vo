"""
YouTube Video Downloader Module
Downloads YouTube videos and extracts audio using yt-dlp
"""

import os
import yt_dlp
from pathlib import Path


class VideoDownloader:
    def __init__(self, temp_dir="temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)

    def download_video(self, url, progress_callback=None):
        """
        Download YouTube video and extract audio

        Args:
            url: YouTube video URL
            progress_callback: Optional callback function for progress updates

        Returns:
            dict with video_path, audio_path, title, duration
        """
        video_id = self._extract_video_id(url)
        video_path = self.temp_dir / f"{video_id}.mp4"
        audio_path = self.temp_dir / f"{video_id}_audio.wav"

        # Create progress hook for yt-dlp that reports detailed download progress
        def ytdlp_progress_hook(d):
            if progress_callback and d['status'] == 'downloading':
                try:
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    if total > 0:
                        percent = (downloaded / total) * 100
                        speed = d.get('speed', 0)
                        speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else "? MB/s"
                        progress_callback(f"Downloading... {percent:.1f}% ({downloaded//1024//1024}MB/{total//1024//1024}MB) @ {speed_str}")
                    else:
                        progress_callback(f"Downloading... {downloaded//1024//1024}MB")
                except Exception:
                    pass

        # Download options - tell yt-dlp where to find ffmpeg
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Simplified - works with ffmpeg available
            'outtmpl': str(video_path),
            'quiet': False,
            'no_warnings': False,
            'http_chunk_size': 10485760,  # 10MB chunks
            'retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 3,
            'ffmpeg_location': '/usr/bin',  # Help yt-dlp find ffmpeg
        }

        if progress_callback:
            ydl_opts['progress_hooks'] = [ytdlp_progress_hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)

            # Extract audio using ffmpeg
            self._extract_audio(video_path, audio_path)

            return {
                'video_path': str(video_path),
                'audio_path': str(audio_path),
                'title': title,
                'duration': duration,
                'video_id': video_id
            }

        except Exception as e:
            raise Exception(f"Failed to download video: {str(e)}")

    def _extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('id', 'video')

    def _extract_audio(self, video_path, audio_path):
        """Extract audio from video using ffmpeg"""
        import subprocess

        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate (good for speech recognition)
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            str(audio_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to extract audio: {result.stderr}")

    def cleanup(self, video_id):
        """Clean up temporary files for a video"""
        files_to_remove = [
            self.temp_dir / f"{video_id}.mp4",
            self.temp_dir / f"{video_id}_audio.wav",
            self.temp_dir / f"{video_id}_mixed.wav",
            self.temp_dir / f"{video_id}_voiceover.wav",
        ]

        for file in files_to_remove:
            if file.exists():
                file.unlink()

        # Also clean up all segment files (segment_0000.wav, segment_0001.wav, etc.)
        for segment_file in self.temp_dir.glob("segment_*.wav"):
            try:
                segment_file.unlink()
            except Exception:
                pass  # Ignore errors for individual segment cleanup

        # Clean up any other temporary files like temp_mixed_*.wav from audio_mixer
        for temp_mixed_file in self.temp_dir.glob("temp_mixed_*.wav"):
            try:
                temp_mixed_file.unlink()
            except Exception:
                pass
