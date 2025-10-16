"""
Authentication Utilities
Password hashing, JWT generation, validation
"""

import bcrypt
import jwt
import re
import time
import random
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify
import os

# JWT Configuration
# BUG #131 FIX: Warn if using default secret
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-production')
JWT_REFRESH_SECRET = os.environ.get('JWT_REFRESH_SECRET', 'dev-refresh-secret-change-in-production')
if JWT_SECRET == 'dev-secret-key-change-in-production':
    print("WARNING: Using default JWT_SECRET. Set JWT_SECRET environment variable for production!")
if JWT_REFRESH_SECRET == 'dev-refresh-secret-change-in-production':
    print("WARNING: Using default JWT_REFRESH_SECRET. Set JWT_REFRESH_SECRET environment variable for production!")
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
REFRESH_TOKEN_EXPIRES = timedelta(days=7)
REFRESH_TOKEN_EXPIRES_REMEMBER = timedelta(days=30)

# Password Requirements
PASSWORD_MIN_LENGTH = 8
# BUG #133 FIX: Add special character requirement (optional but recommended)
# Current regex: lowercase, uppercase, digit
# To require special char, uncomment the line below:
# PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])')
PASSWORD_REGEX = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)')

# Username Requirements
# BUG #242 FIX: Prevent consecutive underscores
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,20}$')

# Email Validation
# BUG #243 FIX: Simplified regex to prevent ReDoS attacks
# Old regex could cause catastrophic backtracking
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]{0,63}@[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}\.[a-zA-Z]{2,}$')


# ============================================================================
# PASSWORD HASHING
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with cost factor 12

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against a hash

    Args:
        password: Plain text password
        hashed: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    # BUG #135 FIX: Log specific errors for debugging
    # BUG #237 FIX: Add random delay to prevent timing attacks
    # bcrypt already provides constant-time comparison, but add extra protection
    start_time = time.time()
    result = False

    try:
        result = bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError as e:
        print(f'Password verification ValueError: Invalid hash format')
        result = False
    except Exception as e:
        print(f'Password verification error: {type(e).__name__}')
        result = False

    # Add random delay (10-50ms) to make timing attacks harder
    elapsed = time.time() - start_time
    target_time = random.uniform(0.01, 0.05)
    if elapsed < target_time:
        time.sleep(target_time - elapsed)

    return result


def validate_password(password: str) -> tuple:
    """
    Validate password meets requirements

    Requirements:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number

    Returns:
        (is_valid: bool, error_message: str or None)
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f'Password must be at least {PASSWORD_MIN_LENGTH} characters long'

    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter'

    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter'

    if not re.search(r'\d', password):
        return False, 'Password must contain at least one number'

    return True, None


# ============================================================================
# INPUT VALIDATION
# ============================================================================

def validate_username(username: str) -> tuple:
    """
    Validate username format

    Requirements:
    - 3-20 characters
    - Only letters, numbers, and underscores
    - No consecutive underscores
    - Must start with letter or number

    Returns:
        (is_valid: bool, error_message: str or None)
    """
    if not username:
        return False, 'Username is required'

    if len(username) < 3:
        return False, 'Username must be at least 3 characters long'

    if len(username) > 20:
        return False, 'Username must be at most 20 characters long'

    if not USERNAME_REGEX.match(username):
        return False, 'Username can only contain letters, numbers, and underscores'

    # BUG #242 FIX: Prevent consecutive underscores
    if '__' in username:
        return False, 'Username cannot contain consecutive underscores'

    # Must start with letter or number
    if username[0] == '_':
        return False, 'Username must start with a letter or number'

    return True, None


def validate_email(email: str) -> tuple:
    """
    Validate email format

    Returns:
        (is_valid: bool, error_message: str or None)
    """
    if not email:
        return False, 'Email is required'

    if not EMAIL_REGEX.match(email):
        return False, 'Invalid email format'

    if len(email) > 255:
        return False, 'Email is too long'

    return True, None


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize user input - remove potentially dangerous characters

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ''

    # BUG #136, #245 FIX: Remove null bytes, Unicode control characters, and dangerous chars
    # Allow only printable ASCII + common whitespace, remove Unicode control chars
    import unicodedata

    # Remove control characters but keep tab, newline, carriage return
    sanitized = []
    for char in text:
        # Get Unicode category
        category = unicodedata.category(char)
        # Allow: Letter, Number, Punctuation, Symbol, Space, plus explicit whitespace
        if category[0] in ('L', 'N', 'P', 'S', 'Z') or char in '\t\n\r':
            # Skip other control characters (category 'C')
            if category != 'Cc' or char in '\t\n\r':
                sanitized.append(char)

    text = ''.join(sanitized)

    # Trim to max length
    text = text[:max_length]

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


# ============================================================================
# JWT TOKEN GENERATION
# ============================================================================

def generate_access_token(user_id: int, username: str) -> str:
    """
    Generate a JWT access token

    Args:
        user_id: User ID
        username: Username

    Returns:
        JWT token string
    """
    # BUG #137 FIX: Use timezone-aware datetime (datetime.utcnow deprecated in Python 3.12+)
    # BUG #231 FIX: Add JTI (JWT ID) for token blacklisting support
    now = datetime.now(timezone.utc)

    payload = {
        'user_id': user_id,
        'username': username,
        'jti': str(uuid.uuid4()),  # Unique token ID for blacklisting
        'iat': now,
        'exp': now + ACCESS_TOKEN_EXPIRES,
        'type': 'access'
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def generate_refresh_token(user_id: int, session_id: int, remember_me: bool = False) -> str:
    """
    Generate a JWT refresh token

    Args:
        user_id: User ID
        session_id: Session ID
        remember_me: Whether to extend expiration

    Returns:
        JWT token string
    """
    # BUG #138 FIX: Use timezone-aware datetime (datetime.utcnow deprecated in Python 3.12+)
    # BUG #231, #232 FIX: Add JTI for blacklisting and token rotation
    now = datetime.now(timezone.utc)

    expiry = REFRESH_TOKEN_EXPIRES_REMEMBER if remember_me else REFRESH_TOKEN_EXPIRES

    payload = {
        'user_id': user_id,
        'session_id': session_id,
        'jti': str(uuid.uuid4()),  # Unique token ID for blacklisting
        'iat': now,
        'exp': now + expiry,
        'type': 'refresh'
    }
    return jwt.encode(payload, JWT_REFRESH_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate an access token

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict

    Raises:
        jwt.ExpiredSignatureError: If token is expired
        jwt.InvalidTokenError: If token is invalid
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def decode_refresh_token(token: str) -> dict:
    """
    Decode and validate a refresh token

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict

    Raises:
        jwt.ExpiredSignatureError: If token is expired
        jwt.InvalidTokenError: If token is invalid
    """
    return jwt.decode(token, JWT_REFRESH_SECRET, algorithms=[JWT_ALGORITHM])


# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================

def token_required(f):
    """
    Decorator to require valid JWT token

    Usage:
        @app.route('/protected')
        @token_required
        def protected_route(current_user):
            # current_user is passed as first argument
            return jsonify({'message': f'Hello {current_user.username}'})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # BUG #139 FIX: Handle multiple spaces and validate format
                parts = auth_header.strip().split()
                if len(parts) != 2 or parts[0].lower() != 'bearer':
                    return jsonify({'success': False, 'message': 'Invalid authorization header format'}), 401
                token = parts[1]
            except (IndexError, AttributeError):
                return jsonify({'success': False, 'message': 'Invalid authorization header format'}), 401

        if not token:
            return jsonify({'success': False, 'message': 'Authentication token is missing'}), 401

        try:
            # Decode token
            payload = decode_access_token(token)

            # BUG #231 FIX: Check if token is blacklisted
            from models import User, TokenBlacklist
            jti = payload.get('jti')
            if jti and TokenBlacklist.is_blacklisted(jti):
                return jsonify({'success': False, 'message': 'Token has been revoked'}), 401

            # Get user from database
            # BUG #140 FIX: Validate user_id is an integer
            try:
                user_id = int(payload.get('user_id', 0))
            except (ValueError, TypeError):
                return jsonify({'success': False, 'message': 'Invalid token payload'}), 401

            current_user = User.query.filter_by(id=user_id).first()

            if not current_user:
                return jsonify({'success': False, 'message': 'User not found'}), 401

            if current_user.account_status != 'active':
                return jsonify({'success': False, 'message': 'Account is not active'}), 403

            # Pass current user to the route
            return f(current_user, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'success': False, 'message': 'Authentication failed', 'error': str(e)}), 401

    return decorated


def admin_required(f):
    """
    Decorator to require admin privileges (placeholder for future use)

    Usage:
        @app.route('/admin-only')
        @token_required
        @admin_required
        def admin_route(current_user):
            return jsonify({'message': 'Admin access!'})
    """
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        # Placeholder for admin check in future
        # if not current_user.is_admin:
        #     return jsonify({'success': False, 'message': 'Admin privileges required'}), 403

        return f(current_user, *args, **kwargs)

    return decorated


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_client_ip():
    """Get client IP address from request"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
    return request.environ.get('REMOTE_ADDR')


def get_user_agent():
    """Get user agent from request"""
    return request.headers.get('User-Agent', '')[:500]  # Limit length


def simulate_operation_delay():
    """
    BUG #236 FIX: Add random delay to prevent account enumeration
    Makes all authentication operations take similar time
    """
    delay = random.uniform(0.05, 0.15)  # 50-150ms random delay
    time.sleep(delay)


def blacklist_token(token_string: str, reason='logout'):
    """
    BUG #231 FIX: Blacklist a JWT token

    Args:
        token_string: The JWT token to blacklist
        reason: Reason for blacklisting ('logout', 'password_change', 'security')

    Returns:
        True if successful, False otherwise
    """
    try:
        from models import TokenBlacklist, db

        # Decode token to get JTI and expiration
        try:
            payload = jwt.decode(token_string, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except:
            # Try refresh token secret
            try:
                payload = jwt.decode(token_string, JWT_REFRESH_SECRET, algorithms=[JWT_ALGORITHM])
            except:
                return False

        jti = payload.get('jti')
        if not jti:
            return False

        exp_timestamp = payload.get('exp')
        if exp_timestamp:
            expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        else:
            # Default to 1 day if no expiration
            expires_at = datetime.now(timezone.utc) + timedelta(days=1)

        # Add to blacklist
        TokenBlacklist.blacklist_token(
            jti=jti,
            token_type=payload.get('type', 'unknown'),
            user_id=payload.get('user_id'),
            expires_at=expires_at,
            reason=reason
        )
        db.session.commit()
        return True

    except Exception as e:
        print(f'Error blacklisting token: {e}')
        return False


def invalidate_all_user_sessions(user_id: int):
    """
    BUG #240 FIX: Invalidate all sessions for a user
    Used when password changes or security breach

    Args:
        user_id: User ID to invalidate sessions for
    """
    from models import Session
    Session.invalidate_all_for_user(user_id)
