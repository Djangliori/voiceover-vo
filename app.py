"""
Georgian Voiceover App - Main Flask Application
Web interface for translating YouTube videos to Georgian with voiceover
Supports geyoutube.com URL pattern (like ssyoutube.com)
"""

import os
import sys
import re
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path
import traceback
import uuid
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from celery.result import AsyncResult

# Load environment variables
load_dotenv()

# Setup structured logging
from src.logging_config import get_logger
logger = get_logger(__name__)

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

# Try to import Celery tasks, fall back to threading if Redis unavailable
try:
    from src.tasks import process_video_task
    USE_CELERY = True
    logger.info("celery_available", status="using celery for task processing")
except Exception as e:
    USE_CELERY = False
    logger.warning("celery_unavailable", error=str(e), fallback="threading")
    import threading

app = Flask(__name__)
CORS(app)

# Configuration
app.config['OUTPUT_DIR'] = os.getenv('OUTPUT_DIR', 'output')
app.config['TEMP_DIR'] = os.getenv('TEMP_DIR', 'temp')
app.config['MAX_VIDEO_LENGTH'] = int(os.getenv('MAX_VIDEO_LENGTH', 1800))

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

# Store processing status for threading mode
processing_status = {}  # video_id -> status_dict


def extract_video_id(url_or_path):
    """
    Extract YouTube video ID from various URL formats or path

    Args:
        url_or_path: YouTube URL or path (e.g., /watch?v=xxx)

    Returns:
        Video ID or None
    """
    # Patterns for YouTube URLs
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'(?:geyoutube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:geyoutube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'[?&]v=([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url_or_path)
        if match:
            return match.group(1)

    return None


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
            processing_status[video_id] = {
                'status': message,
                'progress': progress or 0,
                'video_id': video_id
            }
            logger.info("processing_progress", video_id=video_id, status=message, progress=progress or 0)

        # Initialize components
        downloader = VideoDownloader(temp_dir=app.config['TEMP_DIR'])
        transcriber = Transcriber(use_google_cloud=False)
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

        processing_status[video_id]['complete'] = True
        processing_status[video_id]['r2_url'] = r2_url
        processing_status[video_id]['title'] = video_title

        # Cleanup temporary files
        downloader.cleanup(video_id)

    except Exception as e:
        error_msg = str(e)
        logger.error("processing_error", video_id=video_id, error=error_msg, exc_info=True)
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
    # Main page will handle auto-processing
    return redirect(url_for('index', v=video_id, autostart='1'))


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
def process_video():
    """Legacy API endpoint for processing videos"""
    try:
        data = request.json
        youtube_url = data.get('url')

        if not youtube_url:
            return jsonify({'error': 'No URL provided'}), 400

        # Extract video ID
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        # Check if already processed
        video = db.get_video_by_id(video_id)
        if video and video.processing_status == 'completed':
            return jsonify({
                'success': True,
                'video_id': video_id,
                'already_processed': True,
                'r2_url': video.r2_url
            })

        # Create database entry
        if not video:
            video = db.create_video(video_id, "Processing...", youtube_url)

        # Start background processing (Celery or threading)
        if USE_CELERY:
            task = process_video_task.delay(video_id, youtube_url)
            task_id_map[video_id] = task.id
        else:
            # Initialize processing status for threading mode
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
    # Check database first
    video = db.get_video_by_id(video_id)
    if video:
        if video.processing_status == 'completed':
            return jsonify({
                'complete': True,
                'status': 'Processing complete!',
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
                'progress': 0
            })

    # Check status based on mode
    if USE_CELERY:
        # Check Celery task status
        task_id = task_id_map.get(video_id)
        if task_id:
            task = AsyncResult(task_id)

            if task.state == 'PENDING':
                return jsonify({
                    'complete': False,
                    'status': 'Task pending...',
                    'progress': 0,
                    'video_id': video_id
                })
            elif task.state == 'PROGRESS':
                return jsonify({
                    'complete': False,
                    **task.info,
                })
            elif task.state == 'SUCCESS':
                result = task.result
                return jsonify({
                    'complete': True,
                    **result
                })
            elif task.state == 'FAILURE':
                return jsonify({
                    'complete': False,
                    'status': f"Error: {str(task.info)}",
                    'error': str(task.info),
                    'progress': 0
                })
    else:
        # Check threading status
        if video_id in processing_status:
            return jsonify(processing_status[video_id])

    # Default response
    return jsonify({
        'complete': False,
        'status': 'Processing...',
        'progress': 0
    })


@app.route('/download/<filename>')
def download_file(filename):
    """Download processed video (fallback if R2 not configured)"""
    file_path = os.path.join(app.config['OUTPUT_DIR'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404


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
