-- Migration: Security and Performance Enhancements
-- Date: 2025-10-15
-- Description: Add token blacklist, session enhancements, and performance indexes

-- ============================================================================
-- 1. CREATE TOKEN BLACKLIST TABLE (Bug #231 Fix)
-- ============================================================================

CREATE TABLE IF NOT EXISTS token_blacklist (
    id SERIAL PRIMARY KEY,
    jti VARCHAR(36) UNIQUE NOT NULL,
    token_type VARCHAR(10) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    blacklisted_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    expires_at TIMESTAMP NOT NULL,
    reason VARCHAR(100)
);

-- Indexes for token blacklist
CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti ON token_blacklist(jti);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON token_blacklist(expires_at);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_user ON token_blacklist(user_id);

COMMENT ON TABLE token_blacklist IS 'JWT tokens that have been revoked/blacklisted';
COMMENT ON COLUMN token_blacklist.jti IS 'JWT ID (unique identifier for each token)';
COMMENT ON COLUMN token_blacklist.reason IS 'Reason for blacklisting: logout, password_change, security';

-- ============================================================================
-- 2. ADD SESSION ENHANCEMENTS (Bug #233, #234 Fixes)
-- ============================================================================

-- Add new columns to sessions table
ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS last_activity TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'utc'),
    ADD COLUMN IF NOT EXISTS device_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS device_name VARCHAR(100),
    ADD COLUMN IF NOT EXISTS device_type VARCHAR(50);

-- Update existing sessions to have last_activity
UPDATE sessions
SET last_activity = created_at
WHERE last_activity IS NULL;

-- Indexes for session management
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_sessions_user_active ON sessions(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_device ON sessions(device_id);

COMMENT ON COLUMN sessions.last_activity IS 'Last time this session was used';
COMMENT ON COLUMN sessions.device_id IS 'Client-generated device identifier';
COMMENT ON COLUMN sessions.device_name IS 'User-friendly device name (e.g. iPhone 12)';
COMMENT ON COLUMN sessions.device_type IS 'Device type: desktop, mobile, tablet';

-- ============================================================================
-- 3. ADD PERFORMANCE INDEXES (Bug #282 Fix)
-- ============================================================================

-- GameHistory indexes for leaderboard queries
CREATE INDEX IF NOT EXISTS idx_leaderboard_score
    ON game_history(won, game_mode, score DESC);

CREATE INDEX IF NOT EXISTS idx_leaderboard_time
    ON game_history(won, score DESC, time_seconds ASC);

CREATE INDEX IF NOT EXISTS idx_user_games
    ON game_history(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_recent_games
    ON game_history(created_at DESC, won);

-- Additional useful indexes
CREATE INDEX IF NOT EXISTS idx_game_history_user_id ON game_history(user_id);
CREATE INDEX IF NOT EXISTS idx_game_history_username ON game_history(username);
CREATE INDEX IF NOT EXISTS idx_game_history_difficulty ON game_history(difficulty);
CREATE INDEX IF NOT EXISTS idx_game_history_score ON game_history(score DESC);
CREATE INDEX IF NOT EXISTS idx_game_history_won ON game_history(won);

-- Users table indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_account_status ON users(account_status);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);

-- SecurityAuditLog indexes
CREATE INDEX IF NOT EXISTS idx_audit_user_action ON security_audit_log(user_id, action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON security_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON security_audit_log(action);

-- PasswordResetToken indexes
CREATE INDEX IF NOT EXISTS idx_password_reset_expires ON password_reset_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id);

-- ============================================================================
-- 4. ADD MAINTENANCE FUNCTIONS
-- ============================================================================

-- Function to cleanup expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM token_blacklist
    WHERE expires_at < NOW() AT TIME ZONE 'utc';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_tokens IS 'Remove expired tokens from blacklist';

-- Function to cleanup expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sessions
    WHERE expires_at < NOW() AT TIME ZONE 'utc';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_sessions IS 'Remove expired sessions';

-- Function to cleanup inactive sessions
CREATE OR REPLACE FUNCTION cleanup_inactive_sessions(days_inactive INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
    cutoff_date TIMESTAMP;
BEGIN
    cutoff_date := NOW() AT TIME ZONE 'utc' - (days_inactive || ' days')::INTERVAL;

    DELETE FROM sessions
    WHERE last_activity < cutoff_date;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_inactive_sessions IS 'Remove sessions inactive for specified days';

-- Function to rotate old audit logs
CREATE OR REPLACE FUNCTION rotate_audit_logs(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
    cutoff_date TIMESTAMP;
BEGIN
    cutoff_date := NOW() AT TIME ZONE 'utc' - (days_to_keep || ' days')::INTERVAL;

    -- In production, consider archiving before deleting
    DELETE FROM security_audit_log
    WHERE created_at < cutoff_date;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION rotate_audit_logs IS 'Delete audit logs older than specified days';

-- ============================================================================
-- 5. UPDATE STATISTICS
-- ============================================================================

ANALYZE users;
ANALYZE sessions;
ANALYZE game_history;
ANALYZE security_audit_log;
ANALYZE token_blacklist;

-- ============================================================================
-- 6. VERIFICATION QUERIES
-- ============================================================================

-- Verify token_blacklist table created
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'token_blacklist'
) AS token_blacklist_exists;

-- Verify sessions columns added
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'sessions'
  AND column_name IN ('last_activity', 'device_id', 'device_name', 'device_type');

-- Count indexes created
SELECT COUNT(*) as index_count
FROM pg_indexes
WHERE schemaname = 'public'
  AND (indexname LIKE 'idx_%');

-- Verify functions created
SELECT routine_name
FROM information_schema.routines
WHERE routine_type = 'FUNCTION'
  AND routine_name LIKE 'cleanup%';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Output summary
DO $$
BEGIN
    RAISE NOTICE 'Migration 001_security_and_performance completed successfully';
    RAISE NOTICE 'Tables created: token_blacklist';
    RAISE NOTICE 'Columns added to sessions: last_activity, device_id, device_name, device_type';
    RAISE NOTICE 'Indexes created: 20+ performance indexes';
    RAISE NOTICE 'Functions created: cleanup_expired_tokens, cleanup_expired_sessions, cleanup_inactive_sessions, rotate_audit_logs';
    RAISE NOTICE '';
    RAISE NOTICE 'IMPORTANT: Set up scheduled tasks to call cleanup functions regularly';
    RAISE NOTICE 'Recommended: Daily cleanup of expired tokens/sessions, weekly cleanup of inactive sessions';
END $$;
