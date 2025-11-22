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
from src.tts_factory import get_tts_provider
from src.audio_mixer import AudioMixer
from src.video_processor import VideoProcessor
from src.database import Database, Video
from src.storage import R2Storage
from src.config import Config
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
            logger.info("Celery task initialized database connection")
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
def process_video_task(self, video_id, youtube_url, user_id=None):
    """
    Celery task for processing video with Georgian voiceover

    Args:
        video_id: YouTube video ID
        youtube_url: Full YouTube URL
        user_id: User ID to charge minutes to (optional)

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
        # Use direct database update to ensure it's committed
        try:
            # Use the database's own method to ensure proper session handling
            self.db.update_video_progress(video_id, message, progress or 0)
            logger.debug(f"Database updated: video_id={video_id}, progress={progress}, message={message[:50]}...")
        except Exception as db_error:
            logger.error(f"Database update FAILED: video_id={video_id}, error={str(db_error)}", exc_info=True)

        # Log for debugging
        logger.info("task_progress", video_id=video_id, status=message, progress=progress or 0)

    def calc_sub_progress(start, end, current, total):
        """Calculate progress within a range"""
        if total == 0:
            return start
        range_size = end - start
        sub_progress = (current / total) * range_size
        return int(start + sub_progress)

    video_duration_minutes = 0  # Initialize for usage tracking

    try:
        # First, ensure video exists in database
        session = self.db.get_session()
        video = session.query(Video).filter_by(video_id=video_id).first()
        if not video:
            # Create the video record if it doesn't exist
            video = Video(
                video_id=video_id,
                title="Processing...",
                original_url=youtube_url,
                processing_status='processing',
                progress=0,
                status_message="Initializing..."
            )
            session.add(video)
            session.commit()
            logger.info(f"Created video record for {video_id}")
        self.db.close_session(session)

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
        tts = get_tts_provider()  # Uses TTS_PROVIDER env var (elevenlabs or gemini)
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

        try:
            video_info = downloader.download_video(
                youtube_url,
                progress_callback=download_progress_callback
            )
            video_title = video_info['title']
            video_duration_minutes = video_info.get('duration', 0) / 60  # Convert seconds to minutes
            update_progress(f"✅ Video downloaded: {video_title}", 20)
            logger.info(f"Download complete for {video_id}: {video_title} ({video_duration_minutes:.2f} min)")
        except Exception as e:
            logger.error(f"Download failed for {video_id}: {str(e)}")
            raise

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
        logger.info(f"Starting transcription for {video_id}")

        update_progress("🎤 Starting speech recognition...", 23)
        try:
            segments = transcriber.transcribe(
                video_info['audio_path'],
                progress_callback=lambda msg: update_progress(f"🎤 {msg}", 28)
            )

            # Check if we have speaker diarization
            speakers = None
            if transcriber.has_speaker_diarization():
                speakers = transcriber.get_speakers()
                update_progress(f"✅ Transcribed with {len(speakers)} speakers detected", 33)
                logger.info(f"Speaker diarization: {len(speakers)} speakers detected")
            else:
                segments = transcriber.merge_short_segments(segments)

            update_progress(f"✅ Transcribed speech into {len(segments)} segments", 35)
            logger.info(f"Transcription complete for {video_id}: {len(segments)} segments")
        except Exception as e:
            logger.error(f"Transcription failed for {video_id}: {str(e)}", exc_info=True)
            update_progress(f"❌ Transcription failed: {str(e)}", 35)
            raise

        # Step 3: Translate to Georgian (35-50%)
        update_progress("🌐 Starting translation to Georgian...", 36)
        total_segments = len(segments)
        def translation_progress(message):
            # Handle both simple message and detailed progress
            if isinstance(message, str):
                update_progress(f"🌐 {message}", 40)
            else:
                # If translator sends idx, total, text - handle it
                update_progress(f"🌐 {message}", 40)

        # Pass speaker information if available for context-aware translation
        translated_segments = translator.translate_segments(
            segments,
            progress_callback=translation_progress,
            speakers=speakers  # Pass speaker info for context-aware translation
        )
        update_progress(f"✅ Translated all {len(translated_segments)} segments to Georgian", 50)

        # Step 4: Generate Georgian voiceover (50-70%)
        # Check if we have multiple speakers for multi-voice synthesis
        if speakers and len(speakers) > 1:
            update_progress(f"🎙️ Starting multi-voice synthesis for {len(speakers)} speakers...", 51)

            # Initialize voice manager
            from src.voice_manager import VoiceManager
            voice_manager = VoiceManager(provider=Config.TTS_PROVIDER)

            # Assign voices to speakers
            voice_assignments = voice_manager.assign_voices_to_speakers(
                speakers,
                segments=translated_segments,
                auto_detect_gender=True
            )

            # Log voice assignments
            for speaker_id, voice in voice_assignments.items():
                speaker_label = next((s['label'] for s in speakers if s['id'] == speaker_id), speaker_id)
                logger.info(f"Voice assignment: {speaker_label} -> {voice.name}")

            # Prepare segments with voice assignments
            voiced_segments = voice_manager.prepare_segments_for_multivoice(
                translated_segments,
                voice_assignments
            )

            def tts_progress(message):
                if isinstance(message, str):
                    update_progress(f"🎙️ {message}", 60)
                else:
                    update_progress(f"🎙️ {message}", 60)

            # Generate voiceover with multiple voices
            voiceover_segments = voice_manager.generate_voiceover_multivoice(
                tts,
                voiced_segments,
                temp_dir=temp_dir,
                progress_callback=tts_progress
            )
        else:
            # Single speaker or no speaker info - use default voice
            update_progress("🎙️ Starting Georgian voice synthesis...", 51)

            def tts_progress(message):
                if isinstance(message, str):
                    update_progress(f"🎙️ {message}", 60)
                else:
                    update_progress(f"🎙️ {message}", 60)

            voiceover_segments = tts.generate_voiceover(
                translated_segments,
                temp_dir=temp_dir,
                progress_callback=tts_progress
            )

        update_progress(f"✅ Generated {len(voiceover_segments)} Georgian voiceover clips", 70)

        # Save debug data for inspection
        try:
            debug_data = {
                'transcription': [
                    {
                        'index': i,
                        'text': seg.get('text', ''),
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'speaker': seg.get('speaker', 'unknown'),
                        'duration': round(seg.get('end', 0) - seg.get('start', 0), 2)
                    }
                    for i, seg in enumerate(segments)
                ],
                'translation': [
                    {
                        'index': i,
                        'original_text': seg.get('original_text', seg.get('text', '')),
                        'translated_text': seg.get('translated_text', seg.get('text', '')),
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'speaker': seg.get('speaker', 'unknown')
                    }
                    for i, seg in enumerate(translated_segments)
                ],
                'tts_input': [
                    {
                        'index': i,
                        'text': seg.get('translated_text', seg.get('text', '')),
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'speaker': seg.get('speaker', 'unknown'),
                        'audio_duration': seg.get('audio_duration', 0),
                        'audio_path': seg.get('audio_path', '')
                    }
                    for i, seg in enumerate(voiceover_segments)
                ],
                'speakers': speakers if speakers else [],
                'summary': {
                    'total_segments': len(segments),
                    'translated_segments': len(translated_segments),
                    'voiceover_segments': len(voiceover_segments),
                    'speakers_detected': len(speakers) if speakers else 0
                }
            }
            self.db.save_debug_data(video_id, debug_data)
            logger.info(f"Saved debug data for {video_id}")
        except Exception as e:
            logger.error(f"Failed to save debug data: {e}")

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
        # IMPORTANT: Wait for background video download to complete before combining
        update_progress("🎬 Preparing video for encoding...", 86)
        try:
            downloader.wait_for_video_download(timeout=600)  # Wait up to 10 minutes
            update_progress("🎬 Video download complete, encoding...", 87)
        except Exception as video_wait_error:
            logger.error(f"Video download failed: {video_wait_error}")
            raise Exception(f"Video download failed: {video_wait_error}")

        update_progress("🎬 Encoding final video with Georgian audio...", 88)
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

        # Charge user for minutes used
        if user_id and video_duration_minutes > 0:
            try:
                self.db.record_user_video(user_id, video_id, video_duration_minutes)
                logger.info(f"Charged user {user_id}: {video_duration_minutes:.2f} minutes for video {video_id}")
            except Exception as charge_err:
                logger.error(f"Failed to charge user {user_id}: {charge_err}")

        return {
            'status': 'completed',
            'video_id': video_id,
            'r2_url': r2_url,
            'title': video_title,
            'progress': 100,
            'minutes_charged': video_duration_minutes
        }

    except Exception as exc:
        # Log error
        error_msg = str(exc)
        logger.error("task_failed", video_id=video_id, error=error_msg, exc_info=True)

        # Truncate error message for database (in case column limit)
        error_msg_truncated = error_msg[:900] + '...' if len(error_msg) > 900 else error_msg

        # Update database
        self.db.update_video_status(video_id, 'failed', error_message=error_msg_truncated)

        # Smart retry logic: Only retry on transient errors
        # Do NOT retry on permanent failures that waste API quota
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
            logger.info("task_retry", video_id=video_id, retry_count=self.request.retries + 1, reason="transient_error")
            # Cleanup before retry
            try:
                downloader.cleanup(video_id)
            except Exception:
                pass
            raise self.retry(exc=exc, countdown=60)
        else:
            if is_non_retriable:
                logger.warning("task_not_retrying", video_id=video_id, reason="non_retriable_error")
            else:
                logger.error("task_failed_all_retries", video_id=video_id, max_retries=self.max_retries)

            # Cleanup on final failure
            try:
                downloader.cleanup(video_id)
                logger.info("temp_cleanup", video_id=video_id, status="success")
            except Exception as cleanup_exc:
                logger.warning("temp_cleanup_failed", video_id=video_id, error=str(cleanup_exc))

            return {
                'status': 'failed',
                'video_id': video_id,
                'error': error_msg,
                'progress': 0
            }
