# 🎮 Minesweeper Enhanced

A modern, feature-rich Minesweeper game built with Python and Pygame featuring scoring, leaderboards, hints, and multiplayer-ready architecture.

## ✨ Current Features

### 🎯 Core Game
- **Three Difficulty Modes**: Easy (9×9, 10 mines), Medium (16×16, 40 mines), Hard (16×30, 99 mines)
- **Modern Dark Theme UI**: Clean, professional design
- **Smooth Gameplay**: Hover effects, click feedback
- **Classic Minesweeper Rules**: Left-click reveal, right-click flag

### 🔍 Hint System
- **3 Hints Per Game**: Strategic help when stuck
- **Visual Highlighting**: Yellow border shows safe cells
- **Easy Access**: Click "Hint" button or press 'H'

### 🏆 Scoring & Leaderboards
- **Smart Scoring**:
  - Time-based: Faster completion = more points
  - Difficulty multiplier: Easy ×1, Medium ×2, Hard ×3
  - Hint penalty/bonus: Fewer hints used = more points
  - Formula: `(1000 - time×2 + hints×100) × difficulty_multiplier`

- **Persistent Leaderboards**:
  - Top 10 scores per difficulty
  - Saved locally in `leaderboard.json`
  - Shows score, time, and date

### 🎨 UI Features
- **Bomb Counter**: Shows remaining unflagged mines
- **Real-time Timer**: Tracks your speed
- **Hint Counter**: Shows remaining hints
- **Mode Selection**: Quick difficulty switching
- **New Game Button**: Instant restart
- **Win/Loss Messages**: Clear feedback

## 🎮 How to Play

### Running the Game
```bash
cd ~/minesweeper-python
python3 minesweeper_enhanced.py
```

### Controls
| Action | Input |
|--------|-------|
| Reveal cell | Left Click |
| Flag/unflag mine | Right Click |
| Use hint | 'H' key or Hint button |
| New game | 'F2' key or New button |
| Change difficulty | Click Easy/Medium/Hard |
| Quit | ESC key or close window |

### Gameplay Tips
1. **Start corners**: Generally safer opening moves
2. **Use numbers**: Each number shows adjacent mines
3. **Flag wisely**: Right-click to mark suspected mines
4. **Hints are limited**: Use strategically (only 3 per game)
5. **Speed matters**: Faster completion = higher score

## 📊 Scoring System

### Points Calculation
```python
time_score = 1000 - (seconds × 2)       # Fast = more points
hint_bonus = hints_remaining × 100       # Unused hints = bonus
base_score = time_score + hint_bonus
final_score = base_score × difficulty_multiplier
```

### Difficulty Multipliers
- **Easy**: ×1.0
- **Medium**: ×2.0
- **Hard**: ×3.0

### Example Scores
- Easy in 30s, 3 hints left: `(1000 - 60 + 300) × 1 = 1240 points`
- Medium in 60s, 1 hint left: `(1000 - 120 + 100) × 2 = 1960 points`
- Hard in 120s, 0 hints left: `(1000 - 240 + 0) × 3 = 2280 points`

## 🚀 What's Next: Multiplayer

### Planned Multiplayer Features
- **Room System**: Create/join game rooms
- **Multiple Game Modes**:
  - 🏁 **Race Mode**: Same board, fastest wins
  - 🤝 **Co-op Mode**: Shared board, team score
  - ⚔️ **Battle Mode**: Separate boards, head-to-head

- **Global Leaderboard**: Compete worldwide
- **Room Leaderboards**: Compare with roommates
- **Real-time Sync**: See other players' moves
- **Spectator Mode**: Watch ongoing games

### Multiplayer Tech Stack
- **Backend**: Flask + Socket.IO
- **Database**: PostgreSQL (via Render)
- **Hosting**: Render (backend) + GitHub (code)
- **Client**: Enhanced Pygame with networking

See `MULTIPLAYER_PLAN.md` for detailed implementation plan.

## 📁 Project Structure

```
minesweeper-python/
├── minesweeper_enhanced.py    # Main enhanced game (CURRENT)
├── main.py                     # Original game
├── field.py                    # Original game logic
├── draw.py                     # Original rendering
├── leaderboard.json            # Saved scores
├── MULTIPLAYER_PLAN.md         # Multiplayer roadmap
├── README_ENHANCED.md          # This file
└── assets/                     # Game sprites
```

## 🔧 Requirements

```bash
pip install pygame
```

That's it! Pygame is the only dependency for the current version.

## 🎯 Roadmap

### ✅ Phase 1: Core Features (COMPLETE)
- [x] Three difficulty modes
- [x] Hint system with visual feedback
- [x] Scoring algorithm
- [x] Local leaderboards
- [x] Modern UI with buttons
- [x] Persistent storage

### 🚧 Phase 2: Multiplayer (PLANNED)
- [ ] Flask backend server
- [ ] WebSocket communication
- [ ] Room creation/management
- [ ] Player synchronization
- [ ] Global leaderboard API
- [ ] Race mode implementation

### 📅 Phase 3: Polish & Deploy (FUTURE)
- [ ] Deploy to Render
- [ ] Add authentication
- [ ] Mobile-friendly controls
- [ ] Sound effects
- [ ] Animations
- [ ] Themes/skins

## 🐛 Known Issues & Limitations

- Leaderboard stored locally (multiplayer will use database)
- No authentication yet (coming with multiplayer)
- No sound effects
- No animations on reveal
- Desktop only (mobile version planned)

## 🤝 Contributing

This is a learning project! Feel free to:
- Report bugs
- Suggest features
- Fork and improve
- Add game modes
- Create themes

## 📝 License

Free to use, modify, and distribute. Have fun!

---

**Enjoy the game!** Try to beat the leaderboards and prepare for multiplayer competition! 🎮🏆
