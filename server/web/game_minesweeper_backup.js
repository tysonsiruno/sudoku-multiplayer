// Configuration
// Automatically detect server URL based on current location
// This works for Railway, localhost, or any other deployment
const SERVER_URL = window.location.origin;

// Game State
const state = {
    username: '',
    displayUsername: '', // Display name (masked for ICantLose cheat)
    mode: 'solo', // 'solo' or 'multiplayer'
    gameMode: 'standard', // 'standard', 'luck', 'timebomb', 'survival'
    currentScreen: 'login-screen',
    previousScreen: null, // BUG #485 FIX: Track previous screen for Back button
    gameDifficultyScreen: null, // BUG #487 FIX: Track difficulty selection screen for Back button
    socket: null,
    roomCode: null,
    players: [],
    gameStarted: false,
    currentTurn: null,
    seededRandom: null, // Store seeded random for multiplayer
    lastGameWinner: null, // Track winner for mode selection

    // Game variables
    difficulty: { name: 'Medium', rows: 16, cols: 16, mines: 40 },
    boardDifficulty: 'medium', // 'easy', 'medium', 'hard' for standard/survival modes
    boardDifficulties: {
        easy: { name: 'Easy', rows: 9, cols: 9, mines: 10 },
        medium: { name: 'Medium', rows: 16, cols: 16, mines: 40 },
        hard: { name: 'Hard', rows: 16, cols: 30, mines: 99 } // BUG #484 FIX: 30 wide x 16 tall (landscape)
    },
    board: [],
    cellSize: 30,
    firstClick: true,
    minesPlaced: false, // CRITICAL: Prevent double mine placement
    gameOver: false,
    gameWon: false,
    startTime: null,
    elapsedTime: 0,
    flagsPlaced: 0,
    hintsRemaining: 3,
    hintCell: null,
    hintTimeout: null, // BUG #42 FIX: Track hint timeout for cleanup
    hoverCell: null, // Track cell under cursor
    score: 0,
    timerInterval: null,
    survivalLevelTimeout: null, // BUG #49 FIX: Track survival level timeout
    gameResultTimeout: null, // BUG #237 FIX: Track game result timeout for cleanup
    tilesClicked: 0, // Track tiles clicked for new scoring system
    totalGameClicks: 0, // For multiplayer: total clicks from all players
    soundEnabled: true, // Sound system toggle

    // Time Bomb mode variables
    timebombDifficulty: 'medium', // 'easy', 'medium', 'hard', 'impossible', 'hacker'
    timeRemaining: 60, // Countdown timer
    timebombStartTime: { easy: 90, medium: 60, hard: 45, impossible: 30, hacker: 20 },
    timebombTimeBonus: { easy: 1.0, medium: 0.5, hard: 0.2, impossible: 0.05, hacker: 0.01 }, // Seconds per tile

    // Survival mode variables
    survivalLevel: 1,
    survivalTotalTiles: 0,
    survivalMineCount: 40,
    survivalBaseMines: 40,
    survivalMineIncrease: 1, // Add 1 more mine per level (gradually increasing difficulty)

    // Fog of War mode variables
    fogOfWar: false, // Is fog of war mode active
    fogRevealedCells: new Map(), // Track which cells are currently visible {key: 'row,col', value: timestamp}
    lastClickPosition: null, // {row, col} of last click for 5x5 visibility
    fogFadeTimers: new Map(), // Track fade timers for each cell
    flaresRemaining: 0, // Flare power-ups available
    flareActive: false, // Is flare currently active (revealing whole board)
    flareTimeout: null, // Timeout ID for flare duration

    // Sabotage mode variables (Power-Up System)
    sabotageMode: false, // Is sabotage mode active
    powerUps: [], // Array of collected power-ups {type, id}
    maxPowerUps: 5, // Maximum power-ups that can be held
    powerUpCells: new Map(), // Track which cells have power-ups {key: 'row,col', value: powerUpType}
    activePowerUp: null, // Currently active power-up effect
    shieldActive: false, // Shield power-up status
    fortuneActive: false, // Fortune power-up status (next 5 clicks safe)
    fortuneClicksRemaining: 0, // Clicks remaining for fortune
    freezeEndTime: null, // Timestamp when freeze ends
    ghostModeEndTime: null, // Timestamp when ghost mode ends (hide progress from opponents)
    rewindHistory: [], // Last 3 moves for rewind power-up {row, col, cell state}

    // Speed Chess mode variables (Chess Clock Timer)
    speedChessMode: false, // Is speed chess mode active
    speedChessDifficulty: 'blitz', // bullet, blitz, rapid, marathon
    playerTimeRemaining: null, // Time remaining for current player (in seconds)
    opponentTimeRemaining: null, // Time remaining for opponent (in seconds)
    speedChessTimerInterval: null, // Interval ID for countdown
    speedChessStartTime: {
        bullet: 30,    // 30 seconds
        blitz: 60,     // 1 minute
        rapid: 180,    // 3 minutes
        marathon: 300  // 5 minutes
    },
    isPlayerTurn: true // Whose timer is currently counting down
};

// ============================================================================
// BUG FIXES #181-230: Performance & Event Management Utilities
// ============================================================================

// BUG #181-230 FIXES: Utility functions for performance optimization
const TOUCH_HANDLED_DELAY = 300; // Bug #181: Reduced from 500ms

// Throttle function for performance optimization (Bug #219, #230)
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

// Debounce function for resize handlers (Bug #202, #229)
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

// Rate limiter for socket emits (Bug #200)
const socketRateLimiter = {
    lastEmit: {},
    canEmit(event, minDelay = 1000) {
        const now = Date.now();
        const last = this.lastEmit[event] || 0;
        if (now - last >= minDelay) {
            this.lastEmit[event] = now;
            return true;
        }
        return false;
    }
};

// Safe timer management (Bug #185, #189, #195, #196)
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

// Bug #182, #183: Proper canvas position calculation with offsets
function getCanvasPosition(e, canvas, isTouch = false) {
    const rect = canvas.getBoundingClientRect();
    const clientX = isTouch ? e.touches[0].clientX : e.clientX;
    const clientY = isTouch ? e.touches[0].clientY : e.clientY;

    return {
        x: clientX - rect.left,
        y: clientY - rect.top
    };
}

// Bug #186: Generate unique seed to prevent collisions
function generateUniqueSeed() {
    return Date.now() + Math.floor(Math.random() * 1000000);
}

// Bug #197, #198, #199: Proper time calculation and formatting
function calculateElapsedTime() {
    if (!state.startTime) return 0;
    const elapsed = Math.max(0, Date.now() - state.startTime);
    return Math.floor(elapsed / 1000);
}

function formatTime(seconds) {
    seconds = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
}

// Bug #191-194: Safe socket emit with validation
function safeSocketEmit(event, data) {
    if (!state.socket || !state.socket.connected) {
        console.warn(`Socket not connected, cannot emit ${event}`);
        return false;
    }

    // Validate and sanitize data
    if (data && typeof data === 'object') {
        if (data.row !== undefined) data.row = parseInt(data.row) || 0;
        if (data.col !== undefined) data.col = parseInt(data.col) || 0;
        if (data.score !== undefined) data.score = Math.max(0, parseInt(data.score) || 0);
        if (data.time !== undefined) data.time = Math.max(0, parseInt(data.time) || 0);
    }

    state.socket.emit(event, data);
    return true;
}

// Bug #227, #228: Touch/mouse conflict resolution
let lastInputType = null;
let lastInputTime = 0;
const INPUT_COOLDOWN = 300;

function canProcessInput(type) {
    const now = Date.now();
    if (now - lastInputTime < INPUT_COOLDOWN && lastInputType !== type && lastInputType !== null) {
        return false;
    }
    lastInputType = type;
    lastInputTime = now;
    return true;
}

// Bug #225: Event listener cleanup
function cleanupEventListeners() {
    timerManager.clearAll();

    // Clear specific game timeouts
    if (state.hintTimeout) {
        clearTimeout(state.hintTimeout);
        state.hintTimeout = null;
    }
    if (state.survivalLevelTimeout) {
        clearTimeout(state.survivalLevelTimeout);
        state.survivalLevelTimeout = null;
    }
    if (state.gameResultTimeout) {
        clearTimeout(state.gameResultTimeout);
        state.gameResultTimeout = null;
    }
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
    }
}

// ============================================================================
// END BUG FIXES
// ============================================================================

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    initCanvas();

    // BUG #202, #229 FIX: Debounced resize handler to prevent excessive redraws
    window.addEventListener('resize', debounce(() => {
        if (state.currentScreen === 'game-screen') {
            initCanvas();
            drawBoard();
        }
    }, 250));
});

function setupEventListeners() {
    // Helper to prevent both touch and click from firing
    let touchHandled = false;
    // BUG #181 FIX: Use configurable delay and timerManager
    const preventClickAfterTouch = () => {
        touchHandled = true;
        timerManager.setTimeout(() => { touchHandled = false; }, TOUCH_HANDLED_DELAY);
    };

    // Mode selection - with proper mobile support
    const soloBtn = document.getElementById('solo-btn');
    if (soloBtn) {
        soloBtn.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            preventClickAfterTouch();
            state.mode = 'solo';
            showScreen('gamemode-screen');
        }, { passive: false });

        soloBtn.addEventListener('click', (e) => {
            if (touchHandled) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            state.mode = 'solo';
            showScreen('gamemode-screen');
        });
    } else {
        console.error('✗ solo-btn NOT FOUND');
    }

    const multiplayerBtn = document.getElementById('multiplayer-btn');
    if (multiplayerBtn) {
        multiplayerBtn.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            preventClickAfterTouch();
            state.mode = 'multiplayer';
            showMultiplayerLobby();
        }, { passive: false });

        multiplayerBtn.addEventListener('click', (e) => {
            if (touchHandled) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            state.mode = 'multiplayer';
            showMultiplayerLobby();
        });
    } else {
        console.error('✗ multiplayer-btn NOT FOUND');
    }

    const backToUsernameBtn = document.getElementById('back-to-username');
    if (backToUsernameBtn) {
        backToUsernameBtn.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            preventClickAfterTouch();
            showScreen('username-screen');
        }, { passive: false });

        backToUsernameBtn.addEventListener('click', (e) => {
            if (touchHandled) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            showScreen('username-screen');
        });
    }

    // Username submission
    const usernameSubmit = document.getElementById('username-submit');
    const usernameInput = document.getElementById('username-input');

    if (usernameSubmit && usernameInput) {
        const handleUsernameSubmit = () => {
            let username = usernameInput.value.trim();
            if (username.length > 0) {
                // RANDOM USERNAME GENERATOR: "random" gives self-deprecating names
                if (username.toLowerCase() === 'random') {
                    const selfDeprecatingNames = [
                        'ImActuallyTrash', 'PleaseCarryMe', 'SorryInAdvance', 'FirstTimePlaying',
                        'IDontKnowWhatImDoing', 'HelpMePls', 'ImSoBad', 'CantClickRight',
                        'AccidentallyHere', 'WrongGameSorry', 'ImTrying', 'LearningStill',
                        'NoIdeaWhatsGoingOn', 'CompleteBeginner', 'TerriblePlayer', 'WillProbablyLose',
                        'NotVeryGood', 'KindaBadAtThis', 'LosingIsMyStyle', 'MistakesMeEverywhere',
                        'ConfusedConstantly', 'BadDecisionMaker', 'ClickRandomly', 'HopeForTheBest',
                        'LuckBasedPlayer', 'NoSkillHere', 'PurelyGuessing', 'WhatAmIDoing',
                        'CantReadNumbers', 'ColorBlindMaybe', 'SlowReactionTime', 'FingerSlipped',
                        'WrongButtonPressed', 'AccidentalClick', 'DidntMeanTo', 'MyBadSorry',
                        'IApologizeInAdvance', 'GonnaMissUp', 'WatchMeFail', 'DisappointmentIncoming',
                        'LowExpectations', 'ProbablyAFK', 'LaggingHard', 'BadConnection',
                        'BrokenMouse', 'StickyKeyboard', 'CantSeeScreen', 'WrongPrescription',
                        'ForgotHowToPlay', 'RulesAreHard', 'TooComplicatedForMe', 'SimplyOutmatched',
                        'NotMyGame', 'ShouldQuitNow', 'WhyAmIHere', 'MistakeMadeJoining',
                        'WrongPlace', 'LostAndConfused', 'NeedATutorial', 'ReadTheManual',
                        'WatchedNoVideos', 'ZeroExperience', 'NeverWonBefore', 'LossStreak',
                        'ConsistentlyBad', 'ReliablyTerrible', 'PredictablyAwful', 'ExpectablyWorse',
                        'BottomOfLeaderboard', 'LastPlacePlayer', 'EasyWinForYou', 'FreePoints',
                        'GiftWrappedVictory', 'HandedYouTheWin', 'YoureFineIPromise', 'DontWorryAboutMe',
                        'CarryOnWithoutMe', 'IllJustWatch', 'SpectatorMode', 'BenchWarmer',
                        'SubstituteNeeded', 'WrongTeamMate', 'DeadWeightHere', 'AnchorDragging',
                        'HoldingYouBack', 'SorryTeam', 'BlameMe', 'MyFault',
                        'IMessedUp', 'CriticalError', 'FatalMistake', 'GameThrowingSkills',
                        'SabotageExpert', 'FeedingChamp', 'IntentionallyBad', 'NaturallyAwful',
                        'BornToLose', 'DestinedToFail', 'CursedWithBadLuck', 'UnluckyAlways',
                        'MurphysLawPlayer', 'EverythingGoesWrong', 'WorstCaseScenario', 'DisasterWaiting',
                        'TrainwreckIncoming', 'DumpsterFirePlayer', 'CompleteGarbage', 'AbsoluteTrash'
                    ];
                    username = selfDeprecatingNames[Math.floor(Math.random() * selfDeprecatingNames.length)];
                    state.username = username;
                    state.displayUsername = username;
                }
                // RANDOM USERNAME GENERATOR: "random1" gives two combined words
                else if (username.toLowerCase() === 'random1') {
                    const adjectives = [
                        'Swift', 'Clever', 'Mighty', 'Silent', 'Brave', 'Wild', 'Cosmic', 'Electric',
                        'Frozen', 'Golden', 'Shadow', 'Crystal', 'Thunder', 'Mystic', 'Ancient',
                        'Blazing', 'Turbo', 'Mega', 'Ultra', 'Epic', 'Legendary', 'Supreme',
                        'Phantom', 'Stealth', 'Cyber', 'Neon', 'Atomic', 'Quantum', 'Hyper',
                        'Ninja', 'Dragon', 'Phoenix', 'Titan', 'Viper', 'Raven', 'Wolf'
                    ];
                    const nouns = [
                        'Warrior', 'Hunter', 'Sniper', 'Striker', 'Guardian', 'Champion', 'Legend',
                        'Master', 'Slayer', 'Destroyer', 'Raider', 'Reaper', 'Assassin', 'Ranger',
                        'Knight', 'Samurai', 'Wizard', 'Sorcerer', 'Tempest', 'Storm', 'Blaze',
                        'Vortex', 'Eclipse', 'Nova', 'Comet', 'Meteor', 'Galaxy', 'Nebula',
                        'Raptor', 'Falcon', 'Eagle', 'Hawk', 'Tiger', 'Lion', 'Bear', 'Shark'
                    ];
                    const randomAdj = adjectives[Math.floor(Math.random() * adjectives.length)];
                    const randomNoun = nouns[Math.floor(Math.random() * nouns.length)];
                    username = randomAdj + randomNoun;
                    state.username = username;
                    state.displayUsername = username;
                }
                // ICantLose cheat: Mask the username for display with toxic/cocky names
                else if (username.toLowerCase() === 'icantlose') {
                    state.username = username;
                    // Toxic/cocky usernames for display
                    const toxicNames = [
                        'RUEVNTRYNG?', 'EZWIN', 'UshouldPracticeMore', 'uhhhhisthatit?',
                        'TooEZ4Me', 'GetGoodKid', 'NiceAttemptTho', 'IsThisEasyMode?',
                        'YallTryingRight?', 'LiterallyAFK', 'OneHandedBTW', 'DidntEvenTry',
                        'WasThatSupposedToBeHard', 'ImNotEvenWarmedUp', 'zzzzz'
                    ];
                    state.displayUsername = toxicNames[Math.floor(Math.random() * toxicNames.length)];
                } else {
                    state.username = username;
                    state.displayUsername = username;
                }

                showScreen('mode-screen');
            }
        };

        usernameSubmit.addEventListener('click', handleUsernameSubmit);
        usernameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleUsernameSubmit();
            }
        });
    }

    // Lobby
    // BUG #279 FIX: Add null checks before addEventListener
    const createRoomBtn = document.getElementById('create-room-btn');
    if (createRoomBtn) createRoomBtn.addEventListener('click', () => showScreen('gamemode-screen'));

    const joinRoomBtn = document.getElementById('join-room-btn');
    if (joinRoomBtn) joinRoomBtn.addEventListener('click', () => showScreen('join-screen'));

    const backToModeBtn = document.getElementById('back-to-mode');
    if (backToModeBtn) backToModeBtn.addEventListener('click', () => {
        disconnectSocket();
        showScreen('mode-screen');
    });

    // Join room
    const joinSubmitBtn = document.getElementById('join-submit');
    if (joinSubmitBtn) joinSubmitBtn.addEventListener('click', joinRoom);

    const roomCodeInput = document.getElementById('room-code-input');
    if (roomCodeInput) roomCodeInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') joinRoom();
    });

    const backToLobbyBtn = document.getElementById('back-to-lobby');
    if (backToLobbyBtn) backToLobbyBtn.addEventListener('click', () => showScreen('lobby-screen'));

    // Game mode selection - with proper mobile support (prevent double-fire)
    document.querySelectorAll('.select-mode').forEach(btn => {
        btn.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            preventClickAfterTouch();
            // BUG #280 FIX: Null check on closest() before accessing dataset
            const modeCard = e.target.closest('.mode-card');
            if (!modeCard) return;
            const mode = modeCard.dataset.mode;

            // Store the pending game mode for difficulty selection
            state.pendingGameMode = mode;

            // Time Bomb mode needs difficulty selection first
            if (mode === 'timebomb') {
                showScreen('timebomb-difficulty-screen');
                return;
            }

            // Standard, Survival, Fog of War, and Sabotage modes need board difficulty selection
            if (mode === 'standard' || mode === 'survival' || mode === 'fogofwar' || mode === 'sabotage') {
                // Update title based on mode
                const titleEl = document.getElementById('board-difficulty-title');
                if (titleEl) {
                    if (mode === 'standard') {
                        titleEl.textContent = 'Standard - Choose Difficulty';
                    } else if (mode === 'survival') {
                        titleEl.textContent = 'Survival - Choose Difficulty';
                    } else if (mode === 'fogofwar') {
                        titleEl.textContent = '🌫️ Fog of War - Choose Difficulty';
                    } else if (mode === 'sabotage') {
                        titleEl.textContent = '⚡ Sabotage - Choose Difficulty';
                    }
                }
                // Track which screen we're on for back button
                state.gameDifficultyScreen = 'board-difficulty-screen';
                console.log('[Mode Selection] pendingGameMode set to:', state.pendingGameMode);
                showScreen('board-difficulty-screen');
                return;
            }

            // Speed Chess needs its own difficulty selection (Bullet/Blitz/Rapid/Marathon)
            if (mode === 'speedchess') {
                state.gameDifficultyScreen = 'speedchess-difficulty-screen';
                showScreen('speedchess-difficulty-screen');
                return;
            }

            // Time Bomb needs its own difficulty selection
            if (mode === 'timebomb') {
                state.gameDifficultyScreen = 'timebomb-difficulty-screen';
                showScreen('timebomb-difficulty-screen');
                return;
            }

            // Russian Roulette doesn't need difficulty selection
            // BUG #487 FIX: Track difficulty screen for Back button
            state.gameDifficultyScreen = 'gamemode-screen';
            // Check if we're already in a room (post-game mode selection)
            if (state.roomCode && state.socket && state.socket.connected) {
                // Change mode in existing room
                state.socket.emit('change_game_mode', { game_mode: mode });
            } else if (state.socket && state.socket.connected) {
                // Create new room
                createRoom(mode);
            } else {
                // Solo mode
                startSoloGame(mode);
            }
        }, { passive: false });

        btn.addEventListener('click', (e) => {
            if (touchHandled) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            // BUG #280 FIX: Null check on closest() before accessing dataset
            const modeCard = e.target.closest('.mode-card');
            if (!modeCard) return;
            const mode = modeCard.dataset.mode;

            // Store the pending game mode for difficulty selection
            state.pendingGameMode = mode;

            // Time Bomb mode needs difficulty selection first
            if (mode === 'timebomb') {
                showScreen('timebomb-difficulty-screen');
                return;
            }

            // Standard, Survival, Fog of War, and Sabotage modes need board difficulty selection
            if (mode === 'standard' || mode === 'survival' || mode === 'fogofwar' || mode === 'sabotage') {
                // Update title based on mode
                const titleEl = document.getElementById('board-difficulty-title');
                if (titleEl) {
                    if (mode === 'standard') {
                        titleEl.textContent = 'Standard - Choose Difficulty';
                    } else if (mode === 'survival') {
                        titleEl.textContent = 'Survival - Choose Difficulty';
                    } else if (mode === 'fogofwar') {
                        titleEl.textContent = '🌫️ Fog of War - Choose Difficulty';
                    } else if (mode === 'sabotage') {
                        titleEl.textContent = '⚡ Sabotage - Choose Difficulty';
                    }
                }
                // Track which screen we're on for back button
                state.gameDifficultyScreen = 'board-difficulty-screen';
                console.log('[Mode Selection] pendingGameMode set to:', state.pendingGameMode);
                showScreen('board-difficulty-screen');
                return;
            }

            // Speed Chess needs its own difficulty selection (Bullet/Blitz/Rapid/Marathon)
            if (mode === 'speedchess') {
                state.gameDifficultyScreen = 'speedchess-difficulty-screen';
                showScreen('speedchess-difficulty-screen');
                return;
            }

            // Time Bomb needs its own difficulty selection
            if (mode === 'timebomb') {
                state.gameDifficultyScreen = 'timebomb-difficulty-screen';
                showScreen('timebomb-difficulty-screen');
                return;
            }

            // Russian Roulette doesn't need difficulty selection
            // BUG #487 FIX: Track difficulty screen for Back button
            state.gameDifficultyScreen = 'gamemode-screen';
            // Check if we're already in a room (post-game mode selection)
            if (state.roomCode && state.socket && state.socket.connected) {
                // Change mode in existing room
                state.socket.emit('change_game_mode', { game_mode: mode });
            } else if (state.socket && state.socket.connected) {
                // Create new room
                createRoom(mode);
            } else {
                // Solo mode
                startSoloGame(mode);
            }
        });
    });

    const backToLobby2Btn = document.getElementById('back-to-lobby2');
    if (backToLobby2Btn) {
        backToLobby2Btn.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            preventClickAfterTouch();
            if (state.socket && state.socket.connected) {
                showScreen('lobby-screen');
            } else {
                showScreen('mode-screen');
            }
        }, { passive: false });

        backToLobby2Btn.addEventListener('click', (e) => {
            if (touchHandled) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            if (state.socket && state.socket.connected) {
                showScreen('lobby-screen');
            } else {
                showScreen('mode-screen');
            }
        });
    }

    // Difficulty selection - handles both Time Bomb and Speed Chess with proper mobile support
    document.querySelectorAll('.select-difficulty').forEach(btn => {
        btn.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            preventClickAfterTouch();
            // BUG #280 FIX: Null check on closest() before accessing dataset
            const modeCard = e.target.closest('.mode-card');
            if (!modeCard) return;
            const difficulty = modeCard.dataset.difficulty;

            // Detect which difficulty screen we're on
            const timebombScreen = document.getElementById('timebomb-difficulty-screen');
            const speedchessScreen = document.getElementById('speedchess-difficulty-screen');

            if (timebombScreen && timebombScreen.classList.contains('active')) {
                // Time Bomb mode
                state.timebombDifficulty = difficulty;
                state.gameDifficultyScreen = 'timebomb-difficulty-screen';

                if (state.roomCode && state.socket && state.socket.connected) {
                    state.socket.emit('change_game_mode', { game_mode: 'timebomb' });
                } else if (state.socket && state.socket.connected) {
                    createRoom('timebomb');
                } else {
                    startSoloGame('timebomb');
                }
            } else if (speedchessScreen && speedchessScreen.classList.contains('active')) {
                // Speed Chess mode - save difficulty and move to board selection
                state.speedChessDifficulty = difficulty;
                state.pendingGameMode = 'speedchess';
                state.gameDifficultyScreen = 'speedchess-difficulty-screen';

                // Now show board difficulty selection
                document.getElementById('board-difficulty-title').textContent = '⏱️ Speed Chess - Choose Board Difficulty';
                showScreen('board-difficulty-screen');
            }
        }, { passive: false });

        btn.addEventListener('click', (e) => {
            if (touchHandled) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            // BUG #280 FIX: Null check on closest() before accessing dataset
            const modeCard = e.target.closest('.mode-card');
            if (!modeCard) return;
            const difficulty = modeCard.dataset.difficulty;

            // Detect which difficulty screen we're on
            const timebombScreen = document.getElementById('timebomb-difficulty-screen');
            const speedchessScreen = document.getElementById('speedchess-difficulty-screen');

            if (timebombScreen && timebombScreen.classList.contains('active')) {
                // Time Bomb mode
                state.timebombDifficulty = difficulty;
                state.gameDifficultyScreen = 'timebomb-difficulty-screen';

                if (state.roomCode && state.socket && state.socket.connected) {
                    state.socket.emit('change_game_mode', { game_mode: 'timebomb' });
                } else if (state.socket && state.socket.connected) {
                    createRoom('timebomb');
                } else {
                    startSoloGame('timebomb');
                }
            } else if (speedchessScreen && speedchessScreen.classList.contains('active')) {
                // Speed Chess mode - save difficulty and move to board selection
                state.speedChessDifficulty = difficulty;
                state.pendingGameMode = 'speedchess';
                state.gameDifficultyScreen = 'speedchess-difficulty-screen';

                // Now show board difficulty selection
                document.getElementById('board-difficulty-title').textContent = '⏱️ Speed Chess - Choose Board Difficulty';
                showScreen('board-difficulty-screen');
            }
        });
    });

    const backToGamemodeBtn = document.getElementById('back-to-gamemode');
    if (backToGamemodeBtn) {
        backToGamemodeBtn.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            preventClickAfterTouch();
            showScreen('gamemode-screen');
        }, { passive: false });

        backToGamemodeBtn.addEventListener('click', (e) => {
            if (touchHandled) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            showScreen('gamemode-screen');
        });
    }

    // Board difficulty selection for Standard/Survival modes - with proper mobile support
    document.querySelectorAll('.select-board-difficulty').forEach(btn => {
        btn.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            preventClickAfterTouch();
            // BUG #280 FIX: Null check on closest() before accessing dataset
            const modeCard = e.target.closest('.mode-card');
            if (!modeCard) return;
            const boardDiff = modeCard.dataset.boardDifficulty;
            state.boardDifficulty = boardDiff;

            // BUG #233 FIX: Validate difficulty exists before accessing
            if (!state.boardDifficulties[boardDiff]) {
                console.error('Invalid board difficulty:', boardDiff);
                return;
            }

            // Apply the selected difficulty
            state.difficulty = {
                name: state.boardDifficulties[boardDiff].name,
                rows: state.boardDifficulties[boardDiff].rows,
                cols: state.boardDifficulties[boardDiff].cols,
                mines: state.boardDifficulties[boardDiff].mines
            };

            // For survival mode, also update survivalBaseMines and survivalMineCount
            if (state.pendingGameMode === 'survival') {
                state.survivalBaseMines = state.boardDifficulties[boardDiff].mines;
                state.survivalMineCount = state.survivalBaseMines;
            }

            const mode = state.pendingGameMode || 'standard';
            console.log('[Board Difficulty Selection] Using mode:', mode, '(pendingGameMode was:', state.pendingGameMode, ')');
            // BUG #487 FIX: Track difficulty screen for Back button
            state.gameDifficultyScreen = 'board-difficulty-screen';
            // Check if we're already in a room (post-game mode selection)
            if (state.roomCode && state.socket && state.socket.connected) {
                // Change mode in existing room
                state.socket.emit('change_game_mode', { game_mode: mode });
            } else if (state.socket && state.socket.connected) {
                // Create new room
                createRoom(mode);
            } else {
                // Solo mode
                startSoloGame(mode);
            }
        }, { passive: false });

        btn.addEventListener('click', (e) => {
            if (touchHandled) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            // BUG #280 FIX: Null check on closest() before accessing dataset
            const modeCard = e.target.closest('.mode-card');
            if (!modeCard) return;
            const boardDiff = modeCard.dataset.boardDifficulty;
            state.boardDifficulty = boardDiff;

            // BUG #233 FIX: Validate difficulty exists before accessing
            if (!state.boardDifficulties[boardDiff]) {
                console.error('Invalid board difficulty:', boardDiff);
                return;
            }

            // Apply the selected difficulty
            state.difficulty = {
                name: state.boardDifficulties[boardDiff].name,
                rows: state.boardDifficulties[boardDiff].rows,
                cols: state.boardDifficulties[boardDiff].cols,
                mines: state.boardDifficulties[boardDiff].mines
            };

            // For survival mode, also update survivalBaseMines and survivalMineCount
            if (state.pendingGameMode === 'survival') {
                state.survivalBaseMines = state.boardDifficulties[boardDiff].mines;
                state.survivalMineCount = state.survivalBaseMines;
            }

            const mode = state.pendingGameMode || 'standard';
            console.log('[Board Difficulty Selection] Using mode:', mode, '(pendingGameMode was:', state.pendingGameMode, ')');
            // BUG #487 FIX: Track difficulty screen for Back button
            state.gameDifficultyScreen = 'board-difficulty-screen';
            // Check if we're already in a room (post-game mode selection)
            if (state.roomCode && state.socket && state.socket.connected) {
                // Change mode in existing room
                state.socket.emit('change_game_mode', { game_mode: mode });
            } else if (state.socket && state.socket.connected) {
                // Create new room
                createRoom(mode);
            } else {
                // Solo mode
                startSoloGame(mode);
            }
        });
    });

    const backToGamemode2Btn = document.getElementById('back-to-gamemode2');
    if (backToGamemode2Btn) {
        backToGamemode2Btn.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            preventClickAfterTouch();
            showScreen('gamemode-screen');
        }, { passive: false });

        backToGamemode2Btn.addEventListener('click', (e) => {
            if (touchHandled) {
                e.preventDefault();
                return;
            }
            e.preventDefault();
            showScreen('gamemode-screen');
        });
    }

    // Waiting room
    // BUG #279 FIX: Add null checks before addEventListener
    const readyBtn = document.getElementById('ready-btn');
    if (readyBtn) readyBtn.addEventListener('click', markReady);

    const leaveRoomBtn = document.getElementById('leave-room-btn');
    if (leaveRoomBtn) leaveRoomBtn.addEventListener('click', leaveRoom);

    // Game controls
    const hintBtn = document.getElementById('hint-btn');
    if (hintBtn) hintBtn.addEventListener('click', useHint);

    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) clearBtn.addEventListener('click', handleClearButton);

    const setScoreBtn = document.getElementById('set-score-btn');
    if (setScoreBtn) setScoreBtn.addEventListener('click', handleSetScore);

    const newGameBtn = document.getElementById('new-game-btn');
    if (newGameBtn) newGameBtn.addEventListener('click', handleNewGame);

    const muteBtn = document.getElementById('mute-btn');
    if (muteBtn) muteBtn.addEventListener('click', toggleSound);

    const backBtn = document.getElementById('back-btn');
    if (backBtn) backBtn.addEventListener('click', goBack);

    const resultOkBtn = document.getElementById('result-ok-btn');
    if (resultOkBtn) resultOkBtn.addEventListener('click', () => {
        document.getElementById('result-overlay').classList.remove('active');

        // BUG #35, #80 FIXES: Reset gameStarted and validate players array
        state.gameStarted = false;

        // In multiplayer, winner picks next mode, loser waits
        if (state.mode === 'multiplayer') {
            // Check if we won the last game
            const isWinner = state.lastGameWinner === state.displayUsername;

            if (isWinner) {
                // Winner goes to mode selection
                showScreen('gamemode-screen');
            } else {
                // Loser waits for winner to pick
                showWaitingRoom();
            }
        } else {
            // SOLO MODE: Stay in same mode to grind for better score
            // Just restart the same game mode
            restartSameGameMode();
        }
    });

    const shortcutsOkBtn = document.getElementById('shortcuts-ok-btn');
    if (shortcutsOkBtn) shortcutsOkBtn.addEventListener('click', () => {
        const shortcutsOverlay = document.getElementById('shortcuts-overlay');
        if (shortcutsOverlay) shortcutsOverlay.classList.remove('active');
    });

    // Canvas events
    // BUG #281 FIX: Add null check before adding event listeners to canvas
    const canvas = document.getElementById('game-canvas');
    if (!canvas) {
        console.error('Game canvas not found');
        return;
    }

    canvas.addEventListener('click', handleCanvasClick);
    canvas.addEventListener('contextmenu', handleCanvasRightClick);

    // Mouse hover effect
    canvas.addEventListener('mousemove', (e) => {
        const CANVAS_BORDER_WIDTH = 3;
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left - CANVAS_BORDER_WIDTH;
        const y = e.clientY - rect.top - CANVAS_BORDER_WIDTH;

        const col = Math.floor(x / state.cellSize);
        const row = Math.floor(y / state.cellSize);

        // Bounds checking to prevent hover outside board
        if (row < 0 || row >= state.difficulty.rows || col < 0 || col >= state.difficulty.cols) {
            if (state.hoverCell !== null) {
                state.hoverCell = null;
                drawBoard();
            }
            return;
        }

        // Only update if hover cell changed
        if (!state.hoverCell || state.hoverCell.row !== row || state.hoverCell.col !== col) {
            state.hoverCell = { row, col };
            drawBoard();
        }
    });

    canvas.addEventListener('mouseleave', () => {
        state.hoverCell = null;
        drawBoard();
    });

    // RESPONSIVENESS FIX: Add debouncing and throttling for faster, more reliable clicks
    let touchStartTime = 0;
    let touchStartPos = null;
    let lastClickTime = 0;
    let lastClickCell = null;
    const CANVAS_BORDER_WIDTH = 3; // Canvas has 3px border in CSS
    const CLICK_DEBOUNCE_MS = 50; // Prevent double-clicks within 50ms
    const SAME_CELL_DEBOUNCE_MS = 200; // Prevent repeated clicks on same cell

    canvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        e.stopPropagation(); // RESPONSIVENESS FIX: Stop event propagation
        touchStartTime = Date.now();
        // BUG #282 FIX: Validate e.touches exists and has length
        if (!e.touches || e.touches.length === 0) return;
        const touch = e.touches[0];
        const rect = canvas.getBoundingClientRect();

        // Account for border width - subtract border from coordinates
        const x = touch.clientX - rect.left - CANVAS_BORDER_WIDTH;
        const y = touch.clientY - rect.top - CANVAS_BORDER_WIDTH;

        touchStartPos = { x, y };
    }, { passive: false }); // RESPONSIVENESS FIX: passive: false for preventDefault to work

    canvas.addEventListener('touchend', (e) => {
        e.preventDefault();
        e.stopPropagation(); // RESPONSIVENESS FIX: Stop event propagation
        if (!touchStartPos) return;

        const now = Date.now();

        // BUG #78 FIX: Validate touch duration is positive
        const touchDuration = Math.max(0, now - touchStartTime);
        const col = Math.floor(touchStartPos.x / state.cellSize);
        const row = Math.floor(touchStartPos.y / state.cellSize);

        // Bounds checking - ensure we're within the board
        if (row < 0 || row >= state.difficulty.rows || col < 0 || col >= state.difficulty.cols) {
            touchStartPos = null;
            return;
        }

        // RESPONSIVENESS FIX: Debouncing - prevent rapid repeated clicks
        const cellKey = `${row},${col}`;
        const timeSinceLastClick = now - lastClickTime;

        // Global debounce - prevent any clicks too close together
        if (timeSinceLastClick < CLICK_DEBOUNCE_MS) {
            touchStartPos = null;
            return;
        }

        // Same-cell debounce - prevent spamming same cell
        if (lastClickCell === cellKey && timeSinceLastClick < SAME_CELL_DEBOUNCE_MS) {
            touchStartPos = null;
            return;
        }

        lastClickTime = now;
        lastClickCell = cellKey;

        // RESPONSIVENESS FIX: Use requestAnimationFrame for smoother updates
        requestAnimationFrame(() => {
            if (touchDuration > 500) {
                // Long press = flag
                toggleFlag(row, col);
            } else {
                // Quick tap = reveal
                if (!state.gameOver && state.hintCell && state.hintCell.row === row && state.hintCell.col === col) {
                    state.hintCell = null;
                }
                revealCell(row, col);
            }
        });

        touchStartPos = null;
    }, { passive: false }); // RESPONSIVENESS FIX: passive: false for preventDefault to work

    // RESPONSIVENESS FIX: Prevent touchmove from interfering with clicks
    canvas.addEventListener('touchmove', (e) => {
        e.preventDefault();
        e.stopPropagation();
    }, { passive: false });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Global shortcuts
        if (e.key === '?' || (e.shiftKey && e.key === '/')) {
            e.preventDefault();
            const overlay = document.getElementById('shortcuts-overlay');
            overlay.classList.toggle('active');
        }

        if (e.key === 'Escape') {
            document.getElementById('shortcuts-overlay').classList.remove('active');
            document.getElementById('result-overlay').classList.remove('active');
        }

        // Game screen shortcuts
        if (state.currentScreen === 'game-screen') {
            if (e.key === 'h' || e.key === 'H') useHint();
            if (e.key === 'f' || e.key === 'F') {
                if (state.fogOfWar) activateFlare();
            }
        }
    });
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const screen = document.getElementById(screenId);
    if (!screen) {
        console.error(`Screen not found: ${screenId}`);
        return;
    }
    screen.classList.add('active');
    // BUG #485 FIX: Track screen history for Back button
    state.previousScreen = state.currentScreen;
    state.currentScreen = screenId;
}

function startSoloGame(gameMode = 'standard') {
    console.log('[startSoloGame] Starting with gameMode:', gameMode);
    state.mode = 'solo';
    state.gameMode = gameMode;
    console.log('[startSoloGame] state.gameMode set to:', state.gameMode);

    // BUG #231 FIX: Clear pending game mode after starting
    state.pendingGameMode = null;

    // BUG #232 FIX: Russian Roulette should always use medium difficulty (16x16, 40 mines)
    if (gameMode === 'luck') {
        state.difficulty = {
            name: 'Medium',
            rows: 16,
            cols: 16,
            mines: 40
        };
    }

    showScreen('game-screen');
    document.getElementById('username-display').textContent = state.displayUsername;
    document.getElementById('room-display').textContent = '';

    // Reset survival level when starting fresh
    if (gameMode === 'survival') {
        state.survivalLevel = 1;
        state.survivalTotalTiles = 0;
        state.survivalMineCount = state.survivalBaseMines;
    }

    // Set title based on game mode
    if (gameMode === 'luck') {
        document.getElementById('leaderboard-title').textContent = 'Russian Roulette';
    } else if (gameMode === 'timebomb') {
        document.getElementById('leaderboard-title').textContent = `Time Bomb - ${state.timebombDifficulty.toUpperCase()}`;
    } else if (gameMode === 'survival') {
        document.getElementById('leaderboard-title').textContent = `Survival - ${state.difficulty.name} - Level 1`;
    } else if (gameMode === 'fogofwar') {
        document.getElementById('leaderboard-title').textContent = `🌫️ Fog of War - ${state.difficulty.name}`;
    } else if (gameMode === 'speedchess') {
        document.getElementById('leaderboard-title').textContent = `⏱️ Speed Chess - ${state.speedChessDifficulty.toUpperCase()}`;
    } else if (gameMode === 'sabotage') {
        document.getElementById('leaderboard-title').textContent = `⚡ Sabotage - ${state.difficulty.name}`;
    } else {
        document.getElementById('leaderboard-title').textContent = `Standard - ${state.difficulty.name}`;
    }

    resetGame();
    updateTurnIndicator(); // Show turn indicator for special modes
    updateClearButtonText(); // Update button text based on username
    updateSetScoreButton(); // Show/hide Set Score button for icantlose
    updateHintButtonText(); // Update hint/flare button text based on game mode
    loadLeaderboard(); // Load leaderboard for this game mode
}

function showMultiplayerLobby() {
    showScreen('lobby-screen');

    // Disable buttons until connected
    document.getElementById('create-room-btn').disabled = true;
    document.getElementById('join-room-btn').disabled = true;

    connectToServer();
}

function connectToServer() {
    // BUG #36, #44 FIXES: Prevent duplicate connections and clean up old socket
    if (state.socket) {
        if (state.socket.connected) {
            return;
        }
        // Disconnect old socket before creating new one
        state.socket.removeAllListeners(); // Remove all event listeners
        state.socket.disconnect();
        state.socket = null;
    }

    const statusEl = document.getElementById('connection-status');
    if (statusEl) statusEl.textContent = 'Connecting to server...';

    state.socket = io(SERVER_URL);

    state.socket.on('connect', () => {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) statusEl.textContent = '✅ Connected to server';
        const createBtn = document.getElementById('create-room-btn');
        if (createBtn) createBtn.disabled = false;
        const joinBtn = document.getElementById('join-room-btn');
        if (joinBtn) joinBtn.disabled = false;
    });

    state.socket.on('disconnect', () => {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) statusEl.textContent = '❌ Disconnected from server';
    });

    state.socket.on('room_created', (data) => {
        // BUG #67 FIX: Validate room code format
        if (!data || !data.room_code) {
            console.error('Invalid room_created data:', data);
            alert('Failed to create room. Please try again.');
            return;
        }

        const roomCode = String(data.room_code).trim();
        if (roomCode.length !== 6 || !/^\d{6}$/.test(roomCode)) {
            console.error('Invalid room code format:', roomCode);
            alert('Received invalid room code from server.');
            return;
        }

        state.roomCode = roomCode;
        state.gameMode = data.game_mode || 'standard';
        showWaitingRoom();
    });

    state.socket.on('room_joined', (data) => {
        if (!data || !data.room_code) {
            console.error('Invalid room_joined data:', data);
            return;
        }
        state.roomCode = data.room_code;
        state.players = data.players || [];
        showWaitingRoom();
    });

    state.socket.on('player_joined', (data) => {
        state.players = data.players;
        updatePlayersList();
    });

    state.socket.on('player_left', (data) => {
        if (data.players) {
            state.players = data.players;
        }
        updatePlayersList();
    });

    state.socket.on('player_ready_update', (data) => {
        state.players = data.players;
        updatePlayersList();
    });

    state.socket.on('game_start', (data) => {
        state.gameStarted = true;
        state.gameMode = data.game_mode;
        state.currentTurn = data.current_turn;
        startMultiplayerGame(data.board_seed);
    });

    state.socket.on('player_action', (data) => {
        if (!data || !data.action) {
            console.error('Invalid player_action data:', data);
            return;
        }

        // Handle other players' actions
        // Validate row/col bounds before accessing board
        if (data.action === 'reveal' && data.row !== undefined && data.col !== undefined) {
            if (data.row < 0 || data.row >= state.difficulty.rows || data.col < 0 || data.col >= state.difficulty.cols) {
                console.error('player_action out of bounds:', data);
                return;
            }

            // CRITICAL FIX: Only place mines if they haven't been placed yet
            // Previous bug: If slow to click, other player's action would re-place mines
            if (state.firstClick && !state.minesPlaced && state.mode === 'multiplayer') {
                state.firstClick = false;
                state.startTime = Date.now();

                // Start appropriate timer based on game mode
                if (state.gameMode === 'timebomb') {
                    state.timerInterval = setInterval(updateTimeBombTimer, 1000);
                } else if (state.gameMode === 'speedchess') {
                    state.speedChessTimerInterval = setInterval(updateSpeedChessTimer, 1000);
                } else {
                    state.timerInterval = setInterval(updateTimer, 1000);
                }

                // Place mines using the first player's click coordinates for consistent board
                placeMines(data.row, data.col);
            }

            // ONLY sync cell reveals in Russian Roulette (turn-based mode)
            // In Standard Race, each player plays their own board independently
            if (state.gameMode === 'luck') {
                const cell = state.board[data.row][data.col];
                if (cell && !cell.isRevealed) {
                    cell.isRevealed = true;
                    state.totalGameClicks++;
                    drawBoard();
                }
            }
        } else if (data.action === 'flag' && data.row !== undefined && data.col !== undefined) {
            if (data.row < 0 || data.row >= state.difficulty.rows || data.col < 0 || data.col >= state.difficulty.cols) {
                console.error('player_action out of bounds:', data);
                return;
            }

            // ONLY sync flags in Russian Roulette mode
            if (state.gameMode === 'luck') {
                const cell = state.board[data.row][data.col];
                if (cell && !cell.isRevealed) {
                    cell.isFlagged = !cell.isFlagged;
                    drawBoard();
                }
            }
        }
    });

    state.socket.on('turn_changed', (data) => {
        state.currentTurn = data.current_turn;
        updateTurnIndicator();
        drawBoard(); // Redraw to show any visual changes
    });

    state.socket.on('player_finished', (data) => {
        if (!data || !data.players) {
            console.error('Invalid player_finished data:', data);
            return;
        }
        state.players = data.players;
        updateLeaderboard();
    });

    state.socket.on('game_ended', (data) => {
        // BUG #66 FIX: Handle empty results gracefully
        if (!data || !data.results || !Array.isArray(data.results)) {
            console.error('Invalid game_ended data:', data);
            showGameResult(false, 0);
            return;
        }

        if (data.results.length === 0) {
            console.warn('Empty results array in game_ended');
            showGameResult(false, 0);
            return;
        }

        const results = data.results;
        const myResult = results.find(p => p && p.username === state.displayUsername);
        const won = results[0] && results[0].username === state.displayUsername;
        const finalScore = myResult && typeof myResult.score === 'number' ? myResult.score : 0;

        // Track the winner for mode selection
        state.lastGameWinner = results[0] ? results[0].username : null;

        showGameResult(won, finalScore);
    });

    state.socket.on('player_eliminated', (data) => {
        // Don't show result here - wait for game_ended event
        // This just notifies that a player died
        // The game_ended event will show the final results
    });

    state.socket.on('error', (data) => {
        const message = data && data.message ? data.message : 'Unknown error occurred';

        // If on join screen, show error there
        if (state.currentScreen === 'join-screen') {
            const errorEl = document.getElementById('join-error');
            if (errorEl) {
                errorEl.textContent = message;
                errorEl.style.color = '#ff6b6b'; // Red error color
            }
        } else {
            alert('Error: ' + message);
        }
    });
}

function disconnectSocket() {
    // BUG #37, #44 FIXES: Clean up event listeners before disconnect
    if (state.socket) {
        state.socket.removeAllListeners();
        state.socket.disconnect();
        state.socket = null;
    }

    // Reset connection state
    state.roomCode = null;
    state.players = [];
    state.gameStarted = false;
}

function createRoom(gameMode) {
    // BUG #67 FIX: Validate socket and inputs
    if (!state.socket || !state.socket.connected) {
        console.error('Cannot create room: not connected to server');
        alert('Connection lost. Please return to lobby and try again.');
        return;
    }

    if (!state.displayUsername || state.displayUsername.trim() === '') {
        console.error('Cannot create room: invalid username');
        alert('Invalid username. Please refresh and try again.');
        return;
    }

    state.socket.emit('create_room', {
        username: state.displayUsername,
        difficulty: 'Medium',
        max_players: 3,
        game_mode: gameMode
    });
}

function joinRoom() {
    const roomCodeInput = document.getElementById('room-code-input');
    const errorEl = document.getElementById('join-error');

    if (!roomCodeInput || !errorEl) {
        console.error('Join room elements not found');
        return;
    }

    const roomCode = roomCodeInput.value.trim();

    // Validate room code format
    if (!roomCode || roomCode.length !== 6 || !/^\d{6}$/.test(roomCode)) {
        errorEl.textContent = 'Please enter a valid 6-digit room code';
        errorEl.style.color = '#ff6b6b';
        return;
    }

    // Check socket connection
    if (!state.socket || !state.socket.connected) {
        errorEl.textContent = 'Not connected. Go back to lobby to connect.';
        errorEl.style.color = '#ff6b6b';
        console.error('Socket not connected:', { socket: !!state.socket, connected: state.socket?.connected });
        return;
    }

    // Clear any previous errors and show loading
    errorEl.textContent = 'Joining room...';
    errorEl.style.color = '#667eea';

    console.log('Joining room:', roomCode, 'Username:', state.displayUsername);

    // Emit join_room event
    state.socket.emit('join_room', {
        room_code: roomCode,
        username: state.displayUsername
    });

    // Set a timeout in case join fails
    setTimeout(() => {
        if (state.currentScreen === 'join-screen') {
            errorEl.textContent = 'Failed to join. Please check the room code.';
            errorEl.style.color = '#ff6b6b';
        }
    }, 5000);
}

function showWaitingRoom() {
    showScreen('waiting-screen');
    document.getElementById('display-room-code').textContent = state.roomCode;
    updatePlayersList();
}

function updatePlayersList() {
    // BUG #58, #64 FIXES: Validate element and players array
    const listEl = document.getElementById('players-list');
    if (!listEl) {
        console.warn('Players list element not found');
        return;
    }

    listEl.innerHTML = '<h3>Players:</h3>';

    if (!state.players || !Array.isArray(state.players)) {
        console.warn('Players array invalid');
        return;
    }

    state.players.forEach(player => {
        if (!player || !player.username) return; // Skip invalid players

        const div = document.createElement('div');
        div.className = 'player-item';
        div.innerHTML = `
            <span>${player.username}</span>
            <span class="${player.ready ? 'player-ready' : ''}">${player.ready ? '✓ Ready' : 'Waiting...'}</span>
        `;
        listEl.appendChild(div);
    });
}

function markReady() {
    // BUG #38, #66 FIXES: Validate socket connection
    if (!state.socket || !state.socket.connected) {
        console.error('Cannot mark ready: not connected to server');
        alert('Connection lost. Please return to lobby and try again.');
        return;
    }

    state.socket.emit('player_ready', {});
    const readyBtn = document.getElementById('ready-btn');
    if (readyBtn) {
        readyBtn.disabled = true;
        readyBtn.textContent = 'Waiting for others...';
    }
}

function leaveRoom() {
    // BUG #33, #38 FIXES: Reset game state when leaving room
    if (state.socket && state.socket.connected) {
        state.socket.emit('leave_room', {});
    }

    state.roomCode = null;
    state.players = [];
    state.gameStarted = false; // Reset game state
    state.gameOver = false;

    // Clear any active timers
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
    }
    if (state.hintTimeout) {
        clearTimeout(state.hintTimeout);
        state.hintTimeout = null;
    }
    // BUG #237 FIX: Clear game result timeout
    if (state.gameResultTimeout) {
        clearTimeout(state.gameResultTimeout);
        state.gameResultTimeout = null;
    }

    // Re-enable ready button for next room
    const readyBtn = document.getElementById('ready-btn');
    if (readyBtn) {
        readyBtn.disabled = false;
        readyBtn.textContent = 'Ready';
    }

    showScreen('lobby-screen');
}

function startMultiplayerGame(boardSeed) {
    state.mode = 'multiplayer';

    // BUG #232 FIX: Russian Roulette should always use medium difficulty (16x16, 40 mines)
    if (state.gameMode === 'luck') {
        state.difficulty = {
            name: 'Medium',
            rows: 16,
            cols: 16,
            mines: 40
        };
    }

    showScreen('game-screen');
    document.getElementById('username-display').textContent = state.displayUsername;
    document.getElementById('room-display').textContent = `Room: ${state.roomCode}`;

    // Show game mode name in title
    let modeTitle = 'Multiplayer';
    if (state.gameMode === 'luck') modeTitle = 'Russian Roulette';
    else if (state.gameMode === 'timebomb') modeTitle = `Time Bomb - ${state.timebombDifficulty.toUpperCase()}`;
    else if (state.gameMode === 'survival') modeTitle = `Survival - ${state.difficulty.name}`;
    else if (state.gameMode === 'fogofwar') modeTitle = `🌫️ Fog of War - ${state.difficulty.name}`;
    else if (state.gameMode === 'standard') modeTitle = `Standard - ${state.difficulty.name}`;
    document.getElementById('leaderboard-title').textContent = modeTitle;

    // BUG #68, #70, #74 FIXES: Validate board seed and handle edge cases
    const validSeed = (typeof boardSeed === 'number' && boardSeed > 0) ? boardSeed : Math.floor(Math.random() * 1000000) + 1;

    // Seed random for consistent board across players
    state.seededRandom = (() => {
        const m = 2 ** 35 - 31;
        const a = 185852;
        let s = Math.abs(validSeed) % m;
        if (s === 0) s = 1; // Prevent seed of exactly 0
        return () => {
            s = (s * a) % m;
            const result = s / m;
            return result === 0 ? 0.0001 : result; // BUG #74 FIX: Never return exact 0
        };
    })();

    resetGame();
    updateTurnIndicator();
    updateClearButtonText(); // Update button text based on username
    updateSetScoreButton(); // Show/hide Set Score button for icantlose
    updateHintButtonText(); // Update hint/flare button text based on game mode
    loadGlobalLeaderboard(); // Load global leaderboard for this mode
}

function updateTurnIndicator() {
    const indicator = document.getElementById('turn-indicator');

    if (state.gameMode === 'timebomb') {
        // Show countdown timer for Time Bomb mode
        const timeClass = state.timeRemaining <= 10 ? 'time-critical' : '';
        // Format time to 1 decimal place to avoid floating point precision errors
        const displayTime = state.timeRemaining.toFixed(1);
        indicator.textContent = `⏰ TIME: ${displayTime}s`;
        indicator.className = `turn-indicator ${timeClass}`;
        indicator.style.display = 'block';
    } else if (state.gameMode === 'speedchess') {
        // Show chess clock timers for Speed Chess mode
        const playerTime = Math.max(0, state.playerTimeRemaining);
        const opponentTime = Math.max(0, state.opponentTimeRemaining);

        // Format time as MM:SS
        const formatTime = (seconds) => {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        };

        // Highlight whose turn it is
        const playerDisplay = state.isPlayerTurn ? `⏱️ YOU: ${formatTime(playerTime)}` : `You: ${formatTime(playerTime)}`;
        const opponentDisplay = !state.isPlayerTurn ? `⏱️ OPP: ${formatTime(opponentTime)}` : `Opp: ${formatTime(opponentTime)}`;

        // Warning if time is running low (< 10 seconds)
        const timeClass = (state.isPlayerTurn && playerTime <= 10) || (!state.isPlayerTurn && opponentTime <= 10) ? 'time-critical' : '';

        indicator.textContent = `${playerDisplay} | ${opponentDisplay}`;
        indicator.className = `turn-indicator ${timeClass}`;
        indicator.style.display = 'block';
    } else if (state.gameMode === 'survival') {
        // Show survival level
        indicator.textContent = `🏃 Level ${state.survivalLevel} | ${state.survivalMineCount} Mines`;
        indicator.className = 'turn-indicator';
        indicator.style.display = 'block';
    } else if (state.gameMode === 'luck') {
        if (state.mode === 'solo') {
            indicator.textContent = '🎲 Russian Roulette - No Numbers!';
            indicator.className = 'turn-indicator';
            indicator.style.display = 'block';
        } else if (state.currentTurn) {
            if (state.currentTurn === state.displayUsername) {
                indicator.textContent = '🎯 YOUR TURN!';
                indicator.className = 'turn-indicator';
                indicator.style.display = 'block';
            } else {
                indicator.textContent = `⏳ ${state.currentTurn}'s turn`;
                indicator.className = 'turn-indicator';
                indicator.style.display = 'block';
            }
        }
    } else {
        indicator.style.display = 'none';
    }
}

// Game Logic
function initCanvas() {
    // BUG #71, #72 FIXES: Validate canvas and prevent invalid dimensions
    const canvas = document.getElementById('game-canvas');
    if (!canvas) {
        console.error('Canvas element not found');
        return;
    }

    // Calculate responsive cell size based on screen size and board size
    // Validate difficulty values
    const rows = Math.max(1, state.difficulty.rows || 16);
    const cols = Math.max(1, state.difficulty.cols || 16);

    // Detect mobile vs desktop
    const isMobile = window.innerWidth < 768;

    // Adaptive max dimensions based on board size
    let sidebarSpace, maxWidth, maxHeight;

    if (isMobile) {
        // Mobile: sidebar is below board, use full width minus padding
        sidebarSpace = 40; // Just padding
        const availableWidth = window.innerWidth - sidebarSpace;

        if (cols <= 10) {
            maxWidth = Math.min(availableWidth, 450);
            maxHeight = Math.min(window.innerHeight - 200, 450);
        } else if (cols >= 25) {
            // Hard mode on mobile: use full width, smaller cells
            maxWidth = availableWidth;
            maxHeight = Math.min(window.innerHeight - 200, 500);
        } else {
            maxWidth = Math.min(availableWidth, 600);
            maxHeight = Math.min(window.innerHeight - 200, 600);
        }
    } else {
        // Desktop: account for sidebar (250px) + gap (20px) + padding (90px)
        sidebarSpace = 360;
        const availableWidth = window.innerWidth - sidebarSpace;

        if (cols <= 10) {
            maxWidth = Math.min(availableWidth, 500);
            maxHeight = Math.min(window.innerHeight - 250, 500);
        } else if (cols >= 25) {
            maxWidth = Math.min(availableWidth, 900);
            maxHeight = Math.min(window.innerHeight - 250, 600);
        } else {
            maxWidth = Math.min(availableWidth, 700);
            maxHeight = Math.min(window.innerHeight - 250, 700);
        }
    }

    // Calculate cell size that fits screen
    const cellSizeByWidth = Math.floor(maxWidth / cols);
    const cellSizeByHeight = Math.floor(maxHeight / rows);

    // Use the smaller dimension to ensure it fits screen
    // Mobile: allow 12px minimum for hard mode, Desktop: 15px minimum
    const minCellSize = isMobile && cols >= 25 ? 10 : 15;
    const maxCellSize = cols <= 10 ? 50 : 40;

    const calculatedSize = Math.min(cellSizeByWidth, cellSizeByHeight);
    state.cellSize = Math.max(minCellSize, Math.min(calculatedSize, maxCellSize));

    const width = Math.max(100, cols * state.cellSize);
    const height = Math.max(100, rows * state.cellSize);

    canvas.width = width;
    canvas.height = height;

    console.log(`Canvas initialized: ${cols}x${rows}, cellSize: ${state.cellSize}px, canvas: ${width}x${height}px`);
}

function handleNewGame() {
    // New Game button only works in solo mode
    if (state.mode === 'multiplayer') {
        alert('Cannot start new game in multiplayer. Please return to lobby.');
        return;
    }

    // In survival mode, reset to level 1
    if (state.gameMode === 'survival') {
        state.survivalLevel = 1;
        state.survivalTotalTiles = 0;
        state.survivalMineCount = state.survivalBaseMines;
        state.difficulty.mines = state.survivalBaseMines;
        document.getElementById('leaderboard-title').textContent = `Survival - ${state.difficulty.name} - Level 1`;
    }

    resetGame();
}

function resetGame() {
    // BUG #32, #41, #42, #49 FIXES: Comprehensive state reset and cleanup
    state.board = [];
    state.firstClick = true;
    state.minesPlaced = false;
    state.gameOver = false;
    state.gameWon = false;
    state.startTime = null;
    state.elapsedTime = 0;
    state.flagsPlaced = 0;
    state.hintsRemaining = 3;
    state.hintCell = null;
    state.score = 0;
    state.tilesClicked = 0;
    state.totalGameClicks = 0;

    // Clear ALL timers and timeouts
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
    }
    if (state.hintTimeout) {
        clearTimeout(state.hintTimeout);
        state.hintTimeout = null;
    }
    if (state.survivalLevelTimeout) {
        clearTimeout(state.survivalLevelTimeout);
        state.survivalLevelTimeout = null;
    }
    // BUG #237 FIX: Clear game result timeout
    if (state.gameResultTimeout) {
        clearTimeout(state.gameResultTimeout);
        state.gameResultTimeout = null;
    }

    // Initialize Time Bomb mode countdown
    if (state.gameMode === 'timebomb') {
        state.timeRemaining = state.timebombStartTime[state.timebombDifficulty];
        // ICantLose cheat: infinite time (works in all modes)
        if (state.username.toLowerCase() === 'icantlose') {
            state.timeRemaining = 9999;
        }
    }

    // Initialize Survival mode (only set mines, level is handled by handleNewGame or advanceSurvivalLevel)
    if (state.gameMode === 'survival') {
        state.difficulty.mines = state.survivalMineCount;
    }

    // Initialize Fog of War mode
    if (state.gameMode === 'fogofwar') {
        state.fogOfWar = true;
        state.fogRevealedCells = new Map();
        state.lastClickPosition = null;
        state.fogFadeTimers = new Map();
        state.flaresRemaining = 0;
        state.flareActive = false;
        if (state.flareTimeout) {
            clearTimeout(state.flareTimeout);
            state.flareTimeout = null;
        }
    } else {
        // Disable fog for other modes
        state.fogOfWar = false;
        state.fogRevealedCells = new Map();
        state.lastClickPosition = null;
        state.fogFadeTimers = new Map();
        state.flaresRemaining = 0;
        state.flareActive = false;
    }

    // Initialize Sabotage mode (Power-Up System)
    if (state.gameMode === 'sabotage') {
        state.sabotageMode = true;
        state.powerUps = [];
        state.powerUpCells = new Map();
        state.activePowerUp = null;
        state.shieldActive = false;
        state.fortuneActive = false;
        state.fortuneClicksRemaining = 0;
        state.freezeEndTime = null;
        state.ghostModeEndTime = null;
        state.rewindHistory = [];
    } else {
        // Disable sabotage for other modes
        state.sabotageMode = false;
        state.powerUps = [];
        state.powerUpCells = new Map();
        state.activePowerUp = null;
        state.shieldActive = false;
        state.fortuneActive = false;
        state.fortuneClicksRemaining = 0;
    }

    // Initialize Speed Chess mode (Chess Clock Timer)
    if (state.gameMode === 'speedchess') {
        state.speedChessMode = true;
        state.playerTimeRemaining = state.speedChessStartTime[state.speedChessDifficulty];
        state.opponentTimeRemaining = state.speedChessStartTime[state.speedChessDifficulty];
        state.isPlayerTurn = true; // Player always starts

        // Clear any existing timer
        if (state.speedChessTimerInterval) {
            clearInterval(state.speedChessTimerInterval);
            state.speedChessTimerInterval = null;
        }
    } else {
        // Disable speed chess for other modes
        state.speedChessMode = false;
        state.playerTimeRemaining = null;
        state.opponentTimeRemaining = null;
        if (state.speedChessTimerInterval) {
            clearInterval(state.speedChessTimerInterval);
            state.speedChessTimerInterval = null;
        }
    }

    // Initialize board
    for (let row = 0; row < state.difficulty.rows; row++) {
        state.board[row] = [];
        for (let col = 0; col < state.difficulty.cols; col++) {
            state.board[row][col] = {
                isMine: false,
                isRevealed: false,
                isFlagged: false,
                adjacentMines: 0,
                isCheatSurvived: false // CHEAT FIX: Track mines that were clicked but survived via ICantLose cheat
            };
        }
    }

    updateStats();
    initCanvas(); // BUG #482 FIX: Re-initialize canvas when difficulty changes
    drawBoard();
    updateTurnIndicator();
}

function placeMines(excludeRow, excludeCol) {
    // CRITICAL FIX: Prevent double mine placement
    if (state.minesPlaced) {
        console.warn('Attempted to place mines twice! Blocked.');
        return;
    }

    let minesPlaced = 0;
    const excludeCells = new Set();

    // SURVIVAL MODE: After level 20, disable safe first click (pure luck mode)
    const disableSafeFirstClick = state.gameMode === 'survival' && state.survivalLevel > 20;

    if (!disableSafeFirstClick) {
        // Larger exclusion zone (5x5) to ensure first click always flood fills
        // This guarantees the clicked cell and its neighbors have 0 adjacent mines
        for (let dr = -2; dr <= 2; dr++) {
            for (let dc = -2; dc <= 2; dc++) {
                const r = excludeRow + dr;
                const c = excludeCol + dc;
                if (r >= 0 && r < state.difficulty.rows && c >= 0 && c < state.difficulty.cols) {
                    excludeCells.add(`${r},${c}`);
                }
            }
        }
    }

    // Use seeded random for multiplayer, Math.random for solo
    const getRandom = state.mode === 'multiplayer' && state.seededRandom ? state.seededRandom : Math.random;

    // BUG #288 FIX: Prevent infinite loop if not enough cells available
    const totalCells = state.difficulty.rows * state.difficulty.cols;
    const availableCells = totalCells - excludeCells.size;
    if (state.difficulty.mines > availableCells) {
        console.error(`Cannot place ${state.difficulty.mines} mines in ${availableCells} available cells`);
        // Cap mines to available cells
        state.difficulty.mines = Math.max(1, availableCells - 1);
    }

    while (minesPlaced < state.difficulty.mines) {
        const row = Math.floor(getRandom() * state.difficulty.rows);
        const col = Math.floor(getRandom() * state.difficulty.cols);

        if (!state.board[row][col].isMine && !excludeCells.has(`${row},${col}`)) {
            state.board[row][col].isMine = true;
            minesPlaced++;
        }
    }

    // Calculate adjacent mines
    for (let row = 0; row < state.difficulty.rows; row++) {
        for (let col = 0; col < state.difficulty.cols; col++) {
            if (!state.board[row][col].isMine) {
                let count = 0;
                for (let dr = -1; dr <= 1; dr++) {
                    for (let dc = -1; dc <= 1; dc++) {
                        if (dr === 0 && dc === 0) continue;
                        const r = row + dr;
                        const c = col + dc;
                        if (r >= 0 && r < state.difficulty.rows && c >= 0 && c < state.difficulty.cols) {
                            if (state.board[r][c].isMine) count++;
                        }
                    }
                }
                            state.board[row][col].adjacentMines = count;
            }
        }
    }

    // CRITICAL: Mark mines as placed to prevent re-calling
    state.minesPlaced = true;
}

function revealCell(row, col, isUserClick = true) {
    if (row < 0 || row >= state.difficulty.rows || col < 0 || col >= state.difficulty.cols) return;

    const cell = state.board[row][col];
    if (cell.isRevealed || cell.isFlagged) return;

    // Check turn in Luck Mode
    if (state.mode === 'multiplayer' && state.gameMode === 'luck') {
        if (state.currentTurn !== state.displayUsername) {
            return;
        }
        // Immediately clear turn to prevent double-clicking before server response
        state.currentTurn = null;
        updateTurnIndicator();
    }

    // CRITICAL FIX: Place mines BEFORE revealing cell to prevent board corruption
    if (state.firstClick && !state.minesPlaced) {
        state.firstClick = false;
        state.startTime = Date.now();

        // Start appropriate timer based on game mode
        if (state.gameMode === 'timebomb') {
            state.timerInterval = setInterval(updateTimeBombTimer, 1000);
        } else if (state.gameMode === 'speedchess') {
            state.speedChessTimerInterval = setInterval(updateSpeedChessTimer, 1000);
        } else {
            state.timerInterval = setInterval(updateTimer, 1000);
        }
        placeMines(row, col);
    }

    // CRITICAL: Don't reveal until mines are placed
    if (!state.minesPlaced) {
        console.warn('Attempted to reveal before mines placed! Blocked.');
        return;
    }

    // NOW safe to reveal
    cell.isRevealed = true;

    // SABOTAGE: Collect power-up when revealing cell
    const cellKey = `${row},${col}`;
    if (state.sabotageMode && state.powerUpCells.has(cellKey)) {
        const powerUpType = state.powerUpCells.get(cellKey);
        // Power-up already in inventory from drop
        state.powerUpCells.delete(cellKey); // Remove from board
        console.log(`Power-up collected: ${powerUpType}`);
        // TODO: Show collection notification
    }

    // FOG OF WAR: Track last click position for 5x5 visibility window
    if (state.fogOfWar && isUserClick) {
        state.lastClickPosition = { row, col };
    }

    // Time Bomb: Add time bonus ONLY for direct user clicks (not flood fill)
    // Skip time bonus for ICantLose cheat (they have infinite time already)
    if (state.gameMode === 'timebomb' && !cell.isMine && isUserClick && state.username.toLowerCase() !== 'icantlose') {
        state.timeRemaining += state.timebombTimeBonus[state.timebombDifficulty];
        // BUG #486 FIX: Cap time at 999 seconds (unless icantlose cheat)
        if (state.timeRemaining > 999 && state.username.toLowerCase() !== 'icantlose') {
            state.timeRemaining = 999;
        }
        updateTurnIndicator();
    }

    if (cell.isMine) {
        // CRITICAL FIX: ICantLose cheat WITHOUT modifying board state
        // Previous version recalculated adjacent mines, causing numbers to change mid-game!
        if (state.username.toLowerCase() === 'icantlose') {
            // CHEAT FIX: Mark this mine as survived via cheat for purple highlighting
            cell.isCheatSurvived = true;

            // SOLO MODE: Just skip death,  continue playing
            if (state.mode === 'solo') {
                // Don't mark as revealed (mine stays hidden)
                cell.isRevealed = false; // Undo the reveal from line 1096
                updateStats();
                drawBoard();
                return; // Skip death, continue playing
            } else {
                // MULTIPLAYER: Silent god mode - don't trigger elimination
                // Don't emit eliminated, don't show result, just return
                cell.isRevealed = false; // Undo the reveal
                updateStats();
                drawBoard();
                return; // Skip death silently
            }
        }

        state.gameOver = true;
        revealAllMines();
        calculateScore(); // Calculate score based on clicks

        // In multiplayer, notify server that this player died
        if (state.mode === 'multiplayer') {
            state.socket.emit('game_action', { action: 'eliminated', row, col, clicks: state.tilesClicked });
            // Don't show result immediately - wait for server to send game_ended event
        } else {
            // Solo mode - show result immediately
            drawBoard();
            // BUG #237 FIX: Store timeout so it can be cancelled
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

    // Only count safe tiles (not mines) for scoring
    state.tilesClicked++;
    state.totalGameClicks++;

    // FOG OF WAR: Award flare power-up every 20 tiles revealed
    if (state.fogOfWar && state.tilesClicked > 0 && state.tilesClicked % 20 === 0) {
        state.flaresRemaining++;
    }

    // SABOTAGE: 20% chance to drop power-up on tile reveal
    if (state.sabotageMode && isUserClick && state.powerUps.length < state.maxPowerUps) {
        if (Math.random() < 0.2) {
            const powerUpTypes = ['shield', 'scanner', 'fortune', 'rewind', 'sniper'];
            const randomType = powerUpTypes[Math.floor(Math.random() * powerUpTypes.length)];
            state.powerUps.push(randomType);
            state.powerUpCells.set(`${row},${col}`, randomType);
            console.log(`Power-up dropped: ${randomType}`);
        }
    }

    // Send action to server if multiplayer
    if (state.mode === 'multiplayer' && state.gameStarted) {
        state.socket.emit('game_action', { action: 'reveal', row, col, clicks: state.tilesClicked });
    }

    // Update stats display
    updateStats();

    // Flood fill if no adjacent mines (not in Luck Mode)
    if (state.gameMode !== 'luck' && cell.adjacentMines === 0) {
        for (let dr = -1; dr <= 1; dr++) {
            for (let dc = -1; dc <= 1; dc++) {
                if (dr === 0 && dc === 0) continue;
                revealCell(row + dr, col + dc, false); // Pass false = not a user click
            }
        }
    }

    checkWin();

    // Speed Chess: Switch turn after each successful click
    if (state.gameMode === 'speedchess' && isUserClick && !state.gameOver) {
        switchSpeedChessTurn();
    }

    drawBoard();
}

function toggleFlag(row, col) {
    // BUG #55 FIX: Don't allow flagging before mines placed
    if (!state.minesPlaced || !state.board || state.board.length === 0) {
        console.warn('Cannot flag: board not ready');
        return;
    }

    if (row < 0 || row >= state.difficulty.rows || col < 0 || col >= state.difficulty.cols) return;
    if (!state.board[row] || !state.board[row][col]) return;

    const cell = state.board[row][col];
    if (cell.isRevealed) return;

    const wasFlagged = cell.isFlagged;
    cell.isFlagged = !cell.isFlagged;
    state.flagsPlaced += cell.isFlagged ? 1 : -1;

    // Time Bomb: Add +1 second for placing flag (not removing, not for cheat)
    if (state.gameMode === 'timebomb' && cell.isFlagged && !wasFlagged && state.username.toLowerCase() !== 'icantlose') {
        state.timeRemaining += 1;
        // BUG #486 FIX: Cap time at 999 seconds (unless icantlose cheat)
        if (state.timeRemaining > 999) {
            state.timeRemaining = 999;
        }
        updateTurnIndicator();
    }

    if (state.mode === 'multiplayer' && state.gameStarted) {
        state.socket.emit('game_action', { action: 'flag', row, col });
    }

    updateStats();
    drawBoard();
}

function revealAllMines() {
    // BUG #52 FIX: Validate board exists before revealing
    if (!state.board || state.board.length === 0) {
        console.warn('Cannot reveal mines: board not initialized');
        return;
    }

    for (let row = 0; row < state.difficulty.rows && row < state.board.length; row++) {
        if (!state.board[row]) continue;
        for (let col = 0; col < state.difficulty.cols && col < state.board[row].length; col++) {
            const cell = state.board[row][col];
            if (cell && cell.isMine) {
                cell.isRevealed = true;
            }
        }
    }
}

function checkWin() {
    // BUG #53, #76 FIXES: Validate board and prevent empty board win
    if (!state.board || state.board.length === 0 || !state.minesPlaced) {
        return; // Don't check win on uninitialized board
    }

    for (let row = 0; row < state.difficulty.rows && row < state.board.length; row++) {
        if (!state.board[row]) return;
        for (let col = 0; col < state.difficulty.cols && col < state.board[row].length; col++) {
            const cell = state.board[row][col];
            if (!cell) return;
            if (!cell.isMine && !cell.isRevealed) return;
        }
    }

    state.gameWon = true;

    // Survival mode: Advance to next level
    if (state.gameMode === 'survival' && state.mode === 'solo') {
        advanceSurvivalLevel();
        return;
    }

    state.gameOver = true;
    calculateScore();

    if (state.mode === 'multiplayer') {
        state.socket.emit('game_finished', {
            score: state.score,
            time: state.elapsedTime
        });
    } else {
        // BUG #237 FIX: Store timeout so it can be cancelled
        state.gameResultTimeout = setTimeout(() => {
            state.gameResultTimeout = null;
            showGameResult(true, state.score);
        }, 500);
    }
}

function advanceSurvivalLevel() {
    // Update total tiles for final score
    state.survivalTotalTiles += state.tilesClicked;

    // Advance level
    state.survivalLevel++;
    state.survivalMineCount = state.survivalBaseMines + (state.survivalLevel - 1) * state.survivalMineIncrease;

    // BUG #73 FIX: Strict validation that mines don't exceed capacity
    const totalCells = state.difficulty.rows * state.difficulty.cols;
    const maxMines = Math.max(1, totalCells - 20); // Keep at least 20 safe tiles, min 1

    if (state.survivalMineCount > maxMines) {
        console.warn(`Survival mines ${state.survivalMineCount} exceeds max ${maxMines}, capping`);
        state.survivalMineCount = maxMines;
    }

    // Additional safety check
    if (state.survivalMineCount < 1) {
        state.survivalMineCount = 1;
    }

    // Update difficulty
    state.difficulty.mines = state.survivalMineCount;

    // BUG #488 FIX: Add +1 hint per level (max 5)
    if (state.hintsRemaining < 5) {
        state.hintsRemaining++;
    }

    // Update title
    document.getElementById('leaderboard-title').textContent = `Survival - ${state.difficulty.name} - Level ${state.survivalLevel}`;

    // Show level up message briefly
    const indicator = document.getElementById('turn-indicator');
    indicator.textContent = `🎉 LEVEL ${state.survivalLevel}! +1 HINT! 🎉`;
    indicator.className = 'turn-indicator';
    indicator.style.display = 'block';

    // Reset board state for new level
    state.gameWon = false;
    state.firstClick = true;
    state.minesPlaced = false; // CRITICAL: Reset for new level
    state.flagsPlaced = 0;
    state.tilesClicked = 0;

    // Clear and refill board
    for (let row = 0; row < state.difficulty.rows; row++) {
        for (let col = 0; col < state.difficulty.cols; col++) {
            state.board[row][col] = {
                isMine: false,
                isRevealed: false,
                isFlagged: false,
                adjacentMines: 0,
                isCheatSurvived: false // CHEAT FIX: Reset cheat survived status for new level
            };
        }
    }

    drawBoard();
    updateStats();

    // BUG #49 FIX: Track and clear previous timeout
    if (state.survivalLevelTimeout) {
        clearTimeout(state.survivalLevelTimeout);
    }

    // Reset indicator after 2 seconds
    state.survivalLevelTimeout = setTimeout(() => {
        updateTurnIndicator();
        state.survivalLevelTimeout = null;
    }, 2000);
}

function calculateScore() {
    // BUG #489, #491 FIX: Different scoring for different modes
    if (state.mode === 'solo') {
        // Survival mode: score = total tiles across all levels
        if (state.gameMode === 'survival') {
            state.score = state.survivalTotalTiles + state.tilesClicked;
        } else if (state.gameMode === 'standard') {
            // BUG #491 FIX: Standard mode uses milliseconds for unique competitive scores
            const timeMs = Date.now() - state.startTime;
            state.score = Math.max(0, timeMs); // Time in milliseconds
        } else {
            // Other modes (timebomb, russian roulette): score = tiles clicked
            state.score = state.tilesClicked;
        }
    } else {
        // Multiplayer: winner gets total clicks from all players
        if (state.gameWon) {
            state.score = state.totalGameClicks;
        } else {
            state.score = state.tilesClicked;
        }
    }
}

function handleClearButton() {
    // Route to appropriate function based on username
    if (state.username.toLowerCase() === 'icantlose') {
        clearBoard(); // Cheat: instant win
    } else {
        clearAllFlags(); // Normal: clear flags
    }
}

function updateClearButtonText() {
    // Update button text based on username
    const clearBtn = document.getElementById('clear-btn');
    if (!clearBtn) return;

    if (state.username.toLowerCase() === 'icantlose') {
        clearBtn.textContent = 'Clear Board';
        clearBtn.title = 'Cheat: Instantly clear all safe tiles';
    } else {
        clearBtn.textContent = 'Clear Flags';
        clearBtn.title = 'Remove all flags from the board';
    }
}

function updateSetScoreButton() {
    // Show/hide Set Score button for icantlose in survival mode
    const setScoreBtn = document.getElementById('set-score-btn');
    if (!setScoreBtn) return;

    if (state.username.toLowerCase() === 'icantlose' && state.gameMode === 'survival') {
        setScoreBtn.style.display = 'block';
        setScoreBtn.textContent = 'Set Score';
        setScoreBtn.title = 'Cheat: Set your survival level';
    } else {
        setScoreBtn.style.display = 'none';
    }
}

function updateHintButtonText() {
    // Update hint/flare button text based on game mode
    const hintBtn = document.getElementById('hint-btn');
    if (!hintBtn) return;

    if (state.fogOfWar) {
        hintBtn.textContent = 'Flare (F)';
        hintBtn.title = 'Reveal entire board for 2 seconds';
    } else {
        hintBtn.textContent = 'Hint (H)';
        hintBtn.title = 'Highlight a safe cell';
    }
}

function handleSetScore() {
    // CHEAT: Set score for icantlose in survival mode
    if (state.username.toLowerCase() !== 'icantlose') {
        console.warn('Set Score cheat only available for icantlose username');
        return;
    }

    if (state.gameMode !== 'survival') {
        alert('Set Score only works in Survival mode!');
        return;
    }

    const level = prompt('What survival level do you want to set? (e.g., 18)', state.survivalLevel || 1);
    if (level === null) return; // User cancelled

    const parsedLevel = parseInt(level);
    if (isNaN(parsedLevel) || parsedLevel < 1) {
        alert('Please enter a valid level number (1 or higher)');
        return;
    }

    // Set the survival level
    state.survivalLevel = parsedLevel;

    // Calculate score based on level (same formula as normal progression)
    state.score = calculateSurvivalScore(parsedLevel);

    console.log(`🎮 CHEAT ACTIVATED: Set survival level to ${parsedLevel}, score: ${state.score}`);

    // Update display
    updateTurnIndicator();

    alert(`Survival level set to ${parsedLevel}! Your score is now ${state.score}. Play and die to submit this score to leaderboard.`);
}

function calculateSurvivalScore(level) {
    // Calculate cumulative score for reaching this level
    // Each level gives points based on tiles cleared + level bonus
    let totalScore = 0;
    for (let i = 1; i < level; i++) {
        // Approximate score per level (depends on difficulty)
        const tilesPerLevel = (state.difficulty.rows * state.difficulty.cols) - state.difficulty.mines - i; // -i for added mines
        totalScore += tilesPerLevel * 10; // 10 points per tile
        totalScore += i * 100; // Level bonus
    }
    return totalScore;
}

function clearBoard() {
    // CHEAT: Instantly reveal all safe tiles for instant win (icantlose only)
    if (state.username.toLowerCase() !== 'icantlose') {
        console.warn('Clear Board cheat only available for icantlose username');
        return;
    }

    // MULTIPLAYER: Disable cheat in multiplayer to avoid ruining game for others
    if (state.mode === 'multiplayer') {
        alert('Clear Board cheat is disabled in multiplayer mode!');
        return;
    }

    if (state.gameOver || !state.minesPlaced || !state.board || state.board.length === 0) {
        console.warn('Cannot clear board: game not ready or already over');
        return;
    }

    console.log('🎮 CHEAT ACTIVATED: Clearing board...');

    // Reveal all non-mine cells instantly
    let cellsRevealed = 0;
    for (let row = 0; row < state.difficulty.rows; row++) {
        for (let col = 0; col < state.difficulty.cols; col++) {
            const cell = state.board[row][col];
            if (cell && !cell.isMine && !cell.isRevealed) {
                cell.isRevealed = true;
                state.tilesClicked++; // Count towards score
                cellsRevealed++;
            }
        }
    }

    console.log(`✅ Revealed ${cellsRevealed} safe tiles instantly!`);

    // Update display
    updateStats();
    drawBoard();

    // Trigger win check (will advance level in survival or end game)
    checkWin();
}

function clearAllFlags() {
    // Clear all flags from the board
    if (state.gameOver || !state.minesPlaced || !state.board || state.board.length === 0) {
        console.warn('Cannot clear flags: board not ready or game over');
        return;
    }

    // Count how many flags we're clearing
    let flagsCleared = 0;

    for (let row = 0; row < state.difficulty.rows; row++) {
        for (let col = 0; col < state.difficulty.cols; col++) {
            const cell = state.board[row][col];
            if (cell && cell.isFlagged && !cell.isRevealed) {
                cell.isFlagged = false;
                flagsCleared++;
            }
        }
    }

    // Update the flags placed count
    state.flagsPlaced = 0;

    // Update display
    updateStats();
    drawBoard();

    console.log(`Cleared ${flagsCleared} flags`);
}

// FOG OF WAR: Activate flare to reveal entire board for 2 seconds
function activateFlare() {
    if (state.gameOver || !state.startTime || state.flaresRemaining <= 0) return;

    if (!state.minesPlaced || !state.board || state.board.length === 0) {
        console.warn('Cannot use flare: board not initialized');
        return;
    }

    // Activate flare
    state.flareActive = true;
    state.flaresRemaining--;
    updateStats();
    drawBoard();

    // Clear previous flare timeout if exists
    if (state.flareTimeout) {
        clearTimeout(state.flareTimeout);
    }

    // Deactivate flare after 2 seconds
    state.flareTimeout = setTimeout(() => {
        state.flareActive = false;
        state.flareTimeout = null;
        drawBoard();
    }, 2000);
}

function useHint() {
    // FOG OF WAR: Use flare instead of hint
    if (state.fogOfWar) {
        activateFlare();
        return;
    }

    // BUG #31 FIX: Check if mines are placed before accessing board
    // BUG #42 FIX: Clear previous hint timeout before creating new one
    // BUG #54 FIX: Validate board exists
    if (state.gameOver || !state.startTime || state.hintsRemaining <= 0) return;

    if (!state.minesPlaced || !state.board || state.board.length === 0) {
        console.warn('Cannot use hint: board not initialized');
        return;
    }

    // Hints don't work in Luck Mode since numbers are hidden
    if (state.gameMode === 'luck') {
        alert('Hints are not available in Russian Roulette mode!');
        return;
    }

    const safeCells = [];
    for (let row = 0; row < state.difficulty.rows; row++) {
        for (let col = 0; col < state.difficulty.cols; col++) {
            const cell = state.board[row][col];
            if (cell && !cell.isRevealed && !cell.isMine && !cell.isFlagged) {
                safeCells.push({ row, col });
            }
        }
    }

    if (safeCells.length > 0) {
        // Clear previous hint timeout if exists
        if (state.hintTimeout) {
            clearTimeout(state.hintTimeout);
        }

        const hint = safeCells[Math.floor(Math.random() * safeCells.length)];
        state.hintCell = hint;
        state.hintsRemaining--;
        updateStats();
        drawBoard();

        state.hintTimeout = setTimeout(() => {
            state.hintCell = null;
            state.hintTimeout = null;
            drawBoard();
        }, 2000);
    }
}

// RESPONSIVENESS FIX: Shared debouncing variables for both touch and click
let lastDesktopClickTime = 0;
let lastDesktopClickCell = null;
const DESKTOP_CLICK_DEBOUNCE_MS = 50; // Prevent double-clicks within 50ms

function handleCanvasClick(e) {
    if (state.gameOver) return;

    const now = Date.now();

    const CANVAS_BORDER_WIDTH = 3;
    const rect = e.target.getBoundingClientRect();
    const x = e.clientX - rect.left - CANVAS_BORDER_WIDTH;
    const y = e.clientY - rect.top - CANVAS_BORDER_WIDTH;

    const col = Math.floor(x / state.cellSize);
    const row = Math.floor(y / state.cellSize);

    // Bounds checking
    if (row < 0 || row >= state.difficulty.rows || col < 0 || col >= state.difficulty.cols) {
        return;
    }

    // RESPONSIVENESS FIX: Debouncing for desktop clicks - prevent rapid double-clicks
    const cellKey = `${row},${col}`;
    const timeSinceLastClick = now - lastDesktopClickTime;

    // Global debounce - prevent any clicks too close together
    if (timeSinceLastClick < DESKTOP_CLICK_DEBOUNCE_MS) {
        return;
    }

    lastDesktopClickTime = now;
    lastDesktopClickCell = cellKey;

    if (state.hintCell && state.hintCell.row === row && state.hintCell.col === col) {
        state.hintCell = null;
    }

    // RESPONSIVENESS FIX: Use requestAnimationFrame for smoother updates
    requestAnimationFrame(() => {
        revealCell(row, col);
    });
}

function handleCanvasRightClick(e) {
    e.preventDefault();
    if (state.gameOver) return;

    const CANVAS_BORDER_WIDTH = 3;
    const rect = e.target.getBoundingClientRect();
    const x = e.clientX - rect.left - CANVAS_BORDER_WIDTH;
    const y = e.clientY - rect.top - CANVAS_BORDER_WIDTH;

    const col = Math.floor(x / state.cellSize);
    const row = Math.floor(y / state.cellSize);

    // Bounds checking
    if (row < 0 || row >= state.difficulty.rows || col < 0 || col >= state.difficulty.cols) {
        return;
    }

    toggleFlag(row, col);
}

function drawBoard() {
    // BUG #51, #57, #60 FIXES: Validate canvas and board exist
    const canvas = document.getElementById('game-canvas');
    if (!canvas) {
        console.warn('Canvas element not found');
        return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.warn('Canvas context not available');
        return;
    }

    if (!state.board || state.board.length === 0) {
        console.warn('Board not initialized');
        return;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // BUG #57 FIX: Bounds validation in loop
    for (let row = 0; row < state.difficulty.rows && row < state.board.length; row++) {
        if (!state.board[row]) continue;
        for (let col = 0; col < state.difficulty.cols && col < state.board[row].length; col++) {
            const cell = state.board[row][col];
            if (!cell) continue;
            const x = col * state.cellSize;
            const y = row * state.cellSize;

            // Cell background
            if (cell.isRevealed) {
                ctx.fillStyle = '#ecf0f1';
            } else {
                // Hover effect for unrevealed cells
                if (state.hoverCell && state.hoverCell.row === row && state.hoverCell.col === col && !state.gameOver) {
                    ctx.fillStyle = '#7f8c8d';
                } else {
                    ctx.fillStyle = '#95a5a6';
                }
            }
            ctx.fillRect(x, y, state.cellSize - 1, state.cellSize - 1);

            // ICANTLOSE CHEAT: Show ALL mines with purple highlight (wallhack)
            if (state.username && state.username.toLowerCase() === 'icantlose' && cell.isMine && !cell.isRevealed) {
                ctx.fillStyle = '#9b59b6'; // Purple color
                ctx.globalAlpha = 0.5; // Semi-transparent overlay
                ctx.fillRect(x, y, state.cellSize - 1, state.cellSize - 1);
                ctx.globalAlpha = 1.0; // Reset alpha for other drawings
            }

            // CHEAT FIX: Darker purple for mines clicked and survived
            if (cell.isCheatSurvived) {
                ctx.fillStyle = '#7d3c98'; // Darker purple color
                ctx.globalAlpha = 0.8; // More opaque for survived mines
                ctx.fillRect(x, y, state.cellSize - 1, state.cellSize - 1);
                ctx.globalAlpha = 1.0; // Reset alpha for other drawings
            }

            // Hint highlight
            if (state.hintCell && state.hintCell.row === row && state.hintCell.col === col) {
                ctx.strokeStyle = '#f1c40f';
                ctx.lineWidth = 3;
                ctx.strokeRect(x, y, state.cellSize - 1, state.cellSize - 1);
            }

            // Content
            if (cell.isRevealed) {
                if (cell.isMine) {
                    // Draw mine
                    ctx.fillStyle = '#e74c3c';
                    ctx.beginPath();
                    ctx.arc(x + state.cellSize / 2, y + state.cellSize / 2, state.cellSize / 4, 0, Math.PI * 2);
                    ctx.fill();
                } else if (cell.adjacentMines > 0 && state.gameMode !== 'luck') {
                    // Draw number (not in Luck Mode)
                    const colors = ['', '#3498db', '#2ecc71', '#e74c3c', '#9b59b6', '#f39c12', '#1abc9c', '#34495e', '#2c3e50'];
                    ctx.fillStyle = colors[cell.adjacentMines];
                    ctx.font = 'bold ' + (state.cellSize / 2) + 'px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(cell.adjacentMines, x + state.cellSize / 2, y + state.cellSize / 2);
                }
            } else if (cell.isFlagged) {
                // Draw flag
                ctx.fillStyle = '#2ecc71';
                ctx.beginPath();
                ctx.moveTo(x + state.cellSize / 4, y + state.cellSize / 4);
                ctx.lineTo(x + state.cellSize / 4, y + state.cellSize * 3 / 4);
                ctx.lineTo(x + state.cellSize * 3 / 4, y + state.cellSize / 2);
                ctx.closePath();
                ctx.fill();
            }

            // SABOTAGE: Draw power-up icon on unrevealed cells
            const cellKey = `${row},${col}`;
            if (state.sabotageMode && !cell.isRevealed && state.powerUpCells.has(cellKey)) {
                const powerUpType = state.powerUpCells.get(cellKey);
                const powerUpEmojis = {
                    shield: '🛡️',
                    scanner: '🔍',
                    fortune: '🍀',
                    rewind: '⏪',
                    sniper: '🎯'
                };

                // Draw power-up emoji
                ctx.font = (state.cellSize / 2) + 'px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(powerUpEmojis[powerUpType] || '✨', x + state.cellSize / 2, y + state.cellSize / 2);
            }
        }
    }

    // FOG OF WAR: Render fog overlay
    if (state.fogOfWar && !state.gameOver) {
        renderFogOfWar(ctx);
    }
}

// FOG OF WAR: Render fog overlay on cells not in visibility window
function renderFogOfWar(ctx) {
    const currentTime = Date.now();

    for (let row = 0; row < state.difficulty.rows && row < state.board.length; row++) {
        if (!state.board[row]) continue;
        for (let col = 0; col < state.difficulty.cols && col < state.board[row].length; col++) {
            const cell = state.board[row][col];
            if (!cell) continue;

            const cellKey = `${row},${col}`;
            const x = col * state.cellSize;
            const y = row * state.cellSize;

            // If flare is active, reveal everything
            if (state.flareActive) {
                continue; // Skip fog rendering for all cells
            }

            // Check if cell is in 5x5 visibility window around last click
            let inVisibilityWindow = false;
            if (state.lastClickPosition) {
                const rowDist = Math.abs(row - state.lastClickPosition.row);
                const colDist = Math.abs(col - state.lastClickPosition.col);
                inVisibilityWindow = rowDist <= 2 && colDist <= 2; // 5x5 = 2 cells in each direction
            }

            // Check if cell was previously revealed and still in fade timer
            const revealTime = state.fogRevealedCells.get(cellKey);
            let fadeAlpha = 0;

            if (revealTime) {
                const timeSinceReveal = currentTime - revealTime;
                const fadeStartTime = 3000; // Start fading after 3 seconds

                if (timeSinceReveal < fadeStartTime) {
                    // Still visible, no fog
                    fadeAlpha = 0;
                } else {
                    // Should be fogged over
                    fadeAlpha = 1.0;
                    // Remove from revealed cells map (memory faded)
                    state.fogRevealedCells.delete(cellKey);
                }
            } else {
                // Never revealed or already faded
                fadeAlpha = 1.0;
            }

            // If in current visibility window, no fog
            if (inVisibilityWindow) {
                fadeAlpha = 0;
                // Update revealed time
                state.fogRevealedCells.set(cellKey, currentTime);
            }

            // Draw fog overlay
            if (fadeAlpha > 0) {
                ctx.fillStyle = `rgba(44, 62, 80, ${fadeAlpha * 0.9})`; // Dark fog
                ctx.fillRect(x, y, state.cellSize - 1, state.cellSize - 1);
            }
        }
    }
}

function updateStats() {
    // Show flags placed vs total mines - more intuitive than "mines left"
    document.getElementById('mines-left').textContent = `🚩 Flags: ${state.flagsPlaced}/${state.difficulty.mines}`;

    // Fog of War: Show flares instead of hints
    if (state.fogOfWar) {
        document.getElementById('hints-left').textContent = `✨ Flares: ${state.flaresRemaining}`;
    } else {
        document.getElementById('hints-left').textContent = `💡 Hints: ${state.hintsRemaining}`;
    }

    // Show time and clicks
    if (state.startTime && !state.gameOver) {
        const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        document.getElementById('timer').textContent = `⏱️ ${timeStr} | Clicks: ${state.tilesClicked}`;
    } else {
        document.getElementById('timer').textContent = `Clicks: ${state.tilesClicked}`;
    }

    // Update power-up bar in Sabotage mode
    if (state.sabotageMode) {
        updatePowerUpBar();
    }
}

function updatePowerUpBar() {
    const powerUpBar = document.getElementById('powerup-bar');
    const powerUpSlots = document.getElementById('powerup-slots');

    if (!powerUpBar || !powerUpSlots) return;

    // Show/hide power-up bar
    if (state.sabotageMode && state.startTime) {
        powerUpBar.style.display = 'block';
    } else {
        powerUpBar.style.display = 'none';
        return;
    }

    // Clear existing slots
    powerUpSlots.innerHTML = '';

    // Power-up info
    const powerUpInfo = {
        shield: { emoji: '🛡️', name: 'Shield', desc: 'Survive 1 mine' },
        scanner: { emoji: '🔍', name: 'Scanner', desc: 'Reveal 3x3 area' },
        fortune: { emoji: '🍀', name: 'Fortune', desc: 'Next 3 clicks safe' },
        rewind: { emoji: '⏪', name: 'Rewind', desc: 'Undo 5 moves' },
        sniper: { emoji: '🎯', name: 'Sniper', desc: 'Remove 3 mines' }
    };

    // Create slots for up to 5 power-ups
    for (let i = 0; i < state.maxPowerUps; i++) {
        const slot = document.createElement('div');
        slot.className = 'powerup-slot';
        slot.dataset.index = i;

        if (i < state.powerUps.length) {
            const powerUpType = state.powerUps[i];
            const info = powerUpInfo[powerUpType];

            slot.classList.add('has-powerup');
            slot.innerHTML = `
                <div class="powerup-icon">${info.emoji}</div>
                <div class="powerup-name">${info.name}</div>
                <div class="powerup-key">${i + 1}</div>
            `;
            slot.title = `${info.name}: ${info.desc}`;

            // Click to activate
            slot.addEventListener('click', () => activatePowerUp(i));
        } else {
            slot.innerHTML = `
                <div class="powerup-empty">${i + 1}</div>
            `;
        }

        powerUpSlots.appendChild(slot);
    }
}

function updateTimer() {
    if (state.startTime && !state.gameOver) {
        state.elapsedTime = Math.floor((Date.now() - state.startTime) / 1000);
        updateStats(); // Update display with current time
    }
}

function updateTimeBombTimer() {
    if (state.gameOver) return;

    // Countdown timer for Time Bomb mode - use Math.max to prevent negative values
    state.timeRemaining = Math.max(0, state.timeRemaining - 1);
    updateTurnIndicator();

    // Time's up! Game over
    if (state.timeRemaining <= 0) {
        state.gameOver = true;
        state.timeRemaining = 0;
        revealAllMines();
        calculateScore();
        drawBoard();
        // BUG #237 FIX: Store timeout so it can be cancelled
        state.gameResultTimeout = setTimeout(() => {
            state.gameResultTimeout = null;
            showGameResult(false, state.score, 'Time\'s Up!');
        }, 500);
    }
}

function updateSpeedChessTimer() {
    if (state.gameOver) return;

    // Countdown timer for Speed Chess mode - only count down the active player's timer
    if (state.isPlayerTurn) {
        state.playerTimeRemaining = Math.max(0, state.playerTimeRemaining - 1);
    } else {
        state.opponentTimeRemaining = Math.max(0, state.opponentTimeRemaining - 1);
    }

    updateTurnIndicator();

    // Check if time's up for either player
    if (state.playerTimeRemaining <= 0) {
        state.gameOver = true;
        state.playerTimeRemaining = 0;
        revealAllMines();
        calculateScore();
        drawBoard();

        // Stop the timer
        if (state.speedChessTimerInterval) {
            clearInterval(state.speedChessTimerInterval);
            state.speedChessTimerInterval = null;
        }

        state.gameResultTimeout = setTimeout(() => {
            state.gameResultTimeout = null;
            showGameResult(false, state.score, 'Time\'s Up! You Ran Out of Time!');
        }, 500);
    }
}

function pauseSpeedChessTimer() {
    if (state.speedChessTimerInterval) {
        clearInterval(state.speedChessTimerInterval);
        state.speedChessTimerInterval = null;
    }
}

function resumeSpeedChessTimer() {
    if (!state.speedChessTimerInterval && state.startTime && !state.gameOver) {
        state.speedChessTimerInterval = setInterval(updateSpeedChessTimer, 1000);
    }
}

function switchSpeedChessTurn() {
    // Pause timer
    pauseSpeedChessTimer();

    // Switch turn
    state.isPlayerTurn = !state.isPlayerTurn;

    // Resume timer with new turn
    resumeSpeedChessTimer();
    updateTurnIndicator();
}

function updateLeaderboard() {
    const leaderboard = document.getElementById('leaderboard');
    leaderboard.innerHTML = '';

    // BUG #285 FIX: Validate state.players is iterable before spreading
    if (!state.players || !Array.isArray(state.players)) {
        console.warn('Players array invalid in updateLeaderboard');
        return;
    }

    const sortedPlayers = [...state.players].sort((a, b) => b.score - a.score);

    sortedPlayers.forEach((player, index) => {
        const div = document.createElement('div');
        div.className = 'leaderboard-entry';
        div.innerHTML = `
            <span>${index + 1}. ${player.username}</span>
            <span>${player.finished ? player.score + ' pts' : 'Playing...'}</span>
        `;
        leaderboard.appendChild(div);
    });
}

function showGameResult(won, score, customMessage) {
    const overlay = document.getElementById('result-overlay');
    const resultText = document.getElementById('result-text');
    const resultEmoji = document.getElementById('result-emoji');
    const resultScore = document.getElementById('result-score');

    if (customMessage) {
        resultText.textContent = customMessage;
        resultEmoji.textContent = '💀';
    } else if (won) {
        resultText.textContent = 'YOU WIN!';
        resultEmoji.textContent = '🎉';
    } else {
        resultText.textContent = 'Game Over';
        resultEmoji.textContent = '💥';
    }

    // Show detailed game stats
    const minutes = Math.floor(state.elapsedTime / 60);
    const seconds = state.elapsedTime % 60;
    const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;

    // BUG #75 FIX: Prevent division by zero in accuracy
    const totalSafeTiles = Math.max(1, (state.difficulty.rows * state.difficulty.cols) - state.difficulty.mines);
    const accuracy = (state.tilesClicked > 0 && totalSafeTiles > 0) ?
        Math.round((state.tilesClicked / totalSafeTiles) * 100) : 0;

    resultScore.innerHTML = `
        <div style="margin: 20px 0; line-height: 1.8;">
            <div><strong>Tiles Clicked:</strong> ${score}</div>
            <div><strong>Time Taken:</strong> ${timeStr}</div>
            <div><strong>Flags Placed:</strong> ${state.flagsPlaced}/${state.difficulty.mines}</div>
            <div><strong>Hints Used:</strong> ${3 - state.hintsRemaining}/3</div>
            ${won ? `<div><strong>Completion:</strong> ${accuracy}%</div>` : ''}
        </div>
    `;

    overlay.classList.add('active');

    // Submit score to leaderboard for both solo and multiplayer games
    if (score > 0) {
        submitScoreToBackend(won, score);
    }
}

// Leaderboard Backend Integration
async function submitScoreToBackend(won, score) {
    try {
        // BUG #492 FIX: Include board difficulty in game mode for standard/survival/fogofwar/sabotage modes
        let difficulty = state.gameMode;
        if ((state.gameMode === 'standard' || state.gameMode === 'survival' || state.gameMode === 'fogofwar' || state.gameMode === 'sabotage') && state.boardDifficulty) {
            difficulty = `${state.gameMode}-${state.boardDifficulty}`; // e.g., "standard-easy", "fogofwar-hard"
        }

        const response = await fetch(`${SERVER_URL}/api/leaderboard/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: state.displayUsername, // BUG #493 FIX: Use display name for leaderboard (includes funny names for ICantLose)
                score: score,
                time: state.elapsedTime,
                difficulty: difficulty, // Use combined game mode + board difficulty
                hints_used: 3 - state.hintsRemaining,
                won: won
            })
        });
        await response.json();
    } catch (error) {
        console.error('Failed to submit score to leaderboard:', error);
    }
}

async function loadLeaderboard() {
    if (state.mode === 'solo') {
        loadGlobalLeaderboard();
    }
}

async function loadGlobalLeaderboard() {
    try {
        // BUG #492 FIX: Include board difficulty in game mode for standard/survival/fogofwar/sabotage modes
        let difficulty = state.gameMode;
        if ((state.gameMode === 'standard' || state.gameMode === 'survival' || state.gameMode === 'fogofwar' || state.gameMode === 'sabotage') && state.boardDifficulty) {
            difficulty = `${state.gameMode}-${state.boardDifficulty}`; // e.g., "standard-easy", "fogofwar-hard"
        }

        const response = await fetch(
            `${SERVER_URL}/api/leaderboard/global?difficulty=${difficulty}`
        );
        const data = await response.json();
        displayGlobalLeaderboard(data.leaderboard);
    } catch (error) {
        console.error('Failed to load global leaderboard:', error);
    }
}

function displayGlobalLeaderboard(scores) {
    const leaderboard = document.getElementById('leaderboard');
    leaderboard.innerHTML = '';

    // BUG #286 FIX: Validate scores parameter is not null/undefined
    if (!scores || !Array.isArray(scores)) {
        leaderboard.innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">Unable to load leaderboard.</p>';
        return;
    }

    if (scores.length === 0) {
        leaderboard.innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">No scores yet. Be the first!</p>';
        return;
    }

    scores.slice(0, 5).forEach((entry, index) => {
        const div = document.createElement('div');
        div.className = 'leaderboard-entry';

        // Add medal for top 3
        let medal = '';
        if (index === 0) medal = '🥇 ';
        else if (index === 1) medal = '🥈 ';
        else if (index === 2) medal = '🥉 ';

        // BUG #489, #491 FIX: Show time for standard/fogofwar modes, tiles for others
        let scoreDisplay;
        if (state.gameMode === 'standard' || state.gameMode === 'fogofwar') {
            // BUG #491 FIX: Convert milliseconds to seconds with 3 decimal places for competitive precision
            const seconds = (entry.score / 1000).toFixed(3);
            scoreDisplay = `${seconds}s`;
        } else {
            scoreDisplay = `${entry.score} tiles`;
        }

        div.innerHTML = `
            <span>${medal}${index + 1}. ${entry.username}</span>
            <span>${scoreDisplay}</span>
        `;
        leaderboard.appendChild(div);
    });
}

// Sound System
function toggleSound() {
    state.soundEnabled = !state.soundEnabled;
    const btn = document.getElementById('mute-btn');
    btn.textContent = state.soundEnabled ? '🔊 Sound' : '🔇 Muted';

    // BUG #284 FIX: Wrap localStorage in try-catch (fails in private browsing mode)
    try {
        localStorage.setItem('soundEnabled', state.soundEnabled);
    } catch (e) {
        console.error('Failed to save sound preference:', e);
    }
}

function playSound(soundType) {
    if (!state.soundEnabled) return;

    // Foundation for future sound implementation
    // soundType can be: 'click', 'flag', 'mine', 'win', 'hint'
    // For now, this is a placeholder that does nothing
    // Future: Add Web Audio API or HTML5 Audio elements

    // Example for future implementation:
    // const audio = new Audio(`/sounds/${soundType}.mp3`);
    // audio.volume = 0.3;
    // audio.play().catch(e => console.log('Audio play failed:', e));
}

// Load sound preference from localStorage on init
document.addEventListener('DOMContentLoaded', () => {
    // BUG #284 FIX: Wrap localStorage in try-catch (fails in private browsing mode)
    try {
        const savedSound = localStorage.getItem('soundEnabled');
        if (savedSound !== null) {
            state.soundEnabled = savedSound === 'true';
            const btn = document.getElementById('mute-btn');
            if (btn) btn.textContent = state.soundEnabled ? '🔊 Sound' : '🔇 Muted';
        }
    } catch (e) {
        console.error('Failed to load sound preference:', e);
    }
});

function goBack() {
    // BUG #485 FIX: Smart back button navigation
    // Confirm before going back if game is in progress
    if (state.startTime && !state.gameOver) {
        if (!confirm('Are you sure you want to go back? Your progress will be lost.')) {
            return;
        }
    }

    // Clear ALL timers
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
    }
    if (state.hintTimeout) {
        clearTimeout(state.hintTimeout);
        state.hintTimeout = null;
    }
    if (state.survivalLevelTimeout) {
        clearTimeout(state.survivalLevelTimeout);
        state.survivalLevelTimeout = null;
    }
    if (state.gameResultTimeout) {
        clearTimeout(state.gameResultTimeout);
        state.gameResultTimeout = null;
    }

    // Reset game state
    state.gameStarted = false;
    state.gameOver = true; // Prevent any further game actions

    // Smart navigation based on mode
    if (state.mode === 'multiplayer') {
        leaveRoom();
        showScreen('lobby-screen');
    } else {
        // BUG #487 FIX: Go back to difficulty selection screen, not mode selection
        // Solo mode: return to the difficulty screen they came from
        const targetScreen = state.gameDifficultyScreen || 'mode-screen';
        showScreen(targetScreen);
    }
}

function restartSameGameMode() {
    // Restart the same game mode for grinding better scores
    // This keeps players in the same mode instead of kicking them back to mode selection
    console.log('[restartSameGameMode] Current gameMode:', state.gameMode);

    if (state.gameMode === 'standard') {
        // Restart standard mode with same difficulty
        startSoloGame('standard');
    } else if (state.gameMode === 'luck') {
        // Restart Russian Roulette
        startSoloGame('luck');
    } else if (state.gameMode === 'timebomb') {
        // Restart Time Bomb with same difficulty
        startSoloGame('timebomb');
    } else if (state.gameMode === 'survival') {
        // Restart Survival from level 1
        startSoloGame('survival');
    } else if (state.gameMode === 'fogofwar') {
        // Restart Fog of War with same difficulty
        startSoloGame('fogofwar');
    } else if (state.gameMode === 'speedchess') {
        // Restart Speed Chess with same difficulty
        startSoloGame('speedchess');
    } else if (state.gameMode === 'sabotage') {
        // Restart Sabotage with same difficulty
        startSoloGame('sabotage');
    } else {
        // Fallback: go to mode selection
        showScreen('mode-screen');
    }
}

// Auth system removed - no profiles needed anymore!
