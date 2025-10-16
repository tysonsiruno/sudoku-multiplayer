# 🚀 Comprehensive Implementation Plan
## Minesweeper Multiplayer - Authentication, Security & Bug Fixes

**Created:** October 13, 2025
**Status:** Planning Phase
**Priority:** Critical Bug Fixes → Authentication → Security → Features

---

## 📋 TABLE OF CONTENTS

1. [Critical Bug Fixes (Do First)](#critical-bug-fixes)
2. [Database Setup](#database-setup)
3. [Authentication System](#authentication-system)
4. [Security Features](#security-features)
5. [Frontend Implementation](#frontend-implementation)
6. [Backend Implementation](#backend-implementation)
7. [Email System](#email-system)
8. [Guest Mode](#guest-mode)
9. [Testing & Validation](#testing-validation)
10. [Deployment Considerations](#deployment)

---

## 🔥 CRITICAL BUG FIXES (DO FIRST)
**Priority: P0 - Must fix before adding features**

### 1. Mobile Board Layout Issue
**Problem:** Cells on far left cannot be clicked on mobile
**Impact:** Game unplayable on mobile for leftmost column
**Root Cause:** Canvas offset calculation or touch event positioning

**Fix Steps:**
- [ ] Investigate canvas positioning on mobile (getBoundingClientRect)
- [ ] Check if canvas is being cut off by viewport
- [ ] Test touch event coordinates match canvas coordinates
- [ ] Add padding/margin adjustments for mobile
- [ ] Test on multiple mobile screen sizes

**Files to modify:**
- `server/web/game.js` (touch event handlers, lines 184-215)
- `server/web/styles.css` (canvas responsive styles)

---

### 2. ICantLose Cheat Not Working on Mobile
**Problem:** Cheat username doesn't work on mobile devices
**Impact:** Testing and debugging difficult on mobile
**Root Cause:** Unknown - needs investigation

**Fix Steps:**
- [ ] Add console.log to verify username is stored correctly on mobile
- [ ] Check if cheat logic executes (revealCell mine handling)
- [ ] Test touch events trigger same code path as mouse events
- [ ] Verify localStorage works on mobile browsers
- [ ] Add mobile-specific debugging UI

**Files to check:**
- `server/web/game.js` (lines 256-294 username masking, lines 324-355 mine cheat logic)

---

### 3. Russian Roulette Multiplayer Turn System
**Problem:** Turn system broken - can't click after opponent's turn
**Impact:** Russian Roulette multiplayer completely broken
**Root Cause:** Turn synchronization or state management issue

**Issues to fix:**
- [ ] Opponent's moves not visible in real-time
- [ ] Turn indicator not updating correctly
- [ ] Click events blocked incorrectly
- [ ] Server not broadcasting turn changes properly

**Fix Steps:**
- [ ] Add logging to `turn_changed` socket event
- [ ] Verify `state.currentTurn` updates on client
- [ ] Check `revealCell` turn validation (line 297-299)
- [ ] Test `game_action` broadcast to other players
- [ ] Add visual feedback for opponent's moves
- [ ] Show opponent's revealed cells in real-time

**Files to modify:**
- `server/web/game.js` (turn validation, socket listeners)
- `server/app.py` (turn_changed event, player_action broadcast)

---

## 🗄️ DATABASE SETUP

### PostgreSQL Schema Design

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    is_guest BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    profile_picture_url VARCHAR(500),
    total_games_played INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    total_losses INTEGER DEFAULT 0,
    highest_score INTEGER DEFAULT 0,
    account_status VARCHAR(20) DEFAULT 'active', -- active, suspended, deleted
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP
);

-- Email verification tokens
CREATE TABLE email_verification_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP
);

-- Password reset tokens
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP,
    ip_address VARCHAR(50)
);

-- Sessions
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(50),
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- Game history (enhanced leaderboard)
CREATE TABLE game_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50) NOT NULL, -- Denormalized for guest users
    game_mode VARCHAR(50) NOT NULL,
    difficulty VARCHAR(50),
    score INTEGER NOT NULL,
    time_seconds INTEGER NOT NULL,
    tiles_clicked INTEGER NOT NULL,
    hints_used INTEGER NOT NULL,
    won BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    room_code VARCHAR(10), -- For multiplayer games
    multiplayer BOOLEAN DEFAULT FALSE
);

-- Rate limiting
CREATE TABLE rate_limit_log (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    request_count INTEGER DEFAULT 1,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ip_endpoint (ip_address, endpoint, window_start)
);

-- Security audit log
CREATE TABLE security_audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    ip_address VARCHAR(50),
    user_agent TEXT,
    success BOOLEAN,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Database Connection Setup

**Dependencies:**
```bash
pip install psycopg2-binary
pip install SQLAlchemy  # ORM for easier database operations
```

**Environment Variables:**
```env
DATABASE_URL=postgresql://user:password@localhost:5432/minesweeper_db
```

---

## 🔐 AUTHENTICATION SYSTEM

### 1. User Registration
**Flow:**
1. User enters username, email, password
2. Server validates input (length, format, uniqueness)
3. Password hashed with bcrypt (cost factor 12)
4. User created with `is_verified=False`
5. Verification email sent with unique token
6. Redirect to "Check your email" page

**Validation Rules:**
- Username: 3-20 characters, alphanumeric + underscore
- Email: Valid email format
- Password: Min 8 characters, at least 1 uppercase, 1 lowercase, 1 number, 1 special char
- No SQL injection characters
- Rate limit: 5 registration attempts per IP per hour

**API Endpoint:**
```
POST /api/auth/register
Body: {
    "username": "string",
    "email": "string",
    "password": "string"
}
Response: {
    "success": true,
    "message": "Registration successful. Please check your email to verify your account.",
    "user_id": 123
}
```

---

### 2. Email Verification
**Flow:**
1. User clicks link in email: `/verify-email?token=XYZ`
2. Server validates token (exists, not expired, not used)
3. Mark user as `is_verified=True`
4. Mark token as `used_at=NOW()`
5. Auto-login user or redirect to login page

**Token Details:**
- Format: UUID v4 (128-bit random)
- Expiration: 24 hours
- Single-use only

**API Endpoint:**
```
GET /api/auth/verify-email?token=XYZ
Response: {
    "success": true,
    "message": "Email verified successfully. You can now log in."
}
```

---

### 3. Login System
**Flow:**
1. User enters username/email + password
2. Server checks credentials
3. Check if account is locked (failed attempts)
4. Check if email is verified
5. Generate JWT access token (15 min expiry)
6. Generate refresh token (7 days expiry)
7. Create session record
8. Return tokens + user info

**Security Measures:**
- Max 5 failed attempts → lock account for 15 minutes
- Log all login attempts (success/failure)
- Check if logging in from new IP/device → email notification
- HTTPS only
- httpOnly cookies for tokens

**API Endpoint:**
```
POST /api/auth/login
Body: {
    "username_or_email": "string",
    "password": "string",
    "remember_me": false
}
Response: {
    "success": true,
    "access_token": "jwt_token_here",
    "refresh_token": "refresh_token_here",
    "user": {
        "id": 123,
        "username": "player1",
        "email": "player@example.com",
        "is_verified": true
    }
}
```

---

### 4. Password Reset
**Flow:**
1. User clicks "Forgot Password"
2. Enters email address
3. Server generates reset token (if email exists)
4. Email sent with reset link: `/reset-password?token=XYZ`
5. User clicks link, enters new password
6. Server validates token, updates password
7. Invalidate all existing sessions
8. Send confirmation email

**Security:**
- Token expires in 1 hour
- Single-use token
- Rate limit: 3 reset requests per email per hour
- Log IP address of reset requests
- Notify user if suspicious activity

**API Endpoints:**
```
POST /api/auth/forgot-password
Body: { "email": "string" }
Response: { "success": true, "message": "If email exists, reset link sent" }

POST /api/auth/reset-password
Body: {
    "token": "string",
    "new_password": "string"
}
Response: { "success": true, "message": "Password reset successful" }
```

---

### 5. Token Refresh
**Flow:**
1. Access token expires (15 min)
2. Client sends refresh token
3. Server validates refresh token
4. Generate new access token
5. Optionally rotate refresh token

**API Endpoint:**
```
POST /api/auth/refresh
Body: { "refresh_token": "string" }
Response: {
    "access_token": "new_jwt_token",
    "refresh_token": "new_refresh_token (optional)"
}
```

---

### 6. Logout
**Flow:**
1. Client sends logout request with tokens
2. Server invalidates session
3. Clear cookies
4. Return success

**API Endpoint:**
```
POST /api/auth/logout
Headers: { "Authorization": "Bearer <access_token>" }
Response: { "success": true, "message": "Logged out successfully" }
```

---

## 🛡️ SECURITY FEATURES

### 1. Password Security
- **Hashing:** bcrypt with cost factor 12
- **Requirements:**
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 number
  - At least 1 special character (!@#$%^&*)
- **Validation:** zxcvbn password strength meter on frontend
- **Storage:** Never store plaintext passwords

**Implementation:**
```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
```

---

### 2. JWT Authentication
**Access Token (Short-lived):**
- Expiry: 15 minutes
- Payload: user_id, username, is_verified, iat, exp
- Signed with HS256 algorithm
- Used for API authentication

**Refresh Token (Long-lived):**
- Expiry: 7 days (or 30 days with "Remember Me")
- Stored in database
- Used to generate new access tokens
- Invalidated on logout/password change

**JWT Secret:**
- Stored in environment variable
- Minimum 256-bit random key
- Rotated periodically in production

**Implementation:**
```python
import jwt
from datetime import datetime, timedelta

def generate_access_token(user_id: int, username: str) -> str:
    payload = {
        'user_id': user_id,
        'username': username,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(minutes=15)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')
```

---

### 3. Rate Limiting
**Endpoints to protect:**
- `/api/auth/register` - 5 requests per hour per IP
- `/api/auth/login` - 10 requests per 15 minutes per IP
- `/api/auth/forgot-password` - 3 requests per hour per IP
- `/api/leaderboard/submit` - 100 requests per hour per user
- `/api/rooms/create` - 20 requests per hour per user

**Implementation:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379"
)

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per 15 minutes")
def login():
    pass
```

---

### 4. Input Sanitization
**Protect against:**
- SQL Injection (use parameterized queries)
- XSS (escape HTML in user inputs)
- CSRF (use CSRF tokens)
- Command Injection
- Path Traversal

**Implementation:**
```python
import bleach
from markupsafe import escape

def sanitize_username(username: str) -> str:
    # Allow only alphanumeric and underscore
    return ''.join(c for c in username if c.isalnum() or c == '_')

def sanitize_html(text: str) -> str:
    # Remove all HTML tags
    return bleach.clean(text, tags=[], strip=True)
```

---

### 5. CSRF Protection
**Implementation:**
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)

# In forms, include CSRF token:
# <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

---

### 6. Security Headers
**Add these headers to all responses:**
```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.socket.io; style-src 'self' 'unsafe-inline'"
    return response
```

---

### 7. Account Lockout
**Failed Login Protection:**
- Track failed login attempts per username/email
- After 5 failed attempts → lock account for 15 minutes
- Reset counter on successful login
- Send email notification on account lock

**Implementation:**
```python
def check_account_locked(user):
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).total_seconds() / 60
        return True, f"Account locked. Try again in {int(remaining)} minutes."
    return False, None

def handle_failed_login(user):
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= 5:
        user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        send_account_locked_email(user.email)
    db.session.commit()
```

---

## 🎨 FRONTEND IMPLEMENTATION

### New Screens to Create

#### 1. **Login Screen** (`login.html`)
```html
<div id="login-screen" class="screen">
    <div class="container">
        <h1>Welcome Back!</h1>
        <form id="login-form">
            <input type="text" id="login-username" placeholder="Username or Email" required>
            <input type="password" id="login-password" placeholder="Password" required>
            <label>
                <input type="checkbox" id="remember-me"> Remember Me
            </label>
            <button type="submit" class="btn btn-primary">Login</button>
        </form>
        <div id="login-error" class="error-message"></div>
        <div class="links">
            <a href="#" id="forgot-password-link">Forgot Password?</a>
            <a href="#" id="show-register-link">Create Account</a>
            <a href="#" id="continue-guest-link">Continue as Guest</a>
        </div>
    </div>
</div>
```

---

#### 2. **Registration Screen** (`register.html`)
```html
<div id="register-screen" class="screen">
    <div class="container">
        <h1>Create Account</h1>
        <form id="register-form">
            <input type="text" id="register-username" placeholder="Username (3-20 characters)" required>
            <input type="email" id="register-email" placeholder="Email Address" required>
            <input type="password" id="register-password" placeholder="Password (min 8 characters)" required>
            <input type="password" id="register-confirm-password" placeholder="Confirm Password" required>
            <div id="password-strength"></div>
            <button type="submit" class="btn btn-primary">Create Account</button>
        </form>
        <div id="register-error" class="error-message"></div>
        <div class="links">
            <a href="#" id="show-login-link">Already have an account? Login</a>
        </div>
    </div>
</div>
```

---

#### 3. **Email Verification Screen**
```html
<div id="verify-email-screen" class="screen">
    <div class="container">
        <h1>Check Your Email</h1>
        <p>We've sent a verification link to your email address.</p>
        <p>Please click the link to verify your account.</p>
        <button id="resend-verification" class="btn btn-secondary">Resend Email</button>
    </div>
</div>
```

---

#### 4. **Forgot Password Screen**
```html
<div id="forgot-password-screen" class="screen">
    <div class="container">
        <h1>Reset Password</h1>
        <form id="forgot-password-form">
            <input type="email" id="forgot-email" placeholder="Enter your email" required>
            <button type="submit" class="btn btn-primary">Send Reset Link</button>
        </form>
        <div id="forgot-error" class="error-message"></div>
        <div class="links">
            <a href="#" id="back-to-login-link">Back to Login</a>
        </div>
    </div>
</div>
```

---

#### 5. **Reset Password Screen**
```html
<div id="reset-password-screen" class="screen">
    <div class="container">
        <h1>Set New Password</h1>
        <form id="reset-password-form">
            <input type="password" id="new-password" placeholder="New Password" required>
            <input type="password" id="confirm-new-password" placeholder="Confirm Password" required>
            <button type="submit" class="btn btn-primary">Reset Password</button>
        </form>
        <div id="reset-error" class="error-message"></div>
    </div>
</div>
```

---

#### 6. **Profile Screen**
```html
<div id="profile-screen" class="screen">
    <div class="container">
        <h1>Profile</h1>
        <div class="profile-info">
            <div class="profile-avatar">
                <img id="profile-picture" src="/default-avatar.png" alt="Avatar">
                <button id="change-avatar-btn" class="btn btn-small">Change Avatar</button>
            </div>
            <div class="profile-stats">
                <h2 id="profile-username">Username</h2>
                <p>Email: <span id="profile-email">email@example.com</span></p>
                <p>Member since: <span id="profile-joined">Jan 2025</span></p>
                <hr>
                <h3>Statistics</h3>
                <p>Total Games: <span id="total-games">0</span></p>
                <p>Wins: <span id="total-wins">0</span></p>
                <p>Win Rate: <span id="win-rate">0%</span></p>
                <p>Highest Score: <span id="highest-score">0</span></p>
            </div>
        </div>
        <button id="edit-profile-btn" class="btn btn-primary">Edit Profile</button>
        <button id="logout-btn" class="btn btn-secondary">Logout</button>
    </div>
</div>
```

---

### JavaScript Authentication Handler

**New file:** `server/web/auth.js`
```javascript
// Authentication state
const authState = {
    isLoggedIn: false,
    isGuest: false,
    user: null,
    accessToken: null,
    refreshToken: null
};

// Check if user is logged in on page load
async function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        showLoginScreen();
        return;
    }

    try {
        const response = await fetch(`${SERVER_URL}/api/auth/verify-token`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const data = await response.json();
            authState.isLoggedIn = true;
            authState.user = data.user;
            authState.accessToken = token;
            showUsernameScreen(); // Or skip to mode selection
        } else {
            // Token invalid, try refresh
            await refreshAccessToken();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showLoginScreen();
    }
}

// Login handler
async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const rememberMe = document.getElementById('remember-me').checked;

    try {
        const response = await fetch(`${SERVER_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username_or_email: username, password, remember_me: rememberMe })
        });

        const data = await response.json();
        if (data.success) {
            // Store tokens
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            authState.isLoggedIn = true;
            authState.user = data.user;
            authState.accessToken = data.access_token;

            // Redirect to game
            showScreen('mode-screen');
        } else {
            document.getElementById('login-error').textContent = data.message;
        }
    } catch (error) {
        document.getElementById('login-error').textContent = 'Login failed. Please try again.';
    }
}

// Register handler
async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('register-username').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;

    if (password !== confirmPassword) {
        document.getElementById('register-error').textContent = 'Passwords do not match';
        return;
    }

    try {
        const response = await fetch(`${SERVER_URL}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();
        if (data.success) {
            showScreen('verify-email-screen');
        } else {
            document.getElementById('register-error').textContent = data.message;
        }
    } catch (error) {
        document.getElementById('register-error').textContent = 'Registration failed. Please try again.';
    }
}

// Continue as guest
function continueAsGuest() {
    authState.isGuest = true;
    authState.isLoggedIn = false;
    showScreen('username-screen');
}

// Logout
async function handleLogout() {
    try {
        await fetch(`${SERVER_URL}/api/auth/logout`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authState.accessToken}` }
        });
    } catch (error) {
        console.error('Logout failed:', error);
    }

    // Clear local storage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    // Reset state
    authState.isLoggedIn = false;
    authState.isGuest = false;
    authState.user = null;
    authState.accessToken = null;

    showScreen('login-screen');
}
```

---

## 🔧 BACKEND IMPLEMENTATION

### File Structure
```
server/
├── app.py (main Flask app)
├── models.py (SQLAlchemy models)
├── auth.py (authentication logic)
├── email_service.py (email sending)
├── security.py (security utilities)
├── config.py (configuration)
└── requirements.txt
```

---

### Dependencies
```txt
flask==3.0.0
flask-socketio==5.3.5
flask-cors==4.0.0
flask-limiter==3.5.0
flask-wtf==1.2.1
psycopg2-binary==2.9.9
SQLAlchemy==2.0.23
bcrypt==4.1.2
PyJWT==2.8.0
python-dotenv==1.0.0
sendgrid==6.11.0
bleach==6.1.0
zxcvbn==4.4.28
redis==5.0.1
```

---

### models.py
```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_guest = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    profile_picture_url = db.Column(db.String(500))
    total_games_played = db.Column(db.Integer, default=0)
    total_wins = db.Column(db.Integer, default=0)
    total_losses = db.Column(db.Integer, default=0)
    highest_score = db.Column(db.Integer, default=0)
    account_status = db.Column(db.String(20), default='active')
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)

    # Relationships
    sessions = db.relationship('Session', backref='user', lazy=True, cascade='all, delete-orphan')
    game_history = db.relationship('GameHistory', backref='user', lazy=True)

class EmailVerificationToken(db.Model):
    __tablename__ = 'email_verification_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime)

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime)
    ip_address = db.Column(db.String(50))

class Session(db.Model):
    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    refresh_token = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class GameHistory(db.Model):
    __tablename__ = 'game_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    username = db.Column(db.String(50), nullable=False)
    game_mode = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(50))
    score = db.Column(db.Integer, nullable=False)
    time_seconds = db.Column(db.Integer, nullable=False)
    tiles_clicked = db.Column(db.Integer, nullable=False)
    hints_used = db.Column(db.Integer, nullable=False)
    won = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    room_code = db.Column(db.String(10))
    multiplayer = db.Column(db.Boolean, default=False)
```

---

## 📧 EMAIL SYSTEM

### Email Service Options
1. **SendGrid** (Recommended - 100 free emails/day)
2. **Mailgun** (5,000 free emails/month)
3. **AWS SES** (62,000 free emails/month)

### SendGrid Setup
```bash
pip install sendgrid
```

**Environment Variable:**
```env
SENDGRID_API_KEY=your_api_key_here
FROM_EMAIL=noreply@yourdomain.com
```

### email_service.py
```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@minesweeper.com')

def send_verification_email(to_email: str, username: str, token: str):
    verify_link = f"https://yourdomain.com/verify-email?token={token}"

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject='Verify your email - Minesweeper Multiplayer',
        html_content=f'''
            <h1>Welcome to Minesweeper Multiplayer, {username}!</h1>
            <p>Please click the link below to verify your email address:</p>
            <a href="{verify_link}" style="display: inline-block; padding: 10px 20px; background-color: #667eea; color: white; text-decoration: none; border-radius: 5px;">Verify Email</a>
            <p>This link will expire in 24 hours.</p>
            <p>If you didn't create an account, please ignore this email.</p>
        '''
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_password_reset_email(to_email: str, username: str, token: str):
    reset_link = f"https://yourdomain.com/reset-password?token={token}"

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject='Reset your password - Minesweeper Multiplayer',
        html_content=f'''
            <h1>Password Reset Request</h1>
            <p>Hi {username},</p>
            <p>We received a request to reset your password. Click the link below to set a new password:</p>
            <a href="{reset_link}" style="display: inline-block; padding: 10px 20px; background-color: #667eea; color: white; text-decoration: none; border-radius: 5px;">Reset Password</a>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this, please ignore this email and your password will remain unchanged.</p>
        '''
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
```

---

## 👤 GUEST MODE

### Features
- Play without creating account
- Username stored only in session (not database)
- Limited features:
  - ✅ Can play all game modes
  - ✅ Can join/create multiplayer rooms
  - ❌ Scores not saved to leaderboard
  - ❌ No game history
  - ❌ No profile page
  - ❌ Stats reset on logout

### Implementation
**Frontend:**
- Add "Continue as Guest" button on login screen
- Show banner: "You're playing as guest. Create account to save progress"
- Persistent prompt to create account after games

**Backend:**
- No database entries for guest users
- All game state stored in memory/session only
- Guest scores shown in real-time leaderboard but not persisted

---

## ✅ TESTING & VALIDATION

### Unit Tests
```python
# tests/test_auth.py
def test_registration():
    # Test valid registration
    # Test duplicate username
    # Test duplicate email
    # Test invalid password
    pass

def test_login():
    # Test valid login
    # Test wrong password
    # Test unverified email
    # Test account lockout
    pass

def test_password_reset():
    # Test token generation
    # Test token expiration
    # Test single-use token
    pass
```

### Integration Tests
- Test full registration → verification → login flow
- Test password reset flow
- Test guest mode
- Test rate limiting

### Security Tests
- SQL injection tests
- XSS tests
- CSRF tests
- Brute force login tests
- Token manipulation tests

---

## 🚀 DEPLOYMENT CONSIDERATIONS

### Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# JWT
JWT_SECRET=your-256-bit-secret-key-here
JWT_REFRESH_SECRET=your-refresh-secret-key-here

# Email
SENDGRID_API_KEY=your-sendgrid-api-key
FROM_EMAIL=noreply@yourdomain.com

# Security
FLASK_SECRET_KEY=your-flask-secret-key
CSRF_SECRET=your-csrf-secret

# Redis (for rate limiting)
REDIS_URL=redis://localhost:6379

# App
FLASK_ENV=production
DOMAIN=https://yourdomain.com
```

### Database Migration
```bash
# Using Alembic
alembic init migrations
alembic revision --autogenerate -m "Create user tables"
alembic upgrade head
```

### Production Checklist
- [ ] HTTPS enabled
- [ ] Environment variables set
- [ ] Database backups configured
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Email service configured
- [ ] Error logging (Sentry)
- [ ] Monitoring (uptime checks)

---

## 📊 IMPLEMENTATION PRIORITY ORDER

### Phase 1: Critical Bug Fixes (1-2 hours)
1. ✅ Fix mobile board layout
2. ✅ Fix ICantLose cheat on mobile
3. ✅ Fix Russian Roulette multiplayer turn system

### Phase 2: Database Setup (1 hour)
4. Set up PostgreSQL database
5. Create tables/models
6. Test database connection

### Phase 3: Backend Authentication (3-4 hours)
7. Implement user registration endpoint
8. Implement login endpoint
9. Implement JWT token generation/validation
10. Implement password reset endpoints
11. Add rate limiting

### Phase 4: Email System (1 hour)
12. Set up SendGrid/email service
13. Create email templates
14. Test email sending

### Phase 5: Frontend Auth UI (2-3 hours)
15. Create login screen
16. Create registration screen
17. Create forgot password screen
18. Create profile screen
19. Implement auth.js logic

### Phase 6: Security Features (2 hours)
20. Add password hashing
21. Add input sanitization
22. Add CSRF protection
23. Add security headers
24. Add account lockout

### Phase 7: Guest Mode (1 hour)
25. Implement guest mode logic
26. Add guest UI elements

### Phase 8: Testing (2 hours)
27. Test all authentication flows
28. Test security measures
29. Test on mobile devices
30. Fix any bugs found

**Total Estimated Time: 15-20 hours**

---

## 📝 NOTES

### Optional Enhancements (Future)
- OAuth (Google/Discord login)
- Two-factor authentication (2FA)
- Account deletion
- Username/email change
- Password change (while logged in)
- Session management (see all active sessions)
- Account recovery questions
- IP whitelist/blacklist

### Mobile Optimization
- Touch-friendly buttons (min 44x44px)
- Larger text on small screens
- Better canvas positioning
- Zoom disabled on inputs
- Proper viewport meta tag

---

**Last Updated:** October 13, 2025
**Status:** Ready for Implementation
**Next Step:** Fix critical bugs first, then start Phase 2
