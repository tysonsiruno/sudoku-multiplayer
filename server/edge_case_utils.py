"""
Edge Case Utilities
Comprehensive validation and error handling utilities
Fixes bugs #381-400
"""

import os
import time
import secrets
from datetime import datetime, timezone, timedelta
from functools import wraps


# ============================================================================
# NULL/UNDEFINED HANDLING (#381-390)
# ============================================================================

# BUG #381 FIX: Validate board_seed generation
def generate_board_seed_safe():
    """Generate board seed with fallback"""
    try:
        seed = secrets.randbelow(999999) + 1
        if seed is None or seed == 0:
            # Fallback to timestamp-based seed
            seed = int(time.time() * 1000) % 1000000
        return seed
    except Exception as e:
        print(f"Seed generation error: {e}")
        return int(time.time() * 1000) % 1000000


# BUG #382, #383 FIX: Safe dictionary access
def safe_get(dictionary, key, default=None):
    """Safely get value from dictionary"""
    if dictionary is None:
        return default
    if not isinstance(dictionary, dict):
        return default
    return dictionary.get(key, default)


# BUG #384-390 FIX: Validate all database operations
def validate_db_record(record, required_fields):
    """
    Validate database record has required fields

    Args:
        record: Database model instance
        required_fields: List of field names

    Returns:
        (is_valid: bool, missing_fields: list)
    """
    if record is None:
        return False, required_fields

    missing = []
    for field in required_fields:
        value = getattr(record, field, None)
        if value is None:
            missing.append(field)

    return len(missing) == 0, missing


# ============================================================================
# BOUNDARY CONDITIONS (#391-400)
# ============================================================================

# BUG #391 FIX: Dynamic Max Players
MAX_PLAYERS_PER_ROOM = int(os.environ.get('MAX_PLAYERS_PER_ROOM', 10))
MIN_PLAYERS_PER_ROOM = 2


def validate_max_players(max_players):
    """Validate max players is within bounds"""
    try:
        max_players = int(max_players)
    except (ValueError, TypeError):
        return False, "Invalid max players value"

    if max_players < MIN_PLAYERS_PER_ROOM:
        return False, f"Minimum {MIN_PLAYERS_PER_ROOM} players required"

    if max_players > MAX_PLAYERS_PER_ROOM:
        return False, f"Maximum {MAX_PLAYERS_PER_ROOM} players allowed"

    return True, None


# BUG #392 FIX: Room Code Exhaustion Handling
def cleanup_inactive_rooms(game_rooms, max_age_minutes=30):
    """Remove rooms older than max_age_minutes"""
    cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
    removed = 0

    for code in list(game_rooms.keys()):
        room = game_rooms.get(code)
        if not room:
            continue

        created_at_str = safe_get(room, 'created_at')

        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str)
                if created_at < cutoff:
                    del game_rooms[code]
                    removed += 1
            except:
                pass

    return removed


def generate_room_code_with_retry(game_rooms, max_attempts=100):
    """
    Generate unique room code with exhaustion detection

    Returns:
        (code: str or None, error: str or None)
    """
    for attempt in range(max_attempts):
        code = str(secrets.randbelow(1000000)).zfill(6)

        if code not in game_rooms:
            return code, None

    # Exhaustion detected - clean up old rooms
    cleanup_inactive_rooms(game_rooms)

    # Try again after cleanup
    for attempt in range(max_attempts):
        code = str(secrets.randbelow(1000000)).zfill(6)
        if code not in game_rooms:
            return code, None

    return None, "Server at capacity - all room codes in use"


# BUG #393-394 FIX: Score & Time Validation
SCORE_MIN = 0
SCORE_MAX = int(os.environ.get('MAX_SCORE', 100000))  # Allow higher scores
TIME_MIN = 0
TIME_MAX = int(os.environ.get('MAX_TIME', 172800))  # 48 hours


def validate_score_and_time(score, time_seconds):
    """
    Validate score and time are within acceptable bounds

    Returns:
        (is_valid: bool, clamped_score: int, clamped_time: int, errors: list)
    """
    errors = []

    # Validate types
    try:
        score = int(score)
    except (ValueError, TypeError):
        errors.append("Invalid score type")
        score = 0

    try:
        time_seconds = int(time_seconds)
    except (ValueError, TypeError):
        errors.append("Invalid time type")
        time_seconds = 0

    # Clamp to bounds
    clamped_score = max(SCORE_MIN, min(score, SCORE_MAX))
    clamped_time = max(TIME_MIN, min(time_seconds, TIME_MAX))

    if score != clamped_score:
        errors.append(f"Score clamped from {score} to {clamped_score}")

    if time_seconds != clamped_time:
        errors.append(f"Time clamped from {time_seconds} to {clamped_time}")

    is_valid = len(errors) == 0
    return is_valid, clamped_score, clamped_time, errors


# BUG #395 FIX: Username Length Validation (already in auth.py, but documenting bounds)
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20


# BUG #396-397 FIX: Board Size Validation
BOARD_MIN_SIZE = 5
BOARD_MAX_SIZE = 100


def validate_board_size(rows, cols):
    """Validate board dimensions"""
    errors = []

    # Check for zero/negative
    if rows <= 0 or cols <= 0:
        errors.append('Board dimensions must be positive')

    # Check minimum
    if rows < BOARD_MIN_SIZE or cols < BOARD_MIN_SIZE:
        errors.append(f'Board must be at least {BOARD_MIN_SIZE}x{BOARD_MIN_SIZE}')

    # Check maximum
    if rows > BOARD_MAX_SIZE or cols > BOARD_MAX_SIZE:
        errors.append(f'Board must be at most {BOARD_MAX_SIZE}x{BOARD_MAX_SIZE}')

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


# BUG #398 FIX: Integer Overflow Protection
MAX_SAFE_INTEGER = 2**53 - 1  # JavaScript's Number.MAX_SAFE_INTEGER


def safe_multiply(a, b):
    """Multiply with overflow protection"""
    if a == 0 or b == 0:
        return 0

    result = a * b

    # Check for overflow
    if result > MAX_SAFE_INTEGER or result < 0:
        print(f"Integer overflow prevented: {a} * {b}")
        return MAX_SAFE_INTEGER

    return result


def calculate_score_safe(base_score, multiplier=1):
    """Calculate score with overflow protection"""
    score = safe_multiply(base_score, multiplier)
    return min(score, SCORE_MAX)


# BUG #399-400 FIX: Timestamp & Timezone Handling
def validate_timestamp(timestamp):
    """
    Validate timestamp is reasonable

    Returns:
        (is_valid: bool, normalized_timestamp: datetime)
    """
    if timestamp is None:
        return False, datetime.now(timezone.utc)

    # If already datetime, validate it
    if isinstance(timestamp, datetime):
        # Check if in reasonable range (not in far past/future)
        now = datetime.now(timezone.utc)
        min_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        max_date = now + timedelta(days=365)

        if timestamp < min_date:
            return False, now
        if timestamp > max_date:
            return False, now

        return True, timestamp

    # If unix timestamp, convert
    if isinstance(timestamp, (int, float)):
        # Check for negative (bug #399)
        if timestamp < 0:
            return False, datetime.now(timezone.utc)

        # Check for reasonable range
        if timestamp < 1577836800:  # 2020-01-01
            return False, datetime.now(timezone.utc)

        try:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return True, dt
        except:
            return False, datetime.now(timezone.utc)

    return False, datetime.now(timezone.utc)


def normalize_timestamp(dt):
    """Convert any datetime to UTC"""
    if dt is None:
        return datetime.now(timezone.utc)

    # If naive, assume UTC
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    # Convert to UTC
    return dt.astimezone(timezone.utc)


# ============================================================================
# ERROR HANDLING DECORATOR
# ============================================================================

def safe_route(f):
    """Decorator to handle all errors gracefully"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            from flask import jsonify
            return jsonify({
                'success': False,
                'message': 'Invalid input value',
                'error_type': 'validation_error'
            }), 400
        except KeyError as e:
            from flask import jsonify
            return jsonify({
                'success': False,
                'message': 'Missing required field',
                'error_type': 'missing_field'
            }), 400
        except Exception as e:
            from flask import jsonify
            # Log full error
            print(f"Unexpected error in {f.__name__}: {e}")

            # Return generic error to user
            return jsonify({
                'success': False,
                'message': 'An error occurred',
                'error_type': 'server_error'
            }), 500
    return wrapper


# ============================================================================
# VALIDATION SUMMARY
# ============================================================================

def validate_all_inputs(data, schema):
    """
    Comprehensive input validation

    Args:
        data: Dictionary of input data
        schema: Dictionary of field requirements
            {
                'field_name': {
                    'type': int|str|bool,
                    'required': True|False,
                    'min': value (optional),
                    'max': value (optional),
                    'choices': [list] (optional)
                }
            }

    Returns:
        (is_valid: bool, validated_data: dict, errors: list)
    """
    errors = []
    validated = {}

    for field, rules in schema.items():
        value = data.get(field)

        # Check required
        if rules.get('required') and value is None:
            errors.append(f"{field} is required")
            continue

        if value is None:
            continue

        # Type validation
        expected_type = rules.get('type')
        if expected_type:
            try:
                if expected_type == int:
                    value = int(value)
                elif expected_type == str:
                    value = str(value)
                elif expected_type == bool:
                    value = bool(value)
            except (ValueError, TypeError):
                errors.append(f"{field} must be {expected_type.__name__}")
                continue

        # Range validation
        if 'min' in rules and value < rules['min']:
            errors.append(f"{field} must be at least {rules['min']}")
            continue

        if 'max' in rules and value > rules['max']:
            errors.append(f"{field} must be at most {rules['max']}")
            continue

        # Choices validation
        if 'choices' in rules and value not in rules['choices']:
            errors.append(f"{field} must be one of {rules['choices']}")
            continue

        validated[field] = value

    return len(errors) == 0, validated, errors
