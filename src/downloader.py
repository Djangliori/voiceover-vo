"""
YouTube Video Downloader Module
Downloads YouTube videos using YouTube Video FAST Downloader 24/7 API
Version: 4.0.1 - Switched to FAST API for better reliability
"""

import os
import re
import requests
from pathlib import Path
from src.logging_config import get_logger

logger = get_logger(__name__)


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
        logger.info(f"Starting download for URL: {url}")
        logger.info("Using YouTube Video FAST Downloader 24/7 API")

        if progress_callback:
            progress_callback("Fetching video info from FAST API...")

        # Extract video ID from URL
        video_id = self._extract_video_id_from_url(url)
        logger.info(f"Extracted video ID: {video_id}")

        video_path = self.temp_dir / f"{video_id}.mp4"
        audio_path = self.temp_dir / f"{video_id}_audio.wav"
        logger.info(f"Video path: {video_path}, Audio path: {audio_path}")

        # Call RapidAPI to get download link
        # Using YouTube Video FAST Downloader 24/7 API
        rapidapi_url = f"https://youtube-video-fast-downloader-24-7.p.rapidapi.com/get-videos-info/{video_id}"
        headers = {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": "youtube-video-fast-downloader-24-7.p.rapidapi.com"
        }
        # FAST API uses path parameter, not query params
        params = {}

        logger.info("Fetching video details from RapidAPI...")

        try:
            # Use session with proper cleanup
            with requests.Session() as session:
                response = session.get(rapidapi_url, headers=headers, params=params, timeout=30)

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

            # FAST API returns different structure than DataFanatic
            # Check for formats or videos array
            formats = data.get('formats', [])
            if not formats and 'videos' in data:
                formats = data.get('videos', [])

            if not formats:
                raise Exception("No video formats available from FAST API. Video may be unavailable or private.")

            # Get video info - FAST API structure
            title = data.get('title', data.get('videoDetails', {}).get('title', 'Unknown'))

            # Get duration from various possible fields
            duration = data.get('duration', data.get('lengthSeconds', 0))
            if isinstance(duration, str) and duration.isdigit():
                duration = int(duration)
            elif not isinstance(duration, int):
                duration = 0

            logger.info(f"Video info: {title} (duration: {duration}s)")

            # Check if we got valid data
            if not title or title == 'Unknown':
                logger.warning(f"Could not get video title, using video ID: {video_id}")
                title = f"Video {video_id}"

            # Find best quality MP4 video from formats
            videos = formats

            if not videos:
                raise Exception("No video formats available from RapidAPI")

            # Handle FAST API response format
            if videos and isinstance(videos[0], str):
                # If videos is a list of strings (URLs), use the first one
                download_url = videos[0]
                logger.info(f"Using first available video URL")
                best_video = {'quality': 'default'}
            else:
                # FAST API returns format objects with different fields
                # Look for MP4 formats with video
                mp4_formats = []
                for f in videos:
                    if isinstance(f, dict):
                        # Check if it's a video format (not audio-only)
                        has_video = (
                            f.get('vcodec') != 'none' and
                            f.get('height') is not None
                        )
                        # Check if it's MP4 or compatible
                        is_mp4 = (
                            'mp4' in str(f.get('ext', '')).lower() or
                            'mp4' in str(f.get('container', '')).lower() or
                            'video/mp4' in str(f.get('mimeType', '')).lower()
                        )
                        if has_video and f.get('url'):
                            mp4_formats.append(f)

                if not mp4_formats:
                    # Fallback to any format with URL
                    valid_videos = [v for v in videos if isinstance(v, dict) and v.get('url')]
                    if not valid_videos:
                        raise Exception("No valid video formats found in FAST API response")
                    mp4_formats = valid_videos

                # Get highest quality video
                def get_quality_score(fmt):
                    # Try multiple quality indicators
                    if 'height' in fmt:
                        return int(fmt['height'])
                    if 'quality' in fmt:
                        q = str(fmt['quality'])
                        if q.endswith('p'):
                            return int(q[:-1])
                        if q.isdigit():
                            return int(q)
                    if 'qualityLabel' in fmt:
                        q = str(fmt['qualityLabel'])
                        if q[:-1].isdigit():
                            return int(q[:-1])
                    return 0

                best_video = max(mp4_formats, key=get_quality_score, default=mp4_formats[0])
                download_url = best_video.get('url')

                quality_label = (best_video.get('qualityLabel') or
                               best_video.get('quality') or
                               f"{best_video.get('height', 'unknown')}p")
                logger.info(f"Selected quality: {quality_label}")

            if progress_callback:
                if isinstance(videos[0], str):
                    progress_callback(f"Downloading video...")
                else:
                    quality_str = (best_video.get('qualityLabel') or
                                 best_video.get('quality') or
                                 f"{best_video.get('height', 'unknown')}p")
                    progress_callback(f"Downloading video ({quality_str})...")

            # Download video file with proper session management
            logger.info(f"Downloading from: {download_url[:100]}...")

            with requests.Session() as download_session:
                video_response = download_session.get(download_url, stream=True, timeout=60)
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
        """Extract video ID from YouTube URL using consolidated function"""
        from src.validators import extract_video_id
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError(f"Could not extract video ID from URL: {url}")
        return video_id

    def _extract_audio(self, video_path, audio_path):
        """Extract audio from video using ffmpeg"""
        import subprocess
        import shutil

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