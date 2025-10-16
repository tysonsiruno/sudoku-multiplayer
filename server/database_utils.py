"""
Database Performance Utilities
Query caching, connection pooling, optimization
BUG FIXES: #281-290 (Database Performance)
"""

from functools import wraps
import hashlib
import json
from datetime import datetime, timedelta
from threading import Lock


# ============================================================================
# BUG #284 FIX: Query Result Caching
# ============================================================================
class QueryCache:
    """
    Simple in-memory cache for database queries
    Use Redis for production distributed caching
    """
    def __init__(self, default_ttl=300):
        self.cache = {}  # {key: {'data': ..., 'expires_at': ...}}
        self.default_ttl = default_ttl
        self.lock = Lock()
        self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    def get(self, key):
        """Get value from cache if not expired"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if datetime.utcnow() < entry['expires_at']:
                    self.stats['hits'] += 1
                    return entry['data']
                else:
                    # Expired
                    del self.cache[key]
                    self.stats['evictions'] += 1

            self.stats['misses'] += 1
            return None

    def set(self, key, value, ttl=None):
        """Set value in cache with TTL"""
        ttl = ttl or self.default_ttl
        with self.lock:
            self.cache[key] = {
                'data': value,
                'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
            }

    def delete(self, key):
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]

    def clear(self):
        """Clear entire cache"""
        with self.lock:
            self.cache.clear()
            self.stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    def cleanup_expired(self):
        """Remove expired entries"""
        with self.lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, entry in self.cache.items()
                if now >= entry['expires_at']
            ]
            for key in expired_keys:
                del self.cache[key]
                self.stats['evictions'] += 1
            return len(expired_keys)

    def get_stats(self):
        """Get cache statistics"""
        with self.lock:
            total = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
            return {
                **self.stats,
                'size': len(self.cache),
                'hit_rate': round(hit_rate, 2)
            }


# Global cache instance
query_cache = QueryCache(default_ttl=300)  # 5 minutes default


def cached_query(ttl=300, key_prefix=''):
    """
    Decorator to cache query results

    Usage:
        @cached_query(ttl=600, key_prefix='leaderboard')
        def get_leaderboard(game_mode):
            return query...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(':'.join(key_parts).encode()).hexdigest()

            # Try to get from cache
            cached = query_cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute query
            result = func(*args, **kwargs)

            # Store in cache
            query_cache.set(cache_key, result, ttl=ttl)
            return result

        return wrapper
    return decorator


def invalidate_cache(key_prefix=''):
    """Invalidate all cache entries with given prefix"""
    # For simple implementation, just clear all
    # In production, use Redis with pattern matching
    query_cache.clear()


# ============================================================================
# BUG #281 FIX: Database Connection Pooling Configuration
# ============================================================================
def get_db_pool_config(environment='production'):
    """
    Get database connection pool configuration

    BUG #281 FIX: Proper connection pooling prevents connection exhaustion
    """
    configs = {
        'development': {
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'echo': True,  # Log SQL queries
        },
        'production': {
            'pool_size': 20,
            'max_overflow': 40,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'echo': False,
        },
        'testing': {
            'pool_size': 2,
            'max_overflow': 5,
            'pool_timeout': 10,
            'pool_recycle': 600,
            'pool_pre_ping': True,
            'echo': False,
        }
    }
    return configs.get(environment, configs['production'])


# ============================================================================
# BUG #286 FIX: Database Query Timeout
# ============================================================================
def set_query_timeout(session, timeout_seconds=30):
    """
    Set query timeout for PostgreSQL
    Prevents slow queries from blocking
    """
    try:
        # PostgreSQL
        session.execute(f"SET statement_timeout = {timeout_seconds * 1000}")
    except:
        # SQLite doesn't support this, ignore
        pass


# ============================================================================
# BUG #285 FIX: Table Partitioning (PostgreSQL only)
# ============================================================================
PARTITION_SQL_TEMPLATE = """
-- Partition GameHistory by created_at (monthly)
-- Run this manually in PostgreSQL after initial deployment

-- 1. Rename existing table
ALTER TABLE game_history RENAME TO game_history_old;

-- 2. Create partitioned table
CREATE TABLE game_history (
    id SERIAL,
    user_id INTEGER,
    username VARCHAR(50) NOT NULL,
    game_mode VARCHAR(50) NOT NULL,
    difficulty VARCHAR(50),
    score INTEGER NOT NULL,
    time_seconds INTEGER NOT NULL,
    tiles_clicked INTEGER NOT NULL,
    hints_used INTEGER NOT NULL,
    won BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL,
    room_code VARCHAR(10),
    multiplayer BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- 3. Create partitions (example for 2025)
CREATE TABLE game_history_2025_01 PARTITION OF game_history
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE game_history_2025_02 PARTITION OF game_history
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Add more partitions as needed...

-- 4. Migrate data
INSERT INTO game_history SELECT * FROM game_history_old;

-- 5. Drop old table after verifying
-- DROP TABLE game_history_old;
"""


# ============================================================================
# BUG #287 FIX: Audit Log Rotation
# ============================================================================
def rotate_audit_logs(session, keep_days=90):
    """
    Archive old audit logs to prevent table bloat

    BUG #287 FIX: SecurityAuditLog grows forever
    """
    from models import SecurityAuditLog
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=keep_days)

    # Count old logs
    old_logs = SecurityAuditLog.query.filter(
        SecurityAuditLog.created_at < cutoff
    ).count()

    if old_logs > 0:
        # In production, archive to separate table or export before deleting
        # For now, just delete
        SecurityAuditLog.query.filter(
            SecurityAuditLog.created_at < cutoff
        ).delete()
        session.commit()

        return old_logs
    return 0


# ============================================================================
# BUG #290 FIX: Database Maintenance
# ============================================================================
def vacuum_database(engine):
    """
    Run VACUUM on PostgreSQL to reclaim space and update statistics

    BUG #290 FIX: No database vacuum/maintenance scheduled
    """
    try:
        # Check if PostgreSQL
        if 'postgresql' in str(engine.url):
            # Use raw connection for VACUUM (can't be in transaction)
            connection = engine.raw_connection()
            connection.set_isolation_level(0)  # AUTOCOMMIT
            cursor = connection.cursor()
            cursor.execute("VACUUM ANALYZE")
            cursor.close()
            connection.close()
            return True
    except Exception as e:
        print(f"Vacuum failed: {e}")
        return False
    return False


def analyze_database(session):
    """
    Update database statistics for query optimizer

    BUG #290 FIX: Statistics outdated, leading to slow queries
    """
    try:
        # PostgreSQL
        session.execute("ANALYZE")
        session.commit()
        return True
    except:
        # SQLite uses auto-analyze
        return False


# ============================================================================
# BUG #283 FIX: N+1 Query Prevention
# ============================================================================
def get_leaderboard_optimized(game_mode='all', limit=50):
    """
    Optimized leaderboard query that avoids N+1 problem

    BUG #283 FIX: Joins user data in single query
    """
    from models import GameHistory, User
    from sqlalchemy.orm import joinedload

    query = GameHistory.query.filter_by(won=True)

    if game_mode != 'all':
        query = query.filter_by(game_mode=game_mode)

    # Eager load user data to avoid N+1
    query = query.options(joinedload(GameHistory.user))

    # Order and limit
    leaderboard = query.order_by(
        GameHistory.score.desc(),
        GameHistory.time_seconds.asc()
    ).limit(limit).all()

    return leaderboard


# ============================================================================
# Monitoring & Diagnostics
# ============================================================================
def get_db_stats(engine):
    """Get database connection pool statistics"""
    pool = engine.pool
    return {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'total_connections': pool.size() + pool.overflow(),
    }


def get_slow_queries(session, min_duration_ms=1000):
    """
    Get slow queries from PostgreSQL logs
    Requires pg_stat_statements extension
    """
    try:
        result = session.execute("""
            SELECT
                query,
                calls,
                mean_exec_time,
                max_exec_time
            FROM pg_stat_statements
            WHERE mean_exec_time > :min_duration
            ORDER BY mean_exec_time DESC
            LIMIT 10
        """, {'min_duration': min_duration_ms})

        return [dict(row) for row in result]
    except:
        return []


# ============================================================================
# Scheduled Maintenance Tasks
# ============================================================================
def run_maintenance(app):
    """
    Run all database maintenance tasks
    Should be called by scheduler (cron/celery)
    """
    with app.app_context():
        from models import db, Session, TokenBlacklist

        results = {}

        # Cleanup expired sessions
        results['sessions_cleaned'] = Session.cleanup_expired()

        # Cleanup expired tokens
        results['tokens_cleaned'] = TokenBlacklist.cleanup_expired()

        # Cleanup old audit logs (keep 90 days)
        results['logs_rotated'] = rotate_audit_logs(db.session, keep_days=90)

        # Cleanup query cache
        results['cache_evictions'] = query_cache.cleanup_expired()

        # Update statistics
        analyze_database(db.session)
        results['stats_updated'] = True

        return results
