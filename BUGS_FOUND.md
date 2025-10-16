# Comprehensive Bug List - Minesweeper Multiplayer
## Total Bugs Found: 230+

---

## SERVER BUGS (app.py) - Bugs #81-#120

### Critical Security Issues
- **Bug #81**: Line 162 - Logging sensitive error details to console could expose information
- **Bug #82**: Line 184 - Password verification failure doesn't have rate limiting per IP for brute force
- **Bug #83**: Line 196 - Account lock timing is predictable (always 15 minutes), making timing attacks possible
- **Bug #110**: Line 288 - No CSRF protection on state-changing endpoints
- **Bug #111**: Line 42 - SocketIO CORS allows "*" which is insecure for production
- **Bug #112**: Line 49 - Rate limiter storage_uri falls back to 'memory://' which doesn't work across multiple processes

### Error Handling & Logging
- **Bug #84**: Line 235 - print(f'Login session creation error: {e}') - Exposing database errors
- **Bug #85**: Line 332 - token = auth_header.split(' ')[1] - No bounds check, could crash if malformed
- **Bug #87**: Line 355 - Same issue with refresh token parsing - no bounds check
- **Bug #88**: Line 387 - print(f'Token refresh error: {e}') - Error exposure
- **Bug #89**: Line 514 - print(f'Leaderboard submission error: {e}') - Error exposure

### Session Management
- **Bug #86**: Line 335 - Logout deletes ALL sessions for user, not just current session (forces logout from all devices)
- **Bug #107**: Line 157 - SecurityAuditLog.log_action could fail silently if database commit fails
- **Bug #108**: Line 191 - SecurityAuditLog.log_action called with user.id even if user is None
- **Bug #109**: Line 218 - Session expires_at calculation but no timezone handling consistency

### Socket/Room Management
- **Bug #90**: Line 528 - handle_disconnect doesn't validate if player_sessions[request.sid] exists before accessing
- **Bug #91**: Line 537 - room["players"] list comprehension doesn't handle malformed player objects
- **Bug #92**: Line 555 - handle_create_room doesn't validate data is a dict
- **Bug #93**: Line 591 - board_seed uses secrets.randbelow(1000000) which could return 0 (valid but unusual)
- **Bug #94**: Line 620 - room_code validation allows leading zeros which could cause confusion
- **Bug #95**: Line 684 - handle_leave_room accesses session.get("room_code") but session could be None
- **Bug #96**: Line 722 - handle_change_game_mode doesn't verify session exists
- **Bug #97**: Line 740 - New board_seed generated but old seed not validated

### Game Logic
- **Bug #98**: Line 826-836 - row/col validation but no validation that difficulty matches expected board dimensions
- **Bug #99**: Line 846 - data.get("clicks", 0) not validated for reasonable range
- **Bug #100**: Line 899-906 - Turn rotation logic has infinite loop potential if all players eliminated (while loop with attempts counter)
- **Bug #101**: Line 931 - Same turn rotation infinite loop risk
- **Bug #102**: Line 960-967 - Score and time validation but no check for obviously impossible values (0 score with 1000 time?)
- **Bug #103**: Line 989 - Sorting players by score but no tiebreaker for equal scores

### Data Validation & API
- **Bug #104**: Line 29-31 - DATABASE_URL postgres:// replacement could fail if string appears multiple times
- **Bug #105**: Line 76 - game_rooms and player_sessions are in-memory dicts with no size limit (memory leak potential)
- **Bug #106**: Line 80-84 - generate_room_code has no maximum attempts, could infinite loop if all codes taken
- **Bug #113**: Line 426-438 - list_rooms endpoint has no pagination, could return massive array
- **Bug #114**: Line 446 - GameHistory query has no user_id filter, exposes all users' games
- **Bug #115**: Line 452 - .limit(50) hardcoded with no offset for pagination
- **Bug #116**: Line 475 - username sanitization allows empty string after sanitization
- **Bug #117**: Line 490 - Max score of 10000 seems arbitrary and could be legitimately exceeded
- **Bug #118**: Line 503 - tiles_clicked = score is incorrect assumption (these should be separate)
- **Bug #119**: Line 540-544 - emit() to room doesn't check if room still exists
- **Bug #120**: Line 583-590 - Player object structure not validated before insertion

---

## DATABASE BUGS (models.py) - Bugs #121-#130

### Data Integrity
- **Bug #121**: Line 55 - Division by zero protection exists but could still fail if total_games_played is None
- **Bug #122**: Line 36-38 - Cascading deletes could orphan GameHistory records if not properly handled
- **Bug #123**: Line 189 - SecurityAuditLog.log_action commits immediately which could cause issues in transactions
- **Bug #124**: Line 22 - created_at uses datetime.utcnow but Python 3.12+ deprecates this in favor of datetime.now(timezone.utc)
- **Bug #125**: Line 23 - updated_at onupdate doesn't trigger if no columns actually changed
- **Bug #126**: Line 31 - failed_login_attempts has no maximum value constraint
- **Bug #127**: Line 134 - user_id has ondelete='SET NULL' but username is denormalized - inconsistency
- **Bug #128**: Line 174 - details column is JSON type which isn't supported in SQLite (compatibility issue)
- **Bug #129**: Line 126 - is_expired() doesn't handle None expires_at
- **Bug #130**: Line 125-126 - is_expired() uses datetime.utcnow() but should use same timezone as expires_at

---

## AUTH UTILITIES BUGS (auth.py) - Bugs #131-#140

### Security
- **Bug #131**: Line 15 - JWT_SECRET default is hardcoded, dangerous if deployed without changing
- **Bug #132**: Line 18-20 - Token expiration times use timedelta but no validation of clock skew
- **Bug #133**: Line 24 - PASSWORD_REGEX doesn't check for special characters (weak password policy)
- **Bug #134**: Line 47 - bcrypt.gensalt rounds=12 is reasonable but not configurable
- **Bug #135**: Line 63-65 - verify_password broad exception catching hides real errors
- **Bug #136**: Line 160 - sanitize_input removes null bytes but doesn't handle other control characters
- **Bug #137**: Line 191-193 - generate_access_token uses datetime.utcnow() (deprecated)
- **Bug #138**: Line 216 - generate_refresh_token uses datetime.utcnow() (deprecated)
- **Bug #139**: Line 280 - Authorization header split doesn't handle edge case of multiple spaces
- **Bug #140**: Line 294 - User.query.filter_by(id=...) doesn't handle invalid id types

---

## EMAIL SERVICE BUGS (email_service.py) - Bugs #141-#146

### Email Handling
- **Bug #141**: Line 29-32 - send_email returns False if no API key but prints sensitive email info
- **Bug #142**: Line 45 - Response status codes 200,201,202 checked but 204 also indicates success
- **Bug #143**: Line 48 - Exception catching is too broad, hides specific errors
- **Bug #144**: Line 64 - verify_link doesn't URL-encode the token (could break with special chars)
- **Bug #145**: Line 149 - reset_link doesn't URL-encode the token
- **Bug #146**: Line 395 - DOMAIN hardcoded link doesn't use HTTPS check

---

## CLIENT AUTH BUGS (auth.js) - Bugs #147-#172

### Token Management
- **Bug #147**: Line 27 - accessToken retrieved from localStorage but no expiration check before use
- **Bug #148**: Line 35 - verifyCurrentUser() called without await, promise chain could fail silently
- **Bug #149**: Line 48 - token from URL params not validated or sanitized before use
- **Bug #150**: Line 79 - localStorage.removeItem('user_data') but user_data is never validated on load
- **Bug #151**: Line 94 - Authorization header constructed without validating accessToken is string
- **Bug #152**: Line 116 - response.json() called without checking response.ok first
- **Bug #153**: Line 147 - localStorage.setItem with JSON.stringify but no error handling if JSON fails

### Validation
- **Bug #154**: Line 183 - Email validation only checks for '@' which is insufficient
- **Bug #155**: Line 208 - AbortController timeout of 10 seconds hardcoded
- **Bug #156**: Line 217 - clearTimeout called but timeoutId could be undefined in error paths
- **Bug #157**: Line 238 - passwordConfirmEl value cleared but field might not exist
- **Bug #158**: Line 264 - Exponential backoff uses (retryCount + 1) * 1000 which is linear, not exponential
- **Bug #159**: Line 325 - response.json() called without checking if response is JSON

### UI & UX
- **Bug #160**: Line 410 - Math.floor(Math.random() * 10000) could generate duplicate guest IDs
- **Bug #161**: Line 439 - token passed directly in query string without URL encoding
- **Bug #162**: Line 450 - window.location.href = '/' doesn't preserve any state
- **Bug #163**: Line 472 - AuthState.user.email accessed without null check
- **Bug #164**: Line 488 - alert() used instead of proper UI messages
- **Bug #165**: Line 513 - Email validation duplicates validation from register function
- **Bug #166**: Line 609 - window.resetToken is global variable (namespace pollution)
- **Bug #167**: Line 725 - document.getElementById returns null if element doesn't exist, no null check
- **Bug #168**: Line 727 - login-remember checkbox .checked accessed without null check
- **Bug #169**: Line 793 - display-name-input value accessed without null check
- **Bug #170**: Line 818 - localStorage.setItem could fail if storage is full
- **Bug #171**: Line 832 - document.querySelectorAll returns NodeList, forEach might not work in old browsers
- **Bug #172**: Line 834 - screen could be null if screenId is invalid

---

## HTML/UI BUGS (index.html) - Bugs #173-#180

### Resources & Accessibility
- **Bug #173**: Line 7 - styles.css referenced but file not checked if exists
- **Bug #174**: Line 20 - autofocus attribute on login input could interfere with screen readers
- **Bug #175**: Line 55 - pattern="[a-zA-Z0-9_]+" doesn't match server-side USERNAME_REGEX exactly
- **Bug #176**: Line 67 - Password requirements in small text don't match actual regex (no special char requirement shown)
- **Bug #177**: Line 276 - room-code-input has maxlength="6" but no pattern for digits only
- **Bug #178**: Line 440 - Socket.IO CDN version 4.5.4 hardcoded (could be outdated)
- **Bug #179**: Line 441-442 - Scripts loaded without integrity/crossorigin attributes
- **Bug #180**: No viewport meta tag height restriction for mobile keyboards

---

## ADDITIONAL GAME.JS BUGS - Bugs #181-#230

### Timer & Timing Issues
- **Bug #181**: Line 73 - touchHandled setTimeout 500ms hardcoded, could interfere with rapid taps
- **Bug #182**: Line 371-372 - Mouse position converted to cell coords without checking canvas offset
- **Bug #183**: Line 421-422 - Touch position calculation doesn't account for scrolling
- **Bug #185**: Line 707/709 - setInterval called but previous interval might not be cleared in edge cases
- **Bug #186**: Line 967 - Random seed could theoretically collide in multiplayer (no uniqueness guarantee)
- **Bug #189**: Line 1223/1225 - setInterval called without checking if timer already running
- **Bug #190**: Line 1281/1283 - setTimeout 500ms delays before showing result, could cause confusion if player clicks
- **Bug #195**: Line 1464 - survivalLevelTimeout set but not validated for existing timeout
- **Bug #196**: Line 1529 - hintTimeout set but could overwrite existing timeout
- **Bug #197**: Line 1668-1669 - Time calculation doesn't handle negative elapsed time
- **Bug #198**: Line 1680 - elapsedTime calculation truncates milliseconds
- **Bug #199**: Line 1738 - Minutes calculation for display doesn't handle hours

### Socket Communication
- **Bug #191**: Line 1275 - socket.emit 'eliminated' action doesn't validate socket is connected
- **Bug #192**: Line 1297 - socket.emit 'reveal' doesn't validate row/col are integers
- **Bug #193**: Line 1341 - socket.emit 'flag' doesn't validate coordinates
- **Bug #194**: Line 1393 - socket.emit 'game_finished' doesn't validate score/time values
- **Bug #200**: Line 186/214/267/290 - Multiple change_game_mode emits with no rate limiting

### Event Listeners & Memory
- **Bug #201**: Line 55 - DOMContentLoaded listener but code could run before DOM ready
- **Bug #202**: Line 60 - window.addEventListener('resize') but no throttling/debouncing
- **Bug #203**: Line 79-88 - Both touchend and click listeners on soloBtn (double-trigger possible)
- **Bug #204**: Line 105-114 - Same double listener issue on multiplayerBtn
- **Bug #205**: Line 131-139 - Same double listener issue on backToMainBtn
- **Bug #206**: Line 154 - getElementById without null check before addEventListener
- **Bug #207**: Line 155 - getElementById without null check
- **Bug #208**: Line 156 - getElementById without null check
- **Bug #209**: Line 162-163 - Multiple event listeners on same elements
- **Bug #210**: Line 166 - getElementById without null check
- **Bug #211**: Line 170-196 - forEach on mode select buttons has touchend + click (double trigger)
- **Bug #212**: Line 227-239 - backToLobby2Btn has both touchend and click
- **Bug #213**: Line 256-277 - difficulty buttons have both touchend and click
- **Bug #214**: Line 303-311 - backToGamemodeBtn has both touchend and click
- **Bug #215**: Line 323-330 - Multiple getElementById calls without null checks
- **Bug #216**: Line 331 - result-ok-btn click handler but no validation if overlay is shown
- **Bug #217**: Line 355 - shortcuts-ok-btn click handler without validation
- **Bug #218**: Line 361-362 - Canvas event listeners never removed (memory leak if canvas replaced)
- **Bug #219**: Line 365 - mousemove listener with no throttling (performance issue)
- **Bug #220**: Line 390 - mouseleave listener but mouseenter not paired
- **Bug #221**: Line 400 - touchstart listener sets touchStartPos but doesn't validate bounds
- **Bug #222**: Line 415 - touchend listener calculates duration but doesn't validate touchStartPos exists
- **Bug #223**: Line 448 - keydown listener at document level, never removed
- **Bug #224**: Line 1857 - Another DOMContentLoaded listener (duplicate with line 55)
- **Bug #225**: Event listeners accumulate if game reinitializes without cleanup
- **Bug #226**: No passive:true on touch/scroll listeners (performance)
- **Bug #227**: contextmenu handler calls e.preventDefault() but doesn't check if flagging is allowed
- **Bug #228**: Mouse and touch events could conflict if device supports both
- **Bug #229**: No debounce on resize handler causes excessive redraws
- **Bug #230**: Canvas mousemove constantly updates hoverCell even when not needed

### Game Logic & State
- **Bug #184**: Line 549 - toxicNames array randomly selected without validation
- **Bug #187**: Line 1042-1043 - cellSize calculation could result in 0 if window is too small (already partially fixed)
- **Bug #188**: Line 1160-1165 - Mine placement uses Math.random for solo but seededRandom for multiplayer, inconsistency

---

## SUMMARY
- **Server-side bugs**: 66 (#81-#146)
- **Client auth bugs**: 26 (#147-#172)
- **HTML bugs**: 8 (#173-#180)
- **Additional game.js bugs**: 50 (#181-#230)
- **Previously fixed**: 80 (#1-#80)

**GRAND TOTAL: 230 BUGS IDENTIFIED**

---

## PRIORITY LEVELS

### P0 - Critical (Security & Data Loss)
Bugs #81-83, #110-112, #131-133, #141

### P1 - High (Crashes & Major Functionality)
Bugs #85-95, #105-106, #147-153, #191-194, #218, #225

### P2 - Medium (UX & Performance)
Bugs #96-104, #154-172, #181-190, #195-230

### P3 - Low (Code Quality & Maintenance)
Bugs #113-130, #173-180
