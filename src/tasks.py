"""
Celery Tasks
Background tasks for video processing
"""

import os
import traceback
from celery import Task
from celery_app import celery_app
from dotenv import load_dotenv

# Import processing modules
from src.downloader import VideoDownloader
from src.transcriber import Transcriber
from src.translator import Translator
from src.tts import TextToSpeech
from src.audio_mixer import AudioMixer
from src.video_processor import VideoProcessor
from src.database import Database, Video
from src.storage import R2Storage
from src.logging_config import get_logger

load_dotenv()
logger = get_logger(__name__)


class CallbackTask(Task):
    """Base task with state callback support"""

    def __init__(self):
        super().__init__()
        self._db = None
        self._storage = None

    @property
    def db(self):
        if self._db is None:
            self._db = Database()
        return self._db

    @property
    def storage(self):
        if self._storage is None:
            try:
                self._storage = R2Storage()
            except Exception:
                self._storage = None
        return self._storage


@celery_app.task(bind=True, base=CallbackTask, max_retries=1)  # Only 1 retry to prevent quota waste
def process_video_task(self, video_id, youtube_url):
    """
    Celery task for processing video with Georgian voiceover

    Args:
        video_id: YouTube video ID
        youtube_url: Full YouTube URL

    Returns:
        dict: Processing result with status, r2_url, title
    """

    def update_progress(message, progress=None):
        """Update task progress - now updates database too!"""
        # Update Celery state
        self.update_state(
            state='PROGRESS',
            meta={
                'status': message,
                'progress': progress or 0,
                'video_id': video_id
            }
        )

        # IMPORTANT: Also update database so frontend can see progress
        try:
            session = self.db.get_session()
            video = session.query(Video).filter_by(video_id=video_id).first()
            if video:
                video.processing_status = 'processing'
                video.progress = progress or 0
                video.status_message = message
                session.commit()
            self.db.close_session(session)
        except Exception as db_error:
            logger.warning("progress_db_update_failed", video_id=video_id, error=str(db_error))

        # Log for debugging
        logger.info("task_progress", video_id=video_id, status=message, progress=progress or 0)

    def calc_sub_progress(start, end, current, total):
        """Calculate progress within a range"""
        if total == 0:
            return start
        range_size = end - start
        sub_progress = (current / total) * range_size
        return int(start + sub_progress)

    try:
        # Configuration
        output_dir = os.getenv('OUTPUT_DIR', 'output')
        temp_dir = os.getenv('TEMP_DIR', 'temp')
        original_volume = float(os.getenv('ORIGINAL_AUDIO_VOLUME', 0.05))
        voiceover_volume = float(os.getenv('VOICEOVER_VOLUME', 1.0))

        # Check if R2 storage is configured
        use_r2 = self.storage is not None

        # Initialize components
        downloader = VideoDownloader(temp_dir=temp_dir)
        transcriber = Transcriber()
        translator = Translator()
        tts = TextToSpeech()
        mixer = AudioMixer(
            original_volume=original_volume,
            voiceover_volume=voiceover_volume
        )
        processor = VideoProcessor(output_dir=output_dir)

        # Step 1: Download video (0-20%)
        update_progress("🚀 Initializing video download...", 1)

        def download_progress_callback(msg):
            # Parse download percentage from message like "Downloading... 22.2% (3MB/13MB)"
            import re
            percent_match = re.search(r'(\d+\.?\d*)%', msg)
            if percent_match:
                download_percent = float(percent_match.group(1))
                # Map 0-100% download to 2-19% overall progress
                overall_progress = int(2 + (download_percent / 100) * 17)
                update_progress(f"📥 {msg}", overall_progress)
            else:
                update_progress(f"📥 {msg}", 5)

        video_info = downloader.download_video(
            youtube_url,
            progress_callback=download_progress_callback
        )
        video_title = video_info['title']
        update_progress(f"✅ Video downloaded: {video_title}", 20)

        # Update database with title
        self.db.update_video_status(video_id, 'processing')
        session = self.db.get_session()
        video = session.query(Video).filter_by(video_id=video_id).first()
        if video:
            video.title = video_title
            session.commit()
        self.db.close_session(session)

        # Step 2: Transcribe audio (20-35%)
        update_progress("🎵 Extracting audio from video...", 21)
        update_progress("🎤 Starting speech recognition with OpenAI Whisper...", 23)
        segments = transcriber.transcribe(
            video_info['audio_path'],
            progress_callback=lambda msg: update_progress(f"🎤 {msg}", 28)
        )
        segments = transcriber.merge_short_segments(segments)
        update_progress(f"✅ Transcribed speech into {len(segments)} segments", 35)

        # Step 3: Translate to Georgian (35-50%)
        update_progress("🌐 Starting translation to Georgian...", 36)
        total_segments = len(segments)
        def translation_progress(idx, total, text):
            prog = calc_sub_progress(37, 49, idx, total)
            update_progress(f"🌐 Translating segment {idx}/{total} with GPT-4...", prog)

        translated_segments = translator.translate_segments(
            segments,
            progress_callback=translation_progress
        )
        update_progress(f"✅ Translated all {len(translated_segments)} segments to Georgian", 50)

        # Step 4: Generate Georgian voiceover (50-70%)
        update_progress("🎙️ Starting Georgian voice synthesis with ElevenLabs...", 51)
        def tts_progress(idx, total, text):
            prog = calc_sub_progress(52, 69, idx, total)
            update_progress(f"🎙️ Generating voice for segment {idx}/{total}...", prog)

        voiceover_segments = tts.generate_voiceover(
            translated_segments,
            temp_dir=temp_dir,
            progress_callback=tts_progress
        )
        update_progress(f"✅ Generated {len(voiceover_segments)} Georgian voiceover clips", 70)

        # Step 5: Mix audio (70-85%)
        update_progress("🎛️ Mixing original audio with Georgian voiceover...", 72)
        mixed_audio_path = os.path.join(temp_dir, f"{video_id}_mixed.wav")
        mixer.mix_audio(
            video_info['audio_path'],
            voiceover_segments,
            mixed_audio_path,
            progress_callback=lambda msg: update_progress(f"🎛️ {msg}", 80)
        )
        update_progress("✅ Audio tracks mixed successfully", 85)

        # Step 6: Combine with video (85-95%)
        update_progress("🎬 Encoding final video with Georgian audio...", 87)
        output_filename = f"{video_id}_georgian.mp4"
        final_video_path = processor.combine_video_audio(
            video_info['video_path'],
            mixed_audio_path,
            output_filename,
            progress_callback=lambda msg: update_progress(f"🎬 {msg}", 92)
        )
        update_progress("✅ Video encoding complete", 95)

        # Step 7: Upload to R2 if configured (95-99%)
        r2_url = None
        if use_r2 and self.storage:
            update_progress("☁️ Uploading video to cloud storage...", 96)
            r2_url = self.storage.upload_video(
                final_video_path,
                video_id,
                progress_callback=lambda msg: update_progress(f"☁️ {msg}", 98)
            )
            update_progress("✅ Upload complete! Video ready to watch", 99)
        else:
            # Use local file path
            r2_url = f"/download/{output_filename}"
            update_progress("✅ Video saved locally and ready for download", 99)

        # Update database
        update_progress("🎉 Processing complete! Your Georgian voiceover is ready!", 100)
        self.db.update_video_status(video_id, 'completed', r2_url=r2_url)

        return {
            'status': 'completed',
            'video_id': video_id,
            'r2_url': r2_url,
            'title': video_title,
            'progress': 100
        }

    except Exception as exc:
        # Log error
        error_msg = str(exc)
        logger.error("task_failed", video_id=video_id, error=error_msg, exc_info=True)

        # Update database
        self.db.update_video_status(video_id, 'failed', error_message=error_msg)

        # Smart retry logic: Only retry on transient errors
        # Do NOT retry on permanent failures that waste API quota
        should_retry = False
        error_lower = error_msg.lower()

        # Don't retry these permanent failures (they waste API quota):
        non_retriable_errors = [
            '429',  # Rate limit
            '401',  # Unauthorized
            '403',  # Forbidden
            'too many requests',
            'quota',  # Any quota related error
            'rate limit',
            'exceeded',
            'sign in to confirm',  # Bot detection
            'invalid api response',  # Bad data from API
            'not subscribed',  # API subscription issue
            'authentication',
            'unauthorized',
            'forbidden',
            'invalid response',
            'no video formats',
            'rapidapi',  # Any RapidAPI specific error
            'subscription',
            'disabled for your subscription'
        ]

        # Check if error is non-retriable
        is_non_retriable = any(err in error_lower for err in non_retriable_errors)

        if not is_non_retriable and self.request.retries < self.max_retries:
            # Only retry on transient errors (network issues, timeouts, etc.)
            should_retry = True
            logger.info("task_retry", video_id=video_id, retry_count=self.request.retries + 1, reason="transient_error")
            raise self.retry(exc=exc, countdown=60)
        else:
            if is_non_retriable:
                logger.warning("task_not_retrying", video_id=video_id, reason="non_retriable_error")

    finally:
        # Always cleanup temporary files, regardless of success or failure
        try:
            downloader.cleanup(video_id)
            logger.info("temp_cleanup", video_id=video_id, status="success")
        except Exception as cleanup_exc:
            logger.warning("temp_cleanup_failed", video_id=video_id, error=str(cleanup_exc))

        # If all retries exhausted, return failure
        logger.error("task_failed_all_retries", video_id=video_id, max_retries=self.max_retries)
        return {
            'status': 'failed',
            'video_id': video_id,
            'error': error_msg,
            'progress': 0
        }
