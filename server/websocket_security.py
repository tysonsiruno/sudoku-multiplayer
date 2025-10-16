"""
WebSocket Security Module
Comprehensive security for Socket.IO connections
BUG FIXES: #261-270 (WebSocket Security)
"""

import time
import hmac
import hashlib
from functools import wraps
from flask import request
from flask_socketio import disconnect
from collections import defaultdict
from threading import Lock
import json


# ============================================================================
# BUG #263 FIX: Message Size Limits
# ============================================================================
MAX_MESSAGE_SIZE = 10 * 1024  # 10KB per message
MAX_ROOM_CODE_LENGTH = 10
MAX_USERNAME_LENGTH = 50
MAX_ARRAY_LENGTH = 1000


# ============================================================================
# BUG #266 FIX: Connection Rate Limiting per IP
# ============================================================================
class ConnectionRateLimiter:
    """Rate limit socket connections per IP address"""

    def __init__(self, max_connections_per_minute=10, max_connections_per_hour=100):
        self.max_per_minute = max_connections_per_minute
        self.max_per_hour = max_connections_per_hour
        self.connections = defaultdict(list)  # {ip: [timestamps]}
        self.lock = Lock()

    def is_allowed(self, ip_address):
        """Check if IP is allowed to connect"""
        with self.lock:
            now = time.time()
            timestamps = self.connections[ip_address]

            # Remove old timestamps (older than 1 hour)
            timestamps = [ts for ts in timestamps if now - ts < 3600]
            self.connections[ip_address] = timestamps

            # Check per-minute limit
            recent_minute = [ts for ts in timestamps if now - ts < 60]
            if len(recent_minute) >= self.max_per_minute:
                return False, 'Too many connections per minute'

            # Check per-hour limit
            if len(timestamps) >= self.max_per_hour:
                return False, 'Too many connections per hour'

            # Add current timestamp
            timestamps.append(now)
            return True, None

    def cleanup_old_entries(self):
        """Remove old IP entries to prevent memory bloat"""
        with self.lock:
            now = time.time()
            for ip in list(self.connections.keys()):
                timestamps = [ts for ts in self.connections[ip] if now - ts < 3600]
                if not timestamps:
                    del self.connections[ip]
                else:
                    self.connections[ip] = timestamps


# Global rate limiter instance
connection_rate_limiter = ConnectionRateLimiter()


# ============================================================================
# BUG #270 FIX: Replay Attack Protection
# ============================================================================
class ReplayProtection:
    """Prevent replay attacks on socket messages"""

    def __init__(self, window_seconds=300):
        self.window = window_seconds
        self.seen_nonces = {}  # {nonce: timestamp}
        self.lock = Lock()

    def is_valid(self, nonce, timestamp=None):
        """Check if nonce is valid and not replayed"""
        with self.lock:
            now = time.time()

            # Cleanup old nonces
            self.seen_nonces = {
                n: ts for n, ts in self.seen_nonces.items()
                if now - ts < self.window
            }

            # Check if nonce was already used
            if nonce in self.seen_nonces:
                return False, 'Message replay detected'

            # Check timestamp if provided
            if timestamp:
                if abs(now - timestamp) > self.window:
                    return False, 'Message timestamp out of window'

            # Mark nonce as seen
            self.seen_nonces[nonce] = now
            return True, None


# Global replay protection instance
replay_protection = ReplayProtection()


# ============================================================================
# BUG #268 FIX: Socket Event Schema Validation
# ============================================================================
def validate_message_size(data):
    """Validate message size to prevent memory exhaustion"""
    try:
        size = len(json.dumps(data))
        if size > MAX_MESSAGE_SIZE:
            return False, f'Message too large: {size} bytes (max {MAX_MESSAGE_SIZE})'
        return True, None
    except:
        return False, 'Invalid message format'


def validate_socket_event(schema):
    """
    Decorator to validate socket event data against schema

    BUG #268 FIX: Validate all socket events before processing

    Usage:
        @socketio.on('my_event')
        @validate_socket_event({
            'room_code': {'type': str, 'required': True, 'max_length': 10},
            'username': {'type': str, 'required': True, 'max_length': 50}
        })
        def handle_my_event(data):
            # data is now validated
            pass
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get data from args (Socket.IO passes data as first arg)
            data = args[0] if args else {}

            # BUG #263 FIX: Check message size
            valid, error = validate_message_size(data)
            if not valid:
                return {'success': False, 'message': error}

            # Validate against schema
            if not isinstance(data, dict):
                return {'success': False, 'message': 'Invalid data format'}

            for field, rules in schema.items():
                required = rules.get('required', False)
                field_type = rules.get('type', str)
                max_length = rules.get('max_length')
                min_value = rules.get('min')
                max_value = rules.get('max')
                allowed_values = rules.get('allowed')

                # Check required fields
                if required and field not in data:
                    return {'success': False, 'message': f'Missing required field: {field}'}

                if field in data:
                    value = data[field]

                    # Type validation
                    if not isinstance(value, field_type):
                        return {'success': False, 'message': f'Invalid type for {field}'}

                    # String length validation
                    if field_type == str and max_length and len(value) > max_length:
                        return {'success': False, 'message': f'{field} too long'}

                    # Numeric range validation
                    if field_type in (int, float):
                        if min_value is not None and value < min_value:
                            return {'success': False, 'message': f'{field} too small'}
                        if max_value is not None and value > max_value:
                            return {'success': False, 'message': f'{field} too large'}

                    # Allowed values validation
                    if allowed_values and value not in allowed_values:
                        return {'success': False, 'message': f'Invalid value for {field}'}

                    # Array length validation
                    if isinstance(value, list) and len(value) > MAX_ARRAY_LENGTH:
                        return {'success': False, 'message': f'{field} array too large'}

            return f(*args, **kwargs)
        return wrapped
    return decorator


# ============================================================================
# BUG #264 FIX: Room Permission Verification
# ============================================================================
def verify_room_permission(room_code, username, game_rooms):
    """
    Verify user has permission to access room

    BUG #264 FIX: Verify sender permissions before broadcasting

    Args:
        room_code: Room code to check
        username: Username attempting access
        game_rooms: Global game rooms dict

    Returns:
        (is_allowed: bool, error_message: str or None)
    """
    if room_code not in game_rooms:
        return False, 'Room not found'

    room = game_rooms[room_code]
    players = room.get('players', [])

    # Check if user is in the room
    if username not in [p['username'] for p in players]:
        return False, 'Not authorized for this room'

    return True, None


# ============================================================================
# BUG #269 FIX: Safe Error Messages
# ============================================================================
def safe_error_response(error, debug=False):
    """
    Create safe error response that doesn't leak internal info

    BUG #269 FIX: Don't expose internal state in error messages

    Args:
        error: Exception or error message
        debug: Whether to include debug info (never in production)

    Returns:
        Safe error dict
    """
    # Generic user-facing error messages
    safe_messages = {
        'KeyError': 'Invalid request data',
        'ValueError': 'Invalid data format',
        'TypeError': 'Invalid data type',
        'AttributeError': 'Server error',
        'IndexError': 'Invalid request',
    }

    error_type = type(error).__name__
    message = safe_messages.get(error_type, 'An error occurred')

    response = {
        'success': False,
        'message': message
    }

    # Only include details in debug mode (never in production)
    if debug and not is_production():
        response['debug'] = {
            'type': error_type,
            'details': str(error)
        }

    return response


def is_production():
    """Check if running in production environment"""
    import os
    return os.environ.get('FLASK_ENV') == 'production'


# ============================================================================
# BUG #261 FIX: WebSocket Handshake Validation
# ============================================================================
def validate_websocket_handshake():
    """
    Validate WebSocket handshake to prevent unauthorized connections

    BUG #261 FIX: Validate all WebSocket connections

    Returns:
        (is_valid: bool, error_message: str or None)
    """
    # Check origin header
    origin = request.headers.get('Origin', '')
    allowed_origins = get_allowed_origins()

    if allowed_origins != '*' and origin not in allowed_origins:
        return False, 'Invalid origin'

    # BUG #266 FIX: Check connection rate limit
    ip_address = get_client_ip()
    allowed, message = connection_rate_limiter.is_allowed(ip_address)
    if not allowed:
        return False, message

    return True, None


def get_allowed_origins():
    """Get allowed origins from environment"""
    import os
    origins_str = os.environ.get('CORS_ORIGINS', '*')
    if origins_str == '*':
        return '*'
    return origins_str.split(',')


def get_client_ip():
    """Get client IP address from request"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    return request.environ.get('REMOTE_ADDR', 'unknown')


# ============================================================================
# BUG #262 FIX: Namespaced Room Names
# ============================================================================
def get_namespaced_room(room_code):
    """
    Get namespaced room name to prevent collisions

    BUG #262 FIX: Namespace Socket.IO rooms

    Args:
        room_code: Original room code

    Returns:
        Namespaced room name
    """
    return f'game:{room_code}'


# ============================================================================
# Helper Functions
# ============================================================================
def sanitize_room_code(room_code):
    """Sanitize room code for logging"""
    # BUG #267 FIX: Don't log full room codes in plaintext
    if not room_code or len(room_code) < 3:
        return '***'
    return room_code[:2] + '***'


def get_device_info():
    """Extract device information from user agent"""
    user_agent = request.headers.get('User-Agent', '')

    # Simple device detection
    if 'Mobile' in user_agent or 'Android' in user_agent:
        device_type = 'mobile'
    elif 'Tablet' in user_agent or 'iPad' in user_agent:
        device_type = 'tablet'
    else:
        device_type = 'desktop'

    return {
        'type': device_type,
        'user_agent': user_agent[:200]  # Limit length
    }


# Periodic cleanup task (should be called by scheduler)
def cleanup_security_state():
    """Clean up old security state to prevent memory leaks"""
    connection_rate_limiter.cleanup_old_entries()
    # Replay protection cleans itself up automatically
