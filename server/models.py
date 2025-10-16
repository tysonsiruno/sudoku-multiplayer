"""
Database Models for Minesweeper Multiplayer
Using SQLAlchemy ORM with PostgreSQL
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import secrets

db = SQLAlchemy()


class TokenBlacklist(db.Model):
    """
    BUG #231 FIX: Blacklist for invalidated JWT tokens
    Stores token JTI (JWT ID) to prevent use after logout/password change
    """
    __tablename__ = 'token_blacklist'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    token_type = db.Column(db.String(10), nullable=False)  # 'access' or 'refresh'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    blacklisted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(100))  # 'logout', 'password_change', 'security'

    @staticmethod
    def is_blacklisted(jti):
        """Check if a token JTI is blacklisted"""
        token = TokenBlacklist.query.filter_by(jti=jti).first()
        return token is not None

    @staticmethod
    def blacklist_token(jti, token_type, user_id, expires_at, reason='logout'):
        """Add a token to the blacklist"""
        blacklisted = TokenBlacklist(
            jti=jti,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
            reason=reason
        )
        db.session.add(blacklisted)
        return blacklisted

    @staticmethod
    def cleanup_expired():
        """
        BUG #233 FIX: Remove expired blacklisted tokens
        Call this periodically to prevent table bloat
        """
        now = datetime.now(timezone.utc)
        deleted = TokenBlacklist.query.filter(TokenBlacklist.expires_at < now).delete()
        db.session.commit()
        return deleted

class User(db.Model):
    """User account model"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_guest = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    profile_picture_url = db.Column(db.String(500))
    total_games_played = db.Column(db.Integer, default=0)
    total_wins = db.Column(db.Integer, default=0)
    total_losses = db.Column(db.Integer, default=0)
    highest_score = db.Column(db.Integer, default=0)
    account_status = db.Column(db.String(20), default='active')  # active, suspended, deleted
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)

    # Relationships
    sessions = db.relationship('Session', backref='user', lazy=True, cascade='all, delete-orphan')
    game_history = db.relationship('GameHistory', backref='user', lazy=True)
    password_tokens = db.relationship('PasswordResetToken', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        """Convert user to dictionary (exclude sensitive data)"""
        # BUG #121 FIX: Validate total_games_played is not None and handle edge cases
        total_games = self.total_games_played if self.total_games_played is not None else 0
        total_wins = self.total_wins if self.total_wins is not None else 0

        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'total_games_played': total_games,
            'total_wins': total_wins,
            'total_losses': self.total_losses if self.total_losses is not None else 0,
            'highest_score': self.highest_score if self.highest_score is not None else 0,
            'win_rate': round((total_wins / total_games * 100) if total_games > 0 else 0, 1)
        }


class PasswordResetToken(db.Model):
    """Password reset tokens"""
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime)
    ip_address = db.Column(db.String(50))

    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    def is_expired(self):
        """Check if token is expired"""
        # BUG #129, #130 FIX: Handle None expires_at and use consistent timezone
        if self.expires_at is None:
            return True
        from datetime import timezone
        now = datetime.now(timezone.utc) if self.expires_at.tzinfo else datetime.utcnow()
        return now > self.expires_at

    def is_used(self):
        """Check if token has been used"""
        return self.used_at is not None


class Session(db.Model):
    """User sessions for JWT refresh tokens"""
    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    refresh_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_activity = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    # BUG #234 FIX: Device tracking for better session management
    device_id = db.Column(db.String(100))  # Client-generated device identifier
    device_name = db.Column(db.String(100))  # User-friendly device name
    device_type = db.Column(db.String(50))  # 'desktop', 'mobile', 'tablet'

    def is_expired(self):
        """Check if session is expired"""
        # BUG #129, #130 FIX: Handle None expires_at and use consistent timezone
        if self.expires_at is None:
            return True
        now = datetime.now(timezone.utc) if self.expires_at.tzinfo else datetime.utcnow()
        return now > self.expires_at

    def to_dict(self):
        """Convert session to dictionary for user viewing"""
        return {
            'id': self.id,
            'device_name': self.device_name or 'Unknown Device',
            'device_type': self.device_type or 'unknown',
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_active': self.is_active,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

    @staticmethod
    def cleanup_expired():
        """
        BUG #233 FIX: Remove expired sessions from database
        Should be called periodically via cron job or background task
        """
        now = datetime.now(timezone.utc)
        deleted = Session.query.filter(Session.expires_at < now).delete()
        db.session.commit()
        return deleted

    @staticmethod
    def cleanup_inactive(days=90):
        """
        BUG #233 FIX: Remove old inactive sessions
        Delete sessions that haven't been used in X days
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        deleted = Session.query.filter(Session.last_activity < cutoff).delete()
        db.session.commit()
        return deleted

    @staticmethod
    def invalidate_all_for_user(user_id):
        """
        BUG #240 FIX: Invalidate all sessions for a user
        Used when password changes or account security compromised
        """
        Session.query.filter_by(user_id=user_id).update({'is_active': False})
        db.session.commit()


class GameHistory(db.Model):
    """Game history for leaderboard and stats"""
    __tablename__ = 'game_history'

    # BUG #282 FIX: Add composite indexes for common leaderboard queries
    __table_args__ = (
        db.Index('idx_leaderboard_score', 'won', 'game_mode', 'score'),  # Leaderboard by mode
        db.Index('idx_leaderboard_time', 'won', 'score', 'time_seconds'),  # Score + time tiebreaker
        db.Index('idx_user_games', 'user_id', 'created_at'),  # User's game history
        db.Index('idx_recent_games', 'created_at', 'won'),  # Recent winners
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), index=True)  # BUG #282 FIX
    username = db.Column(db.String(50), nullable=False, index=True)  # BUG #282 FIX: For guest lookups
    game_mode = db.Column(db.String(50), nullable=False, index=True)
    difficulty = db.Column(db.String(50), index=True)  # BUG #282 FIX
    score = db.Column(db.Integer, nullable=False, index=True)  # BUG #282 FIX
    time_seconds = db.Column(db.Integer, nullable=False)
    tiles_clicked = db.Column(db.Integer, nullable=False)
    hints_used = db.Column(db.Integer, nullable=False)
    won = db.Column(db.Boolean, nullable=False, index=True)  # BUG #282 FIX
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    room_code = db.Column(db.String(10))
    multiplayer = db.Column(db.Boolean, default=False)

    def to_dict(self):
        """Convert game history to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'game_mode': self.game_mode,
            'difficulty': self.difficulty,
            'score': self.score,
            'time_seconds': self.time_seconds,
            'tiles_clicked': self.tiles_clicked,
            'hints_used': self.hints_used,
            'won': self.won,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'multiplayer': self.multiplayer
        }


class SecurityAuditLog(db.Model):
    """Security audit log for tracking important events"""
    __tablename__ = 'security_audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    action = db.Column(db.String(100), nullable=False, index=True)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    success = db.Column(db.Boolean)
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @staticmethod
    def log_action(user_id, action, success, ip_address=None, user_agent=None, details=None):
        """Log a security action"""
        # BUG #123 FIX: Don't commit immediately - let caller control transaction
        log_entry = SecurityAuditLog(
            user_id=user_id,
            action=action,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        db.session.add(log_entry)
        # Don't commit - let the caller handle the transaction
        # db.session.commit()
        return log_entry
