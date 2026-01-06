"""
Authentication Module
Handles user login, logout, registration, and session management
"""

import os
import functools
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, g
from src.database import Database, User, Tier
from src.logging_config import get_logger

logger = get_logger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Initialize database
db = Database()

# Import rate limiter (initialized in app.py)
from src.rate_limit_config import limiter


def login_required(f):
    """Decorator to require login for a route"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401

        # Load user into g
        user = db.get_user_by_id(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            return jsonify({'error': 'Invalid session'}), 401

        g.user = user
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin access"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401

        user = db.get_user_by_id(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            return jsonify({'error': 'Invalid session'}), 401

        if not user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403

        g.user = user
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get currently logged in user or None"""
    if 'user_id' not in session:
        return None
    return db.get_user_by_id(session['user_id'])


def validate_password_strength(password):
    """
    Validate password meets security requirements.

    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 12:
        return False, 'Password must be at least 12 characters long'

    if not any(c.isupper() for c in password):
        return False, 'Password must contain at least one uppercase letter'

    if not any(c.islower() for c in password):
        return False, 'Password must contain at least one lowercase letter'

    if not any(c.isdigit() for c in password):
        return False, 'Password must contain at least one number'

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, 'Password must contain at least one special character (!@#$%^&*...)'

    return True, None


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per hour")
@limiter.limit("10 per day")
def register():
    """
    Register a new user.

    Rate limited to prevent abuse:
    - 5 registration attempts per hour per IP
    - 10 registration attempts per day per IP
    """
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        name = data.get('name', '').strip()

        # Email validation
        if not email or '@' not in email:
            return jsonify({'error': 'Valid email required'}), 400

        # Password strength validation
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            return jsonify({'error': error_msg}), 400

        # Create user (defaults to free tier)
        user = db.create_user(email=email, password=password, name=name, tier_name='free')

        # Auto-login after registration
        session['user_id'] = user.id
        session.permanent = True

        logger.info(f"New user registered: {email}")

        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'message': 'Registration successful'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per hour")
@limiter.limit("30 per day")
def login():
    """
    Login user.

    Rate limited to prevent brute force attacks:
    - 10 login attempts per hour per IP
    - 30 login attempts per day per IP
    """
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        user = db.authenticate_user(email, password)

        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401

        # Set session
        session['user_id'] = user.id
        session.permanent = True

        logger.info(f"User logged in: {email}")

        return jsonify({
            'success': True,
            'user': user.to_dict()
        })

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'})


@auth_bp.route('/me', methods=['GET'])
def get_me():
    """Get current user info"""
    user = get_current_user()
    if not user:
        return jsonify({'authenticated': False})

    return jsonify({
        'authenticated': True,
        'user': user.to_dict()
    })


@auth_bp.route('/check-usage', methods=['GET'])
@login_required
def check_usage():
    """Check if user can process more videos"""
    user = g.user
    remaining = user.get_remaining_minutes()

    return jsonify({
        'can_process': remaining > 0,
        'minutes_remaining': remaining if remaining != float('inf') else -1,
        'minutes_used': user.minutes_used_this_month,
        'tier': user.tier.to_dict() if user.tier else None
    })


# ==================== Admin Routes ====================

@auth_bp.route('/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    """Get all users (admin only)"""
    users = db.get_all_users()
    return jsonify({
        'users': [u.to_dict() for u in users]
    })


@auth_bp.route('/admin/users/<int:user_id>/tier', methods=['PUT'])
@admin_required
def admin_update_tier(user_id):
    """Update user's tier (admin only)"""
    try:
        data = request.json
        tier_name = data.get('tier')

        if not tier_name:
            return jsonify({'error': 'Tier name required'}), 400

        user = db.update_user_tier(user_id, tier_name)

        return jsonify({
            'success': True,
            'message': f'User tier updated to {tier_name}'
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Admin tier update error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to update tier'}), 500


@auth_bp.route('/admin/tiers', methods=['GET'])
@admin_required
def admin_get_tiers():
    """Get all tiers (admin only)"""
    tiers = db.get_all_tiers()
    return jsonify({
        'tiers': [t.to_dict() for t in tiers]
    })


def init_admin_user():
    """
    Initialize the default admin user if not exists.

    Admin credentials MUST be set via environment variables:
    - ADMIN_EMAIL: Admin user email
    - ADMIN_PASSWORD: Admin user password (minimum 12 characters)
    - ADMIN_NAME: Admin user display name (optional, defaults to 'Admin')

    SECURITY: Never hardcode credentials in source code!
    """
    try:
        # Get admin credentials from environment variables
        admin_email = os.getenv('ADMIN_EMAIL')
        admin_password = os.getenv('ADMIN_PASSWORD')
        admin_name = os.getenv('ADMIN_NAME', 'Admin')

        # Validate that credentials are provided
        if not admin_email or not admin_password:
            logger.warning(
                "Admin user initialization skipped: ADMIN_EMAIL and ADMIN_PASSWORD "
                "environment variables must be set to create admin user"
            )
            return

        # Validate password strength
        if len(admin_password) < 12:
            logger.error(
                "Admin user initialization failed: ADMIN_PASSWORD must be at least 12 characters"
            )
            raise ValueError("Admin password must be at least 12 characters")

        existing = db.get_user_by_email(admin_email)
        if existing:
            logger.info(f"Admin user already exists: {admin_email}")
            return

        # Initialize tiers first
        db.init_default_tiers()

        # Create admin user
        db.create_admin_user(
            email=admin_email,
            password=admin_password,
            name=admin_name
        )
        logger.info(f"Admin user created successfully: {admin_email}")

    except Exception as e:
        logger.error(f"Failed to initialize admin user: {e}", exc_info=True)
