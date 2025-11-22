"""
Database Module
Tracks processed videos, users, and usage
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Boolean, Float, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from src.logging_config import get_logger

logger = get_logger(__name__)

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
    progress = Column(Integer, default=0)  # Progress percentage (0-100)
    status_message = Column(String(500))  # Current processing step message
    error_message = Column(Text)  # Use Text for long error messages
    debug_data = Column(Text)  # JSON: transcription, translation, TTS details for debugging
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
            'progress': self.progress,
            'status_message': self.status_message,
            'error_message': self.error_message,
            'debug_data': self.debug_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'view_count': self.view_count
        }


class Tier(Base):
    """Subscription tier model"""
    __tablename__ = 'tiers'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # free, basic, pro, unlimited
    display_name = Column(String(100), nullable=False)  # "Free", "Basic", "Pro", "Unlimited"
    minutes_per_month = Column(Integer, nullable=False)  # -1 for unlimited
    price_monthly = Column(Float, default=0.0)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    users = relationship("User", back_populates="tier")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'minutes_per_month': self.minutes_per_month,
            'price_monthly': self.price_monthly,
            'description': self.description,
            'is_active': self.is_active
        }


class User(Base):
    """User model for authentication and usage tracking"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100))
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Tier relationship
    tier_id = Column(Integer, ForeignKey('tiers.id'), nullable=False)
    tier = relationship("Tier", back_populates="users")

    # Usage tracking
    minutes_used_this_month = Column(Float, default=0.0)
    usage_reset_date = Column(DateTime, default=datetime.utcnow)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    # Relationship to videos processed by this user
    videos = relationship("UserVideo", back_populates="user")

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)

    def get_remaining_minutes(self):
        """Get remaining minutes for this month"""
        if self.tier.minutes_per_month == -1:
            return float('inf')  # Unlimited
        return max(0, self.tier.minutes_per_month - self.minutes_used_this_month)

    def can_process_video(self, video_duration_seconds):
        """Check if user has enough minutes to process a video"""
        video_minutes = video_duration_seconds / 60
        return self.get_remaining_minutes() >= video_minutes

    def add_usage(self, minutes):
        """Add usage minutes"""
        self.minutes_used_this_month += minutes

    def reset_monthly_usage(self):
        """Reset usage for new month"""
        self.minutes_used_this_month = 0.0
        self.usage_reset_date = datetime.utcnow()

    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'tier': self.tier.to_dict() if self.tier else None,
            'minutes_used_this_month': self.minutes_used_this_month,
            'minutes_remaining': self.get_remaining_minutes() if self.tier else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
        return data


class UserVideo(Base):
    """Track which user processed which video"""
    __tablename__ = 'user_videos'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    video_id = Column(String(20), ForeignKey('videos.video_id'), nullable=False)
    minutes_charged = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="videos")

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'video_id': self.video_id,
            'minutes_charged': self.minutes_charged,
            'created_at': self.created_at.isoformat() if self.created_at else None
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
            logger.warning("DATABASE_URL not set! Using SQLite fallback. This will cause issues if Flask and Celery use different databases!")

        # Fix for Railway's postgres:// URL (needs to be postgresql://)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)

        # Log which database we're connecting to (mask password)
        safe_url = database_url
        if '@' in safe_url:
            # Mask password in URL for logging
            import re
            safe_url = re.sub(r'://[^:]+:[^@]+@', '://***:***@', safe_url)
        logger.info(f"Database connection: {safe_url}")

        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

        # Create tables
        Base.metadata.create_all(self.engine)

        # Run migrations for new columns
        self._run_migrations()

    def get_session(self):
        """Get database session"""
        return self.Session()

    def close_session(self, session):
        """Close database session"""
        session.close()

    def _run_migrations(self):
        """Run database migrations for new columns"""
        from sqlalchemy import inspect, text

        inspector = inspect(self.engine)

        # Check if videos table exists
        if 'videos' not in inspector.get_table_names():
            return

        # Get existing columns in videos table
        columns = {col['name'] for col in inspector.get_columns('videos')}

        # Add debug_data column if it doesn't exist
        if 'debug_data' not in columns:
            with self.engine.connect() as conn:
                try:
                    conn.execute(text('ALTER TABLE videos ADD COLUMN debug_data TEXT'))
                    conn.commit()
                    logger.info("Migration: Added debug_data column to videos table")
                except Exception as e:
                    logger.warning(f"Migration: debug_data column may already exist: {e}")

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
            # Expire all to force fresh data from database
            session.expire_all()
            video = session.query(Video).filter_by(video_id=video_id).first()
            if video:
                # Refresh to get latest data
                session.refresh(video)
                # Detach from session to avoid LazyLoadingError after session closes
                session.expunge(video)
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
            # Detach from session before returning
            session.expunge(video)
            return video
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session(session)

    def update_video_progress(self, video_id, status_message, progress):
        """
        Update video progress and status message

        Args:
            video_id: YouTube video ID
            status_message: Current status message
            progress: Progress percentage (0-100)

        Returns:
            Updated Video object
        """
        session = self.get_session()
        try:
            video = session.query(Video).filter_by(video_id=video_id).first()
            if video:
                video.processing_status = 'processing'
                video.progress = progress
                video.status_message = status_message
                session.commit()
                return video
            else:
                logger.error(f"Video not found for progress update: {video_id}")
                return None
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating progress: {e}")
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

    def save_debug_data(self, video_id, debug_data):
        """
        Save debug data (transcription, translation, TTS details) for a video

        Args:
            video_id: YouTube video ID
            debug_data: Dictionary with pipeline debug info
        """
        import json
        session = self.get_session()
        try:
            video = session.query(Video).filter_by(video_id=video_id).first()
            if video:
                video.debug_data = json.dumps(debug_data, ensure_ascii=False)
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save debug data: {e}")
        finally:
            self.close_session(session)

    def get_debug_data(self, video_id):
        """
        Get debug data for a video

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with debug data or None
        """
        import json
        video = self.get_video(video_id)
        if video and video.debug_data:
            try:
                return json.loads(video.debug_data)
            except:
                return None
        return None

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

    # ==================== Tier Management ====================

    def init_default_tiers(self):
        """Initialize default subscription tiers"""
        session = self.get_session()
        try:
            # Check if tiers already exist
            existing = session.query(Tier).first()
            if existing:
                logger.info("Tiers already initialized")
                return

            default_tiers = [
                Tier(
                    name='free',
                    display_name='Free',
                    minutes_per_month=10,
                    price_monthly=0.0,
                    description='10 minutes per month for free'
                ),
                Tier(
                    name='basic',
                    display_name='Basic',
                    minutes_per_month=60,
                    price_monthly=9.99,
                    description='60 minutes per month'
                ),
                Tier(
                    name='pro',
                    display_name='Pro',
                    minutes_per_month=300,
                    price_monthly=29.99,
                    description='300 minutes per month'
                ),
                Tier(
                    name='unlimited',
                    display_name='Unlimited',
                    minutes_per_month=-1,
                    price_monthly=99.99,
                    description='Unlimited minutes'
                )
            ]

            for tier in default_tiers:
                session.add(tier)

            session.commit()
            logger.info("Default tiers initialized successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to initialize tiers: {e}")
            raise
        finally:
            self.close_session(session)

    def get_tier_by_name(self, name):
        """Get tier by name"""
        session = self.get_session()
        try:
            tier = session.query(Tier).filter_by(name=name).first()
            if tier:
                session.expunge(tier)
            return tier
        finally:
            self.close_session(session)

    def get_all_tiers(self):
        """Get all active tiers"""
        session = self.get_session()
        try:
            tiers = session.query(Tier).filter_by(is_active=True).all()
            for tier in tiers:
                session.expunge(tier)
            return tiers
        finally:
            self.close_session(session)

    # ==================== User Management ====================

    def create_user(self, email, password, name=None, tier_name='free'):
        """Create a new user"""
        session = self.get_session()
        try:
            # Check if user already exists
            existing = session.query(User).filter_by(email=email).first()
            if existing:
                raise ValueError("User with this email already exists")

            # Get the tier
            tier = session.query(Tier).filter_by(name=tier_name).first()
            if not tier:
                # Initialize tiers if not exists
                self.init_default_tiers()
                tier = session.query(Tier).filter_by(name=tier_name).first()

            user = User(
                email=email,
                name=name,
                tier_id=tier.id
            )
            user.set_password(password)

            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

            logger.info(f"User created: {email}")
            return user
        except Exception as e:
            session.rollback()
            raise
        finally:
            self.close_session(session)

    def get_user_by_email(self, email):
        """Get user by email"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(email=email).first()
            if user:
                # Eagerly load tier
                _ = user.tier
                session.expunge(user)
            return user
        finally:
            self.close_session(session)

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                _ = user.tier
                session.expunge(user)
            return user
        finally:
            self.close_session(session)

    def authenticate_user(self, email, password):
        """Authenticate user and update last login"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(email=email, is_active=True).first()
            if user and user.check_password(password):
                user.last_login = datetime.utcnow()
                session.commit()
                _ = user.tier
                session.expunge(user)
                return user
            return None
        finally:
            self.close_session(session)

    def update_user_tier(self, user_id, tier_name):
        """Update user's subscription tier"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            tier = session.query(Tier).filter_by(name=tier_name).first()

            if not user:
                raise ValueError("User not found")
            if not tier:
                raise ValueError("Tier not found")

            user.tier_id = tier.id
            session.commit()
            logger.info(f"User {user.email} tier updated to {tier_name}")
            return user
        except Exception as e:
            session.rollback()
            raise
        finally:
            self.close_session(session)

    def add_user_usage(self, user_id, minutes):
        """Add usage minutes to user"""
        session = self.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.add_usage(minutes)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise
        finally:
            self.close_session(session)

    def get_all_users(self):
        """Get all users (for admin)"""
        session = self.get_session()
        try:
            users = session.query(User).all()
            for user in users:
                _ = user.tier
                session.expunge(user)
            return users
        finally:
            self.close_session(session)

    def create_admin_user(self, email, password, name=None):
        """Create an admin user"""
        session = self.get_session()
        try:
            # Get unlimited tier for admin
            tier = session.query(Tier).filter_by(name='unlimited').first()
            if not tier:
                self.init_default_tiers()
                tier = session.query(Tier).filter_by(name='unlimited').first()

            user = User(
                email=email,
                name=name,
                tier_id=tier.id,
                is_admin=True
            )
            user.set_password(password)

            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

            logger.info(f"Admin user created: {email}")
            return user
        except Exception as e:
            session.rollback()
            raise
        finally:
            self.close_session(session)

    def record_user_video(self, user_id, video_id, minutes_charged):
        """Record that a user processed a video"""
        session = self.get_session()
        try:
            user_video = UserVideo(
                user_id=user_id,
                video_id=video_id,
                minutes_charged=minutes_charged
            )
            session.add(user_video)

            # Also add to user's usage
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                user.add_usage(minutes_charged)

            session.commit()
            return user_video
        except Exception as e:
            session.rollback()
            raise
        finally:
            self.close_session(session)
