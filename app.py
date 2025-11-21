"""
Georgian Voiceover App - Main Flask Application
Web interface for translating YouTube videos to Georgian with voiceover
Supports geyoutube.com URL pattern (like ssyoutube.com)
"""

import os
import re
import threading
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

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
from src.database import Database
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
    import redis

    # Try to connect to Redis to verify it's actually available
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    r = redis.from_url(redis_url, socket_connect_timeout=1)
    r.ping()

    USE_CELERY = True
    logger.info("celery_available", status="using celery for task processing", redis_url=redis_url)
except Exception as e:
    USE_CELERY = False
    logger.warning("celery_unavailable", error=str(e), fallback="threading")
    import threading

app = Flask(__name__)
CORS(app)

# Configuration from central config
app.config['OUTPUT_DIR'] = Config.OUTPUT_DIR
app.config['TEMP_DIR'] = Config.TEMP_DIR
app.config['MAX_VIDEO_LENGTH'] = Config.MAX_VIDEO_LENGTH
app.config['MAX_FILE_SIZE'] = Config.MAX_FILE_SIZE
app.config['MAX_CONCURRENT_JOBS'] = Config.MAX_CONCURRENT_JOBS
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Initialize database and storage
db = Database()
try:
    storage = R2Storage()
    use_r2 = True
    logger.info("r2_storage_initialized", status="success")
except Exception as e:
    logger.warning("r2_storage_not_configured", error=str(e))
    storage = None
    use_r2 = False

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


def process_video_threading(video_id, youtube_url):
    """Fallback threading-based video processing when Celery unavailable"""
    from src.downloader import VideoDownloader
    from src.transcriber import Transcriber
    from src.translator import Translator
    from src.tts import TextToSpeech
    from src.audio_mixer import AudioMixer
    from src.video_processor import VideoProcessor

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

        # Update database with title
        db.update_video_status(video_id, 'processing')
        session = db.get_session()
        video = session.query(db.Video).filter_by(video_id=video_id).first()
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


@app.route('/process', methods=['POST'])
@validate_json_request(required_fields=['url'])
def process_video():
    """Legacy API endpoint for processing videos"""
    try:
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
                    'already_processed': True,
                    'r2_url': video.r2_url
                })
            elif video.processing_status == 'processing':
                # Video is already being processed, don't start another job
                return jsonify({
                    'success': True,
                    'video_id': video_id,
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

        # Create database entry
        if not video:
            video = db.create_video(video_id, "Processing...", youtube_url)

        # Start background processing (Celery or threading)
        if USE_CELERY:
            task = process_video_task.delay(video_id, youtube_url)
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
                args=(video_id, youtube_url)
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
