"""
Georgian Voiceover App - Main Flask Application
Web interface for translating YouTube videos to Georgian with voiceover
Supports geyoutube.com URL pattern (like ssyoutube.com)
"""

import os
import re
import threading
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, g
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Setup structured logging
from src.logging_config import get_logger
logger = get_logger(__name__)

# Import central configuration
from src.config import Config

# Set Google credentials if file exists
google_creds_path = os.path.join(
    os.path.dirname(__file__),
    os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google-credentials.json')
)
if os.path.exists(google_creds_path):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_creds_path

# Import database and tasks
from src.database import Database, Video
from src.storage import R2Storage
from src.validators import (
    validate_youtube_url,
    validate_video_id,
    validate_json_request,
    sanitize_filename,
    ValidationError
)

# Try to import Celery tasks and check if Redis is available
try:
    from src.tasks import process_video_task
    from src.redis_config import get_redis_url, test_redis_connection
    import redis
    import time

    # Get Redis URL from environment
    redis_url = os.getenv('REDIS_URL')
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            # Increased timeout for Railway's internal network
            # socket_keepalive causes "Error 22" on Railway, so disabled
            r = redis.from_url(redis_url, socket_connect_timeout=10)
            r.ping()
            USE_CELERY = True
            logger.info("celery_available",
                       status="using celery for task processing",
                       redis_url=redis_url,
                       attempt=attempt + 1)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Redis connection attempt {attempt + 1} failed, retrying in {retry_delay}s: {e}")
                time.sleep(retry_delay)
            else:
                raise e

except Exception as e:
    USE_CELERY = False
    # Log detailed error for debugging
    logger.error("celery_unavailable",
                error=str(e),
                redis_url=os.getenv('REDIS_URL', 'NOT SET'),
                fallback="threading",
                hint="Redis connection failed after retries. Check Railway logs!")
    logger.warning("IMPORTANT: Running in threading mode - Celery worker will NOT receive tasks!")
    import threading

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Configuration from central config
app.config['OUTPUT_DIR'] = Config.OUTPUT_DIR
app.config['TEMP_DIR'] = Config.TEMP_DIR
app.config['MAX_VIDEO_LENGTH'] = Config.MAX_VIDEO_LENGTH
app.config['MAX_FILE_SIZE'] = Config.MAX_FILE_SIZE
app.config['MAX_CONCURRENT_JOBS'] = Config.MAX_CONCURRENT_JOBS
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Register auth blueprint (optional - for Railway deployment)
try:
    from src.auth import auth_bp, init_admin_user, login_required, get_current_user
    app.register_blueprint(auth_bp)
    AUTH_ENABLED = True
    logger.info("Authentication system enabled")
except Exception as e:
    logger.warning(f"Authentication system disabled: {e}")
    AUTH_ENABLED = False
    # Define dummy functions when auth is disabled
    def get_current_user():
        return None
    def login_required(f):
        return f

# Initialize database and storage
db = Database()

# Initialize default tiers and admin user
try:
    db.init_default_tiers()
    if AUTH_ENABLED:
        init_admin_user()
except Exception as e:
    logger.warning(f"Failed to initialize tiers/admin: {e}")

try:
    storage = R2Storage()
    use_r2 = True
    logger.info("r2_storage_initialized", status="success")
except Exception as e:
    logger.warning("r2_storage_not_configured", error=str(e))
    storage = None
    use_r2 = False


@app.before_request
def load_logged_in_user():
    """Load user before each request"""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = db.get_user_by_id(user_id)


@app.context_processor
def inject_user():
    """Inject user into all templates"""
    return dict(current_user=g.get('user', None))

# Store Celery task IDs mapped to video IDs (Celery mode)
task_id_map = {}  # video_id -> celery_task_id

# Store processing status for threading mode with thread safety
processing_status = {}  # video_id -> status_dict
processing_status_lock = threading.Lock()  # Protect against race conditions


# Import the consolidated extract_video_id from validators
from src.validators import extract_video_id


def construct_youtube_url(video_id):
    """Construct standard YouTube URL from video ID"""
    return f"https://www.youtube.com/watch?v={video_id}"


def process_video_threading(video_id, youtube_url, user_id=None):
    """Fallback threading-based video processing when Celery unavailable"""
    from src.downloader import VideoDownloader
    from src.transcriber import Transcriber
    from src.translator import Translator
    from src.tts import TextToSpeech
    from src.audio_mixer import AudioMixer
    from src.video_processor import VideoProcessor

    video_duration_minutes = 0  # Track for usage charging

    try:
        def update_status(message, progress=None):
            with processing_status_lock:
                processing_status[video_id] = {
                    'status': message,
                    'progress': progress or 0,
                    'video_id': video_id
                }
            logger.info("processing_progress", video_id=video_id, status=message, progress=progress or 0)

        # Initialize components
        downloader = VideoDownloader(temp_dir=app.config['TEMP_DIR'])
        transcriber = Transcriber()
        translator = Translator()
        tts = TextToSpeech()
        mixer = AudioMixer(
            original_volume=float(os.getenv('ORIGINAL_AUDIO_VOLUME', 0.05)),
            voiceover_volume=float(os.getenv('VOICEOVER_VOLUME', 1.0))
        )
        processor = VideoProcessor(output_dir=app.config['OUTPUT_DIR'])

        # Step 1: Download video
        update_status("Downloading video from YouTube...", 10)
        video_info = downloader.download_video(youtube_url)
        video_title = video_info['title']
        video_duration_minutes = video_info.get('duration', 0) / 60  # Convert seconds to minutes

        # Update database with title
        db.update_video_status(video_id, 'processing')
        session = db.get_session()
        video = session.query(Video).filter_by(video_id=video_id).first()
        if video:
            video.title = video_title
            session.commit()
        db.close_session(session)

        # Step 2: Transcribe audio
        update_status("Transcribing audio...", 25)
        segments = transcriber.transcribe(
            video_info['audio_path'],
            progress_callback=lambda msg: update_status(f"Transcribing: {msg}", 30)
        )
        segments = transcriber.merge_short_segments(segments)
        update_status(f"Transcription complete: {len(segments)} segments", 40)

        # Step 3: Translate to Georgian
        update_status("Translating to Georgian...", 45)
        translated_segments = translator.translate_segments(
            segments,
            progress_callback=lambda msg: update_status(f"Translation: {msg}", 50)
        )
        update_status("Translation complete", 55)

        # Step 4: Generate Georgian voiceover
        update_status("Generating Georgian voiceover...", 60)
        voiceover_segments = tts.generate_voiceover(
            translated_segments,
            temp_dir=app.config['TEMP_DIR'],
            progress_callback=lambda msg: update_status(f"TTS: {msg}", 70)
        )
        update_status("Voiceover generation complete", 75)

        # Step 5: Mix audio
        update_status("Mixing audio tracks...", 80)
        mixed_audio_path = os.path.join(app.config['TEMP_DIR'], f"{video_id}_mixed.wav")
        mixer.mix_audio(
            video_info['audio_path'],
            voiceover_segments,
            mixed_audio_path,
            progress_callback=lambda msg: update_status(f"Mixing: {msg}", 85)
        )
        update_status("Audio mixing complete", 90)

        # Step 6: Combine with video
        update_status("Creating final video...", 92)
        output_filename = f"{video_id}_georgian.mp4"
        final_video_path = processor.combine_video_audio(
            video_info['video_path'],
            mixed_audio_path,
            output_filename,
            progress_callback=lambda msg: update_status(f"Video: {msg}", 95)
        )

        # Step 7: Upload to R2 if configured
        r2_url = None
        if use_r2 and storage:
            update_status("Uploading to cloud storage...", 97)
            r2_url = storage.upload_video(
                final_video_path,
                video_id,
                progress_callback=lambda msg: update_status(msg, 98)
            )
            update_status("Upload complete!", 99)
        else:
            r2_url = f"/download/{output_filename}"

        # Update database
        update_status("Processing complete!", 100)
        db.update_video_status(video_id, 'completed', r2_url=r2_url)

        # Charge user for minutes used
        if user_id and video_duration_minutes > 0:
            try:
                db.record_user_video(user_id, video_id, video_duration_minutes)
                logger.info(f"Charged user {user_id}: {video_duration_minutes:.2f} minutes for video {video_id}")
            except Exception as charge_err:
                logger.error(f"Failed to charge user {user_id}: {charge_err}")

        with processing_status_lock:
            processing_status[video_id]['complete'] = True
            processing_status[video_id]['r2_url'] = r2_url
            processing_status[video_id]['title'] = video_title

        # Cleanup temporary files
        downloader.cleanup(video_id)

    except Exception as e:
        error_msg = str(e)
        logger.error("processing_error", video_id=video_id, error=error_msg, exc_info=True)
        with processing_status_lock:
            processing_status[video_id] = {
                'status': f"Error: {error_msg}",
                'error': error_msg,
                'complete': False,
                'progress': 0
            }
        db.update_video_status(video_id, 'failed', error_message=error_msg)


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/watch')
def watch():
    """
    YouTube-style watch page
    Handles URLs like: geyoutube.com/watch?v=VIDEO_ID
    Redirects to main page with unified interface
    """
    video_id = request.args.get('v')

    if not video_id:
        return redirect(url_for('index'))

    # Check if video already processed
    video = db.get_video_by_id(video_id)

    if video and video.processing_status == 'completed':
        # Video already processed, show player
        db.increment_view_count(video_id)
        return render_template('player.html', video=video.to_dict())

    # For processing/new/failed videos, redirect to main page with video ID
    # Main page will show the video preview and wait for user to click translate
    return redirect(url_for('index', v=video_id))


@app.route('/shorts/<video_id>')
def shorts(video_id):
    """Handle YouTube Shorts URLs"""
    return redirect(url_for('watch', v=video_id))


@app.route('/library')
def library():
    """Show library of processed videos"""
    recent_videos = db.get_recent_videos(limit=50)
    return render_template('library.html',
                         videos=[v.to_dict() for v in recent_videos])


@app.route('/popular')
def popular():
    """Show popular videos"""
    popular_videos = db.get_popular_videos(limit=50)
    return render_template('library.html',
                         videos=[v.to_dict() for v in popular_videos],
                         title="Popular Videos")


@app.route('/login')
def login_page():
    """Login page"""
    if g.user:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/register')
def register_page():
    """Registration page"""
    if g.user:
        return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/admin')
def admin_panel():
    """Admin panel"""
    if not g.user or not g.user.is_admin:
        return redirect(url_for('login_page'))

    users = db.get_all_users()
    tiers = db.get_all_tiers()
    return render_template('admin.html', users=users, tiers=tiers)


@app.route('/process', methods=['POST'])
@validate_json_request(required_fields=['url'])
def process_video():
    """API endpoint for processing videos - requires login if auth enabled"""
    try:
        # Check authentication only if enabled
        if AUTH_ENABLED:
            user = get_current_user()
            if not user:
                return jsonify({
                    'error': 'Please login to translate videos',
                    'login_required': True
                }), 401

            # Check if user has remaining minutes
            remaining = user.get_remaining_minutes()
            if remaining <= 0:
                return jsonify({
                    'error': 'You have used all your minutes for this month. Please upgrade your plan.',
                    'quota_exceeded': True,
                    'tier': user.tier.to_dict() if user.tier else None
            }), 403

        data = request.json
        youtube_url = data.get('url')

        # Validate and extract video ID using new validator
        try:
            video_id = validate_youtube_url(youtube_url)
        except ValidationError as ve:
            return jsonify({'error': ve.message}), ve.status_code

        # Check if already processed or in progress
        video = db.get_video_by_id(video_id)
        if video:
            if video.processing_status == 'completed':
                return jsonify({
                    'success': True,
                    'video_id': video_id,
                    'job_id': video_id,  # Include for consistency
                    'already_processed': True,
                    'r2_url': video.r2_url
                })
            elif video.processing_status == 'processing':
                # Video is already being processed, don't start another job
                return jsonify({
                    'success': True,
                    'video_id': video_id,
                    'job_id': video_id,  # Include so JS can poll status
                    'already_processing': True,
                    'message': 'Video is already being processed. Please wait.'
                })

        # Check concurrent job limits
        if not USE_CELERY:
            with processing_status_lock:
                active_jobs = sum(1 for status in processing_status.values()
                                if not status.get('complete', False))
                if active_jobs >= app.config['MAX_CONCURRENT_JOBS']:
                    return jsonify({
                        'success': False,
                        'error': f"Too many videos processing. Maximum {app.config['MAX_CONCURRENT_JOBS']} allowed."
                    }), 429

        # Create database entry or reset failed video
        if not video:
            video = db.create_video(video_id, "Processing...", youtube_url)
        elif video.processing_status == 'failed':
            # Reset failed video to retry
            db.update_video_status(video_id, 'processing')
            db.update_video_progress(video_id, "Retrying...", 0)

        # Start background processing (Celery or threading)
        # Pass user_id to charge minutes after completion
        user_id = None
        if AUTH_ENABLED:
            user = get_current_user()
            user_id = user.id if user else None

        if USE_CELERY:
            task = process_video_task.delay(video_id, youtube_url, user_id)
            task_id_map[video_id] = task.id
        else:
            # Initialize processing status for threading mode
            with processing_status_lock:
                processing_status[video_id] = {
                    'status': 'Starting...',
                    'progress': 0,
                    'video_id': video_id
                }
            thread = threading.Thread(
                target=process_video_threading,
                args=(video_id, youtube_url, user_id)
            )
            thread.daemon = True
            thread.start()

        # Always return video_id as job_id for unified interface
        return jsonify({
            'success': True,
            'video_id': video_id,
            'job_id': video_id  # Use video_id for status polling
        })

    except Exception as e:
        error_msg = str(e)
        logger.error("process_video_error", error=error_msg, exc_info=True)
        return jsonify({'error': error_msg}), 500


@app.route('/status/<video_id>')
def get_status(video_id):
    """Get processing status (Celery or threading)"""
    try:
        # Validate video ID
        try:
            video_id = validate_video_id(video_id)
        except ValidationError as ve:
            return jsonify({'error': ve.message}), ve.status_code

        # Check database first
        video = db.get_video_by_id(video_id)
        if video:
            if video.processing_status == 'completed':
                return jsonify({
                    'complete': True,
                    'status': video.status_message or 'Processing complete!',
                    'progress': 100,
                    'video_id': video_id,
                    'r2_url': video.r2_url,
                    'title': video.title
                })
            elif video.processing_status == 'failed':
                return jsonify({
                    'complete': False,
                    'status': f"Error: {video.error_message}",
                    'error': video.error_message,
                    'progress': video.progress or 0
                })
            elif video.processing_status == 'processing':
                # Return live progress updates!
                return jsonify({
                    'complete': False,
                    'status': video.status_message or 'Processing...',
                    'progress': video.progress or 0,
                    'video_id': video_id
                })

        # If database doesn't have completed/failed status, check in-memory status
        # For Celery mode, the task updates the database directly
        # For threading mode, check the in-memory dict
        if not USE_CELERY:
            with processing_status_lock:
                if video_id in processing_status:
                    # Make a copy to avoid returning reference to shared dict
                    return jsonify(dict(processing_status[video_id]))

        # Default response - video is being processed
        return jsonify({
            'complete': False,
            'status': 'Processing...',
            'progress': 0,
            'video_id': video_id
        })

    except Exception as e:
        # Log the error and return JSON error response
        error_msg = str(e)
        logger.error("status_check_error", video_id=video_id, error=error_msg, exc_info=True)
        return jsonify({
            'error': f'Status check failed: {error_msg}',
            'complete': False,
            'status': 'Error checking status',
            'progress': 0
        }), 500


@app.route('/download/<filename>')
def download_file(filename):
    """Download processed video (fallback if R2 not configured)"""
    # Sanitize filename to prevent path traversal attacks
    try:
        filename = sanitize_filename(filename)
    except ValidationError as ve:
        return jsonify({'error': ve.message}), ve.status_code

    file_path = os.path.join(app.config['OUTPUT_DIR'], filename)

    # Double-check the resolved path is within OUTPUT_DIR
    output_dir_abs = os.path.abspath(app.config['OUTPUT_DIR'])
    file_path_abs = os.path.abspath(file_path)
    if not file_path_abs.startswith(output_dir_abs):
        return jsonify({'error': 'Invalid file path'}), 403

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404


@app.route('/debug/<video_id>')
def debug_video(video_id):
    """Debug endpoint to see detailed processing status"""
    try:
        video_id = validate_video_id(video_id)
        video = db.get_video_by_id(video_id)

        if not video:
            return jsonify({'error': 'Video not found'}), 404

        # Get detailed info
        debug_info = {
            'video_id': video_id,
            'database_record': video.to_dict(),
            'celery_mode': USE_CELERY,
            'timestamp': datetime.now().isoformat()
        }

        # If threading mode, include in-memory status
        if not USE_CELERY:
            with processing_status_lock:
                if video_id in processing_status:
                    debug_info['threading_status'] = dict(processing_status[video_id])

        return jsonify(debug_info)

    except ValidationError as ve:
        return jsonify({'error': ve.message}), ve.status_code
    except Exception as e:
        logger.error("debug_endpoint_error", video_id=video_id, error=str(e), exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/console/<video_id>')
def console_viewer(video_id):
    """Display console logs for a video"""
    return render_template('console.html', video_id=video_id)


@app.route('/api/logs/<video_id>')
def get_console_logs(video_id):
    """Get console logs for a specific video processing job"""
    from src.console_logger import console

    try:
        logs = console.get_logs(session_id=video_id, last_n=200)
        formatted = console.format_for_display(logs)

        return jsonify({
            'success': True,
            'video_id': video_id,
            'logs': logs,
            'formatted': formatted,
            'count': len(logs)
        })
    except Exception as e:
        logger.error(f"Error fetching console logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/usage-stats', methods=['GET'])
def api_usage_stats():
    """Get API usage statistics"""
    try:
        from src.api_tracker import api_tracker
        stats = api_tracker.get_usage_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/pipeline-debug/<video_id>')
def api_pipeline_debug(video_id):
    """
    Get detailed pipeline debug data for a video.
    Shows: transcription, translation, TTS input with all timecodes.
    """
    try:
        video_id = validate_video_id(video_id)

        # Get debug data from database
        debug_data = db.get_debug_data(video_id)

        if not debug_data:
            # Try to get basic video info
            video = db.get_video_by_id(video_id)
            if not video:
                return jsonify({
                    'success': False,
                    'error': 'Video not found'
                }), 404

            return jsonify({
                'success': False,
                'error': 'Debug data not available for this video. It may have been processed before debug logging was enabled.',
                'video': video.to_dict()
            }), 404

        # Get video info too
        video = db.get_video_by_id(video_id)

        return jsonify({
            'success': True,
            'video_id': video_id,
            'video': video.to_dict() if video else None,
            'debug_data': debug_data
        })

    except ValidationError as ve:
        return jsonify({'success': False, 'error': ve.message}), ve.status_code
    except Exception as e:
        logger.error("pipeline_debug_error", video_id=video_id, error=str(e), exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/pipeline/<video_id>')
def pipeline_viewer(video_id):
    """
    Debug UI page showing pipeline steps: transcription -> translation -> TTS
    """
    try:
        video_id = validate_video_id(video_id)
        video = db.get_video_by_id(video_id)

        return render_template('pipeline.html',
                             video_id=video_id,
                             video=video.to_dict() if video else None)

    except ValidationError as ve:
        return render_template('pipeline.html',
                             video_id=video_id,
                             error=ve.message)
    except Exception as e:
        return render_template('pipeline.html',
                             video_id=video_id,
                             error=str(e))


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint showing system status"""
    redis_status = "not_configured"
    redis_url = os.getenv('REDIS_URL', 'NOT SET')

    # Test Redis connection
    if redis_url != 'NOT SET':
        try:
            import redis
            r = redis.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            redis_status = "connected"
        except Exception as e:
            redis_status = f"error: {str(e)}"

    # Show database URL (masked) for debugging
    db_url = os.getenv('DATABASE_URL', 'NOT SET (using SQLite!)')
    if db_url and '@' in db_url:
        # Mask password
        import re
        db_url = re.sub(r'://[^:]+:[^@]+@', '://***:***@', db_url)

    return jsonify({
        'status': 'healthy',
        'mode': 'celery' if USE_CELERY else 'threading',
        'database': {
            'url': db_url,
            'type': 'PostgreSQL' if os.getenv('DATABASE_URL') else 'SQLite (LOCAL!)'
        },
        'redis': {
            'url': redis_url if redis_url != 'NOT SET' else None,
            'status': redis_status
        },
        'celery_enabled': USE_CELERY,
        'warning': None if USE_CELERY else 'Running in threading mode - Celery worker not receiving tasks!'
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', os.getenv('FLASK_PORT', 5000)))

    logger.info("server_starting",
                port=port,
                database='PostgreSQL' if os.getenv('DATABASE_URL') else 'SQLite',
                storage='Cloudflare R2' if use_r2 else 'Local files')

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  Georgian Voiceover App - geyoutube.com                      ║
║  YouTube to Georgian Translation with Voiceover              ║
╚══════════════════════════════════════════════════════════════╝

🚀 Server starting on http://localhost:{port}

📝 Instructions:
   1. Open http://localhost:{port} in your browser
   2. Or use: geyoutube.com/watch?v=VIDEO_ID
   3. Video will be automatically processed
   4. Watch directly in browser!

🗄️  Database: {'PostgreSQL' if os.getenv('DATABASE_URL') else 'SQLite'}
☁️   Storage: {'Cloudflare R2' if use_r2 else 'Local files'}

Press CTRL+C to stop the server
""")
    app.run(host='0.0.0.0', port=port, debug=True, threaded=True)
