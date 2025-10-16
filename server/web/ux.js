/**
 * UX Improvements Module
 * Implements fixes #431-480 from UX_IMPROVEMENTS.md
 */

// ============================================================================
// BUG #431-440 FIX: Error Messages
// ============================================================================

const ErrorMessages = {
    // Network errors
    CONNECTION_LOST: {
        title: "Connection Lost",
        message: "Unable to connect to game server. Retrying...",
        action: "refresh",
        recoverable: true
    },
    CONNECTION_TIMEOUT: {
        title: "Connection Timeout",
        message: "The server took too long to respond. Please check your internet connection.",
        action: "retry",
        recoverable: true
    },

    // Authentication errors
    LOGIN_INVALID_CREDENTIALS: {
        title: "Login Failed",
        message: "Incorrect username or password. Please try again.",
        suggestions: ["Check your username for typos", "Verify your password", "Try password reset if needed"],
        recoverable: true
    },
    ACCOUNT_LOCKED: {
        title: "Account Temporarily Locked",
        message: "Too many failed login attempts. Your account will be unlocked in {time} minutes.",
        severity: "warning",
        recoverable: false
    },

    // Game errors
    ROOM_NOT_FOUND: {
        title: "Room Not Found",
        message: "The room code you entered doesn't exist or has expired.",
        suggestions: ["Double-check the room code", "Ask the host for a new code"],
        recoverable: true
    },
    ROOM_FULL: {
        title: "Room Is Full",
        message: "This game room has reached its maximum number of players.",
        suggestions: ["Try creating your own room", "Ask to join a different room"],
        recoverable: true
    }
};

function showError(errorType, context = {}) {
    const error = ErrorMessages[errorType];
    if (!error) {
        showGenericError("An error occurred. Please try again.");
        return;
    }

    // Format message with context
    let message = error.message;
    Object.keys(context).forEach(key => {
        message = message.replace(`{${key}}`, context[key]);
    });

    const errorHTML = `
        <div class="error-dialog" data-severity="${error.severity || 'error'}">
            <div class="error-icon">
                ${error.recoverable ? '⚠️' : '❌'}
            </div>
            <div class="error-content">
                <h3>${error.title}</h3>
                <p>${message}</p>
                ${error.suggestions ? `
                    <ul class="suggestions">
                        ${error.suggestions.map(s => `<li>${s}</li>`).join('')}
                    </ul>
                ` : ''}
            </div>
            <div class="error-actions">
                ${error.action === 'retry' ? '<button onclick="UX.retryLastAction()">Retry</button>' : ''}
                ${error.action === 'refresh' ? '<button onclick="location.reload()">Refresh Page</button>' : ''}
                <button onclick="UX.closeError()">Dismiss</button>
            </div>
        </div>
    `;

    const container = document.getElementById('errorContainer') || createErrorContainer();
    container.innerHTML = errorHTML;
    container.style.display = 'block';
}

function showGenericError(message = "An error occurred. Please try again.") {
    const errorHTML = `
        <div class="error-dialog">
            <div class="error-icon">❌</div>
            <div class="error-content">
                <h3>Error</h3>
                <p>${message}</p>
            </div>
            <div class="error-actions">
                <button onclick="UX.closeError()">Dismiss</button>
            </div>
        </div>
    `;

    const container = document.getElementById('errorContainer') || createErrorContainer();
    container.innerHTML = errorHTML;
    container.style.display = 'block';
}

function closeError() {
    const container = document.getElementById('errorContainer');
    if (container) {
        container.style.display = 'none';
        container.innerHTML = '';
    }
}

function createErrorContainer() {
    const container = document.createElement('div');
    container.id = 'errorContainer';
    container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 10000; max-width: 400px;';
    document.body.appendChild(container);
    return container;
}

// ============================================================================
// BUG #441-450 FIX: Loading States
// ============================================================================

const LoadingManager = {
    activeLoading: new Set(),
    container: null,

    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'loadingContainer';
            this.container.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 9999;
            `;
            document.body.appendChild(this.container);
        }
    },

    show(id, message = "Loading...") {
        this.init();
        this.activeLoading.add(id);
        this.render(message);
    },

    hide(id) {
        this.activeLoading.delete(id);
        this.render();
    },

    render(message = "Loading...") {
        if (!this.container) return;

        if (this.activeLoading.size === 0) {
            this.container.style.display = 'none';
            this.container.innerHTML = '';
        } else {
            this.container.style.display = 'flex';
            this.container.innerHTML = `
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    <p>${message}</p>
                </div>
            `;
        }
    }
};

function showLeaderboardSkeleton() {
    const skeleton = `
        <div class="leaderboard-skeleton">
            ${Array(10).fill(0).map(() => `
                <div class="skeleton-item">
                    <div class="skeleton-avatar"></div>
                    <div class="skeleton-text"></div>
                    <div class="skeleton-score"></div>
                </div>
            `).join('')}
        </div>
    `;
    const leaderboard = document.getElementById('leaderboard');
    if (leaderboard) {
        leaderboard.innerHTML = skeleton;
    }
}

function setButtonLoading(button, loading) {
    if (!button) return;

    if (loading) {
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        button.innerHTML = '<span class="spinner"></span> Loading...';
    } else {
        button.disabled = false;
        button.textContent = button.dataset.originalText || 'Submit';
    }
}

function showProgress(percent, message = '') {
    let progressBar = document.getElementById('progressBar');
    if (!progressBar) {
        progressBar = document.createElement('div');
        progressBar.id = 'progressBar';
        progressBar.innerHTML = `
            <div class="progress-container">
                <div class="progress-fill"></div>
                <div class="progress-message"></div>
            </div>
        `;
        document.body.appendChild(progressBar);
    }

    progressBar.style.display = 'block';
    const fill = progressBar.querySelector('.progress-fill');
    const msg = progressBar.querySelector('.progress-message');

    if (fill) fill.style.width = `${percent}%`;
    if (msg) msg.textContent = message;
}

// ============================================================================
// BUG #451-460 FIX: Mobile UX Optimizations
// ============================================================================

// Haptic feedback support
function triggerHaptic(type = 'light') {
    if ('vibrate' in navigator) {
        switch (type) {
            case 'light':
                navigator.vibrate(10);
                break;
            case 'medium':
                navigator.vibrate(20);
                break;
            case 'heavy':
                navigator.vibrate(50);
                break;
        }
    }
}

// Mobile keyboard handling
window.addEventListener('resize', () => {
    const isKeyboardVisible = window.innerHeight < screen.height * 0.75;
    document.body.classList.toggle('keyboard-visible', isKeyboardVisible);
});

// ============================================================================
// BUG #461-470 FIX: Accessibility
// ============================================================================

// Screen reader announcements
function announceToScreenReader(message) {
    const announcement = document.getElementById('gameStatus') || createScreenReaderAnnouncer();
    announcement.textContent = message;

    // Trigger haptic for confirmation
    triggerHaptic('light');
}

function createScreenReaderAnnouncer() {
    const announcer = document.createElement('div');
    announcer.id = 'gameStatus';
    announcer.setAttribute('role', 'status');
    announcer.setAttribute('aria-live', 'polite');
    announcer.setAttribute('aria-atomic', 'true');
    announcer.className = 'sr-only';
    announcer.style.cssText = `
        position: absolute;
        left: -10000px;
        width: 1px;
        height: 1px;
        overflow: hidden;
    `;
    document.body.appendChild(announcer);
    return announcer;
}

// Keyboard navigation
function initKeyboardNav() {
    if (!window.state) return;

    let focusRow = 0, focusCol = 0;

    document.addEventListener('keydown', (e) => {
        if (!window.state.gameStarted) return;

        const rows = window.state.difficulty.rows;
        const cols = window.state.difficulty.cols;

        switch (e.key) {
            case 'ArrowUp':
                focusRow = Math.max(0, focusRow - 1);
                e.preventDefault();
                break;
            case 'ArrowDown':
                focusRow = Math.min(rows - 1, focusRow + 1);
                e.preventDefault();
                break;
            case 'ArrowLeft':
                focusCol = Math.max(0, focusCol - 1);
                e.preventDefault();
                break;
            case 'ArrowRight':
                focusCol = Math.min(cols - 1, focusCol + 1);
                e.preventDefault();
                break;
            case 'Space':
            case 'Enter':
                if (window.revealCell) {
                    window.revealCell(focusRow, focusCol);
                    announceToScreenReader(`Revealed cell at row ${focusRow + 1}, column ${focusCol + 1}`);
                }
                e.preventDefault();
                break;
            case 'f':
            case 'F':
                if (window.toggleFlag) {
                    window.toggleFlag(focusRow, focusCol);
                    announceToScreenReader(`Flagged cell at row ${focusRow + 1}, column ${focusCol + 1}`);
                }
                e.preventDefault();
                break;
        }

        if (window.drawFocusIndicator) {
            window.drawFocusIndicator(focusRow, focusCol);
        }
    });
}

// High contrast mode support
if (window.matchMedia('(prefers-contrast: high)').matches) {
    document.body.classList.add('high-contrast');
}

// Reduced motion support
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.body.classList.add('reduced-motion');
}

// ============================================================================
// BUG #471-480 FIX: Internationalization
// ============================================================================

const translations = {
    en: {
        game: {
            title: "Minesweeper Multiplayer",
            newGame: "New Game",
            difficulty: "Difficulty",
            easy: "Easy",
            medium: "Medium",
            hard: "Hard",
            timer: "Time:",
            score: "Score:",
            mines: "Mines:",
            win: "You Win!",
            lose: "Game Over"
        }
    },
    es: {
        game: {
            title: "Buscaminas Multijugador",
            newGame: "Nuevo Juego",
            difficulty: "Dificultad",
            easy: "Fácil",
            medium: "Medio",
            hard: "Difícil",
            timer: "Tiempo:",
            score: "Puntuación:",
            mines: "Minas:",
            win: "¡Ganaste!",
            lose: "Juego Terminado"
        }
    }
};

let currentLanguage = 'en';

function t(key, lang = currentLanguage) {
    const keys = key.split('.');
    let value = translations[lang];

    for (const k of keys) {
        value = value?.[k];
    }

    return value || key;  // Fallback to key if not found
}

function detectLocale() {
    const browserLang = navigator.language.split('-')[0];
    return translations[browserLang] ? browserLang : 'en';
}

function setLanguage(lang) {
    if (translations[lang]) {
        currentLanguage = lang;
        localStorage.setItem('language', lang);
        updateUILanguage();
    }
}

function updateUILanguage() {
    // Update all translatable elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        el.textContent = t(key);
    });
}

function formatDate(date, locale = currentLanguage) {
    return new Intl.DateTimeFormat(locale, {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

function formatNumber(num, locale = currentLanguage) {
    return new Intl.NumberFormat(locale).format(num);
}

function setTextDirection(lang) {
    const rtlLanguages = ['ar', 'he', 'fa'];
    const isRTL = rtlLanguages.includes(lang);

    document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
    document.documentElement.lang = lang;
}

function pluralize(count, singular, plural, lang = 'en') {
    const rules = new Intl.PluralRules(lang);
    const rule = rules.select(count);

    const forms = {
        one: singular,
        other: plural
    };

    return forms[rule] || forms.other;
}

// ============================================================================
// Retry mechanism
// ============================================================================

let lastAction = null;

function setLastAction(action) {
    lastAction = action;
}

function retryLastAction() {
    if (lastAction) {
        lastAction();
    }
    closeError();
}

// ============================================================================
// Public API
// ============================================================================

window.UX = {
    // Error handling
    showError,
    showGenericError,
    closeError,
    ErrorMessages,

    // Loading states
    LoadingManager,
    showLeaderboardSkeleton,
    setButtonLoading,
    showProgress,

    // Mobile
    triggerHaptic,

    // Accessibility
    announceToScreenReader,
    initKeyboardNav,

    // i18n
    t,
    detectLocale,
    setLanguage,
    formatDate,
    formatNumber,
    setTextDirection,
    pluralize,

    // Retry
    setLastAction,
    retryLastAction
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Detect and set language
    const savedLang = localStorage.getItem('language') || detectLocale();
    setLanguage(savedLang);
    setTextDirection(savedLang);

    // Initialize keyboard navigation
    initKeyboardNav();

    // Create screen reader announcer
    createScreenReaderAnnouncer();
});
