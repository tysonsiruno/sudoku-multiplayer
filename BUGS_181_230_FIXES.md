# Comprehensive Fixes for Bugs #181-230

## Implementation Plan

### Phase 1: Utility Functions (Add to top of game.js)
```javascript
// Throttle function for performance optimization
function throttle(func, delay) {
    let lastCall = 0;
    return function(...args) {
        const now = Date.now();
        if (now - lastCall >= delay) {
            lastCall = now;
            return func.apply(this, args);
        }
    };
}

// Debounce function for resize handlers
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

// Rate limiter for socket emits
const socketRateLimiter = {
    lastEmit: {},
    canEmit(event, minDelay = 100) {
        const now = Date.now();
        const last = this.lastEmit[event] || 0;
        if (now - last >= minDelay) {
            this.lastEmit[event] = now;
            return true;
        }
        return false;
    }
};

// Safe timer management
const timerManager = {
    timers: new Set(),
    intervals: new Set(),

    setTimeout(callback, delay) {
        const id = setTimeout(() => {
            this.timers.delete(id);
            callback();
        }, delay);
        this.timers.add(id);
        return id;
    },

    setInterval(callback, delay) {
        const id = setInterval(callback, delay);
        this.intervals.add(id);
        return id;
    },

    clearTimeout(id) {
        if (id) {
            clearTimeout(id);
            this.timers.delete(id);
        }
    },

    clearInterval(id) {
        if (id) {
            clearInterval(id);
            this.intervals.delete(id);
        }
    },

    clearAll() {
        this.timers.forEach(id => clearTimeout(id));
        this.intervals.forEach(id => clearInterval(id));
        this.timers.clear();
        this.intervals.clear();
    }
};
```

### Phase 2: Specific Bug Fixes

#### Bug #181: Touch handled timeout configurable
```javascript
const TOUCH_HANDLED_DELAY = 300; // Reduced from 500ms

const preventClickAfterTouch = () => {
    touchHandled = true;
    timerManager.setTimeout(() => { touchHandled = false; }, TOUCH_HANDLED_DELAY);
};
```

#### Bug #182-183: Mouse/Touch position with proper offset calculation
```javascript
function getCanvasMousePosition(e, canvas) {
    const rect = canvas.getBoundingClientRect();
    const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
    const scrollY = window.pageYOffset || document.documentElement.scrollTop;

    return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
    };
}

function getCanvasTouchPosition(touch, canvas) {
    const rect = canvas.getBoundingClientRect();
    const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
    const scrollY = window.pageYOffset || document.documentElement.scrollTop;

    return {
        x: touch.clientX - rect.left,
        y: touch.clientY - rect.top
    };
}
```

#### Bug #185, #189: Clear previous timers before setting new ones
```javascript
// Replace all setInterval calls with:
if (state.timerInterval) {
    timerManager.clearInterval(state.timerInterval);
}
state.timerInterval = timerManager.setInterval(() => {
    // timer logic
}, 100);
```

#### Bug #186: Unique seed generation
```javascript
function generateUniqueSeed() {
    return Date.now() + Math.floor(Math.random() * 1000000);
}
```

#### Bug #190: Remove confusing delay
```javascript
// Replace setTimeout 500ms with immediate show:
showGameResult(won);
// Remove the 500ms timeout entirely
```

#### Bug #195-196: Validate and clear existing timeouts
```javascript
// Before setting new timeout:
if (state.survivalLevelTimeout) {
    timerManager.clearTimeout(state.survivalLevelTimeout);
    state.survivalLevelTimeout = null;
}

if (state.hintTimeout) {
    timerManager.clearTimeout(state.hintTimeout);
    state.hintTimeout = null;
}
```

#### Bug #197-199: Proper time calculations
```javascript
function calculateElapsedTime() {
    if (!state.startTime) return 0;
    const elapsed = Math.max(0, Date.now() - state.startTime); // Prevent negative
    return Math.floor(elapsed / 1000); // Seconds (not truncating milliseconds incorrectly)
}

function formatTime(seconds) {
    seconds = Math.max(0, seconds); // Prevent negative display
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
}
```

#### Bug #200: Rate-limited socket emits
```javascript
// Wrap all change_game_mode emits:
if (socketRateLimiter.canEmit('change_game_mode', 1000)) {
    state.socket.emit('change_game_mode', { game_mode: 'timebomb' });
}
```

#### Bug #191-194: Validate socket before emitting
```javascript
function safeSocketEmit(event, data) {
    if (!state.socket || !state.socket.connected) {
        console.warn(`Socket not connected, cannot emit ${event}`);
        return false;
    }

    // Validate data types
    if (event === 'game_action' && data.row !== undefined) {
        data.row = parseInt(data.row);
        data.col = parseInt(data.col);
    }

    if (event === 'game_finished' && data.score !== undefined) {
        data.score = Math.max(0, parseInt(data.score));
        data.time = Math.max(0, parseInt(data.time));
    }

    state.socket.emit(event, data);
    return true;
}
```

#### Bug #202: Throttled resize handler
```javascript
window.addEventListener('resize', debounce(() => {
    if (state.currentScreen === 'game-screen') {
        initCanvas();
        drawBoard();
    }
}, 250));
```

#### Bug #203-217, #225: Event listener cleanup
```javascript
// Add cleanup function
function cleanupEventListeners() {
    // Remove canvas listeners if they exist
    const canvas = document.getElementById('game-canvas');
    if (canvas) {
        const newCanvas = canvas.cloneNode(true);
        canvas.parentNode.replaceChild(newCanvas, canvas);
    }

    // Clear all timers
    timerManager.clearAll();
}

// Call before reinitializing:
function resetGame() {
    cleanupEventListeners();
    // ... rest of reset logic
}
```

#### Bug #219, #230: Throttled mousemove
```javascript
canvas.addEventListener('mousemove', throttle((e) => {
    const pos = getCanvasMousePosition(e, canvas);
    const col = Math.floor(pos.x / state.cellSize);
    const row = Math.floor(pos.y / state.cellSize);

    if (row >= 0 && row < state.difficulty.rows &&
        col >= 0 && col < state.difficulty.cols) {
        if (state.hoverCell?.row !== row || state.hoverCell?.col !== col) {
            state.hoverCell = { row, col };
            drawBoard();
        }
    }
}, 50));
```

#### Bug #226: Passive event listeners
```javascript
// Add passive: true to scroll/touch listeners that don't prevent default:
canvas.addEventListener('touchstart', handler, { passive: true });
canvas.addEventListener('touchmove', handler, { passive: true });
```

#### Bug #227-228: Better touch/mouse conflict resolution
```javascript
let lastInputType = null;
const INPUT_COOLDOWN = 300;
let lastInputTime = 0;

function canProcessInput(type) {
    const now = Date.now();
    if (now - lastInputTime < INPUT_COOLDOWN && lastInputType !== type) {
        return false; // Ignore mixed input during cooldown
    }
    lastInputType = type;
    lastInputTime = now;
    return true;
}
```

## Summary of Fixes

### Performance Improvements
- ✅ Throttled resize handler (250ms debounce)
- ✅ Throttled mousemove handler (50ms throttle)
- ✅ Reduced touch cooldown (500ms → 300ms)
- ✅ Passive event listeners for scrolling
- ✅ Rate limiting on socket emits

### Memory Leak Fixes
- ✅ Timer manager for centralized cleanup
- ✅ Event listener cleanup on reset
- ✅ Canvas listener removal via cloning

### Validation Improvements
- ✅ Socket connection validation before emit
- ✅ Data type validation for socket events
- ✅ Canvas offset/scroll calculation
- ✅ Negative time prevention
- ✅ Unique seed generation

### UX Improvements
- ✅ Hour display in time format
- ✅ Removed confusing 500ms delay
- ✅ Better touch/mouse conflict handling
- ✅ Proper timer clearing before setting new

## Testing Checklist
- [ ] Test on mobile (touch events)
- [ ] Test on desktop (mouse events)
- [ ] Test on hybrid devices (both)
- [ ] Verify no memory leaks (devtools profiler)
- [ ] Check socket reconnection
- [ ] Validate multiplayer sync
- [ ] Test rapid mode changes
- [ ] Verify timer accuracy
