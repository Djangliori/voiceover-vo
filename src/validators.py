"""
Input validation utilities for API endpoints
"""

import re
from urllib.parse import urlparse, parse_qs
from functools import wraps
from flask import request, jsonify


# YouTube URL patterns
YOUTUBE_PATTERNS = [
    r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
    r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
    r'(?:https?:\/\/)?youtu\.be\/([a-zA-Z0-9_-]{11})',
    r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
]

# Validation constants
MAX_URL_LENGTH = 2048
VALID_VIDEO_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{11}$')


class ValidationError(Exception):
    """Raised when input validation fails"""
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def validate_youtube_url(url):
    """
    Validate YouTube URL format and extract video ID

    Args:
        url: YouTube URL string

    Returns:
        str: Extracted video ID

    Raises:
        ValidationError: If URL is invalid
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL must be a non-empty string")

    # Check URL length
    if len(url) > MAX_URL_LENGTH:
        raise ValidationError(f"URL exceeds maximum length of {MAX_URL_LENGTH} characters")

    # Sanitize URL (remove whitespace)
    url = url.strip()

    # Try to match against YouTube patterns
    for pattern in YOUTUBE_PATTERNS:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            # Validate video ID format
            if VALID_VIDEO_ID_PATTERN.match(video_id):
                return video_id

    # If no pattern matched, raise error
    raise ValidationError(
        "Invalid YouTube URL. Please provide a valid youtube.com or youtu.be URL"
    )


def validate_video_id(video_id):
    """
    Validate video ID format

    Args:
        video_id: Video ID string

    Returns:
        str: Sanitized video ID

    Raises:
        ValidationError: If video ID is invalid
    """
    if not video_id or not isinstance(video_id, str):
        raise ValidationError("Video ID must be a non-empty string")

    video_id = video_id.strip()

    if not VALID_VIDEO_ID_PATTERN.match(video_id):
        raise ValidationError(
            "Invalid video ID format. Must be 11 characters (alphanumeric, hyphens, underscores)"
        )

    return video_id


def validate_json_request(required_fields=None):
    """
    Decorator to validate JSON request body

    Args:
        required_fields: List of required field names
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Check Content-Type
            if not request.is_json:
                return jsonify({
                    'error': 'Content-Type must be application/json'
                }), 400

            # Get JSON data
            try:
                data = request.get_json()
            except Exception:
                return jsonify({
                    'error': 'Invalid JSON in request body'
                }), 400

            if data is None:
                return jsonify({
                    'error': 'Request body must contain valid JSON'
                }), 400

            # Check required fields
            if required_fields:
                missing_fields = [
                    field for field in required_fields
                    if field not in data or not data[field]
                ]
                if missing_fields:
                    return jsonify({
                        'error': f'Missing required fields: {", ".join(missing_fields)}'
                    }), 400

            return f(*args, **kwargs)
        return wrapped
    return decorator


def sanitize_filename(filename):
    """
    Sanitize filename to prevent path traversal attacks

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename

    Raises:
        ValidationError: If filename is invalid or dangerous
    """
    if not filename or not isinstance(filename, str):
        raise ValidationError("Filename must be a non-empty string")

    # Remove any directory components
    filename = filename.split('/')[-1].split('\\')[-1]

    # Check for path traversal attempts
    if '..' in filename or filename.startswith('.'):
        raise ValidationError("Invalid filename: path traversal not allowed")

    # Allow only safe characters: alphanumeric, dots, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        raise ValidationError(
            "Invalid filename: only alphanumeric characters, dots, hyphens, and underscores allowed"
        )

    # Check length
    if len(filename) > 255:
        raise ValidationError("Filename exceeds maximum length of 255 characters")

    return filename
