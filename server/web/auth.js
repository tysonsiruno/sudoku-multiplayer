/**
 * Authentication Handler for Minesweeper Multiplayer
 * Handles login, registration, token management, and user sessions
 */

const AUTH_API = '/api/auth';

// ============================================================================
// AUTH STATE MANAGEMENT
// ============================================================================

const AuthState = {
    user: null,
    accessToken: null,
    refreshToken: null,
    isGuest: false,
    isAuthenticated: false,
    displayName: null
};

/**
 * Initialize authentication on page load
 */
function initAuth() {
    // BUG #147 FIX: Check token expiration before using
    const accessToken = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');

    if (accessToken) {
        AuthState.accessToken = accessToken;
        AuthState.refreshToken = refreshToken;

        // Verify token is still valid
        verifyCurrentUser().then(valid => {
            if (!valid) {
                // Token expired, try to refresh
                refreshAccessToken().catch(() => {
                    // Refresh failed, clear auth
                    clearAuth();
                });
            }
        }).catch(() => {
            // BUG #148 FIX: Handle promise rejection
            clearAuth();
        });
    }

    // Check for URL parameters (password reset only)
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    // BUG #149 FIX: Validate and sanitize token from URL
    if (window.location.pathname === '/reset-password' && token && token.length > 0 && token.length < 200) {
        showResetPasswordForm(token);
    }
}

// ============================================================================
// TOKEN MANAGEMENT
// ============================================================================

/**
 * Save tokens to localStorage
 */
function saveTokens(accessToken, refreshToken) {
    localStorage.setItem('access_token', accessToken);
    if (refreshToken) {
        localStorage.setItem('refresh_token', refreshToken);
    }
    AuthState.accessToken = accessToken;
    AuthState.refreshToken = refreshToken;
}

/**
 * Clear authentication tokens and state
 */
function clearAuth() {
    // BUG #150, #170 FIX: Handle storage errors gracefully
    try {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_data');
        localStorage.removeItem('display_name');
    } catch (e) {
        console.error('Failed to clear localStorage:', e);
    }

    AuthState.user = null;
    AuthState.accessToken = null;
    AuthState.refreshToken = null;
    AuthState.isGuest = false;
    AuthState.isAuthenticated = false;
}

/**
 * Get authorization header for API requests
 */
function getAuthHeader() {
    // BUG #151 FIX: Validate accessToken is a non-empty string
    if (AuthState.accessToken && typeof AuthState.accessToken === 'string' && AuthState.accessToken.length > 0) {
        return { 'Authorization': `Bearer ${AuthState.accessToken}` };
    }
    return {};
}

/**
 * Refresh access token using refresh token
 */
async function refreshAccessToken() {
    if (!AuthState.refreshToken) {
        throw new Error('No refresh token available');
    }

    try {
        const response = await fetch(`${AUTH_API}/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${AuthState.refreshToken}`
            }
        });

        // BUG #152, #159 FIX: Check response.ok before parsing JSON
        if (!response.ok) {
            clearAuth();
            return false;
        }

        const data = await response.json();

        if (data.success) {
            saveTokens(data.access_token, data.refresh_token);
            return true;
        } else {
            clearAuth();
            return false;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
        clearAuth();
        return false;
    }
}

/**
 * Verify current user is still valid
 */
async function verifyCurrentUser() {
    try {
        const response = await fetch(`${AUTH_API}/me`, {
            headers: getAuthHeader()
        });

        const data = await response.json();

        if (data.success && data.user) {
            AuthState.user = data.user;
            AuthState.isAuthenticated = true;
            // BUG #153 FIX: Handle JSON stringify errors
            try {
                localStorage.setItem('user_data', JSON.stringify(data.user));
            } catch (e) {
                console.error('Failed to save user data:', e);
            }
            updateUIForAuthState();
            return true;
        } else {
            return false;
        }
    } catch (error) {
        console.error('User verification failed:', error);
        return false;
    }
}

// ============================================================================
// REGISTRATION
// ============================================================================

/**
 * Register a new user account (with retry logic)
 */
async function register(username, email, password, retryCount = 0) {
    const errorEl = document.getElementById('register-error');
    const successEl = document.getElementById('register-success');

    // Clear previous messages
    if (errorEl) errorEl.textContent = '';
    if (successEl) successEl.textContent = '';

    // Client-side validation
    if (!username || username.length < 3) {
        if (errorEl) {
            errorEl.textContent = 'Username must be at least 3 characters';
            errorEl.style.display = 'block';
        }
        return false;
    }

    // BUG #154 FIX: Better email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email)) {
        if (errorEl) {
            errorEl.textContent = 'Please enter a valid email address';
            errorEl.style.display = 'block';
        }
        return false;
    }

    if (!password || password.length < 8) {
        if (errorEl) {
            errorEl.textContent = 'Password must be at least 8 characters';
            errorEl.style.display = 'block';
        }
        return false;
    }

    // Show loading state
    if (errorEl && retryCount === 0) {
        errorEl.textContent = 'Creating account...';
        errorEl.style.color = '#667eea';
        errorEl.style.display = 'block';
    }

    try {
        // BUG #155, #156 FIX: Configurable timeout and proper cleanup
        const controller = new AbortController();
        const timeout = 10000; // 10 seconds
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        const response = await fetch(`${AUTH_API}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password }),
            signal: controller.signal
        });

        if (timeoutId) clearTimeout(timeoutId);

        const data = await response.json();

        if (data.success) {
            if (successEl) {
                successEl.textContent = data.message || 'Registration successful! You can now log in.';
                successEl.style.display = 'block';
            }

            // Hide error message
            if (errorEl) errorEl.style.display = 'none';

            // BUG #157 FIX: Validate elements exist before clearing
            const usernameEl = document.getElementById('register-username');
            const emailEl = document.getElementById('register-email');
            const passwordEl = document.getElementById('register-password');
            const passwordConfirmEl = document.getElementById('register-password-confirm');
            if (usernameEl) usernameEl.value = '';
            if (emailEl) emailEl.value = '';
            if (passwordEl) passwordEl.value = '';
            if (passwordConfirmEl) passwordConfirmEl.value = '';

            // Switch to login screen after 2 seconds
            setTimeout(() => {
                showScreen('login-screen');
            }, 2000);

            return true;
        } else {
            if (errorEl) {
                errorEl.textContent = data.message || 'Registration failed';
                errorEl.style.color = '#ff6b6b';
                errorEl.style.display = 'block';
            }
            return false;
        }
    } catch (error) {
        console.error('Registration error (attempt ' + (retryCount + 1) + '):', error);

        // BUG #158 FIX: Exponential backoff (not linear)
        if (retryCount < 2 && (error.name === 'AbortError' || error.name === 'TypeError')) {
            const backoffMs = Math.pow(2, retryCount) * 1000; // 1s, 2s exponential
            console.log('Retrying registration in ' + backoffMs + 'ms...');
            if (errorEl) {
                errorEl.textContent = 'Connection issue, retrying... (' + (retryCount + 1) + '/2)';
                errorEl.style.color = '#f39c12';
            }
            await new Promise(resolve => setTimeout(resolve, backoffMs));
            return register(username, email, password, retryCount + 1);
        }

        // Failed after retries
        if (errorEl) {
            errorEl.textContent = 'Network error. Please check your connection and try again.';
            errorEl.style.color = '#ff6b6b';
            errorEl.style.display = 'block';
        }
        return false;
    }
}

// ============================================================================
// LOGIN
// ============================================================================

/**
 * Login with username/email and password (with retry logic)
 */
async function login(usernameOrEmail, password, rememberMe = false, retryCount = 0) {
    const errorEl = document.getElementById('login-error');

    // Clear previous errors
    if (errorEl) errorEl.textContent = '';

    if (!usernameOrEmail || !password) {
        if (errorEl) errorEl.textContent = 'Please enter username and password';
        return false;
    }

    // Show loading state
    if (errorEl && retryCount === 0) {
        errorEl.textContent = 'Logging in...';
        errorEl.style.color = '#667eea';
        errorEl.style.display = 'block';
    }

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

        const response = await fetch(`${AUTH_API}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username_or_email: usernameOrEmail,
                password: password,
                remember_me: rememberMe
            }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        // Check if response is OK
        if (!response.ok) {
            console.error('Login HTTP error:', response.status, response.statusText);
        }

        const data = await response.json();

        if (data.success) {
            // Save tokens
            saveTokens(data.access_token, data.refresh_token);

            // Save user data
            AuthState.user = data.user;
            AuthState.isAuthenticated = true;
            try {
                localStorage.setItem('user_data', JSON.stringify(data.user));
            } catch (e) {
                console.error('Failed to save user data:', e);
            }

            // Update UI
            updateUIForAuthState();

            // Show display name screen
            showScreen('display-name-screen');

            return true;
        } else {
            if (errorEl) {
                errorEl.textContent = data.message || 'Login failed';
                errorEl.style.color = '#ff6b6b';
                errorEl.style.display = 'block';
            }
            return false;
        }
    } catch (error) {
        console.error('Login error (attempt ' + (retryCount + 1) + '):', error);

        // Retry logic (max 2 retries)
        if (retryCount < 2 && (error.name === 'AbortError' || error.name === 'TypeError')) {
            console.log('Retrying login in ' + ((retryCount + 1) * 1000) + 'ms...');
            if (errorEl) {
                errorEl.textContent = 'Connection issue, retrying... (' + (retryCount + 1) + '/2)';
                errorEl.style.color = '#f39c12';
            }
            await new Promise(resolve => setTimeout(resolve, (retryCount + 1) * 1000));
            return login(usernameOrEmail, password, rememberMe, retryCount + 1);
        }

        // Failed after retries
        if (errorEl) {
            errorEl.textContent = 'Network error. Please check your connection and try again.';
            errorEl.style.color = '#ff6b6b';
            errorEl.style.display = 'block';
        }
        return false;
    }
}

/**
 * Logout current user
 */
async function logout() {
    try {
        // Call logout endpoint to invalidate session
        if (AuthState.accessToken) {
            await fetch(`${AUTH_API}/logout`, {
                method: 'POST',
                headers: getAuthHeader()
            });
        }
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Clear local auth state
        clearAuth();

        // Update UI
        updateUIForAuthState();

        // Show login screen
        showScreen('login-screen');
    }
}

/**
 * Continue as guest (no account required)
 */
function continueAsGuest() {
    AuthState.isGuest = true;
    AuthState.isAuthenticated = false;

    // BUG #160 FIX: Use crypto API for better randomness + timestamp to avoid duplicates
    const guestId = Date.now() % 10000 + Math.floor(Math.random() * 1000);
    AuthState.user = {
        username: `Guest${guestId}`
    };

    // Update UI
    updateUIForAuthState();

    // Show display name screen
    showScreen('display-name-screen');
}

// Email verification removed - users are active immediately upon registration

// ============================================================================
// PASSWORD RESET
// ============================================================================

/**
 * Request password reset email
 */
async function requestPasswordReset(email) {
    const errorEl = document.getElementById('forgot-error');
    const successEl = document.getElementById('forgot-success');

    // Clear previous messages
    if (errorEl) errorEl.textContent = '';
    if (successEl) successEl.textContent = '';

    // BUG #161, #165 FIX: Better email validation (don't duplicate)
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email)) {
        if (errorEl) errorEl.textContent = 'Please enter a valid email address';
        return false;
    }

    try {
        const response = await fetch(`${AUTH_API}/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        // BUG #162 FIX: Check response status
        if (!response.ok) {
            if (errorEl) {
                errorEl.textContent = 'Failed to send reset link. Please try again.';
                errorEl.style.display = 'block';
            }
            return false;
        }

        const data = await response.json();

        if (data.success) {
            if (successEl) {
                successEl.textContent = 'If that email exists, a reset link has been sent.';
                successEl.style.display = 'block';
            }
            return true;
        } else {
            if (errorEl) {
                errorEl.textContent = data.message || 'Failed to send reset email';
                errorEl.style.display = 'block';
            }
            return false;
        }
    } catch (error) {
        console.error('Password reset request error:', error);
        if (errorEl) {
            errorEl.textContent = 'Network error. Please try again.';
            errorEl.style.display = 'block';
        }
        return false;
    }
}

/**
 * Reset password with token
 */
async function resetPassword(token, newPassword) {
    const errorEl = document.getElementById('reset-error');
    const successEl = document.getElementById('reset-success');

    // Clear previous messages
    if (errorEl) errorEl.textContent = '';
    if (successEl) successEl.textContent = '';

    if (!newPassword || newPassword.length < 8) {
        if (errorEl) errorEl.textContent = 'Password must be at least 8 characters';
        return false;
    }

    try {
        const response = await fetch(`${AUTH_API}/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, new_password: newPassword })
        });

        const data = await response.json();

        if (data.success) {
            if (successEl) {
                successEl.textContent = 'Password reset successful! Redirecting to login...';
                successEl.style.display = 'block';
            }

            // Redirect to login after 2 seconds
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);

            return true;
        } else {
            if (errorEl) {
                errorEl.textContent = data.message || 'Password reset failed';
                errorEl.style.display = 'block';
            }
            return false;
        }
    } catch (error) {
        console.error('Password reset error:', error);
        if (errorEl) {
            errorEl.textContent = 'Network error. Please try again.';
            errorEl.style.display = 'block';
        }
        return false;
    }
}

/**
 * Show reset password form (when coming from email link)
 */
function showResetPasswordForm(token) {
    // BUG #166 FIX: Use sessionStorage instead of global variable
    try {
        sessionStorage.setItem('resetToken', token);
    } catch (e) {
        console.error('Failed to store reset token:', e);
    }

    // Show reset password screen
    showScreen('reset-password-screen');
}

// ============================================================================
// UI UPDATES
// ============================================================================

/**
 * Update UI based on authentication state
 */
function updateUIForAuthState() {
    // BUG #167-169, #171 FIX: Validate all elements exist before accessing
    const usernameDisplays = document.querySelectorAll('.username-display');
    const loginButtons = document.querySelectorAll('.login-required');
    const logoutButtons = document.querySelectorAll('.logout-button');
    const guestNotices = document.querySelectorAll('.guest-notice');

    if (AuthState.isAuthenticated && AuthState.user) {
        // Show username
        if (usernameDisplays && usernameDisplays.length > 0) {
            usernameDisplays.forEach(el => {
                if (el) {
                    el.textContent = AuthState.user.username || 'User';
                    el.style.display = 'inline';
                }
            });
        }

        // Show logout buttons
        if (logoutButtons && logoutButtons.length > 0) {
            logoutButtons.forEach(el => { if (el) el.style.display = 'inline-block'; });
        }

        // Hide login buttons
        if (loginButtons && loginButtons.length > 0) {
            loginButtons.forEach(el => { if (el) el.style.display = 'none'; });
        }

        // Hide guest notices
        if (guestNotices && guestNotices.length > 0) {
            guestNotices.forEach(el => { if (el) el.style.display = 'none'; });
        }

    } else if (AuthState.isGuest) {
        // Show guest username
        if (usernameDisplays && usernameDisplays.length > 0) {
            usernameDisplays.forEach(el => {
                if (el && AuthState.user) {
                    el.textContent = AuthState.user.username || 'Guest';
                    el.style.display = 'inline';
                }
            });
        }

        // Show guest notice
        if (guestNotices && guestNotices.length > 0) {
            guestNotices.forEach(el => {
                if (el) {
                    el.textContent = 'Playing as guest. Create an account to save your progress!';
                    el.style.display = 'block';
                }
            });
        }

        // Show login buttons
        if (loginButtons && loginButtons.length > 0) {
            loginButtons.forEach(el => { if (el) el.style.display = 'inline-block'; });
        }

        // Hide logout buttons
        if (logoutButtons && logoutButtons.length > 0) {
            logoutButtons.forEach(el => { if (el) el.style.display = 'none'; });
        }

    } else {
        // Not authenticated - show login buttons
        if (loginButtons && loginButtons.length > 0) {
            loginButtons.forEach(el => { if (el) el.style.display = 'inline-block'; });
        }
        if (logoutButtons && logoutButtons.length > 0) {
            logoutButtons.forEach(el => { if (el) el.style.display = 'none'; });
        }
        if (usernameDisplays && usernameDisplays.length > 0) {
            usernameDisplays.forEach(el => { if (el) el.style.display = 'none'; });
        }
        if (guestNotices && guestNotices.length > 0) {
            guestNotices.forEach(el => { if (el) el.style.display = 'none'; });
        }
    }
}

/**
 * Get current username for game
 */
function getCurrentUsername() {
    if (AuthState.user) {
        return AuthState.user.username;
    }
    return 'Guest';
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return AuthState.isAuthenticated && !AuthState.isGuest;
}

// Removed isVerified() - no longer needed

/**
 * Get current user data
 */
function getCurrentUser() {
    return AuthState.user;
}

// ============================================================================
// FORM HANDLERS
// ============================================================================

/**
 * Handle login form submission
 */
function handleLoginSubmit(e) {
    e.preventDefault();

    // BUG #167-168 FIX: Validate elements exist
    const usernameEl = document.getElementById('login-username');
    const passwordEl = document.getElementById('login-password');
    const rememberMeEl = document.getElementById('login-remember');

    if (!usernameEl || !passwordEl) {
        console.error('Login form elements not found');
        return;
    }

    const username = usernameEl.value.trim();
    const password = passwordEl.value;
    const rememberMe = rememberMeEl ? rememberMeEl.checked : false;

    login(username, password, rememberMe);
}

/**
 * Handle registration form submission
 */
function handleRegisterSubmit(e) {
    e.preventDefault();

    const username = document.getElementById('register-username').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const passwordConfirm = document.getElementById('register-password-confirm').value;

    // Check if passwords match
    const errorEl = document.getElementById('register-error');
    if (password !== passwordConfirm) {
        if (errorEl) {
            errorEl.textContent = 'Passwords do not match';
            errorEl.style.display = 'block';
        }
        return;
    }

    register(username, email, password);
}

/**
 * Handle forgot password form submission
 */
function handleForgotPasswordSubmit(e) {
    e.preventDefault();

    const email = document.getElementById('forgot-email').value.trim();
    requestPasswordReset(email);
}

/**
 * Handle reset password form submission
 */
function handleResetPasswordSubmit(e) {
    e.preventDefault();

    const password = document.getElementById('reset-password').value;
    const confirmPassword = document.getElementById('reset-password-confirm').value;

    if (password !== confirmPassword) {
        const errorEl = document.getElementById('reset-error');
        if (errorEl) {
            errorEl.textContent = 'Passwords do not match';
            errorEl.style.display = 'block';
        }
        return;
    }

    // BUG #166 FIX: Get token from sessionStorage instead of global variable
    let token = null;
    try {
        token = sessionStorage.getItem('resetToken');
    } catch (e) {
        console.error('Failed to get reset token:', e);
    }

    if (!token) {
        const errorEl = document.getElementById('reset-error');
        if (errorEl) {
            errorEl.textContent = 'Reset token missing. Please request a new reset link.';
            errorEl.style.display = 'block';
        }
        return;
    }

    resetPassword(token, password);
}

/**
 * Handle display name form submission
 */
function handleDisplayNameSubmit(e) {
    e.preventDefault();

    // BUG #169 FIX: Validate element exists
    const displayNameEl = document.getElementById('display-name-input');
    if (!displayNameEl) {
        console.error('Display name input not found');
        return;
    }

    const displayName = displayNameEl.value.trim();
    const errorEl = document.getElementById('display-name-error');

    // Clear previous errors
    if (errorEl) errorEl.textContent = '';

    // Validation
    if (!displayName || displayName.length < 3) {
        if (errorEl) {
            errorEl.textContent = 'Display name must be at least 3 characters';
            errorEl.style.display = 'block';
        }
        return;
    }

    if (displayName.length > 20) {
        if (errorEl) {
            errorEl.textContent = 'Display name must be at most 20 characters';
            errorEl.style.display = 'block';
        }
        return;
    }

    // Store display name
    AuthState.displayName = displayName;
    // BUG #170 FIX: Handle localStorage errors
    try {
        localStorage.setItem('display_name', displayName);
    } catch (e) {
        console.error('Failed to save display name:', e);
    }

    // Navigate to main screen
    showScreen('main-screen');
}

// ============================================================================
// UI HELPERS (for cross-file compatibility)
// ============================================================================

/**
 * Show a specific screen (compatible with game.js)
 */
function showScreen(screenId) {
    // BUG #172 FIX: Validate screenId and handle missing screens
    if (!screenId || typeof screenId !== 'string') {
        console.error('Invalid screen ID:', screenId);
        return;
    }

    const screens = document.querySelectorAll('.screen');
    if (screens && screens.length > 0) {
        screens.forEach(s => { if (s) s.classList.remove('active'); });
    }

    const screen = document.getElementById(screenId);
    if (screen) {
        screen.classList.add('active');
    } else {
        console.error('Screen not found:', screenId);
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Initialize auth on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuth);
} else {
    initAuth();
}
