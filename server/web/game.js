/**
 * Sudoku Multiplayer - Game Logic
 * Adapted from Minesweeper Multiplayer
 */

// Game state
const gameState = {
    board: Array(9).fill().map(() => Array(9).fill(0)),
    solution: Array(9).fill().map(() => Array(9).fill(0)),
    initialCells: new Set(),  // Immutable pre-filled cells (stored as "row,col")
    selectedCell: null,  // {row, col}
    playerCells: {},  // Track each player's moves
    mistakes: {},
    hintsUsed: {},
    mode: 'race',
    difficulty: 'Medium',
    roomCode: null,
    username: null,
    isPlaying: false,
    canvas: null,
    ctx: null,
    cellSize: 0
};

// Initialize game canvas
function initCanvas() {
    gameState.canvas = document.getElementById('gameCanvas');
    gameState.ctx = gameState.canvas.getContext('2d');

    // Set canvas size
    const container = document.querySelector('.game-container');
    const size = Math.min(container.clientWidth - 40, 600);
    gameState.canvas.width = size;
    gameState.canvas.height = size;
    gameState.cellSize = size / 9;

    // Add event listeners
    gameState.canvas.addEventListener('click', handleCanvasClick);
    gameState.canvas.addEventListener('mousemove', handleCanvasHover);
    document.addEventListener('keydown', handleKeyPress);
}

// Draw Sudoku board
function drawBoard() {
    const { ctx, cellSize, board, initialCells, selectedCell } = gameState;

    // Clear canvas
    ctx.clearRect(0, 0, gameState.canvas.width, gameState.canvas.height);

    // Draw grid lines
    for (let i = 0; i <= 9; i++) {
        const lineWidth = i % 3 === 0 ? 3 : 1;
        ctx.lineWidth = lineWidth;
        ctx.strokeStyle = '#333';

        // Vertical lines
        ctx.beginPath();
        ctx.moveTo(i * cellSize, 0);
        ctx.lineTo(i * cellSize, gameState.canvas.height);
        ctx.stroke();

        // Horizontal lines
        ctx.beginPath();
        ctx.moveTo(0, i * cellSize);
        ctx.lineTo(gameState.canvas.width, i * cellSize);
        ctx.stroke();
    }

    // Draw numbers
    ctx.font = `${cellSize * 0.6}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    for (let row = 0; row < 9; row++) {
        for (let col = 0; col < 9; col++) {
            const num = board[row][col];
            if (num !== 0) {
                const x = col * cellSize + cellSize / 2;
                const y = row * cellSize + cellSize / 2;

                // Color based on cell type
                if (initialCells.has(`${row},${col}`)) {
                    ctx.fillStyle = '#000';  // Initial cells (black)
                } else {
                    ctx.fillStyle = '#0066cc';  // Player cells (blue)
                }

                ctx.fillText(num, x, y);
            }
        }
    }

    // Highlight selected cell
    if (selectedCell) {
        const { row, col } = selectedCell;
        ctx.strokeStyle = '#ff6600';
        ctx.lineWidth = 3;
        ctx.strokeRect(col * cellSize + 2, row * cellSize + 2, cellSize - 4, cellSize - 4);
    }
}

// Handle canvas click
function handleCanvasClick(e) {
    if (!gameState.isPlaying) return;

    const rect = gameState.canvas.getBoundingClientRect();
    const col = Math.floor((e.clientX - rect.left) / gameState.cellSize);
    const row = Math.floor((e.clientY - rect.top) / gameState.cellSize);

    if (row >= 0 && row < 9 && col >= 0 && col < 9) {
        // Check if cell is initial (immutable)
        if (gameState.initialCells.has(`${row},${col}`)) {
            showMessage('Cannot modify initial cells', 'error');
            return;
        }

        gameState.selectedCell = { row, col };
        drawBoard();
    }
}

// Handle canvas hover (visual feedback)
function handleCanvasHover(e) {
    // Add hover effect if needed
}

// Handle keyboard input
function handleKeyPress(e) {
    if (!gameState.selectedCell || !gameState.isPlaying) return;

    const num = parseInt(e.key);
    if (num >= 1 && num <= 9) {
        placeNumber(gameState.selectedCell.row, gameState.selectedCell.col, num);
    } else if (e.key === 'Backspace' || e.key === 'Delete' || e.key === '0') {
        placeNumber(gameState.selectedCell.row, gameState.selectedCell.col, 0);
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowDown' || e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        moveSelection(e.key);
        e.preventDefault();
    }
}

// Move cell selection with arrow keys
function moveSelection(key) {
    if (!gameState.selectedCell) return;

    let { row, col } = gameState.selectedCell;

    switch (key) {
        case 'ArrowUp':
            row = Math.max(0, row - 1);
            break;
        case 'ArrowDown':
            row = Math.min(8, row + 1);
            break;
        case 'ArrowLeft':
            col = Math.max(0, col - 1);
            break;
        case 'ArrowRight':
            col = Math.min(8, col + 1);
            break;
    }

    gameState.selectedCell = { row, col };
    drawBoard();
}

// Place number via socket
function placeNumber(row, col, number) {
    socket.emit('place_number', {
        room_code: gameState.roomCode,
        row: row,
        col: col,
        number: number
    });
}

// Request hint
function requestHint() {
    socket.emit('get_hint', {
        room_code: gameState.roomCode
    });
}

// Socket event handlers
socket.on('game_start', (data) => {
    console.log('Game starting with data:', data);

    gameState.board = data.puzzle;
    gameState.solution = data.solution || gameState.board;  // Fallback
    gameState.initialCells = new Set(data.initial_cells.map(([r, c]) => `${r},${c}`));
    gameState.mode = data.game_mode;
    gameState.difficulty = data.difficulty;
    gameState.isPlaying = true;
    gameState.selectedCell = null;

    initCanvas();
    drawBoard();

    // Show game screen
    document.getElementById('waitingRoom').style.display = 'none';
    document.getElementById('gameScreen').style.display = 'flex';

    showMessage('Game started!', 'success');
});

socket.on('cell_update', (data) => {
    const { username, row, col, number, is_correct } = data;

    // Update board
    gameState.board[row][col] = number;

    if (!is_correct && number !== 0) {
        showMessage(`${username} made a mistake!`, 'warning');
    }

    drawBoard();
});

socket.on('mistake', (data) => {
    const { username, count } = data;
    gameState.mistakes[username] = count;

    if (username === gameState.username) {
        showMessage(`Mistake #${count}!`, 'error');
    }
});

socket.on('hint_provided', (data) => {
    const { row, col, number } = data;

    // Auto-fill the hint
    placeNumber(row, col, number);
    showMessage('Hint applied!', 'info');
});

socket.on('game_ended', (data) => {
    gameState.isPlaying = false;

    const { winner, results } = data;

    let message = winner ? `${winner} wins!` : 'Game Over!';
    showMessage(message, 'success');

    // Show results modal
    displayResults(results);

    // Reset game state after 3 seconds
    setTimeout(() => {
        resetGame();
    }, 3000);
});

// Display results
function displayResults(results) {
    const resultsDiv = document.getElementById('gameResults');
    if (!resultsDiv) return;

    let html = '<h3>Game Results</h3><div class="results-list">';

    results.forEach((player, index) => {
        html += `
            <div class="result-item">
                <span class="rank">${index + 1}</span>
                <span class="player-name">${player.username}</span>
                <span class="player-score">Score: ${player.score || 0}</span>
                <span class="player-mistakes">Mistakes: ${gameState.mistakes[player.username] || 0}</span>
            </div>
        `;
    });

    html += '</div>';
    resultsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';

    // Hide after 5 seconds
    setTimeout(() => {
        resultsDiv.style.display = 'none';
    }, 5000);
}

// Reset game
function resetGame() {
    gameState.board = Array(9).fill().map(() => Array(9).fill(0));
    gameState.solution = Array(9).fill().map(() => Array(9).fill(0));
    gameState.initialCells = new Set();
    gameState.selectedCell = null;
    gameState.mistakes = {};
    gameState.hintsUsed = {};
    gameState.isPlaying = false;

    // Show waiting room
    document.getElementById('gameScreen').style.display = 'none';
    document.getElementById('waitingRoom').style.display = 'block';
}

// Show message
function showMessage(message, type = 'info') {
    const messageDiv = document.getElementById('gameMessage');
    if (!messageDiv) return;

    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';

    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 3000);
}

// Number pad button handlers
function numberPadClick(number) {
    if (!gameState.selectedCell) {
        showMessage('Select a cell first!', 'warning');
        return;
    }

    placeNumber(gameState.selectedCell.row, gameState.selectedCell.col, number);
}

// Expose functions globally for button onclick
window.requestHint = requestHint;
window.numberPadClick = numberPadClick;
window.resetGame = resetGame;

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Sudoku game.js loaded');
});
