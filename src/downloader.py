"""
YouTube Video Downloader Module
Downloads YouTube videos using YouTube Media Downloader (DataFanatic) API
Version: 6.0.0 - Parallel audio + video download for faster processing
"""

import os
import re
import time
import threading
import requests
from pathlib import Path
from src.logging_config import get_logger
from src.api_tracker import api_tracker

logger = get_logger(__name__)

# Rate limiting for API calls
LAST_API_CALL_TIME = 0
MIN_TIME_BETWEEN_CALLS = 2  # Minimum 2 seconds between API calls


class VideoDownloader:
    def __init__(self, temp_dir="temp"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.rapidapi_key = os.getenv('RAPIDAPI_KEY')

        if not self.rapidapi_key:
            raise ValueError("RAPIDAPI_KEY environment variable is required")

        # Parallel download state
        self._video_download_thread = None
        self._video_download_error = None
        self._video_download_complete = threading.Event()

    def download_video(self, url, progress_callback=None):
        """
        Download YouTube video and extract audio using RapidAPI.
        Uses parallel download: audio-only stream downloads first (smaller),
        video stream downloads in background while audio processing starts.

        Args:
            url: YouTube video URL
            progress_callback: Optional callback function for progress updates

        Returns:
            dict with video_path, audio_path, title, duration, video_id

        Raises:
            Exception: If download fails or API quota is exceeded
        """
        logger.info(f"Starting parallel download for URL: {url}")
        logger.info("Using YouTube Media Downloader (DataFanatic) API with parallel streams")

        if progress_callback:
            progress_callback("Fetching video info from RapidAPI...")

        # Extract video ID from URL
        video_id = self._extract_video_id_from_url(url)
        logger.info(f"Extracted video ID: {video_id}")

        video_path = self.temp_dir / f"{video_id}.mp4"
        audio_path = self.temp_dir / f"{video_id}_audio.m4a"  # Audio file (no conversion needed)

        # Reset parallel download state
        self._video_download_error = None
        self._video_download_complete = threading.Event()

        # Fetch video info from API
        data = self._fetch_video_info(video_id, progress_callback)

        # Get video metadata
        title = data.get('title', 'Unknown')
        duration = data.get('lengthSeconds')
        if duration is None:
            duration_str = data.get('duration', '0')
            duration = int(duration_str) if duration_str and str(duration_str).isdigit() else 0
        else:
            duration = int(duration) if duration else 0

        logger.info(f"Video info: {title} (duration: {duration}s)")

        if not title or title == 'Unknown':
            logger.warning(f"Could not get video title, using video ID: {video_id}")
            title = f"Video {video_id}"

        # Parse available formats
        formats = self._parse_formats(data)

        if not formats:
            raise Exception("No video formats available from RapidAPI")

        # Find best audio-only and video-only streams for parallel download
        audio_only_stream = self._find_best_audio_stream(formats)
        video_only_stream = self._find_best_video_stream(formats)
        combined_stream = self._find_best_combined_stream(formats)

        # Strategy: If we have separate streams, download in parallel
        # Otherwise, fall back to combined stream
        use_parallel = audio_only_stream is not None and video_only_stream is not None

        if use_parallel:
            logger.info("Using PARALLEL download strategy (audio-only + video-only streams)")
            logger.info(f"Audio stream: {audio_only_stream.get('quality', 'unknown')}")
            logger.info(f"Video stream: {video_only_stream.get('quality', 'unknown')}")

            # Start video download in background thread
            if progress_callback:
                progress_callback("Starting parallel download (audio + video)...")

            self._video_download_thread = threading.Thread(
                target=self._download_file_thread,
                args=(video_only_stream['url'], video_path, "video"),
                daemon=True
            )
            self._video_download_thread.start()

            # Download audio in foreground (smaller, faster)
            if progress_callback:
                progress_callback("Downloading audio stream (video downloading in background)...")

            self._download_file(audio_only_stream['url'], audio_path, "audio", progress_callback)

            # Verify the downloaded file actually has audio
            if not self._verify_audio_file(audio_path):
                logger.warning("Downloaded 'audio' stream has no audio! Falling back to combined stream")
                # Clean up bad file and fall back
                if audio_path.exists():
                    audio_path.unlink()
                # Cancel video download and use combined stream instead
                use_parallel = False
                # Wait for video thread to finish or timeout quickly
                if self._video_download_thread:
                    self._video_download_thread.join(timeout=5)

            if use_parallel:
                logger.info("Audio ready for processing, video still downloading in background")

        # Fall back to combined stream if parallel failed or not available
        if not use_parallel:
            logger.info("Using SEQUENTIAL download (combined stream)")

            if not combined_stream:
                raise Exception("No valid video URL found in API response")

            if progress_callback:
                progress_callback(f"Downloading video ({combined_stream.get('quality', 'unknown')})...")

            self._download_file(combined_stream['url'], video_path, "video", progress_callback)

            # Extract audio from video
            if progress_callback:
                progress_callback("Extracting audio...")

            self._extract_audio(video_path, audio_path)
            logger.info("Audio extraction complete")

            # Mark video as complete (no background thread)
            self._video_download_complete.set()

        return {
            'video_path': str(video_path),
            'audio_path': str(audio_path),
            'title': title,
            'duration': duration,
            'video_id': video_id
        }

    def wait_for_video_download(self, timeout=600):
        """
        Wait for background video download to complete.
        Call this before combining video with audio.

        Args:
            timeout: Maximum seconds to wait (default 10 minutes)

        Returns:
            True if download completed successfully

        Raises:
            Exception: If download failed or timed out
        """
        if self._video_download_complete.is_set():
            # Already complete
            if self._video_download_error:
                raise Exception(f"Video download failed: {self._video_download_error}")
            return True

        logger.info("Waiting for background video download to complete...")

        # Wait for the event with timeout
        completed = self._video_download_complete.wait(timeout=timeout)

        if not completed:
            raise Exception(f"Video download timed out after {timeout} seconds")

        if self._video_download_error:
            raise Exception(f"Video download failed: {self._video_download_error}")

        logger.info("Background video download completed successfully")
        return True

    def _fetch_video_info(self, video_id, progress_callback=None):
        """Fetch video info from RapidAPI"""
        rapidapi_url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
        headers = {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": "youtube-media-downloader.p.rapidapi.com"
        }
        params = {
            "videoId": video_id,
            "includeFormats": "true"
        }

        # Check API usage limits
        can_proceed, message = api_tracker.can_make_request()
        if not can_proceed:
            logger.error(f"API limit reached: {message}")
            if progress_callback:
                progress_callback(f"Error: {message}")
            raise Exception(message)

        # Rate limiting
        global LAST_API_CALL_TIME
        current_time = time.time()
        time_since_last_call = current_time - LAST_API_CALL_TIME
        if time_since_last_call < MIN_TIME_BETWEEN_CALLS:
            wait_time = MIN_TIME_BETWEEN_CALLS - time_since_last_call
            logger.info(f"Rate limiting: waiting {wait_time:.1f}s before API call")
            time.sleep(wait_time)

        LAST_API_CALL_TIME = time.time()

        try:
            with requests.Session() as session:
                response = session.get(rapidapi_url, headers=headers, params=params, timeout=30)

                if response.status_code == 429:
                    api_tracker.record_request(success=False)
                    raise Exception("RapidAPI quota exceeded. Please check your API limits.")

                if response.status_code != 200:
                    api_tracker.record_request(success=False)
                    raise Exception(f"RapidAPI error: HTTP {response.status_code}")

                api_tracker.record_request(success=True)
                data = response.json()

            if 'error' in data:
                raise Exception(f"RapidAPI error: {data.get('error', 'Unknown error')}")

            if not data.get('videos'):
                raise Exception("No video formats available. Video may be unavailable or private.")

            return data

        except requests.Timeout:
            raise Exception("Request to RapidAPI timed out. Please try again.")
        except requests.RequestException as e:
            raise Exception(f"Network error while contacting RapidAPI: {str(e)}")

    def _parse_formats(self, data):
        """Parse available formats from API response"""
        videos_container = data.get('videos', {})
        formats = []

        if isinstance(videos_container, dict):
            logger.info(f"Videos container keys: {list(videos_container.keys())}")

            if videos_container.get('errorId') == 'Success' and 'items' in videos_container:
                items = videos_container.get('items', [])
            elif videos_container.get('errorId'):
                raise Exception(f"API returned error: {videos_container.get('errorId')}")
            elif 'items' in videos_container:
                items = videos_container.get('items', [])
            else:
                items = []
        else:
            items = videos_container if isinstance(videos_container, list) else []

        for item in items:
            if isinstance(item, dict):
                url = item.get('url')
                if url and url.startswith('http'):
                    formats.append({
                        'url': url,
                        'quality': item.get('quality') or item.get('format') or 'unknown',
                        'hasAudio': item.get('hasAudio', True),
                        'hasVideo': item.get('hasVideo', True),
                        'extension': item.get('extension', 'mp4'),
                        'size': item.get('size', 0)
                    })

        logger.info(f"Parsed {len(formats)} available formats")

        # Log first few formats for debugging
        for i, fmt in enumerate(formats[:8]):
            logger.info(f"Format {i}: quality={fmt['quality']}, hasAudio={fmt['hasAudio']}, "
                       f"hasVideo={fmt.get('hasVideo', 'unknown')}, ext={fmt['extension']}")

        return formats

    def _find_best_audio_stream(self, formats):
        """Find best audio-only stream (no video)"""
        # Look for streams that have audio but explicitly NO video (hasVideo=False)
        audio_streams = [f for f in formats if f.get('hasAudio') == True and f.get('hasVideo') == False]

        if not audio_streams:
            # Also check for formats explicitly marked as audio by quality name or extension
            audio_streams = [f for f in formats
                           if ('audio' in str(f.get('quality', '')).lower()
                               or f.get('extension') in ('m4a', 'mp3', 'aac', 'opus'))
                           and '720' not in str(f.get('quality', ''))
                           and '1080' not in str(f.get('quality', ''))
                           and '480' not in str(f.get('quality', ''))]

        if not audio_streams:
            logger.info("No audio-only stream found")
            return None

        # Prefer higher quality audio
        def audio_score(f):
            score = 0
            q = str(f.get('quality', '')).lower()
            if '320' in q: score = 320
            elif '256' in q: score = 256
            elif '192' in q: score = 192
            elif '128' in q: score = 128
            elif '64' in q: score = 64
            # Prefer m4a over webm
            if f.get('extension') == 'm4a':
                score += 10
            return score

        best = max(audio_streams, key=audio_score)
        logger.info(f"Selected audio-only stream: {best.get('quality')}")
        return best

    def _find_best_video_stream(self, formats):
        """Find best video-only stream (no audio)"""
        # Look for streams that have video but explicitly NO audio (hasAudio=False)
        video_streams = [f for f in formats if f.get('hasVideo') == True and f.get('hasAudio') == False]

        if not video_streams:
            logger.info("No video-only stream found")
            return None

        # Prefer higher resolution, mp4
        def video_score(f):
            score = 0
            q = str(f.get('quality', ''))
            if '1080' in q: score = 1080
            elif '720' in q: score = 720
            elif '480' in q: score = 480
            elif '360' in q: score = 360
            elif '240' in q: score = 240
            if f.get('extension') == 'mp4':
                score += 50
            return score

        best = max(video_streams, key=video_score)
        logger.info(f"Selected video-only stream: {best.get('quality')}")
        return best

    def _find_best_combined_stream(self, formats):
        """Find best combined stream (has both audio and video)"""
        combined = [f for f in formats if f.get('hasAudio') and f.get('hasVideo', True)]

        if not combined:
            # Fall back to any stream that might have both
            combined = [f for f in formats
                       if f.get('extension') == 'mp4' and f.get('hasAudio', True)]

        if not combined:
            return None

        def combined_score(f):
            score = 0
            q = str(f.get('quality', ''))
            if f.get('hasAudio', True):
                score += 10000
            if '1080' in q: score += 1080
            elif '720' in q: score += 720
            elif '480' in q: score += 480
            elif '360' in q: score += 360
            if f.get('extension') == 'mp4':
                score += 100
            return score

        best = max(combined, key=combined_score)
        logger.info(f"Selected combined stream: {best.get('quality')} (hasAudio={best.get('hasAudio')})")
        return best

    def _download_file(self, url, path, stream_type, progress_callback=None):
        """Download a file from URL to path with retry logic"""
        import time as time_module
        logger.info(f"Downloading {stream_type} from: {url[:100]}...")

        # Use browser-like headers to avoid YouTube blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
            'Referer': 'https://www.youtube.com/',
            'Origin': 'https://www.youtube.com'
        }

        # Retry logic for transient 403 errors
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                with requests.Session() as session:
                    response = session.get(url, stream=True, timeout=300, headers=headers)
                    response.raise_for_status()

                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    with open(path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if progress_callback and total_size > 0:
                                    percent = (downloaded / total_size) * 100
                                    size_mb = downloaded // (1024*1024)
                                    total_mb = total_size // (1024*1024)
                                    progress_callback(f"Downloading {stream_type}... {percent:.1f}% ({size_mb}MB/{total_mb}MB)")

                    logger.info(f"{stream_type.capitalize()} download complete: {downloaded//(1024*1024)}MB")

                    if total_size > 0 and downloaded < total_size:
                        logger.warning(f"Incomplete {stream_type} download: {downloaded}/{total_size} bytes")

                    return  # Success, exit retry loop

            except requests.exceptions.HTTPError as e:
                last_error = e
                if e.response.status_code == 403 and attempt < max_retries - 1:
                    logger.warning(f"Download attempt {attempt + 1} failed with 403, retrying in 2 seconds...")
                    time_module.sleep(2)
                    continue
                raise  # Re-raise if not 403 or last attempt

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"Download attempt {attempt + 1} failed: {e}, retrying...")
                    time_module.sleep(1)
                    continue
                raise

        # If we get here, all retries failed
        if last_error:
            raise last_error

    def _verify_audio_file(self, file_path):
        """Verify that a file contains an audio stream using ffprobe"""
        import subprocess
        import shutil

        # Find ffprobe
        nix_ffprobe = '/nix/var/nix/profiles/default/bin/ffprobe'
        if os.path.exists(nix_ffprobe):
            ffprobe_path = nix_ffprobe
        else:
            ffprobe_path = shutil.which('ffprobe')
            if not ffprobe_path:
                # Try common locations
                for path in ['/usr/bin/ffprobe', '/usr/local/bin/ffprobe']:
                    if os.path.exists(path):
                        ffprobe_path = path
                        break

        if not ffprobe_path:
            logger.warning("ffprobe not found, skipping audio verification")
            return True  # Assume OK if we can't verify

        try:
            cmd = [
                ffprobe_path,
                '-v', 'error',
                '-select_streams', 'a',  # Select audio streams only
                '-show_entries', 'stream=codec_type',
                '-of', 'csv=p=0',
                str(file_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            has_audio = 'audio' in result.stdout.lower()
            logger.info(f"Audio verification for {file_path}: has_audio={has_audio}")
            return has_audio
        except Exception as e:
            logger.warning(f"Audio verification failed: {e}")
            return True  # Assume OK on error

    def _download_file_thread(self, url, path, stream_type):
        """Download file in background thread"""
        try:
            logger.info(f"Background thread starting {stream_type} download...")
            self._download_file(url, path, stream_type)
            logger.info(f"Background {stream_type} download completed")
        except Exception as e:
            self._video_download_error = str(e)
            logger.error(f"Background {stream_type} download failed: {e}")
        finally:
            self._video_download_complete.set()

    def _get_ffmpeg_path(self):
        """Get ffmpeg path"""
        import shutil

        nix_ffmpeg = '/nix/var/nix/profiles/default/bin/ffmpeg'
        if os.path.exists(nix_ffmpeg):
            return nix_ffmpeg

        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path

        for path in ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']:
            if os.path.exists(path):
                return path

        raise Exception("ffmpeg not found")

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

        # First, check if video has audio stream
        probe_cmd = [
            ffmpeg_path,
            '-i', str(video_path),
            '-hide_banner'
        ]

        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)

        # Check if there's an audio stream
        has_audio_stream = 'Audio:' in probe_result.stderr

        if not has_audio_stream:
            logger.error("Video file has no audio stream!")
            logger.error("This video appears to be video-only. The API may have returned a format without audio.")
            raise Exception("Video file has no audio stream. The downloaded format is video-only. Please try a different video or check API settings.")

        # Extract audio with codec copy for speed (no re-encoding)
        # pydub and Whisper API can handle various audio formats
        cmd = [
            ffmpeg_path,
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'copy',  # Copy audio codec (fast, no re-encoding)
            '-y',  # Overwrite
            str(audio_path)
        ]

        logger.info(f"ffmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"ffmpeg failed with return code {result.returncode}")
            logger.error(f"ffmpeg stderr: {result.stderr}")

            # Check specific error cases
            if "Output file #0 does not contain any stream" in result.stderr:
                raise Exception("Video file has no audio stream. The API returned a video-only format.")
            else:
                raise Exception(f"Failed to extract audio: {result.stderr}")
        else:
            logger.info(f"Audio extracted successfully to {audio_path}")

    def cleanup(self, video_id):
        """Clean up temporary files for a video"""
        files_to_remove = [
            self.temp_dir / f"{video_id}.mp4",
            self.temp_dir / f"{video_id}_audio.m4a",  # Audio file
            self.temp_dir / f"{video_id}_audio.wav",  # Legacy WAV (if exists)
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