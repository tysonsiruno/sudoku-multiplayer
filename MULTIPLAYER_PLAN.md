# Minesweeper Multiplayer Implementation Plan

## Overview
This document outlines the plan to add multiplayer functionality to the Minesweeper game.

## Architecture

### Backend (Python + Flask + SocketIO)
```
minesweeper-server/
├── app.py                 # Main Flask app
├── game_room.py           # Room management
├── database.py            # Database models
├── requirements.txt       # Python dependencies
├── Procfile              # For Render deployment
└── render.yaml           # Render config
```

### Database Schema
```sql
-- Global Leaderboard
CREATE TABLE leaderboard (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(50),
    score INTEGER,
    time INTEGER,
    difficulty VARCHAR(10),
    hints_used INTEGER,
    date TIMESTAMP,
    room_id VARCHAR(50) NULL
);

-- Rooms
CREATE TABLE rooms (
    id VARCHAR(50) PRIMARY KEY,
    host_id VARCHAR(50),
    difficulty VARCHAR(10),
    max_players INTEGER,
    created_at TIMESTAMP,
    status VARCHAR(20)
);

-- Players
CREATE TABLE players (
    id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50),
    room_id VARCHAR(50),
    score INTEGER,
    connected BOOLEAN
);
```

## Features to Implement

### Phase 1: Backend Setup
1. ✓ Flask server with Socket.IO
2. ✓ Room creation/joining system
3. ✓ Player management
4. ✓ Global leaderboard API

### Phase 2: Client Updates
1. Add network layer to pygame client
2. Room browser UI
3. Multiplayer lobby
4. Real-time game state sync
5. Spectator mode

### Phase 3: Game Modes
1. **Race Mode**: Same board, fastest wins
2. **Cooperative Mode**: Shared board, work together
3. **Battle Mode**: Separate boards, head-to-head

### Phase 4: Deployment
1. GitHub repository setup
2. Render deployment
3. Environment variables
4. Database hosting (Render PostgreSQL)

## API Endpoints

### REST API
```
POST   /api/rooms/create       # Create new room
GET    /api/rooms/list         # List active rooms
POST   /api/rooms/join         # Join room
GET    /api/leaderboard/global # Get global leaderboard
GET    /api/leaderboard/room   # Get room leaderboard
POST   /api/players/register   # Register player
```

### WebSocket Events
```
// Client -> Server
connect                    # Connect to server
create_room               # Create game room
join_room                 # Join room
leave_room                # Leave room
start_game                # Start game
cell_reveal               # Reveal cell action
cell_flag                 # Flag cell action

// Server -> Client
room_created              # Room created successfully
room_joined               # Joined room
player_joined             # Another player joined
player_left               # Player left
game_started              # Game started
game_state_update         # Board state update
game_ended                # Game finished
leaderboard_update        # Leaderboard changed
```

## Tech Stack

### Backend
- **Flask**: Web framework
- **Flask-SocketIO**: WebSocket support
- **SQLAlchemy**: ORM for database
- **PostgreSQL**: Database
- **Redis**: Session/cache storage

### Client
- **Pygame**: Game rendering (current)
- **Requests**: HTTP requests
- **python-socketio**: WebSocket client

### Deployment
- **GitHub**: Code repository
- **Render**: Backend hosting (Free tier available)
- **Render PostgreSQL**: Database hosting

## Getting Started with Multiplayer

### 1. Install Dependencies
```bash
pip install flask flask-socketio flask-sqlalchemy psycopg2-binary python-socketio requests eventlet
```

### 2. Set Up GitHub Repository
```bash
cd ~/minesweeper-python
git init
git add .
git commit -m "Initial commit - Minesweeper Enhanced"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/minesweeper-multiplayer.git
git push -u origin main
```

### 3. Deploy to Render
1. Go to https://render.com
2. Connect GitHub repository
3. Create new Web Service
4. Add PostgreSQL database
5. Set environment variables
6. Deploy!

## Scoring System (Multiplayer)

### Race Mode Points
```python
base_score = (1000 - time * 2 + hints_used * 100) * difficulty_multiplier
placement_bonus = [500, 300, 100, 50][placement - 1]  # 1st, 2nd, 3rd, 4th
final_score = base_score + placement_bonus
```

### Cooperative Mode Points
```python
team_score = sum(player_scores) / num_players
time_bonus = max(0, 500 - total_time)
final_score = team_score + time_bonus
```

### Battle Mode Points
```python
wins_bonus = wins * 1000
mines_found_bonus = mines_found * 50
accuracy = correct_flags / total_flags
accuracy_bonus = accuracy * 200
final_score = base_score + wins_bonus + mines_found_bonus + accuracy_bonus
```

## Next Steps

1. Review this plan
2. Decide which features to prioritize
3. Set up backend infrastructure
4. Implement client-server communication
5. Test locally
6. Deploy to production

## Estimated Timeline

- **Backend Setup**: 2-3 days
- **Client Integration**: 2-3 days
- **Testing**: 1-2 days
- **Deployment**: 1 day
- **Total**: ~1-2 weeks

## Notes

- Start with simple race mode for MVP
- Global leaderboard can work without rooms
- Consider rate limiting for API
- Add authentication later (OAuth)
- Mobile version possible with Pygame SDL2
