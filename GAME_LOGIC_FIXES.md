# Game Logic Bug Fixes (#581-590)

## BUG #582 FIX: Recursive Reveal Stack Overflow Prevention

**Problem:** Current `revealCell` function uses recursion which can cause stack overflow on large boards.

**Solution:** Convert to iterative approach using a queue.

**Add this function to game.js:**

```javascript
// BUG #582 FIX: Non-recursive flood fill to prevent stack overflow
function revealCellIterative(startRow, startCol, isUserClick = true) {
    // Bounds check
    if (startRow < 0 || startRow >= state.difficulty.rows ||
        startCol < 0 || startCol >= state.difficulty.cols) return;

    const startCell = state.board[startRow][startCol];
    if (startCell.isRevealed || startCell.isFlagged) return;

    // Check turn in Luck Mode
    if (state.mode === 'multiplayer' && state.gameMode === 'luck') {
        if (state.currentTurn !== state.displayUsername) {
            return;
        }
        state.currentTurn = null;
        updateTurnIndicator();
    }

    // Handle first click and mine placement
    if (state.firstClick && !state.minesPlaced) {
        state.firstClick = false;
        state.startTime = Date.now();

        if (state.gameMode === 'timebomb') {
            state.timerInterval = setInterval(updateTimeBombTimer, 1000);
        } else {
            state.timerInterval = setInterval(updateTimer, 1000);
        }
        placeMines(startRow, startCol);
    }

    if (!state.minesPlaced) {
        console.warn('Attempted to reveal before mines placed! Blocked.');
        return;
    }

    // Use queue for iterative flood fill (prevents stack overflow)
    const queue = [{row: startRow, col: startCol, isUserClick: isUserClick}];
    const processed = new Set();

    while (queue.length > 0) {
        const {row, col, isUserClick} = queue.shift();
        const key = `${row},${col}`;

        // Skip if already processed
        if (processed.has(key)) continue;
        processed.add(key);

        // Bounds check
        if (row < 0 || row >= state.difficulty.rows ||
            col < 0 || col >= state.difficulty.cols) continue;

        const cell = state.board[row][col];
        if (cell.isRevealed || cell.isFlagged) continue;

        // Reveal cell
        cell.isRevealed = true;

        // Time Bomb bonus
        if (state.gameMode === 'timebomb' && !cell.isMine && isUserClick &&
            state.username.toLowerCase() !== 'icantlose') {
            state.timeRemaining += state.timebombTimeBonus[state.timebombDifficulty];
            updateTurnIndicator();
        }

        // Hit a mine
        if (cell.isMine) {
            // ICantLose cheat
            if (state.username.toLowerCase() === 'icantlose') {
                cell.isCheatSurvived = true;
                cell.isRevealed = false;
                updateStats();
                drawBoard();
                return;
            }

            state.gameOver = true;
            revealAllMines();
            calculateScore();

            if (state.mode === 'multiplayer') {
                state.socket.emit('game_action', {
                    action: 'eliminated',
                    row,
                    col,
                    clicks: state.tilesClicked
                });
            } else {
                drawBoard();
                if (state.gameMode === 'survival') {
                    state.gameResultTimeout = setTimeout(() => {
                        state.gameResultTimeout = null;
                        showGameResult(false, state.score, `Died on Level ${state.survivalLevel}`);
                    }, 500);
                } else {
                    state.gameResultTimeout = setTimeout(() => {
                        state.gameResultTimeout = null;
                        showGameResult(false, state.score);
                    }, 500);
                }
            }
            drawBoard();
            return;
        }

        // Count tile
        state.tilesClicked++;
        state.totalGameClicks++;

        // Send to server
        if (state.mode === 'multiplayer' && state.gameStarted) {
            state.socket.emit('game_action', {
                action: 'reveal',
                row,
                col,
                clicks: state.tilesClicked
            });
        }

        // Flood fill if no adjacent mines (NOT in Luck Mode)
        if (state.gameMode !== 'luck' && cell.adjacentMines === 0) {
            // Add all 8 neighbors to queue
            for (let dr = -1; dr <= 1; dr++) {
                for (let dc = -1; dc <= 1; dc++) {
                    if (dr === 0 && dc === 0) continue;
                    queue.push({
                        row: row + dr,
                        col: col + dc,
                        isUserClick: false
                    });
                }
            }
        }
    }

    updateStats();
    checkWin();
    drawBoard();
}
```

**Then replace all calls to `revealCell` with `revealCellIterative`**

---

## BUG #584 FIX: Flag Count Validation

**Problem:** No validation that flags don't exceed mine count.

**Add to game.js:**

```javascript
// BUG #584 FIX: Validate flag count
function canPlaceFlag() {
    const flaggedCount = state.board.flat().filter(cell => cell.isFlagged).length;
    return flaggedCount < state.difficulty.mines;
}

// Update toggleFlag function:
function toggleFlag(row, col) {
    if (row < 0 || row >= state.difficulty.rows ||
        col < 0 || col >= state.difficulty.cols) return;

    const cell = state.board[row][col];
    if (cell.isRevealed) return;

    if (cell.isFlagged) {
        // Always allow unflagging
        cell.isFlagged = false;
    } else {
        // Check if we can place more flags (BUG #584 FIX)
        if (!canPlaceFlag()) {
            // Optional: show warning to user
            console.warn('Maximum flags placed');
            return;
        }
        cell.isFlagged = true;
    }

    drawBoard();
    updateStats();

    // Send to server if multiplayer
    if (state.mode === 'multiplayer' && state.gameStarted) {
        state.socket.emit('game_action', {
            action: 'flag',
            row,
            col
        });
    }
}
```

---

## BUG #585 FIX: Hint System Safety

**Problem:** Hint system could accidentally reveal mines.

**Add validation:**

```javascript
// BUG #585 FIX: Safe hint generation
function generateSafeHint() {
    const unrevealed = [];

    // Collect all unrevealed safe cells
    for (let row = 0; row < state.difficulty.rows; row++) {
        for (let col = 0; col < state.difficulty.cols; col++) {
            const cell = state.board[row][col];
            if (!cell.isRevealed && !cell.isFlagged && !cell.isMine) {
                unrevealed.push({row, col, adjacentMines: cell.adjacentMines});
            }
        }
    }

    if (unrevealed.length === 0) {
        return null;  // No safe hints available
    }

    // Prioritize cells with 0 adjacent mines (will flood fill)
    const zeroMineCells = unrevealed.filter(c => c.adjacentMines === 0);
    if (zeroMineCells.length > 0) {
        return zeroMineCells[Math.floor(Math.random() * zeroMineCells.length)];
    }

    // Otherwise, return random safe cell
    return unrevealed[Math.floor(Math.random() * unrevealed.length)];
}
```

---

## BUG #586 FIX: Timer Pause on Disconnect

**Add to socket disconnect handler:**

```javascript
socket.on('disconnect', () => {
    console.log('Disconnected from server');

    // BUG #586 FIX: Pause timer on disconnect
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
        state.timerPausedAt = Date.now();
    }

    state.connected = false;
    updateConnectionStatus();
});

socket.on('connect', () => {
    console.log('Reconnected to server');

    // BUG #586 FIX: Resume timer on reconnect
    if (state.timerPausedAt && state.gameStarted && !state.gameOver) {
        // Calculate time spent disconnected
        const disconnectedTime = Date.now() - state.timerPausedAt;

        // Add disconnected time to start time (effectively pauses)
        state.startTime += disconnectedTime;

        // Resume appropriate timer
        if (state.gameMode === 'timebomb') {
            state.timerInterval = setInterval(updateTimeBombTimer, 1000);
        } else {
            state.timerInterval = setInterval(updateTimer, 1000);
        }

        state.timerPausedAt = null;
    }

    state.connected = true;
    updateConnectionStatus();
});
```

---

## BUG #587 FIX: Score Calculation Edge Cases

**Add validation:**

```javascript
// BUG #587 FIX: Robust score calculation
function calculateScore() {
    // Validate inputs
    const tilesClicked = Math.max(0, Math.floor(state.tilesClicked || 0));
    const totalSafeTiles = (state.difficulty.rows * state.difficulty.cols) - state.difficulty.mines;

    // Cap tiles clicked to maximum possible
    const validTilesClicked = Math.min(tilesClicked, totalSafeTiles);

    // Calculate base score
    let score = validTilesClicked;

    // Time bonus (if won)
    if (!state.gameOver || state.won) {
        const timeElapsed = calculateElapsedTime();
        if (timeElapsed > 0 && timeElapsed < 86400) {  // Max 24 hours
            // Faster completion = higher multiplier (max 2x)
            const timeBonus = Math.max(0, Math.min(score, score * (300 / timeElapsed)));
            score += Math.floor(timeBonus);
        }
    }

    // Survival mode level multiplier
    if (state.gameMode === 'survival') {
        const level = Math.max(1, Math.floor(state.survivalLevel || 1));
        score *= level;
    }

    // Ensure score is valid integer
    state.score = Math.max(0, Math.floor(score));
    return state.score;
}
```

---

## BUG #588 FIX: Multiplayer Sync Issues

**Add synchronization checks:**

```javascript
// BUG #588 FIX: Validate multiplayer actions
function validateMultiplayerState(action, data) {
    // Don't process actions if game not started
    if (!state.gameStarted) {
        console.warn(`Action ${action} ignored: game not started`);
        return false;
    }

    // Don't process actions if game over
    if (state.gameOver) {
        console.warn(`Action ${action} ignored: game over`);
        return false;
    }

    // Validate coordinates
    if (data.row !== undefined && data.col !== undefined) {
        if (data.row < 0 || data.row >= state.difficulty.rows ||
            data.col < 0 || data.col >= state.difficulty.cols) {
            console.warn(`Action ${action} ignored: invalid coordinates`);
            return false;
        }
    }

    return true;
}

// Add to all socket.on('player_action') handlers:
socket.on('player_action', (data) => {
    if (!validateMultiplayerState(data.action, data)) {
        return;  // Ignore invalid action
    }

    // Process action...
});
```

---

## BUG #589 FIX: Turn Skip Prevention

**Add turn validation:**

```javascript
// BUG #589 FIX: Prevent turn skipping in Luck Mode
function validateTurn(username) {
    if (state.gameMode !== 'luck') {
        return true;  // Not turn-based
    }

    if (state.currentTurn !== username) {
        console.warn(`Turn validation failed: expected ${state.currentTurn}, got ${username}`);
        return false;
    }

    return true;
}

// Add to revealCell:
if (state.gameMode === 'luck') {
    if (!validateTurn(state.displayUsername)) {
        return;  // Not your turn
    }
}
```

---

## BUG #590 FIX: Consistent Game End Conditions

**Standardize win/loss checks:**

```javascript
// BUG #590 FIX: Consistent game end check
function checkGameEnd() {
    // Already ended
    if (state.gameOver) {
        return {ended: true, won: state.won};
    }

    // Check if player hit mine
    const hitMine = state.board.some(row =>
        row.some(cell => cell.isRevealed && cell.isMine)
    );

    if (hitMine) {
        return {ended: true, won: false, reason: 'hit_mine'};
    }

    // Check if all safe tiles revealed
    const totalSafeTiles = (state.difficulty.rows * state.difficulty.cols) - state.difficulty.mines;
    const revealedSafeTiles = state.board.flat().filter(
        cell => cell.isRevealed && !cell.isMine
    ).length;

    if (revealedSafeTiles >= totalSafeTiles) {
        return {ended: true, won: true, reason: 'all_tiles_cleared'};
    }

    // Time bomb: check if time ran out
    if (state.gameMode === 'timebomb' && state.timeRemaining <= 0) {
        return {ended: true, won: false, reason: 'time_expired'};
    }

    // Game still ongoing
    return {ended: false};
}
```

---

## BUG #583 FIX: Diagonal Mine Counting

**Current implementation is correct** (lines 1656-1668 in game.js). The loop properly checks all 8 neighbors including diagonals. No fix needed.

---

## BUG #581 FIX: First Click Safety

**Current implementation is correct** (lines 1616-1628 in game.js). A 5x5 exclusion zone ensures first click is always safe. No fix needed.

---

## Summary

**Fixed:**
- #581: ✅ Already correct
- #582: ✅ Convert to iterative flood fill
- #583: ✅ Already correct
- #584: ✅ Add flag count validation
- #585: ✅ Ensure hints never reveal mines
- #586: ✅ Pause timer on disconnect
- #587: ✅ Validate score calculations
- #588: ✅ Add multiplayer state validation
- #589: ✅ Prevent turn skipping
- #590: ✅ Standardize game end conditions

**Implementation:** These fixes should be integrated into game.js. Most can be added as new functions, with a few requiring modifications to existing event handlers.
