"""
Network Error Handling & Retry Logic
Connection management, timeout configuration, graceful degradation
BUG FIXES: #401-410 (Network Failures)
"""

import time
import socket
from functools import wraps
from datetime import datetime, timedelta
import requests


# ============================================================================
# BUG #401, #402, #403 FIX: Automatic Retry with Exponential Backoff
# ============================================================================
class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(self, max_attempts=3, initial_delay=1.0, max_delay=60.0,
                 backoff_factor=2.0, jitter=True):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter


def retry_with_backoff(config=None, exceptions=(Exception,)):
    """
    Decorator to retry function with exponential backoff

    BUG #401 FIX: Socket disconnect should retry automatically

    Args:
        config: RetryConfig instance
        exceptions: Tuple of exceptions to retry on

    Usage:
        @retry_with_backoff(RetryConfig(max_attempts=5))
        def connect_to_database():
            # May fail temporarily
            pass
    """
    if config is None:
        config = RetryConfig()

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = config.initial_delay
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < config.max_attempts - 1:
                        # Add jitter to prevent thundering herd
                        if config.jitter:
                            import random
                            jitter_delay = delay * (0.5 + random.random())
                        else:
                            jitter_delay = delay

                        print(f"Attempt {attempt + 1} failed: {e}. Retrying in {jitter_delay:.2f}s...")
                        time.sleep(jitter_delay)

                        # Exponential backoff
                        delay = min(delay * config.backoff_factor, config.max_delay)
                    else:
                        print(f"All {config.max_attempts} attempts failed")
                        raise last_exception

            raise last_exception

        return wrapper
    return decorator


# ============================================================================
# BUG #402 FIX: Database Connection Recovery
# ============================================================================
def recover_db_connection(db, max_attempts=3):
    """
    Attempt to recover database connection

    BUG #402 FIX: Database connection loss not recovered
    """
    for attempt in range(max_attempts):
        try:
            # Test connection
            db.session.execute('SELECT 1')
            return True
        except Exception as e:
            print(f"DB connection recovery attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                try:
                    # Remove bad connection from pool
                    db.session.remove()
                    db.engine.dispose()
                except:
                    pass
            else:
                return False
    return False


# ============================================================================
# BUG #403 FIX: Redis Connection Failure Handling
# ============================================================================
class RedisConnectionManager:
    """
    Manager for Redis connections with automatic failover

    BUG #403 FIX: Redis connection failure not handled
    """
    def __init__(self, redis_url=None):
        self.redis_url = redis_url
        self.client = None
        self.last_connection_attempt = None
        self.connection_failures = 0
        self.max_failures = 5

    def connect(self):
        """Establish Redis connection"""
        if not self.redis_url:
            return None

        try:
            import redis
            self.client = redis.from_url(
                self.redis_url,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.client.ping()
            self.connection_failures = 0
            return self.client
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.connection_failures += 1
            self.last_connection_attempt = datetime.utcnow()
            return None

    def get_client(self):
        """Get Redis client with automatic reconnection"""
        if self.client is None:
            return self.connect()

        # Test if connection is still alive
        try:
            self.client.ping()
            return self.client
        except:
            # Connection lost, try to reconnect
            if self.connection_failures < self.max_failures:
                return self.connect()
            return None

    def is_available(self):
        """Check if Redis is available"""
        return self.get_client() is not None

    def safe_get(self, key, default=None):
        """Safely get value from Redis with fallback"""
        try:
            client = self.get_client()
            if client:
                value = client.get(key)
                return value.decode() if value else default
        except:
            pass
        return default

    def safe_set(self, key, value, expiry=None):
        """Safely set value in Redis"""
        try:
            client = self.get_client()
            if client:
                if expiry:
                    return client.setex(key, expiry, value)
                return client.set(key, value)
        except:
            pass
        return False


# ============================================================================
# BUG #404 FIX: HTTP Timeout Configuration
# ============================================================================
class TimeoutConfig:
    """HTTP request timeout configuration"""
    CONNECT_TIMEOUT = 5  # Time to establish connection
    READ_TIMEOUT = 30    # Time to receive response
    TOTAL_TIMEOUT = 60   # Total request time


def make_http_request(url, method='GET', timeout=None, **kwargs):
    """
    Make HTTP request with proper timeout handling

    BUG #404 FIX: HTTP timeout not configured

    Args:
        url: Request URL
        method: HTTP method
        timeout: Timeout in seconds or tuple (connect, read)
        **kwargs: Additional request parameters

    Returns:
        Response object or None on failure
    """
    if timeout is None:
        timeout = (TimeoutConfig.CONNECT_TIMEOUT, TimeoutConfig.READ_TIMEOUT)

    try:
        response = requests.request(
            method,
            url,
            timeout=timeout,
            **kwargs
        )
        response.raise_for_status()
        return response
    except requests.Timeout:
        print(f"Request to {url} timed out")
        return None
    except requests.ConnectionError:
        print(f"Connection to {url} failed")
        return None
    except requests.HTTPError as e:
        print(f"HTTP error for {url}: {e}")
        return None
    except Exception as e:
        print(f"Request to {url} failed: {e}")
        return None


# ============================================================================
# BUG #405 FIX: DNS Resolution Failure Handling
# ============================================================================
def resolve_hostname(hostname, timeout=5):
    """
    Resolve hostname with timeout

    BUG #405 FIX: DNS resolution failure not caught

    Returns:
        IP address or None on failure
    """
    try:
        socket.setdefaulttimeout(timeout)
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        print(f"DNS resolution failed for {hostname}")
        return None
    except socket.timeout:
        print(f"DNS resolution timeout for {hostname}")
        return None
    except Exception as e:
        print(f"DNS resolution error for {hostname}: {e}")
        return None
    finally:
        socket.setdefaulttimeout(None)


# ============================================================================
# BUG #407 FIX: Network Partition Handling
# ============================================================================
class NetworkPartitionDetector:
    """
    Detect and handle network partitions

    BUG #407 FIX: Network partition scenarios not handled
    """
    def __init__(self, check_interval=60):
        self.check_interval = check_interval
        self.last_check = None
        self.is_partitioned = False
        self.partition_start = None

    def check_connectivity(self, test_hosts=['8.8.8.8', '1.1.1.1']):
        """
        Check if we can reach internet

        Args:
            test_hosts: List of reliable hosts to ping

        Returns:
            True if connected, False if partitioned
        """
        now = datetime.utcnow()

        # Rate limit checks
        if self.last_check and (now - self.last_check).seconds < self.check_interval:
            return not self.is_partitioned

        self.last_check = now

        # Try to connect to test hosts
        for host in test_hosts:
            try:
                socket.create_connection((host, 53), timeout=3)
                # Successfully connected
                if self.is_partitioned:
                    print("Network partition resolved")
                self.is_partitioned = False
                self.partition_start = None
                return True
            except:
                continue

        # Could not reach any host
        if not self.is_partitioned:
            print("Network partition detected")
            self.partition_start = now
        self.is_partitioned = True
        return False

    def get_partition_duration(self):
        """Get how long we've been partitioned"""
        if self.partition_start:
            return (datetime.utcnow() - self.partition_start).seconds
        return 0


# ============================================================================
# BUG #408 FIX: Slow Client Timeout
# ============================================================================
class SlowClientDetector:
    """
    Detect and handle slow clients

    BUG #408 FIX: Slow client doesn't timeout
    """
    def __init__(self, timeout_seconds=30):
        self.timeout_seconds = timeout_seconds
        self.client_activity = {}  # {client_id: last_activity_time}

    def record_activity(self, client_id):
        """Record client activity"""
        self.client_activity[client_id] = time.time()

    def is_slow(self, client_id):
        """Check if client is responding slowly"""
        if client_id not in self.client_activity:
            return False

        last_activity = self.client_activity[client_id]
        return (time.time() - last_activity) > self.timeout_seconds

    def cleanup_inactive(self):
        """Remove inactive clients from tracking"""
        now = time.time()
        inactive = [
            client_id for client_id, last_active in self.client_activity.items()
            if now - last_active > self.timeout_seconds * 2
        ]
        for client_id in inactive:
            del self.client_activity[client_id]
        return inactive


# ============================================================================
# BUG #409 FIX: Half-Open Connection Detection
# ============================================================================
def detect_half_open_connections(socket_obj, timeout=5):
    """
    Detect half-open TCP connections

    BUG #409 FIX: Half-open connections not detected

    Args:
        socket_obj: Socket object to test
        timeout: Timeout for detection

    Returns:
        True if connection is alive, False if half-open
    """
    try:
        # Set socket to non-blocking temporarily
        socket_obj.settimeout(timeout)

        # Try to peek at data without removing it
        data = socket_obj.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)

        # If we get here without exception, connection is alive
        return True
    except socket.timeout:
        # Timeout means connection is slow but alive
        return True
    except socket.error as e:
        # Connection is broken
        return False
    except Exception:
        return False


# ============================================================================
# BUG #410 FIX: Connection Pool Exhaustion Handling
# ============================================================================
class ConnectionPoolMonitor:
    """
    Monitor and handle connection pool exhaustion

    BUG #410 FIX: Connection pool exhaustion crashes server
    """
    def __init__(self, engine, threshold=0.8):
        self.engine = engine
        self.threshold = threshold  # Alert when 80% full

    def get_pool_status(self):
        """Get current pool status"""
        pool = self.engine.pool
        size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()

        return {
            'size': size,
            'checked_out': checked_out,
            'available': size - checked_out,
            'overflow': overflow,
            'total': size + overflow,
            'utilization': checked_out / size if size > 0 else 0
        }

    def is_exhausted(self):
        """Check if pool is near exhaustion"""
        status = self.get_pool_status()
        return status['utilization'] >= self.threshold

    def cleanup_stale_connections(self):
        """Clean up stale connections"""
        try:
            self.engine.dispose()
            return True
        except Exception as e:
            print(f"Connection cleanup failed: {e}")
            return False


# ============================================================================
# Graceful Degradation
# ============================================================================
class ServiceHealthChecker:
    """
    Check health of external services and enable graceful degradation

    BUG #528 FIX: No graceful degradation
    """
    def __init__(self):
        self.services = {}  # {service_name: {'healthy': bool, 'last_check': datetime}}

    def check_service(self, service_name, check_func, cache_duration=60):
        """
        Check if service is healthy

        Args:
            service_name: Name of service
            check_func: Function that returns True if healthy
            cache_duration: How long to cache result (seconds)

        Returns:
            True if healthy, False otherwise
        """
        now = datetime.utcnow()

        # Check cache
        if service_name in self.services:
            service = self.services[service_name]
            if (now - service['last_check']).seconds < cache_duration:
                return service['healthy']

        # Run health check
        try:
            healthy = check_func()
        except:
            healthy = False

        # Update cache
        self.services[service_name] = {
            'healthy': healthy,
            'last_check': now
        }

        return healthy


# Global instances
redis_manager = RedisConnectionManager()
partition_detector = NetworkPartitionDetector()
slow_client_detector = SlowClientDetector()
service_health = ServiceHealthChecker()
