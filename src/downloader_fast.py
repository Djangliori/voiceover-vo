"""
YouTube Video Downloader Module - FAST Downloader 24/7 Implementation
Downloads YouTube videos using YouTube Video FAST Downloader 24/7 API
Version: 1.0.0 - Alternative to DataFanatic with better reliability
"""

import os
import re
import json
import requests
from pathlib import Path


class FastVideoDownloader:
    def __init__(self, temp_dir="temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.rapidapi_key = os.getenv('RAPIDAPI_KEY')

        if not self.rapidapi_key:
            raise ValueError("RAPIDAPI_KEY environment variable is required")

    def download_video(self, url, progress_callback=None):
        """
        Download YouTube video using FAST Downloader 24/7 API

        Args:
            url: YouTube video URL
            progress_callback: Optional callback function for progress updates

        Returns:
            dict with video_path, audio_path, title, duration
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Starting download with FAST Downloader 24/7 for URL: {url}")

        if progress_callback:
            progress_callback("Fetching video info from FAST API...")

        # Extract video ID from URL
        video_id = self._extract_video_id_from_url(url)
        logger.info(f"Extracted video ID: {video_id}")

        video_path = self.temp_dir / f"{video_id}.mp4"
        audio_path = self.temp_dir / f"{video_id}_audio.wav"

        try:
            # Step 1: Get video info and download links
            info_url = f"https://youtube-video-fast-downloader-24-7.p.rapidapi.com/get-videos-info/{video_id}"

            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "youtube-video-fast-downloader-24-7.p.rapidapi.com"
            }

            logger.info("Fetching video info from FAST API...")
            response = requests.get(info_url, headers=headers, timeout=30)

            # Handle rate limiting
            if response.status_code == 429:
                error_msg = "RapidAPI quota exceeded. Please check your API limits."
                logger.error(error_msg)
                raise Exception(error_msg)

            # Handle other errors
            if response.status_code != 200:
                error_msg = f"FAST API error: HTTP {response.status_code}"
                logger.error(f"{error_msg}. Response: {response.text}")
                raise Exception(error_msg)

            data = response.json()
            logger.info(f"API Response structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")

            # Parse the response - FAST API returns different structure
            if not data or (isinstance(data, dict) and data.get('error')):
                error_msg = data.get('error', 'Unknown error') if isinstance(data, dict) else 'Invalid response'
                raise Exception(f"FAST API error: {error_msg}")

            # Extract video info based on FAST API response structure
            # The API typically returns format like: { "title": "...", "formats": [...], "duration": ... }
            title = "Unknown"
            duration = 0
            download_url = None

            if isinstance(data, dict):
                # Get title
                title = data.get('title', data.get('videoDetails', {}).get('title', 'Unknown'))

                # Get duration (might be in seconds or string format)
                duration = data.get('duration', data.get('lengthSeconds', 0))
                if isinstance(duration, str):
                    duration = int(duration) if duration.isdigit() else 0

                # Find best quality video URL
                formats = data.get('formats', [])
                if not formats and 'videos' in data:
                    formats = data.get('videos', [])

                if formats:
                    # Sort by quality and get best MP4
                    mp4_formats = [f for f in formats if isinstance(f, dict) and
                                 ('mp4' in f.get('mimeType', '').lower() or
                                  f.get('ext') == 'mp4' or
                                  'video/mp4' in f.get('type', ''))]

                    if mp4_formats:
                        # Try to sort by quality/resolution
                        def get_quality_score(fmt):
                            # Try different quality indicators
                            if 'quality' in fmt:
                                q = fmt['quality']
                                if isinstance(q, str) and q.endswith('p'):
                                    return int(q[:-1])
                                return int(q) if str(q).isdigit() else 0
                            if 'height' in fmt:
                                return int(fmt['height'])
                            if 'resolution' in fmt:
                                res = fmt['resolution']
                                if isinstance(res, str) and 'x' in res:
                                    return int(res.split('x')[1])
                            return 0

                        best_format = max(mp4_formats, key=get_quality_score, default=mp4_formats[0])
                        download_url = best_format.get('url')

                        quality = best_format.get('quality', best_format.get('qualityLabel', 'unknown'))
                        logger.info(f"Selected video quality: {quality}")
                    else:
                        # Fall back to any video format
                        if formats:
                            download_url = formats[0].get('url') if isinstance(formats[0], dict) else formats[0]

                # Alternative: Check if direct download links are provided
                if not download_url and 'downloadUrl' in data:
                    download_url = data['downloadUrl']
                elif not download_url and 'url' in data:
                    download_url = data['url']

            if not download_url:
                raise Exception("No download URL found in FAST API response")

            logger.info(f"Video info: {title} (duration: {duration}s)")

            # Step 2: Download the video
            if progress_callback:
                progress_callback("Downloading video...")

            logger.info(f"Downloading from URL: {download_url[:100]}...")
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

            # Step 3: Extract audio using ffmpeg
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
            error_msg = "Request to FAST API timed out"
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            raise

    def _extract_video_id_from_url(self, url):
        """Extract video ID from YouTube URL"""
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

        raise ValueError(f"Could not extract video ID from URL: {url}")

    def _extract_audio(self, video_path, audio_path):
        """Extract audio from video using ffmpeg"""
        import subprocess
        import logging
        import shutil
        logger = logging.getLogger(__name__)

        logger.info(f"Extracting audio from {video_path}")

        # Find ffmpeg
        nix_ffmpeg = '/nix/var/nix/profiles/default/bin/ffmpeg'
        if os.path.exists(nix_ffmpeg):
            ffmpeg_path = nix_ffmpeg
        else:
            ffmpeg_path = shutil.which('ffmpeg')
            if not ffmpeg_path:
                possible_paths = ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']
                for path in possible_paths:
                    if os.path.exists(path):
                        ffmpeg_path = path
                        break

        if not ffmpeg_path:
            raise Exception("ffmpeg not found")

        cmd = [
            ffmpeg_path,
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            str(audio_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr}")
            raise Exception(f"Failed to extract audio: {result.stderr}")

        logger.info("Audio extracted successfully")

    def cleanup(self, video_id):
        """Clean up temporary files"""
        files_to_remove = [
            self.temp_dir / f"{video_id}.mp4",
            self.temp_dir / f"{video_id}_audio.wav",
            self.temp_dir / f"{video_id}_mixed.wav",
            self.temp_dir / f"{video_id}_voiceover.wav",
        ]

        for file in files_to_remove:
            if file.exists():
                file.unlink()