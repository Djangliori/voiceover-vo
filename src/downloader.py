"""
YouTube Video Downloader Module
Downloads YouTube videos and extracts audio using yt-dlp
Version: 1.0.1 - Fixed ffmpeg path detection for Railway/Nix
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
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Starting download for URL: {url}")
        video_id = self._extract_video_id(url)
        logger.info(f"Extracted video ID: {video_id}")

        video_path = self.temp_dir / f"{video_id}.mp4"
        audio_path = self.temp_dir / f"{video_id}_audio.wav"
        logger.info(f"Video path: {video_path}, Audio path: {audio_path}")

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

        # Download options - flexible format selector that works with all videos
        ydl_opts = {
            # Format priority: best quality video+audio, falling back to whatever works
            # This will use ffmpeg to merge if needed (now available in PATH)
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'outtmpl': str(video_path),
            'quiet': False,
            'no_warnings': False,
            'http_chunk_size': 10485760,  # 10MB chunks
            'retries': 10,
            'fragment_retries': 10,
            'extractor_retries': 3,
            'ffmpeg_location': '/usr/bin',  # Tell yt-dlp where ffmpeg is
            # Bypass YouTube bot detection - use multiple strategies
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web'],  # Try multiple clients
                    'skip': ['hls', 'dash'],  # Skip formats that might trigger bot detection
                }
            },
            # Spoof user agent to look like a real browser
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'nocheckcertificate': True,
        }

        if progress_callback:
            ydl_opts['progress_hooks'] = [ytdlp_progress_hook]

        try:
            logger.info("Creating YoutubeDL instance with format selector")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("Extracting video info...")
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                logger.info(f"Video downloaded successfully: {title} (duration: {duration}s)")

            # Extract audio using ffmpeg
            logger.info("Extracting audio from video...")
            self._extract_audio(video_path, audio_path)
            logger.info("Audio extraction complete")

            return {
                'video_path': str(video_path),
                'audio_path': str(audio_path),
                'title': title,
                'duration': duration,
                'video_id': video_id
            }

        except Exception as e:
            logger.error(f"Download failed with error: {str(e)}", exc_info=True)
            raise Exception(f"Failed to download video: {str(e)}")

    def _extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('id', 'video')

    def _extract_audio(self, video_path, audio_path):
        """Extract audio from video using ffmpeg"""
        import subprocess
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Running ffmpeg to extract audio from {video_path}")

        # Find ffmpeg - try multiple locations and verify they exist
        import shutil
        ffmpeg_path = shutil.which('ffmpeg')

        if not ffmpeg_path:
            # Try common installation paths (check if file actually exists)
            possible_paths = [
                '/nix/var/nix/profiles/default/bin/ffmpeg',  # Railway/Nix
                '/usr/bin/ffmpeg',                            # Standard Linux
                '/usr/local/bin/ffmpeg',                      # Homebrew/manual install
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    ffmpeg_path = path
                    logger.info(f"Found ffmpeg at: {path}")
                    break

        if not ffmpeg_path:
            raise Exception("ffmpeg not found in PATH or common locations. Install ffmpeg or add it to PATH.")

        logger.info(f"Using ffmpeg at: {ffmpeg_path}")

        cmd = [
            ffmpeg_path,
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate (good for speech recognition)
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            str(audio_path)
        ]

        logger.info(f"ffmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"ffmpeg failed with return code {result.returncode}")
            logger.error(f"ffmpeg stderr: {result.stderr}")
            raise Exception(f"Failed to extract audio: {result.stderr}")
        else:
            logger.info(f"Audio extracted successfully to {audio_path}")

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
