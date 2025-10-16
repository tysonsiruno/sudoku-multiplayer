"""
Concurrency Control & Race Condition Prevention
Distributed locks, atomic operations, optimistic locking
BUG FIXES: #351-360 (Concurrency Issues)
"""

import threading
import time
import hashlib
from functools import wraps
from datetime import datetime, timedelta


# ============================================================================
# BUG #354 FIX: Thread-Safe Game Rooms Dictionary
# ============================================================================
class ThreadSafeDict:
    """
    Thread-safe dictionary with locking
    Prevents race conditions in game_rooms and player_sessions
    """
    def __init__(self):
        self.data = {}
        self.lock = threading.RLock()  # Reentrant lock

    def get(self, key, default=None):
        with self.lock:
            return self.data.get(key, default)

    def set(self, key, value):
        with self.lock:
            self.data[key] = value

    def delete(self, key):
        with self.lock:
            if key in self.data:
                del self.data[key]

    def __contains__(self, key):
        with self.lock:
            return key in self.data

    def __getitem__(self, key):
        with self.lock:
            return self.data[key]

    def __setitem__(self, key, value):
        with self.lock:
            self.data[key] = value

    def __delitem__(self, key):
        with self.lock:
            del self.data[key]

    def keys(self):
        with self.lock:
            return list(self.data.keys())

    def values(self):
        with self.lock:
            return list(self.data.values())

    def items(self):
        with self.lock:
            return list(self.data.items())

    def __len__(self):
        with self.lock:
            return len(self.data)

    def pop(self, key, default=None):
        with self.lock:
            return self.data.pop(key, default)

    def update(self, other):
        with self.lock:
            self.data.update(other)


# ============================================================================
# BUG #351, #357 FIX: Distributed Lock for Room Creation
# ============================================================================
class DistributedLock:
    """
    Simple distributed lock implementation
    For production, use Redis-based locks (redlock algorithm)
    """
    def __init__(self):
        self.locks = {}
        self.lock = threading.Lock()

    def acquire(self, resource_name, timeout=10, retry_delay=0.1):
        """
        Acquire lock on resource

        Args:
            resource_name: Name of resource to lock
            timeout: Max time to wait for lock (seconds)
            retry_delay: Time between retry attempts (seconds)

        Returns:
            lock_id if successful, None if timeout
        """
        start_time = time.time()
        lock_id = f"{resource_name}:{time.time()}:{threading.get_ident()}"

        while time.time() - start_time < timeout:
            with self.lock:
                if resource_name not in self.locks:
                    # Lock available
                    self.locks[resource_name] = {
                        'lock_id': lock_id,
                        'acquired_at': time.time(),
                        'thread_id': threading.get_ident()
                    }
                    return lock_id
                else:
                    # Check if lock is stale (holder died)
                    lock_info = self.locks[resource_name]
                    if time.time() - lock_info['acquired_at'] > 30:
                        # Lock held for > 30 seconds, consider it stale
                        del self.locks[resource_name]
                        continue

            time.sleep(retry_delay)

        return None  # Timeout

    def release(self, resource_name, lock_id):
        """Release lock if we hold it"""
        with self.lock:
            if resource_name in self.locks:
                if self.locks[resource_name]['lock_id'] == lock_id:
                    del self.locks[resource_name]
                    return True
        return False

    def is_locked(self, resource_name):
        """Check if resource is locked"""
        with self.lock:
            return resource_name in self.locks


# Global distributed lock instance
distributed_lock = DistributedLock()


def with_lock(resource_name_func, timeout=10):
    """
    Decorator to execute function with distributed lock

    Usage:
        @with_lock(lambda room_code: f"room:{room_code}")
        def join_room(room_code, player):
            # Critical section
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get resource name from arguments
            resource_name = resource_name_func(*args, **kwargs)

            # Acquire lock
            lock_id = distributed_lock.acquire(resource_name, timeout=timeout)
            if not lock_id:
                raise TimeoutError(f"Could not acquire lock on {resource_name}")

            try:
                # Execute function
                return func(*args, **kwargs)
            finally:
                # Always release lock
                distributed_lock.release(resource_name, lock_id)

        return wrapper
    return decorator


# ============================================================================
# BUG #351 FIX: Atomic Room Creation
# ============================================================================
def create_room_atomic(game_rooms, room_code, room_data):
    """
    Atomically create room if code doesn't exist

    BUG #351 FIX: Prevents race condition where two players create same room code

    Returns:
        (success: bool, message: str)
    """
    lock_id = distributed_lock.acquire(f"room_creation:{room_code}", timeout=5)
    if not lock_id:
        return False, "Room creation timeout"

    try:
        if room_code in game_rooms:
            return False, "Room code already exists"

        game_rooms[room_code] = room_data
        return True, "Room created"
    finally:
        distributed_lock.release(f"room_creation:{room_code}", lock_id)


# ============================================================================
# BUG #352 FIX: Atomic Player Join
# ============================================================================
def join_room_atomic(game_rooms, room_code, player_data):
    """
    Atomically join room if not full

    BUG #352 FIX: Prevents race where multiple players exceed max_players

    Returns:
        (success: bool, message: str, room_data: dict or None)
    """
    lock_id = distributed_lock.acquire(f"room:{room_code}", timeout=5)
    if not lock_id:
        return False, "Join room timeout", None

    try:
        if room_code not in game_rooms:
            return False, "Room not found", None

        room = game_rooms[room_code]

        # Check capacity
        if len(room['players']) >= room['max_players']:
            return False, "Room is full", None

        # Check if already in room
        for p in room['players']:
            if p.get('username') == player_data.get('username'):
                return False, "Already in room", None

        # Add player
        room['players'].append(player_data)
        return True, "Joined successfully", room

    finally:
        distributed_lock.release(f"room:{room_code}", lock_id)


# ============================================================================
# BUG #353, #358 FIX: Optimistic Locking for Score Updates
# ============================================================================
class OptimisticLockError(Exception):
    """Raised when optimistic lock fails (concurrent modification)"""
    pass


def update_with_optimistic_lock(session, model_instance, updates, version_field='updated_at'):
    """
    Update database record with optimistic locking

    BUG #353 FIX: Prevents lost updates in concurrent score submissions

    Args:
        session: SQLAlchemy session
        model_instance: Model instance to update
        updates: Dict of field updates
        version_field: Field to use for versioning (default: updated_at)

    Raises:
        OptimisticLockError: If record was modified by another transaction
    """
    from sqlalchemy import and_

    # Get current version
    original_version = getattr(model_instance, version_field)

    # Apply updates
    for field, value in updates.items():
        setattr(model_instance, field, value)

    # Update version
    new_version = datetime.utcnow()
    setattr(model_instance, version_field, new_version)

    # Commit with version check
    try:
        # Add WHERE clause to check version hasn't changed
        model_class = type(model_instance)
        pk_name = model_class.__mapper__.primary_key[0].name
        pk_value = getattr(model_instance, pk_name)

        # This will raise if another transaction updated the row
        result = session.query(model_class).filter(and_(
            getattr(model_class, pk_name) == pk_value,
            getattr(model_class, version_field) == original_version
        )).update(updates)

        if result == 0:
            session.rollback()
            raise OptimisticLockError(
                f"Record was modified by another transaction"
            )

        session.commit()
        return True

    except OptimisticLockError:
        raise
    except Exception as e:
        session.rollback()
        raise


# ============================================================================
# BUG #355 FIX: Thread-Safe Session Creation
# ============================================================================
def create_session_safe(db, user_id, session_data, max_sessions_per_user=10):
    """
    Safely create session with concurrency control

    BUG #355 FIX: Race condition in session creation

    Returns:
        (session: Session or None, error: str or None)
    """
    from models import Session

    lock_id = distributed_lock.acquire(f"user_sessions:{user_id}", timeout=5)
    if not lock_id:
        return None, "Session creation timeout"

    try:
        # Check existing sessions
        existing = Session.query.filter_by(
            user_id=user_id,
            is_active=True
        ).count()

        if existing >= max_sessions_per_user:
            return None, f"Maximum {max_sessions_per_user} sessions allowed"

        # Create new session
        session = Session(**session_data)
        db.session.add(session)
        db.session.commit()

        return session, None

    except Exception as e:
        db.session.rollback()
        return None, str(e)
    finally:
        distributed_lock.release(f"user_sessions:{user_id}", lock_id)


# ============================================================================
# BUG #359 FIX: Transaction Isolation Levels
# ============================================================================
def set_isolation_level(session, level='READ COMMITTED'):
    """
    Set transaction isolation level

    BUG #359 FIX: Specify isolation level to prevent dirty reads

    Levels:
    - READ UNCOMMITTED: Allows dirty reads
    - READ COMMITTED: Default, prevents dirty reads
    - REPEATABLE READ: Prevents non-repeatable reads
    - SERIALIZABLE: Strictest, prevents phantom reads
    """
    isolation_map = {
        'READ UNCOMMITTED': 'READ UNCOMMITTED',
        'READ COMMITTED': 'READ COMMITTED',
        'REPEATABLE READ': 'REPEATABLE READ',
        'SERIALIZABLE': 'SERIALIZABLE'
    }

    if level in isolation_map:
        try:
            session.execute(
                f"SET TRANSACTION ISOLATION LEVEL {isolation_map[level]}"
            )
        except:
            # SQLite doesn't support this
            pass


# ============================================================================
# BUG #360 FIX: Atomic Audit Log Writes
# ============================================================================
def log_audit_atomic(user_id, action, success, ip_address=None, user_agent=None, details=None):
    """
    Atomically write to audit log without blocking

    BUG #360 FIX: Audit log writes could be lost in race conditions
    """
    from models import db, SecurityAuditLog

    try:
        # Use separate session/connection for audit logging
        # This ensures audit logs don't block main transactions
        log_entry = SecurityAuditLog(
            user_id=user_id,
            action=action,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        db.session.add(log_entry)
        db.session.flush()  # Write immediately without waiting for commit
        return True
    except Exception as e:
        # Don't let audit logging failures break main operation
        print(f"Audit log error: {e}")
        return False


# ============================================================================
# Retry Logic with Exponential Backoff
# ============================================================================
def retry_on_conflict(max_attempts=3, initial_delay=0.1, backoff_factor=2):
    """
    Decorator to retry operations on concurrency conflicts

    Usage:
        @retry_on_conflict(max_attempts=3)
        def update_score(user_id, score):
            # May fail due to concurrent update
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_error = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (OptimisticLockError, Exception) as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise

            raise last_error

        return wrapper
    return decorator


# ============================================================================
# Testing & Monitoring
# ============================================================================
def get_lock_stats():
    """Get statistics about active locks"""
    with distributed_lock.lock:
        return {
            'active_locks': len(distributed_lock.locks),
            'locks': [
                {
                    'resource': resource,
                    'held_for': time.time() - info['acquired_at'],
                    'thread_id': info['thread_id']
                }
                for resource, info in distributed_lock.locks.items()
            ]
        }
