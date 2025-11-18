"""
Database Module
Tracks processed videos and their metadata
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

Base = declarative_base()


class Video(Base):
    """Video model for tracking processed videos"""
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True)
    video_id = Column(String(20), unique=True, nullable=False, index=True)  # YouTube video ID
    title = Column(String(500))
    original_url = Column(String(500))
    r2_url = Column(String(500))  # Cloudflare R2 storage URL
    duration = Column(Integer)  # Duration in seconds
    processing_status = Column(String(50), default='processing')  # processing, completed, failed
    error_message = Column(String(1000))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    view_count = Column(Integer, default=0)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'video_id': self.video_id,
            'title': self.title,
            'original_url': self.original_url,
            'r2_url': self.r2_url,
            'duration': self.duration,
            'processing_status': self.processing_status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'view_count': self.view_count
        }


class Database:
    def __init__(self, database_url=None):
        """
        Initialize database connection

        Args:
            database_url: PostgreSQL connection string (defaults to env var)
        """
        if database_url is None:
            database_url = os.getenv('DATABASE_URL')

        if not database_url:
            # Fall back to SQLite for local development
            database_url = 'sqlite:///videos.db'

        # Fix for Railway's postgres:// URL (needs to be postgresql://)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)

        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

        # Create tables
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Get database session"""
        return self.Session()

    def close_session(self, session):
        """Close database session"""
        session.close()

    def get_video_by_id(self, video_id):
        """
        Get video by YouTube ID

        Args:
            video_id: YouTube video ID

        Returns:
            Video object or None
        """
        session = self.get_session()
        try:
            video = session.query(Video).filter_by(video_id=video_id).first()
            return video
        finally:
            self.close_session(session)

    def create_video(self, video_id, title, original_url):
        """
        Create new video record

        Args:
            video_id: YouTube video ID
            title: Video title
            original_url: Original YouTube URL

        Returns:
            Video object
        """
        session = self.get_session()
        try:
            video = Video(
                video_id=video_id,
                title=title,
                original_url=original_url,
                processing_status='processing'
            )
            session.add(video)
            session.commit()
            session.refresh(video)
            return video
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session(session)

    def update_video_status(self, video_id, status, error_message=None, r2_url=None):
        """
        Update video processing status

        Args:
            video_id: YouTube video ID
            status: New status (processing, completed, failed)
            error_message: Error message if failed
            r2_url: R2 storage URL if completed

        Returns:
            Updated Video object
        """
        session = self.get_session()
        try:
            video = session.query(Video).filter_by(video_id=video_id).first()
            if video:
                video.processing_status = status
                if error_message:
                    video.error_message = error_message
                if r2_url:
                    video.r2_url = r2_url
                if status == 'completed':
                    video.completed_at = datetime.utcnow()
                session.commit()
                session.refresh(video)
            return video
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session(session)

    def increment_view_count(self, video_id):
        """
        Increment view count for a video

        Args:
            video_id: YouTube video ID
        """
        session = self.get_session()
        try:
            video = session.query(Video).filter_by(video_id=video_id).first()
            if video:
                video.view_count += 1
                session.commit()
        except Exception as e:
            session.rollback()
        finally:
            self.close_session(session)

    def get_recent_videos(self, limit=20):
        """
        Get recently processed videos

        Args:
            limit: Number of videos to return

        Returns:
            List of Video objects
        """
        session = self.get_session()
        try:
            videos = session.query(Video)\
                .filter_by(processing_status='completed')\
                .order_by(Video.completed_at.desc())\
                .limit(limit)\
                .all()
            return videos
        finally:
            self.close_session(session)

    def get_popular_videos(self, limit=20):
        """
        Get most viewed videos

        Args:
            limit: Number of videos to return

        Returns:
            List of Video objects
        """
        session = self.get_session()
        try:
            videos = session.query(Video)\
                .filter_by(processing_status='completed')\
                .order_by(Video.view_count.desc())\
                .limit(limit)\
                .all()
            return videos
        finally:
            self.close_session(session)
