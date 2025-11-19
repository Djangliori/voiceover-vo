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
from src.database import Database
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


@celery_app.task(bind=True, base=CallbackTask, max_retries=3)
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
            video = session.query(self.db.Video).filter_by(video_id=video_id).first()
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
        transcriber = Transcriber(use_google_cloud=False)
        translator = Translator()
        tts = TextToSpeech()
        mixer = AudioMixer(
            original_volume=original_volume,
            voiceover_volume=voiceover_volume
        )
        processor = VideoProcessor(output_dir=output_dir)

        # Step 1: Download video
        update_progress("Downloading video from YouTube...", 10)
        video_info = downloader.download_video(youtube_url)
        video_title = video_info['title']

        # Update database with title
        self.db.update_video_status(video_id, 'processing')
        session = self.db.get_session()
        video = session.query(self.db.Video).filter_by(video_id=video_id).first()
        if video:
            video.title = video_title
            session.commit()
        self.db.close_session(session)

        # Step 2: Transcribe audio
        update_progress("Transcribing audio...", 25)
        segments = transcriber.transcribe(
            video_info['audio_path'],
            progress_callback=lambda msg: update_progress(f"Transcribing: {msg}", 30)
        )
        segments = transcriber.merge_short_segments(segments)
        update_progress(f"Transcription complete: {len(segments)} segments", 40)

        # Step 3: Translate to Georgian
        update_progress("Translating to Georgian...", 45)
        translated_segments = translator.translate_segments(
            segments,
            progress_callback=lambda msg: update_progress(f"Translation: {msg}", 50)
        )
        update_progress("Translation complete", 55)

        # Step 4: Generate Georgian voiceover
        update_progress("Generating Georgian voiceover...", 60)
        voiceover_segments = tts.generate_voiceover(
            translated_segments,
            temp_dir=temp_dir,
            progress_callback=lambda msg: update_progress(f"TTS: {msg}", 70)
        )
        update_progress("Voiceover generation complete", 75)

        # Step 5: Mix audio
        update_progress("Mixing audio tracks...", 80)
        mixed_audio_path = os.path.join(temp_dir, f"{video_id}_mixed.wav")
        mixer.mix_audio(
            video_info['audio_path'],
            voiceover_segments,
            mixed_audio_path,
            progress_callback=lambda msg: update_progress(f"Mixing: {msg}", 85)
        )
        update_progress("Audio mixing complete", 90)

        # Step 6: Combine with video
        update_progress("Creating final video...", 92)
        output_filename = f"{video_id}_georgian.mp4"
        final_video_path = processor.combine_video_audio(
            video_info['video_path'],
            mixed_audio_path,
            output_filename,
            progress_callback=lambda msg: update_progress(f"Video: {msg}", 95)
        )

        # Step 7: Upload to R2 if configured
        r2_url = None
        if use_r2 and self.storage:
            update_progress("Uploading to cloud storage...", 97)
            r2_url = self.storage.upload_video(
                final_video_path,
                video_id,
                progress_callback=lambda msg: update_progress(msg, 98)
            )
            update_progress("Upload complete!", 99)
        else:
            # Use local file path
            r2_url = f"/download/{output_filename}"

        # Update database
        update_progress("Processing complete!", 100)
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

        # Retry task if possible
        if self.request.retries < self.max_retries:
            logger.info("task_retry", video_id=video_id, retry_count=self.request.retries + 1)
            raise self.retry(exc=exc, countdown=60)

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
