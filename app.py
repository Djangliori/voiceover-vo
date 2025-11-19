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
from src.tasks import process_video_task

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

# Store Celery task IDs mapped to video IDs
task_id_map = {}  # video_id -> celery_task_id


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


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/watch')
def watch():
    """
    YouTube-style watch page
    Handles URLs like: geyoutube.com/watch?v=VIDEO_ID
    """
    video_id = request.args.get('v')

    if not video_id:
        return render_template('error.html',
                             error="No video ID provided"), 400

    # Check if video already processed
    video = db.get_video_by_id(video_id)

    if video and video.processing_status == 'completed':
        # Video already processed, show player
        db.increment_view_count(video_id)
        return render_template('player.html', video=video.to_dict())

    elif video and video.processing_status == 'processing':
        # Video currently processing, show progress
        return render_template('processing.html',
                             video_id=video_id,
                             job_id=video_id)

    elif video and video.processing_status == 'failed':
        # Previous attempt failed, allow retry
        return render_template('error.html',
                             error=f"Previous processing failed: {video.error_message}",
                             video_id=video_id,
                             allow_retry=True)

    else:
        # New video, start processing
        youtube_url = construct_youtube_url(video_id)

        # Create database entry
        try:
            video = db.create_video(video_id, "Processing...", youtube_url)
        except Exception as e:
            # Video might already exist, get it
            video = db.get_video_by_id(video_id)

        # Start Celery background task
        task = process_video_task.delay(video_id, youtube_url)
        task_id_map[video_id] = task.id

        # Show processing page
        return render_template('processing.html',
                             video_id=video_id,
                             job_id=task.id)


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

        # Start Celery task
        task = process_video_task.delay(video_id, youtube_url)
        task_id_map[video_id] = task.id

        return jsonify({
            'success': True,
            'video_id': video_id,
            'task_id': task.id
        })

    except Exception as e:
        error_msg = str(e)
        logger.error("process_video_error", error=error_msg, exc_info=True)
        return jsonify({'error': error_msg}), 500


@app.route('/status/<video_id>')
def get_status(video_id):
    """Get processing status from Celery task"""
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
                **task.info,  # Contains status, progress, video_id
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
            return jsonify({
                'complete': False,
                'status': 'Processing...',
                'progress': 0
            })
    else:
        return jsonify({'error': 'Video not found'}), 404


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
