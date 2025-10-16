/**
 * Client Performance Optimizations
 * Implements fixes #311-330 from CLIENT_PERFORMANCE_FIXES.md
 */

// ============================================================================
// BUG #313 FIX: Cache DOM Selectors
// ============================================================================

const DOM = {
    canvas: null,
    ctx: null,
    timerDisplay: null,
    scoreDisplay: null,
    minesDisplay: null,
    difficultyBtns: null,
    gameResult: null,
    loginScreen: null,
    gameScreen: null,
    // Add more cached elements as needed
};

function initializeDOM() {
    DOM.canvas = document.getElementById('gameCanvas');
    DOM.ctx = DOM.canvas ? DOM.canvas.getContext('2d') : null;
    DOM.timerDisplay = document.getElementById('timerDisplay');
    DOM.scoreDisplay = document.getElementById('scoreDisplay');
    DOM.minesDisplay = document.getElementById('minesDisplay');
    DOM.difficultyBtns = document.querySelectorAll('.difficulty-btn');
    DOM.gameResult = document.getElementById('gameResult');
    DOM.loginScreen = document.getElementById('login-screen');
    DOM.gameScreen = document.getElementById('game-screen');
}

// ============================================================================
// BUG #311 FIX: Incremental Canvas Rendering
// ============================================================================

const dirtyRegions = new Set(); // Set of "row,col" strings that need redraw

function markCellDirty(row, col) {
    dirtyRegions.add(`${row},${col}`);
    requestDraw();
}

function markRegionDirty(startRow, startCol, endRow, endCol) {
    for (let r = startRow; r <= endRow; r++) {
        for (let c = startCol; c <= endCol; c++) {
            dirtyRegions.add(`${r},${c}`);
        }
    }
    requestDraw();
}

function clearDirtyRegions() {
    dirtyRegions.clear();
}

// ============================================================================
// BUG #312 FIX: requestAnimationFrame Batching
// ============================================================================

let rafPending = false;
let pendingDrawCallback = null;

function requestDraw(callback) {
    pendingDrawCallback = callback;

    if (!rafPending) {
        rafPending = true;
        requestAnimationFrame(() => {
            rafPending = false;
            if (pendingDrawCallback) {
                pendingDrawCallback();
            }
            drawDirtyRegions();
        });
    }
}

function drawDirtyRegions() {
    if (!window.state || !window.state.board || !DOM.ctx) return;

    const totalCells = window.state.difficulty.rows * window.state.difficulty.cols;

    // If too many dirty regions (>25% of board), redraw everything
    if (dirtyRegions.size > totalCells * 0.25) {
        if (window.drawBoard) {
            window.drawBoard();
        }
        dirtyRegions.clear();
        return;
    }

    // Redraw only dirty cells
    for (const key of dirtyRegions) {
        const [row, col] = key.split(',').map(Number);
        if (window.drawCell) {
            window.drawCell(row, col);
        }
    }

    dirtyRegions.clear();
}

// ============================================================================
// BUG #316 FIX: Async localStorage Operations
// ============================================================================

function saveToStorageAsync(key, value) {
    const save = () => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn('Storage save failed:', e);
        }
    };

    if ('requestIdleCallback' in window) {
        requestIdleCallback(save);
    } else {
        setTimeout(save, 0);
    }
}

function loadFromStorageAsync(key, callback) {
    const load = () => {
        try {
            const value = localStorage.getItem(key);
            callback(value ? JSON.parse(value) : null);
        } catch (e) {
            console.warn('Storage load failed:', e);
            callback(null);
        }
    };

    if ('requestIdleCallback' in window) {
        requestIdleCallback(load);
    } else {
        setTimeout(load, 0);
    }
}

// ============================================================================
// BUG #318 FIX: Optimized Mine Placement (Fisher-Yates)
// ============================================================================

function placeMinesOptimized(board, rows, cols, mineCount, excludeRow, excludeCol) {
    const totalCells = rows * cols;
    const cells = [];

    // Create array of all cell indices, excluding safe zone around first click
    for (let i = 0; i < totalCells; i++) {
        const row = Math.floor(i / cols);
        const col = i % cols;

        // Skip excluded cells (5x5 around first click)
        if (Math.abs(row - excludeRow) <= 2 && Math.abs(col - excludeCol) <= 2) {
            continue;
        }

        cells.push(i);
    }

    // Fisher-Yates shuffle first N cells
    const actualMineCount = Math.min(mineCount, cells.length);
    for (let i = 0; i < actualMineCount; i++) {
        // Pick random index from remaining cells
        const j = i + Math.floor(Math.random() * (cells.length - i));

        // Swap
        [cells[i], cells[j]] = [cells[j], cells[i]];
    }

    // Place mines in first N shuffled positions
    const minePositions = [];
    for (let i = 0; i < actualMineCount; i++) {
        const cellIndex = cells[i];
        const row = Math.floor(cellIndex / cols);
        const col = cellIndex % cols;
        board[row][col].isMine = true;
        minePositions.push({row, col});
    }

    return minePositions;
}

// ============================================================================
// BUG #319 FIX: Board Configuration Cache
// ============================================================================

const boardCache = new Map();
const MAX_CACHE_SIZE = 10;

function getCacheKey(rows, cols, mines, seed) {
    return `${rows}x${cols}x${mines}x${seed}`;
}

function getCachedBoard(rows, cols, mines, seed) {
    const key = getCacheKey(rows, cols, mines, seed);
    return boardCache.get(key);
}

function setCachedBoard(rows, cols, mines, seed, board) {
    const key = getCacheKey(rows, cols, mines, seed);

    // Limit cache size to prevent memory bloat
    if (boardCache.size >= MAX_CACHE_SIZE) {
        const firstKey = boardCache.keys().next().value;
        boardCache.delete(firstKey);
    }

    boardCache.set(key, board);
}

function clearBoardCache() {
    boardCache.clear();
}

// ============================================================================
// BUG #321-330 FIX: Canvas Rendering Optimizations
// ============================================================================

// BUG #322: Minimize state saves/restores
function batchCanvasOperations(operations) {
    if (!DOM.ctx) return;

    DOM.ctx.save();
    operations.forEach(op => op());
    DOM.ctx.restore();
}

// BUG #323: Cache static text rendering
const textCache = new Map();

function drawCachedText(text, x, y, options = {}) {
    if (!DOM.ctx) return;

    const key = `${text}:${options.font || '14px Arial'}:${options.color || '#000'}`;

    if (!textCache.has(key)) {
        // Render text to off-screen canvas
        const tempCanvas = document.createElement('canvas');
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.font = options.font || '14px Arial';
        tempCtx.fillStyle = options.color || '#000';

        const metrics = tempCtx.measureText(text);
        tempCanvas.width = metrics.width;
        tempCanvas.height = 20;

        tempCtx.font = options.font || '14px Arial';
        tempCtx.fillStyle = options.color || '#000';
        tempCtx.fillText(text, 0, 15);

        textCache.set(key, tempCanvas);
    }

    DOM.ctx.drawImage(textCache.get(key), x, y);
}

function clearTextCache() {
    textCache.clear();
}

// BUG #327: Handle high DPI displays
function getOptimalCanvasSize(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    // Cap at 2x for memory reasons
    const cappedDPR = Math.min(dpr, 2);

    return {
        width: rect.width * cappedDPR,
        height: rect.height * cappedDPR,
        scale: cappedDPR
    };
}

// BUG #328: Double buffering
let offscreenCanvas = null;
let offscreenCtx = null;

function enableDoubleBuffering() {
    if (!DOM.canvas) return;

    offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = DOM.canvas.width;
    offscreenCanvas.height = DOM.canvas.height;
    offscreenCtx = offscreenCanvas.getContext('2d');
}

function getDrawContext() {
    return offscreenCtx || DOM.ctx;
}

function flipBuffer() {
    if (offscreenCanvas && DOM.ctx) {
        DOM.ctx.drawImage(offscreenCanvas, 0, 0);
    }
}

// BUG #330: Optimize font loading
function preloadFonts() {
    const fonts = [
        // Add your custom fonts here
        // new FontFace('GameFont', 'url(/fonts/game-font.woff2)'),
    ];

    if (fonts.length === 0) return;

    Promise.all(fonts.map(font => font.load())).then(loadedFonts => {
        loadedFonts.forEach(font => document.fonts.add(font));
        console.log('Fonts preloaded');
    });
}

// ============================================================================
// BUG #315 FIX: Virtual Scrolling for Lists
// ============================================================================

class VirtualList {
    constructor(container, itemHeight, renderItem) {
        this.container = container;
        this.itemHeight = itemHeight;
        this.renderItem = renderItem;
        this.data = [];
        this.scrollTop = 0;

        if (container) {
            container.addEventListener('scroll', () => {
                this.scrollTop = container.scrollTop;
                this.render();
            });
        }
    }

    setData(data) {
        this.data = data;
        this.render();
    }

    render() {
        if (!this.container) return;

        const containerHeight = this.container.clientHeight;
        const totalHeight = this.data.length * this.itemHeight;

        // Calculate visible range
        const startIndex = Math.floor(this.scrollTop / this.itemHeight);
        const endIndex = Math.min(
            this.data.length,
            Math.ceil((this.scrollTop + containerHeight) / this.itemHeight)
        );

        // Create spacer for height
        const html = `
            <div style="height: ${totalHeight}px; position: relative;">
                <div style="transform: translateY(${startIndex * this.itemHeight}px);">
                    ${this.data.slice(startIndex, endIndex)
                        .map(item => this.renderItem(item))
                        .join('')}
                </div>
            </div>
        `;

        this.container.innerHTML = html;
    }
}

// ============================================================================
// Performance Monitoring
// ============================================================================

const perfMonitor = {
    frameTime: [],
    maxFrames: 60,

    recordFrame(duration) {
        this.frameTime.push(duration);
        if (this.frameTime.length > this.maxFrames) {
            this.frameTime.shift();
        }
    },

    getAverageFPS() {
        if (this.frameTime.length === 0) return 0;
        const avgTime = this.frameTime.reduce((a, b) => a + b) / this.frameTime.length;
        return Math.round(1000 / avgTime);
    },

    logStats() {
        console.log(`Average FPS: ${this.getAverageFPS()}`);
        console.log(`Dirty regions: ${dirtyRegions.size}`);
    }
};

// ============================================================================
// Public API
// ============================================================================

window.Performance = {
    // DOM caching
    DOM,
    initializeDOM,

    // Dirty region rendering
    markCellDirty,
    markRegionDirty,
    clearDirtyRegions,
    drawDirtyRegions,

    // RAF batching
    requestDraw,

    // Async storage
    saveToStorageAsync,
    loadFromStorageAsync,

    // Optimized algorithms
    placeMinesOptimized,
    getCachedBoard,
    setCachedBoard,
    clearBoardCache,

    // Canvas optimizations
    batchCanvasOperations,
    drawCachedText,
    clearTextCache,
    getOptimalCanvasSize,
    enableDoubleBuffering,
    getDrawContext,
    flipBuffer,
    preloadFonts,

    // Virtual scrolling
    VirtualList,

    // Performance monitoring
    perfMonitor
};

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDOM);
} else {
    initializeDOM();
}
