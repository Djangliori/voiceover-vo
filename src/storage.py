"""
Cloudflare R2 Storage Module
Handles video upload and retrieval from Cloudflare R2
"""

import os
import boto3
from botocore.config import Config
from pathlib import Path
from src.logging_config import get_logger

logger = get_logger(__name__)


class R2Storage:
    def __init__(self):
        """Initialize Cloudflare R2 client"""
        # R2 credentials from environment
        self.account_id = os.getenv('CLOUDFLARE_ACCOUNT_ID')
        self.access_key_id = os.getenv('R2_ACCESS_KEY_ID')
        self.secret_access_key = os.getenv('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('R2_BUCKET_NAME', 'geyoutube-videos')

        if not all([self.account_id, self.access_key_id, self.secret_access_key]):
            raise ValueError("Missing R2 credentials in environment variables")

        # R2 endpoint
        self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"

        # Initialize S3 client for R2
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )

        # Public URL for videos (if R2 public domain is configured)
        self.public_url = os.getenv('R2_PUBLIC_URL', f"https://videos.geyoutube.com")

    def upload_video(self, local_path, video_id, progress_callback=None):
        """
        Upload video to R2 storage

        Args:
            local_path: Path to local video file
            video_id: YouTube video ID (used as key)
            progress_callback: Optional callback for progress updates

        Returns:
            Public URL of uploaded video
        """
        if progress_callback:
            progress_callback(f"Uploading video to cloud storage...")

        file_path = Path(local_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {local_path}")

        # S3 key (path in bucket)
        s3_key = f"videos/{video_id}_georgian.mp4"

        try:
            # Upload file
            with open(local_path, 'rb') as f:
                self.s3_client.upload_fileobj(
                    f,
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'video/mp4',
                        'CacheControl': 'public, max-age=31536000',  # Cache for 1 year
                    }
                )

            if progress_callback:
                progress_callback(f"Video uploaded successfully!")

            # Return public URL
            return f"{self.public_url}/{s3_key}"

        except Exception as e:
            raise Exception(f"R2 upload error: {str(e)}")

    def get_video_url(self, video_id):
        """
        Get public URL for a video

        Args:
            video_id: YouTube video ID

        Returns:
            Public URL or None if not found
        """
        s3_key = f"videos/{video_id}_georgian.mp4"

        try:
            # Check if object exists
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return f"{self.public_url}/{s3_key}"
        except Exception as e:
            # Log error properly instead of bare except
            logger.error("r2_upload_error", error=str(e), exc_info=True)
            return None
