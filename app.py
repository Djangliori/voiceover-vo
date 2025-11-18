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
import threading
import uuid
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Load environment variables
load_dotenv()

# Set Google credentials if file exists
google_creds_path = os.path.join(
    os.path.dirname(__file__),
    os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google-credentials.json')
)
if os.path.exists(google_creds_path):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_creds_path

# Import processing modules
from src.downloader import VideoDownloader
from src.transcriber import Transcriber
from src.translator import Translator
from src.tts import TextToSpeech
from src.audio_mixer import AudioMixer
from src.video_processor import VideoProcessor
from src.database import Database
from src.storage import R2Storage

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
except Exception as e:
    print(f"R2 storage not configured: {e}")
    storage = None
    use_r2 = False

# Store processing status
processing_status = {}


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

        # Start background processing
        thread = threading.Thread(
            target=process_video_background,
            args=(video_id, youtube_url)
        )
        thread.daemon = True
        thread.start()

        # Show processing page
        return render_template('processing.html',
                             video_id=video_id,
                             job_id=video_id)


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


def process_video_background(video_id, youtube_url):
    """Background processing function"""
    try:
        def update_status(message, progress=None):
            processing_status[video_id] = {
                'status': message,
                'progress': progress or 0,
                'video_id': video_id
            }
            print(f"[{video_id}] {message}")

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
            # Use local file path
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
        traceback.print_exc()
        processing_status[video_id] = {
            'status': f"Error: {error_msg}",
            'error': error_msg,
            'complete': False,
            'progress': 0
        }
        db.update_video_status(video_id, 'failed', error_message=error_msg)


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

        # Start processing in background
        thread = threading.Thread(
            target=process_video_background,
            args=(video_id, youtube_url)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'video_id': video_id
        })

    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500


@app.route('/status/<video_id>')
def get_status(video_id):
    """Get processing status"""
    # Check in-memory status first
    if video_id in processing_status:
        return jsonify(processing_status[video_id])

    # Check database
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
