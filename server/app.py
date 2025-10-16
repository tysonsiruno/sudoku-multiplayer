"""
Sudoku Multiplayer Server
Flask + Socket.IO backend for multiplayer functionality
(Adapted from Minesweeper Multiplayer)
"""

import os
import secrets
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, 'web')

# Initialize Flask app
app = Flask(__name__, static_folder=WEB_DIR, static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Database Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
# BUG #104 FIX: Only replace first occurrence
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = 'postgresql://' + DATABASE_URL[11:]

# BUG #281 FIX: Enhanced database configuration with proper pooling
from database_utils import get_db_pool_config

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///sudoku.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# BUG #281, #286 FIX: Optimized connection pooling
environment = os.environ.get('FLASK_ENV', 'production')
pool_config = get_db_pool_config(environment)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = pool_config

# Initialize extensions
# BUG #111 FIX: Configure CORS properly for production
cors_origins = os.environ.get('CORS_ORIGINS', '*').split(',') if os.environ.get('FLASK_ENV') != 'development' else '*'
CORS(app, origins=cors_origins)
socketio = SocketIO(app, cors_allowed_origins=cors_origins)

# BUG #112 FIX: Rate limiter with proper storage configuration
# memory:// doesn't work across multiple processes - warn if not using Redis
rate_limit_storage = os.environ.get('REDIS_URL')
if not rate_limit_storage:
    print("WARNING: No REDIS_URL configured. Rate limiting will not work across multiple processes.")
    rate_limit_storage = 'memory://'

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=rate_limit_storage
)

# Initialize database
# BUG #231 FIX: Import TokenBlacklist for JWT blacklisting
from models import db, User, Session, GameHistory, PasswordResetToken, SecurityAuditLog, TokenBlacklist

db.init_app(app)

# Import authentication utilities
# BUG #231, #236, #240 FIX: Import new security functions
from auth import (
    hash_password, verify_password, validate_password, validate_username, validate_email,
    generate_access_token, generate_refresh_token, decode_access_token, decode_refresh_token,
    token_required, get_client_ip, get_user_agent, sanitize_input,
    blacklist_token, invalidate_all_user_sessions, simulate_operation_delay
)

# Import WebSocket security
# BUG #261-270 FIX: WebSocket security middleware
from websocket_security import (
    validate_socket_event, validate_websocket_handshake, verify_room_permission,
    safe_error_response, get_namespaced_room, sanitize_room_code,
    connection_rate_limiter, get_device_info, cleanup_security_state
)

# Import Edge Case utilities
# BUG #381-400 FIX: Comprehensive validation and error handling
from edge_case_utils import (
    safe_get, validate_db_record, validate_max_players,
    cleanup_inactive_rooms, generate_room_code_with_retry,
    validate_score_and_time, validate_board_size,
    safe_multiply, validate_timestamp, normalize_timestamp,
    safe_route, validate_all_inputs
)

# Import Sudoku generator
from sudoku_generator import sudoku_generator

# Import email service
from email_service import (
    send_verification_email, send_password_reset_email,
    send_account_locked_email, send_welcome_email
)

# Create database tables
with app.app_context():
    db.create_all()
    print("Database tables created successfully!")

# BUG #105, #354 FIX: Thread-safe in-memory storage with size limits
from concurrency import ThreadSafeDict, create_room_atomic, join_room_atomic

game_rooms = ThreadSafeDict()  # {room_code: {host, players, difficulty, status, puzzle, solution, initial_cells, player_cells, mistakes, hints_used}}
player_sessions = ThreadSafeDict()  # {session_id: {username, room_code}}
MAX_ROOMS = 1000  # Prevent memory exhaustion
MAX_SESSIONS = 10000

def generate_room_code():
    """Generate a unique 6-digit numeric room code"""
    # BUG #392 FIX: Use enhanced room code generation with retry and cleanup
    code, error = generate_room_code_with_retry(game_rooms)
    if error:
        raise Exception(error)
    return code

# Security headers middleware
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Web Client Routes

@app.route('/')
def index():
    """Serve the web client"""
    return send_from_directory(WEB_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(WEB_DIR, path)

# REST API Endpoints

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Render"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per hour")
def register():
    """User registration"""
    data = request.json
    username = sanitize_input(data.get('username', ''), 20)
    email = sanitize_input(data.get('email', ''), 255).lower()
    password = data.get('password', '')

    # Validation
    valid, msg = validate_username(username)
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400

    valid, msg = validate_email(email)
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400

    valid, msg = validate_password(password)
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400

    # Check if username or email already exists
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Username already taken'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 400

    # Create user
    try:
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password)
        )
        db.session.add(user)
        db.session.commit()

        SecurityAuditLog.log_action(user.id, 'register', True, get_client_ip(), get_user_agent())

        return jsonify({'success': True, 'message': 'Registration successful! You can now log in.', 'user_id': user.id})
    except Exception as e:
        db.session.rollback()
        # BUG #81 FIX: Don't expose sensitive error details
        print(f'Registration error occurred')
        return jsonify({'success': False, 'message': 'Registration failed. Please try again.'}), 500

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per 15 minutes")
def login():
    """User login"""
    data = request.json
    # Get raw input without sanitization first for password
    username_or_email_raw = data.get('username_or_email', '').strip()
    password = data.get('password', '')
    remember_me = data.get('remember_me', False)

    # Sanitize but don't lowercase username (only lowercase email)
    username_or_email = sanitize_input(username_or_email_raw, 255)

    # Try case-sensitive username first, then case-insensitive email
    user = User.query.filter(User.username == username_or_email).first()
    if not user:
        # Try as email (case-insensitive)
        user = User.query.filter(User.email == username_or_email.lower()).first()

    if not user or not verify_password(password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                # BUG #83 FIX: Randomize lockout time (15-20 mins) to prevent timing attacks
                import random
                lockout_minutes = random.randint(15, 20)
                user.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
                # Email disabled: send_account_locked_email(user.email, user.username, lockout_minutes)
            db.session.commit()
        # BUG #108 FIX: Only log with user.id if user exists
        SecurityAuditLog.log_action(user.id if user else None, 'login', False, get_client_ip(), get_user_agent())
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
        return jsonify({'success': False, 'message': f'Account locked. Try again in {remaining} minutes.'}), 403

    # Reset failed attempts and create session
    try:
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Generate tokens
        access_token = generate_access_token(user.id, user.username)
        refresh_token_str = secrets.token_urlsafe(32)

        session = Session(
            user_id=user.id,
            session_token=secrets.token_urlsafe(32),
            refresh_token=refresh_token_str,
            expires_at=datetime.utcnow() + (timedelta(days=30) if remember_me else timedelta(days=7)),
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        db.session.add(session)
        db.session.commit()

        SecurityAuditLog.log_action(user.id, 'login', True, get_client_ip(), get_user_agent())

        return jsonify({
            'success': True,
            'access_token': access_token,
            'refresh_token': refresh_token_str,
            'user': user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        # BUG #84 FIX: Don't expose database errors
        print(f'Login session creation error occurred')
        return jsonify({'success': False, 'message': 'Login failed. Please try again.'}), 500

# Email verification disabled - no email service configured
# @app.route('/api/auth/verify-email', methods=['GET'])
# def verify_email():
#     """Verify user email with token"""
#     token = request.args.get('token')
#     if not token:
#         return jsonify({'success': False, 'message': 'Token required'}), 400
#
#     verification = EmailVerificationToken.query.filter_by(token=token).first()
#     if not verification or verification.is_expired() or verification.is_used():
#         return jsonify({'success': False, 'message': 'Invalid or expired token'}), 400
#
#     try:
#         user = User.query.get(verification.user_id)
#         user.is_verified = True
#         verification.used_at = datetime.utcnow()
#         db.session.commit()
#
#         send_welcome_email(user.email, user.username)
#         SecurityAuditLog.log_action(user.id, 'email_verified', True, get_client_ip(), get_user_agent())
#
#         return jsonify({'success': True, 'message': 'Email verified successfully!'})
#     except Exception as e:
#         db.session.rollback()
#         print(f'Email verification error: {e}')
#         return jsonify({'success': False, 'message': 'Verification failed. Please try again.'}), 500

# Password reset via email disabled - no email service configured
# To re-enable: uncomment this endpoint and configure SendGrid
# @app.route('/api/auth/forgot-password', methods=['POST'])
# @limiter.limit("3 per hour")
# def forgot_password():
#     """Request password reset"""
#     data = request.json
#     email = sanitize_input(data.get('email', ''), 255).lower()
#
#     user = User.query.filter_by(email=email).first()
#     if user:
#         try:
#             token = PasswordResetToken.generate_token()
#             reset = PasswordResetToken(
#                 user_id=user.id,
#                 token=token,
#                 expires_at=datetime.utcnow() + timedelta(hours=1),
#                 ip_address=get_client_ip()
#             )
#             db.session.add(reset)
#             db.session.commit()
#             send_password_reset_email(email, user.username, token)
#         except Exception as e:
#             db.session.rollback()
#             print(f'Password reset token creation error: {e}')
#             return jsonify({'success': False, 'message': 'Failed to send reset link. Please try again.'}), 500
#
#     return jsonify({'success': True, 'message': 'If email exists, reset link has been sent'})

# Password reset endpoint disabled (depends on email)
# @app.route('/api/auth/reset-password', methods=['POST'])
# def reset_password():
#     """Reset password with token"""
#     data = request.json
#     token = data.get('token')
#     new_password = data.get('new_password')
#
#     valid, msg = validate_password(new_password)
#     if not valid:
#         return jsonify({'success': False, 'message': msg}), 400
#
#     reset = PasswordResetToken.query.filter_by(token=token).first()
#     if not reset or reset.is_expired() or reset.is_used():
#         return jsonify({'success': False, 'message': 'Invalid or expired token'}), 400
#
#     try:
#         user = User.query.get(reset.user_id)
#         user.password_hash = hash_password(new_password)
#         reset.used_at = datetime.utcnow()
#
#         # Invalidate all sessions
#         Session.query.filter_by(user_id=user.id).delete()
#         db.session.commit()
#
#         SecurityAuditLog.log_action(user.id, 'password_reset', True, get_client_ip(), get_user_agent())
#         return jsonify({'success': True, 'message': 'Password reset successfully'})
#     except Exception as e:
#         db.session.rollback()
#         print(f'Password reset error: {e}')
#         return jsonify({'success': False, 'message': 'Password reset failed. Please try again.'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout(current_user):
    """Logout user"""
    try:
        auth_header = request.headers.get('Authorization', '')
        # BUG #85 FIX: Validate token format before splitting
        if not auth_header or ' ' not in auth_header:
            return jsonify({'success': False, 'message': 'Invalid authorization header'}), 401

        parts = auth_header.split(' ')
        if len(parts) != 2:
            return jsonify({'success': False, 'message': 'Invalid authorization header format'}), 401

        token = parts[1]

        # BUG #86 FIX: Only invalidate current session, not all sessions
        # Find the specific session with this refresh token
        # For now, we'll delete the most recent session
        recent_session = Session.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).order_by(Session.created_at.desc()).first()

        if recent_session:
            db.session.delete(recent_session)
            db.session.commit()

        SecurityAuditLog.log_action(current_user.id, 'logout', True, get_client_ip(), get_user_agent())
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        db.session.rollback()
        print(f'Logout error occurred')
        return jsonify({'success': False, 'message': 'Logout failed. Please try again.'}), 500

@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """Get current user info"""
    return jsonify({'success': True, 'user': current_user.to_dict()})

@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    auth_header = request.headers.get('Authorization', '')

    # BUG #87 FIX: Validate header format before splitting
    if not auth_header or ' ' not in auth_header:
        return jsonify({'success': False, 'message': 'Refresh token required'}), 401

    parts = auth_header.split(' ')
    if len(parts) != 2:
        return jsonify({'success': False, 'message': 'Invalid authorization header format'}), 401

    refresh_token_str = parts[1]

    if not refresh_token_str:
        return jsonify({'success': False, 'message': 'Refresh token required'}), 401

    # Find session with this refresh token
    session = Session.query.filter_by(refresh_token=refresh_token_str, is_active=True).first()

    if not session or session.is_expired():
        return jsonify({'success': False, 'message': 'Invalid or expired refresh token'}), 401

    # Get user
    user = User.query.get(session.user_id)
    if not user or user.account_status != 'active':
        return jsonify({'success': False, 'message': 'User not found or inactive'}), 401

    try:
        # BUG #234 FIX: generate_access_token only takes 2 parameters, not 3
        access_token = generate_access_token(user.id, user.username)

        # Optionally rotate refresh token for better security
        new_refresh_token = secrets.token_urlsafe(32)
        session.refresh_token = new_refresh_token
        db.session.commit()

        return jsonify({
            'success': True,
            'access_token': access_token,
            'refresh_token': new_refresh_token
        })
    except Exception as e:
        db.session.rollback()
        # BUG #88 FIX: Don't expose error details
        print(f'Token refresh error occurred')
        return jsonify({'success': False, 'message': 'Token refresh failed. Please try again.'}), 500

# Email verification disabled - no email service configured
# @app.route('/api/auth/resend-verification', methods=['POST'])
# @token_required
# @limiter.limit("3 per hour")
# def resend_verification(current_user):
#     """Resend email verification"""
#     if current_user.is_verified:
#         return jsonify({'success': False, 'message': 'Email already verified'}), 400
#
#     try:
#         # Invalidate old tokens
#         EmailVerificationToken.query.filter_by(user_id=current_user.id, used_at=None).delete()
#
#         # Create new verification token
#         token = EmailVerificationToken.generate_token()
#         verification = EmailVerificationToken(
#             user_id=current_user.id,
#             token=token,
#             expires_at=datetime.utcnow() + timedelta(hours=24)
#         )
#         db.session.add(verification)
#         db.session.commit()
#
#         # Send verification email
#         send_verification_email(current_user.email, current_user.username, token)
#
#         SecurityAuditLog.log_action(current_user.id, 'resend_verification', True, get_client_ip(), get_user_agent())
#
#         return jsonify({'success': True, 'message': 'Verification email sent'})
#     except Exception as e:
#         db.session.rollback()
#         print(f'Resend verification error: {e}')
#         return jsonify({'success': False, 'message': 'Failed to send verification email. Please try again.'}), 500

@app.route('/api/rooms/list', methods=['GET'])
def list_rooms():
    """Get list of active rooms"""
    active_rooms = [
        {
            "code": code,
            "host": room["host"],
            "difficulty": room["difficulty"],
            "players": len(room["players"]),
            "max_players": room["max_players"],
            "status": room["status"]
        }
        for code, room in game_rooms.items()
        if room["status"] == "waiting"
    ]
    return jsonify({"rooms": active_rooms})

@app.route('/api/leaderboard/global', methods=['GET'])
def get_global_leaderboard():
    """Get global leaderboard from database"""
    game_mode = request.args.get('difficulty', 'all')  # Using 'difficulty' param for backwards compatibility

    # BUG #490 FIX: Russian Roulette (luck mode) shows all attempts, others only wins
    if game_mode == 'luck':
        query = GameHistory.query  # Show all attempts (wins and losses)
    else:
        query = GameHistory.query.filter_by(won=True)  # Only show wins for other modes

    if game_mode != 'all' and game_mode != 'luck':
        query = query.filter_by(game_mode=game_mode)
    elif game_mode == 'luck':
        query = query.filter_by(game_mode='luck')

    # BUG #489, #492 FIX: Standard mode sorts by time (ASC), others by score (DESC)
    # Check if game_mode starts with 'standard' to handle standard-easy, standard-medium, etc.
    if game_mode.startswith('standard'):
        leaderboard = query.order_by(GameHistory.score.asc()).limit(50).all()
    else:
        leaderboard = query.order_by(GameHistory.score.desc()).limit(50).all()

    return jsonify({
        "leaderboard": [
            {
                "username": game.username,
                "score": game.score,
                "time": game.time_seconds,
                "difficulty": game.game_mode,
                "hints_used": game.hints_used,
                "date": game.created_at.isoformat() if game.created_at else None
            }
            for game in leaderboard
        ]
    })

@app.route('/api/leaderboard/submit', methods=['POST'])
@limiter.limit("100 per hour")
def submit_score():
    """Submit score to database leaderboard"""
    data = request.json

    # Validate and sanitize inputs
    username = sanitize_input(data.get("username", "Guest"), 50)

    # BUG #393-394 FIX: Use comprehensive validation with clamping
    valid, score, time_seconds, errors = validate_score_and_time(
        data.get("score", 0),
        data.get("time", 0)
    )

    if not valid:
        print(f"Score/time validation warnings: {errors}")
    # Continue with clamped values

    # Validate hints_used
    try:
        hints_used = int(data.get("hints_used", 0))
        hints_used = max(0, min(hints_used, 100))  # Clamp to 0-100
    except (ValueError, TypeError):
        hints_used = 0

    game_mode = sanitize_input(data.get("difficulty", "standard"), 50)  # Using 'difficulty' for backwards compatibility
    won = bool(data.get("won", False))

    try:
        # Create game history entry
        game = GameHistory(
            username=username,
            game_mode=game_mode,
            score=score,
            time_seconds=time_seconds,
            tiles_clicked=score,  # Score is tiles clicked
            hints_used=hints_used,
            won=won,
            multiplayer=False
        )
        db.session.add(game)
        db.session.commit()

        return jsonify({"success": True, "entry": game.to_dict()})
    except Exception as e:
        db.session.rollback()
        # BUG #89 FIX: Don't expose error details
        print(f'Leaderboard submission error occurred')
        return jsonify({"success": False, "message": "Failed to submit score. Please try again."}), 500

@app.route('/api/admin/clear-leaderboard', methods=['POST'])
def clear_leaderboard():
    """
    BUG #494 FIX: Admin endpoint to clear all testing leaderboard data
    SECURITY: This should be protected with authentication in production
    """
    try:
        # Count records before deletion
        count = GameHistory.query.count()
        print(f"Clearing {count} leaderboard entries...")

        # Delete all records
        GameHistory.query.delete()
        db.session.commit()

        print(f"✅ Successfully deleted {count} leaderboard entries!")
        return jsonify({
            "success": True,
            "message": f"Cleared {count} leaderboard entries",
            "entries_deleted": count
        })
    except Exception as e:
        db.session.rollback()
        print(f'Error clearing leaderboard: {e}')
        return jsonify({"success": False, "message": "Failed to clear leaderboard"}), 500

# WebSocket Events

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")
    emit('connected', {"session_id": request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")

    # BUG #90 FIX: Validate player_sessions exists and has request.sid
    if not player_sessions or request.sid not in player_sessions:
        return

    # Remove player from any room they're in
    if request.sid in player_sessions:
        session = player_sessions[request.sid]
        room_code = session.get("room_code")

        if room_code and room_code in game_rooms:
            room = game_rooms[room_code]
            # BUG #91 FIX: Validate player objects before filtering
            room["players"] = [
                p for p in room.get("players", [])
                if isinstance(p, dict) and p.get("session_id") != request.sid
            ]

            # Notify other players
            emit('player_left', {
                "username": session["username"],
                "players_remaining": len(room["players"]),
                "players": room["players"]
            }, room=room_code)

            # Delete room if empty
            if len(room["players"]) == 0:
                del game_rooms[room_code]

        del player_sessions[request.sid]

@socketio.on('create_room')
def handle_create_room(data):
    """Create a new game room"""
    # BUG #92 FIX: Validate data is a dict
    if not data or not isinstance(data, dict):
        emit('error', {"message": "Invalid data"})
        return

    # BUG #235 FIX: Enforce MAX_ROOMS limit to prevent memory exhaustion
    if len(game_rooms) >= MAX_ROOMS:
        emit('error', {"message": "Server at capacity. Please try again later."})
        return

    # Sanitize and validate inputs
    username = sanitize_input(data.get("username", "Player"), 50)
    difficulty = sanitize_input(data.get("difficulty", "Medium"), 20)
    game_mode = sanitize_input(data.get("game_mode", "standard"), 20)

    # BUG #391 FIX: Validate max_players with configurable limits
    max_players_input = data.get("max_players", 3)
    valid, error_msg = validate_max_players(max_players_input)
    if not valid:
        emit('error', {"message": error_msg})
        return
    max_players = int(max_players_input)

    room_code = generate_room_code()

    # Generate Sudoku puzzle based on difficulty
    difficulty_mapping = {
        'Easy': 'easy',
        'Medium': 'medium',
        'Hard': 'hard',
        'Expert': 'expert',
        'Evil': 'evil'
    }
    sudoku_difficulty = difficulty_mapping.get(difficulty, 'medium')
    puzzle, solution = sudoku_generator.generate(sudoku_difficulty)
    initial_cells = sudoku_generator.get_initial_cells(puzzle)

    game_rooms[room_code] = {
        "code": room_code,
        "host": username,
        "difficulty": difficulty,
        "max_players": max_players,
        "game_mode": game_mode,
        "status": "waiting",
        "players": [{
            "username": username,
            "session_id": request.sid,
            "ready": False,
            "score": 0,
            "finished": False,
            "eliminated": False
        }],
        "puzzle": puzzle,
        "solution": solution,
        "initial_cells": list(initial_cells),  # Convert set to list for JSON serialization
        "player_cells": {},  # {username: [(row, col, num), ...]}
        "mistakes": {},  # {username: count}
        "hints_used": {},  # {username: count}
        "current_turn": username if game_mode == "turn_based" else None,
        "created_at": datetime.now().isoformat()
    }

    player_sessions[request.sid] = {
        "username": username,
        "room_code": room_code
    }

    join_room(room_code)

    emit('room_created', {
        "room_code": room_code,
        "difficulty": difficulty,
        "max_players": max_players,
        "game_mode": game_mode
    })

    print(f"Room {room_code} created by {username} (mode: {game_mode})")

@socketio.on('join_room')
def handle_join_room(data):
    """Join an existing game room"""
    # BUG #92 FIX: Validate data is a dict
    if not data or not isinstance(data, dict):
        emit('error', {"message": "Invalid data"})
        return

    # BUG #235 FIX: Enforce MAX_SESSIONS limit to prevent memory exhaustion
    if len(player_sessions) >= MAX_SESSIONS:
        emit('error', {"message": "Server at capacity. Please try again later."})
        return

    # Validate and sanitize room code
    room_code = str(data.get("room_code", "")).strip()

    # BUG #236 FIX: Normalize room code properly by converting to int first
    # This avoids issues with "000000" being treated differently than "0"
    try:
        room_code_int = int(room_code)
        if room_code_int < 0 or room_code_int > 999999:
            emit('error', {"message": "Invalid room code - must be between 000000 and 999999"})
            return
        room_code = str(room_code_int).zfill(6)
    except (ValueError, TypeError):
        emit('error', {"message": "Invalid room code format - must be 6 digits"})
        return

    if not room_code or len(room_code) != 6:
        emit('error', {"message": "Invalid room code format - must be 6 digits"})
        return

    # Sanitize username
    username = sanitize_input(data.get("username", "Player"), 50)
    if not username:
        emit('error', {"message": "Username required"})
        return

    if room_code not in game_rooms:
        emit('error', {"message": "Room not found"})
        return

    room = game_rooms[room_code]

    if room["status"] != "waiting":
        emit('error', {"message": "Game already in progress"})
        return

    if len(room["players"]) >= room["max_players"]:
        emit('error', {"message": "Room is full"})
        return

    # Add player to room
    room["players"].append({
        "username": username,
        "session_id": request.sid,
        "ready": False,
        "score": 0,
        "finished": False,
        "eliminated": False
    })

    player_sessions[request.sid] = {
        "username": username,
        "room_code": room_code
    }

    join_room(room_code)

    # Notify player they joined
    emit('room_joined', {
        "room_code": room_code,
        "difficulty": room["difficulty"],
        "host": room["host"],
        "players": room["players"]
    })

    # Notify other players
    emit('player_joined', {
        "username": username,
        "players": room["players"]
    }, room=room_code, skip_sid=request.sid)

    print(f"{username} joined room {room_code}")

@socketio.on('leave_room')
def handle_leave_room():
    """Leave current room"""
    if request.sid not in player_sessions:
        return

    # BUG #95 FIX: Validate session exists and is a dict
    session = player_sessions.get(request.sid)
    if not session or not isinstance(session, dict):
        return

    room_code = session.get("room_code")
    if not room_code:
        return

    if room_code in game_rooms:
        room = game_rooms[room_code]
        room["players"] = [p for p in room["players"] if p["session_id"] != request.sid]

        leave_room(room_code)

        emit('left_room', {"success": True})
        emit('player_left', {
            "username": session["username"],
            "players_remaining": len(room["players"]),
            "players": room["players"]
        }, room=room_code)

        # Delete room if empty
        if len(room["players"]) == 0:
            del game_rooms[room_code]

    # Safely remove from player_sessions
    if request.sid in player_sessions:
        del player_sessions[request.sid]

@socketio.on('change_game_mode')
def handle_change_game_mode(data):
    """Change game mode for existing room (host only)"""
    # BUG #92, #96 FIX: Validate data and session exist
    if not data or not isinstance(data, dict):
        return

    if request.sid not in player_sessions:
        return

    session = player_sessions.get(request.sid)
    if not session or not isinstance(session, dict):
        return

    room_code = session.get("room_code")
    if not room_code or room_code not in game_rooms:
        return

    room = game_rooms[room_code]

    # Only host can change mode
    if room["host"] != session["username"]:
        emit('error', {"message": "Only host can change game mode"})
        return

    # Get and validate new game mode
    new_mode = sanitize_input(data.get("game_mode", "standard"), 20)

    # Update room settings
    room["game_mode"] = new_mode
    # BUG #93, #97 FIX: Ensure board_seed is never 0
    room["board_seed"] = secrets.randbelow(999999) + 1
    room["current_turn"] = session["username"] if new_mode == "luck" else None

    # Auto-ready all players and start immediately
    for player in room["players"]:
        player["ready"] = True

    room["status"] = "playing"

    # Regenerate puzzle for new mode
    difficulty_mapping = {
        'Easy': 'easy',
        'Medium': 'medium',
        'Hard': 'hard',
        'Expert': 'expert',
        'Evil': 'evil'
    }
    sudoku_difficulty = difficulty_mapping.get(room["difficulty"], 'medium')
    puzzle, solution = sudoku_generator.generate(sudoku_difficulty)
    initial_cells = sudoku_generator.get_initial_cells(puzzle)

    room["puzzle"] = puzzle
    room["solution"] = solution
    room["initial_cells"] = list(initial_cells)
    room["player_cells"] = {}
    room["mistakes"] = {}
    room["hints_used"] = {}

    # Notify all players about mode change and game start
    emit('game_start', {
        "difficulty": room["difficulty"],
        "puzzle": room["puzzle"],
        "initial_cells": room["initial_cells"],
        "game_mode": new_mode,
        "current_turn": room.get("current_turn"),
        "players": room["players"]
    }, room=room_code)

    print(f"Room {room_code} mode changed to {new_mode} by host {session['username']}")

@socketio.on('player_ready')
def handle_player_ready(data):
    """Mark player as ready to start"""
    if request.sid not in player_sessions:
        return

    session = player_sessions[request.sid]
    room_code = session["room_code"]

    if room_code not in game_rooms:
        return

    room = game_rooms[room_code]

    # Mark player as ready
    for player in room["players"]:
        if player["session_id"] == request.sid:
            player["ready"] = True
            break

    # Check if all players are ready
    all_ready = all(p["ready"] for p in room["players"])

    emit('player_ready_update', {
        "username": session["username"],
        "players": room["players"],
        "all_ready": all_ready
    }, room=room_code)

    # Start game if all ready (need at least 2 players for multiplayer)
    if all_ready and len(room["players"]) >= 2:
        room["status"] = "playing"
        emit('game_start', {
            "difficulty": room["difficulty"],
            "puzzle": room["puzzle"],
            "initial_cells": room["initial_cells"],
            "game_mode": room["game_mode"],
            "current_turn": room.get("current_turn"),
            "players": room["players"]
        }, room=room_code)

@socketio.on('game_action')
def handle_game_action(data):
    """Handle game actions (cell reveal, flag)"""
    if not data:
        return

    if request.sid not in player_sessions:
        return

    session = player_sessions[request.sid]
    room_code = session["room_code"]

    if room_code not in game_rooms:
        return

    room = game_rooms[room_code]
    action = data.get("action")

    # Validate action type
    valid_actions = ["reveal", "flag", "eliminated"]
    if action not in valid_actions:
        return

    # Validate row and col if provided
    if action in ["reveal", "flag"]:
        try:
            row = data.get("row")
            col = data.get("col")
            if row is not None:
                row = int(row)
                # BUG #98 FIX: Validate within reasonable bounds
                if row < 0 or row > 100:  # Reasonable max board size
                    return
            if col is not None:
                col = int(col)
                if col < 0 or col > 100:  # Reasonable max board size
                    return
        except (ValueError, TypeError):
            return

    # Handle elimination in ALL game modes
    if action == "eliminated":
        # Mark player as eliminated and record their score
        # BUG #99 FIX: Validate clicks value
        clicks = data.get("clicks", 0)
        try:
            clicks = int(clicks)
            clicks = max(0, min(clicks, 100000))  # Reasonable range
        except (ValueError, TypeError):
            clicks = 0

        for player in room["players"]:
            if player["session_id"] == request.sid:
                player["eliminated"] = True
                player["finished"] = True
                player["score"] = clicks
                break

        # Check if only one player remains
        active_players = [p for p in room["players"] if not p["eliminated"]]

        if len(active_players) == 1:
            # Last player standing wins!
            winner = active_players[0]
            winner["finished"] = True

            # Notify all players that someone was eliminated and there's a winner
            emit('player_eliminated', {
                "username": session["username"],
                "winner": winner["username"]
            }, room=room_code)

            # Sort players by score (winner first, then by who lasted longest)
            sorted_players = sorted(room["players"], key=lambda x: (not x["eliminated"], x["score"]), reverse=True)

            # Send game_ended event to show results and return to waiting room
            emit('game_ended', {
                "results": sorted_players
            }, room=room_code)

            # Reset room status for next game
            room["status"] = "waiting"
            for player in room["players"]:
                player["ready"] = False
                player["score"] = 0
                player["finished"] = False
                player["eliminated"] = False

        elif len(active_players) == 0:
            # Everyone died somehow - tie game
            emit('game_ended', {
                "results": room["players"]
            }, room=room_code)

            room["status"] = "waiting"
            for player in room["players"]:
                player["ready"] = False
                player["score"] = 0
                player["finished"] = False
                player["eliminated"] = False
        else:
            # Multiple players still alive, just notify elimination
            emit('player_eliminated', {
                "username": session["username"]
            }, room=room_code)

            # In Luck Mode (turn-based), move to next player's turn
            if room["game_mode"] == "luck":
                current_idx = next((i for i, p in enumerate(room["players"]) if p["username"] == room["current_turn"]), 0)
                next_idx = (current_idx + 1) % len(room["players"])

                # BUG #100 FIX: Add max attempts check to prevent infinite loop
                max_attempts = len(room["players"])
                attempts = 0
                while attempts < max_attempts and room["players"][next_idx].get("eliminated", False):
                    next_idx = (next_idx + 1) % len(room["players"])
                    attempts += 1

                if attempts < max_attempts:
                    room["current_turn"] = room["players"][next_idx]["username"]
                    emit('turn_changed', {
                        "current_turn": room["current_turn"]
                    }, room=room_code)
        return

    # Broadcast action to other players in room
    emit('player_action', {
        "username": session["username"],
        "action": action,
        "row": data.get("row"),
        "col": data.get("col")
    }, room=room_code, skip_sid=request.sid)

    # In Luck Mode, change turn after reveal action
    if room["game_mode"] == "luck" and action == "reveal":
        # Find next player
        current_idx = next((i for i, p in enumerate(room["players"]) if p["username"] == room["current_turn"]), 0)
        next_idx = (current_idx + 1) % len(room["players"])

        # BUG #101 FIX: Add max attempts check to prevent infinite loop
        max_attempts = len(room["players"])
        attempts = 0
        while attempts < max_attempts and room["players"][next_idx].get("eliminated", False):
            next_idx = (next_idx + 1) % len(room["players"])
            attempts += 1

        if attempts < max_attempts:
            room["current_turn"] = room["players"][next_idx]["username"]
            emit('turn_changed', {
                "current_turn": room["current_turn"]
            }, room=room_code)

@socketio.on('game_finished')
def handle_game_finished(data):
    """Handle player finishing game"""
    if not data:
        return

    if request.sid not in player_sessions:
        return

    session = player_sessions[request.sid]
    room_code = session["room_code"]

    if room_code not in game_rooms:
        return

    room = game_rooms[room_code]

    # BUG #102 FIX: Validate score and time with sanity checks
    try:
        score = int(data.get("score", 0))
        time = int(data.get("time", 0))
        if score < 0 or time < 0:
            score, time = 0, 0
        # Check for obviously impossible values (0 score with high time = suspicious)
        if score == 0 and time > 10:
            score, time = 0, 0
        if score > 10000 or time > 86400:  # Reasonable max values
            score, time = min(score, 10000), min(time, 86400)
    except (ValueError, TypeError):
        score, time = 0, 0

    # Update player score
    for player in room["players"]:
        if player["session_id"] == request.sid:
            player["score"] = score
            player["time"] = time
            player["finished"] = True
            break

    # Check if all players finished
    all_finished = all(p["finished"] for p in room["players"])

    emit('player_finished', {
        "username": session["username"],
        "score": data.get("score", 0),
        "time": data.get("time", 0),
        "players": room["players"]
    }, room=room_code)

    if all_finished:
        # BUG #103 FIX: Sort by score with time as tiebreaker
        sorted_players = sorted(
            room["players"],
            key=lambda x: (x.get("score", 0), -x.get("time", 0)),
            reverse=True
        )

        emit('game_ended', {
            "results": sorted_players
        }, room=room_code)

        # Reset room status
        room["status"] = "waiting"
        for player in room["players"]:
            player["ready"] = False
            player["score"] = 0
            player["finished"] = False
            player["eliminated"] = False

# ============================================================================
# SUDOKU-SPECIFIC WEBSOCKET HANDLERS
# ============================================================================

@socketio.on('place_number')
def handle_place_number(data):
    """Handle Sudoku number placement"""
    if not data or not isinstance(data, dict):
        return

    if request.sid not in player_sessions:
        return

    session = player_sessions[request.sid]
    room_code = session.get("room_code")
    username = session.get("username")

    if not room_code or room_code not in game_rooms:
        return

    room = game_rooms[room_code]

    if room["status"] != "playing":
        return

    # Get placement data
    try:
        row = int(data.get("row", -1))
        col = int(data.get("col", -1))
        number = int(data.get("number", 0))

        # Validate coordinates
        if row < 0 or row > 8 or col < 0 or col > 8:
            emit('error', {"message": "Invalid cell coordinates"})
            return

        # Validate number (0 = clear, 1-9 = place)
        if number < 0 or number > 9:
            emit('error', {"message": "Invalid number"})
            return
    except (ValueError, TypeError):
        emit('error', {"message": "Invalid input"})
        return

    # Check if cell is initial (immutable)
    if [row, col] in room["initial_cells"]:
        emit('error', {"message": "Cannot modify initial cells"})
        return

    # Check if number is correct
    is_correct = sudoku_generator.validate_move(room["puzzle"], room["solution"], row, col, number)

    if not is_correct and number != 0:
        # Increment mistake count
        room["mistakes"][username] = room["mistakes"].get(username, 0) + 1
        emit('mistake', {
            "username": username,
            "count": room["mistakes"][username]
        }, room=room_code)

    # Update player's move list
    if username not in room["player_cells"]:
        room["player_cells"][username] = []

    # Remove any previous move at this position by this player
    room["player_cells"][username] = [
        (r, c, n) for r, c, n in room["player_cells"][username]
        if not (r == row and c == col)
    ]

    # Add new move if not clearing
    if number != 0:
        room["player_cells"][username].append((row, col, number))

    # Update the puzzle state
    room["puzzle"][row][col] = number

    # Broadcast move to all players in room
    emit('cell_update', {
        "username": username,
        "row": row,
        "col": col,
        "number": number,
        "is_correct": is_correct
    }, room=room_code)

    # Check if puzzle is complete
    if sudoku_generator.check_complete(room["puzzle"], room["solution"]):
        # Player wins!
        for player in room["players"]:
            if player["username"] == username:
                player["finished"] = True
                player["score"] = len(room["player_cells"].get(username, []))
                break

        emit('game_ended', {
            "winner": username,
            "results": room["players"]
        }, room=room_code)

        # Reset room status
        room["status"] = "waiting"
        for player in room["players"]:
            player["ready"] = False
            player["score"] = 0
            player["finished"] = False

@socketio.on('get_hint')
def handle_get_hint(data):
    """Provide a hint for the Sudoku puzzle"""
    if request.sid not in player_sessions:
        return

    session = player_sessions[request.sid]
    room_code = session.get("room_code")
    username = session.get("username")

    if not room_code or room_code not in game_rooms:
        return

    room = game_rooms[room_code]

    if room["status"] != "playing":
        return

    # Increment hint count
    room["hints_used"][username] = room["hints_used"].get(username, 0) + 1

    # Get a hint
    hint = sudoku_generator.get_hint(room["puzzle"], room["solution"])

    if hint:
        row, col, number = hint
        emit('hint_provided', {
            "row": row,
            "col": col,
            "number": number
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug_mode)
