"""
YouTube Video Downloader Module
Downloads YouTube videos using RapidAPI only
Version: 3.0.0 - RapidAPI only (no yt-dlp dependency)
"""

import os
import re
import requests
from pathlib import Path


class VideoDownloader:
    def __init__(self, temp_dir="temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.rapidapi_key = os.getenv('RAPIDAPI_KEY')

        if not self.rapidapi_key:
            raise ValueError("RAPIDAPI_KEY environment variable is required")

    def download_video(self, url, progress_callback=None):
        """
        Download YouTube video and extract audio using RapidAPI only

        Args:
            url: YouTube video URL
            progress_callback: Optional callback function for progress updates

        Returns:
            dict with video_path, audio_path, title, duration

        Raises:
            Exception: If download fails or API quota is exceeded
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Starting download for URL: {url}")
        logger.info("Using RapidAPI for download")

        if progress_callback:
            progress_callback("Fetching video info from RapidAPI...")

        # Extract video ID from URL
        video_id = self._extract_video_id_from_url(url)
        logger.info(f"Extracted video ID: {video_id}")

        video_path = self.temp_dir / f"{video_id}.mp4"
        audio_path = self.temp_dir / f"{video_id}_audio.wav"
        logger.info(f"Video path: {video_path}, Audio path: {audio_path}")

        # Call RapidAPI to get download link
        # Using YouTube Media Downloader API
        rapidapi_url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
        headers = {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": "youtube-media-downloader.p.rapidapi.com"
        }
        params = {"videoId": video_id}

        logger.info("Fetching video details from RapidAPI...")

        try:
            response = requests.get(rapidapi_url, headers=headers, params=params, timeout=30)

            # Handle rate limiting specifically
            if response.status_code == 429:
                error_msg = "RapidAPI quota exceeded. Please check your API limits or upgrade your plan."
                logger.error(error_msg)
                if progress_callback:
                    progress_callback(f"Error: {error_msg}")
                raise Exception(error_msg)

            # Handle other HTTP errors
            if response.status_code != 200:
                error_msg = f"RapidAPI error: HTTP {response.status_code}"
                logger.error(error_msg)
                raise Exception(error_msg)

            data = response.json()

            # Check for API-level errors
            if 'error' in data:
                error_msg = f"RapidAPI error: {data.get('error', 'Unknown error')}"
                logger.error(error_msg)
                raise Exception(error_msg)

            if not data.get('videos'):
                raise Exception("No video formats available from RapidAPI. Video may be unavailable or private.")

            # Get video info - handle both DataFanatic and other API formats
            title = data.get('title', 'Unknown')

            # Try lengthSeconds first (DataFanatic), then duration (other APIs)
            duration = data.get('lengthSeconds')
            if duration is None:
                duration_str = data.get('duration', '0')
                duration = int(duration_str) if duration_str and str(duration_str).isdigit() else 0
            else:
                duration = int(duration) if duration else 0

            logger.info(f"Video info: {title} (duration: {duration}s)")

            # Check if we got valid data
            if not title or title == 'Unknown':
                logger.warning(f"Could not get video title, using video ID: {video_id}")
                title = f"Video {video_id}"

            # Find best quality MP4 video
            videos = data.get('videos', [])

            if not videos:
                raise Exception("No video formats available from RapidAPI")

            # Handle different response formats from RapidAPI
            if videos and isinstance(videos[0], str):
                # If videos is a list of strings (URLs), use the first one
                download_url = videos[0]
                logger.info(f"Using first available video URL")
            else:
                # If videos is a list of objects, find best quality
                # DataFanatic API uses 'quality' field like '720p', '1080p'
                valid_videos = [v for v in videos if isinstance(v, dict) and v.get('url')]

                if not valid_videos:
                    raise Exception("No valid video formats found in API response")

                # Get highest quality video
                best_video = max(valid_videos, key=lambda v: int(v.get('quality', '0').rstrip('p') or '0'))
                download_url = best_video['url']
                logger.info(f"Selected quality: {best_video.get('quality', 'unknown')}")

            if progress_callback:
                if isinstance(videos[0], str):
                    progress_callback(f"Downloading video...")
                else:
                    progress_callback(f"Downloading video ({best_video.get('quality', 'unknown')})...")

            # Download video file
            logger.info(f"Downloading from: {download_url[:100]}...")
            video_response = requests.get(download_url, stream=True, timeout=60)
            video_response.raise_for_status()

            total_size = int(video_response.headers.get('content-length', 0))
            downloaded = 0

            with open(video_path, 'wb') as f:
                for chunk in video_response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            percent = (downloaded / total_size) * 100
                            progress_callback(f"Downloading... {percent:.1f}% ({downloaded//1024//1024}MB/{total_size//1024//1024}MB)")

            logger.info("Video download complete")

            # Extract audio
            if progress_callback:
                progress_callback("Extracting audio...")

            self._extract_audio(video_path, audio_path)
            logger.info("Audio extraction complete")

            return {
                'video_path': str(video_path),
                'audio_path': str(audio_path),
                'title': title,
                'duration': duration,
                'video_id': video_id
            }

        except requests.Timeout:
            error_msg = "Request to RapidAPI timed out. Please try again."
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.RequestException as e:
            error_msg = f"Network error while contacting RapidAPI: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            # Re-raise with more context if needed
            if "quota" in str(e).lower() or "429" in str(e):
                raise Exception("API quota exceeded. Please check your RapidAPI subscription.")
            raise

    def _extract_video_id_from_url(self, url):
        """Extract video ID from YouTube URL using regex"""
        # Handle various YouTube URL formats
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)',
            r'youtube\.com/embed/([^&\n?#]+)',
            r'youtube\.com/v/([^&\n?#]+)',
            r'youtube\.com/shorts/([^&\n?#]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # If no pattern matches, raise error
        raise ValueError(f"Could not extract video ID from URL: {url}")

    def _extract_audio(self, video_path, audio_path):
        """Extract audio from video using ffmpeg"""
        import subprocess
        import logging
        import shutil
        logger = logging.getLogger(__name__)

        logger.info(f"Running ffmpeg to extract audio from {video_path}")

        # Find ffmpeg - check Nix path first (Railway), then system PATH
        # Try Nix path first (Railway environment)
        nix_ffmpeg = '/nix/var/nix/profiles/default/bin/ffmpeg'
        if os.path.exists(nix_ffmpeg):
            ffmpeg_path = nix_ffmpeg
            logger.info(f"Found ffmpeg at Nix path: {ffmpeg_path}")
        else:
            # Try system PATH
            ffmpeg_path = shutil.which('ffmpeg')

            if not ffmpeg_path:
                # Try other common locations
                possible_paths = [
                    '/usr/bin/ffmpeg',          # Standard Linux
                    '/usr/local/bin/ffmpeg',    # Homebrew/manual install
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