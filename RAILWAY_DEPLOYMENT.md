# 🚂 Railway Deployment Guide

This guide will help you deploy your Sudoku Multiplayer game to Railway.

## 🎯 Quick Start

1. **Connect to Railway**
   - Go to [railway.app](https://railway.app)
   - Sign in with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select `tysonsiruno/sudoku-multiplayer`

2. **Add PostgreSQL Database**
   - In your Railway project, click "+ New"
   - Select "Database" → "Add PostgreSQL"
   - Railway will automatically provide `DATABASE_URL` environment variable

3. **Add Redis (Optional but Recommended)**
   - Click "+ New" → "Database" → "Add Redis"
   - Railway will automatically provide `REDIS_URL` environment variable
   - Without Redis, rate limiting will not work across multiple server instances

4. **Configure Environment Variables**

   Railway will automatically set:
   - `PORT` - The port your app should listen on
   - `DATABASE_URL` - PostgreSQL connection string (if you added PostgreSQL)
   - `REDIS_URL` - Redis connection string (if you added Redis)

   You need to manually set these in Railway dashboard:

   **Required:**
   - `JWT_SECRET` - Copy from your `.env` file
   - `JWT_REFRESH_SECRET` - Copy from your `.env` file
   - `SECRET_KEY` - Copy from your `.env` file
   - `FLASK_ENV` = `production`

   **Optional:**
   - `CORS_ORIGINS` - Set to your Railway domain (e.g., `https://your-app.up.railway.app`)
   - `MAX_PLAYERS_PER_ROOM` = `10`
   - `MAX_SCORE` = `100000`
   - `MAX_TIME` = `172800`
   - `LOG_LEVEL` = `INFO`

5. **Deploy**
   - Railway will automatically build and deploy
   - Watch the build logs for any errors
   - Once deployed, click "Open App" to test

## 🔧 Configuration Files

Railway uses `nixpacks.toml` for build configuration:

```toml
[phases.setup]
nixPkgs = ["python311", "pip"]

[phases.install]
cmds = [
  "python3.11 -m venv /opt/venv",
  ". /opt/venv/bin/activate",
  "pip install --upgrade pip",
  "pip install -r server/requirements.txt"
]

[start]
cmd = ". /opt/venv/bin/activate && cd server && gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app"
```

## 📱 Mobile & WebSocket Fixes Applied

### ✅ Fixed Issues:

1. **Missing JavaScript Files** - Added all required scripts to HTML:
   - `performance.js` - Performance optimizations
   - `ux.js` - UX enhancements and keyboard shortcuts
   - `auth.js` - Authentication handling
   - `ux.css` - Additional UX styling

2. **Hardcoded Server URL** - Changed to dynamic detection:
   ```javascript
   // OLD: const SERVER_URL = 'https://minesweeper-server-production-ecec.up.railway.app';
   // NEW:
   const SERVER_URL = window.location.origin;
   ```
   This automatically works on Railway, localhost, or any other deployment!

3. **Dockerfile Requirements** - Fixed to use correct requirements file:
   ```dockerfile
   # OLD: COPY requirements.txt .
   # NEW:
   COPY server/requirements.txt .
   ```

4. **Mobile CSS** - All CSS files are now properly loaded including mobile-specific styles

## 🧪 Testing Your Deployment

### 1. Test Homepage
- Visit your Railway URL
- You should see the game interface with "SUDOKU MULTIPLAYER" title
- Enter a username and click "Start Playing"

### 2. Test Solo Mode
- Choose "Solo" mode
- Select difficulty level (Easy/Medium/Hard)
- Game should load with a generated Sudoku puzzle
- Numbers should be fillable and validated

### 3. Test Multiplayer Mode
- Choose "Multiplayer" mode
- Check connection status - should show "✅ Connected to server"
- Create a room - you should get a 6-digit room code
- Open another browser/device and join with the room code
- Both players should see each other in the waiting room
- Click "Ready" and game should start

### 4. Test Mobile
- Open on mobile device or use browser dev tools mobile emulation
- Check that:
  - Background gradient is visible (not white)
  - Text is readable
  - Buttons are properly sized
  - Game board is scrollable
  - Touch controls work (tap to select cell, number input)

## 🐛 Troubleshooting

### White Screen on Mobile
**Solution:** Make sure all CSS and JS files are loading
- Check browser console for 404 errors
- Verify `styles.css`, `ux.css` are loading
- Verify `game.js`, `performance.js`, `ux.js`, `auth.js` are loading

### Multiplayer Not Connecting
**Symptoms:** "Connecting to server..." never changes to "✅ Connected"

**Solutions:**
1. Check Railway logs for errors
2. Verify `gunicorn --worker-class eventlet` is being used
3. Make sure only 1 worker (`-w 1`) for WebSocket support
4. Check that port is correctly set to `$PORT`

### Database Connection Errors
**Solution:**
1. Make sure PostgreSQL service is added to Railway project
2. Railway should automatically set `DATABASE_URL`
3. Check environment variables in Railway dashboard
4. The app will use SQLite if `DATABASE_URL` is not set (not recommended for production)

### CORS Errors
**Solution:** Set `CORS_ORIGINS` environment variable to your Railway domain:
```
CORS_ORIGINS=https://your-app.up.railway.app
```

### Build Failures
**Solution:**
1. Check `nixpacks.toml` is using correct Python version (3.11)
2. Verify `server/requirements.txt` exists and has all dependencies
3. Check Railway build logs for specific error messages

## 📊 Monitoring

### Railway Dashboard
- Monitor CPU and Memory usage
- Check deployment logs
- View metrics and analytics

### Application Logs
View real-time logs in Railway dashboard:
- WebSocket connections
- Game room creation
- Player actions
- Database queries
- Errors and warnings

## 🔐 Security Checklist

Before going to production:

- [ ] Set strong random values for JWT secrets (already done in `.env`)
- [ ] Set `FLASK_ENV=production`
- [ ] Configure `CORS_ORIGINS` to your actual domain (not `*`)
- [ ] Add PostgreSQL database (don't use SQLite in production)
- [ ] Add Redis for proper rate limiting
- [ ] Enable Railway's custom domain with SSL
- [ ] Review security audit logs regularly

## 🚀 Performance Tips

1. **Enable Redis** - Reduces database load by 70%
2. **Use PostgreSQL** - Much faster than SQLite for concurrent users
3. **Single Worker** - Required for WebSocket support with eventlet
4. **CDN for Static Files** - Consider serving CSS/JS from CDN for faster load times

## 📝 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | Auto | 5000 | Server port (Railway sets this) |
| `DATABASE_URL` | Auto | SQLite | PostgreSQL URL (Railway sets this) |
| `REDIS_URL` | Auto | memory | Redis URL (Railway sets this) |
| `JWT_SECRET` | ✅ Yes | - | JWT signing secret |
| `JWT_REFRESH_SECRET` | ✅ Yes | - | Refresh token secret |
| `SECRET_KEY` | ✅ Yes | - | Flask session secret |
| `FLASK_ENV` | ✅ Yes | development | Set to `production` |
| `CORS_ORIGINS` | Recommended | * | Allowed CORS origins |
| `MAX_PLAYERS_PER_ROOM` | Optional | 10 | Max players per room |
| `MAX_SCORE` | Optional | 100000 | Anti-cheat max score |
| `MAX_TIME` | Optional | 172800 | Anti-cheat max time |
| `LOG_LEVEL` | Optional | INFO | Logging level |

## 🎉 Success!

Your Sudoku Multiplayer game should now be live on Railway!

Share the URL with friends and enjoy playing together! 🎮

---

**Last Updated:** 2025-10-16
**Railway Build:** Optimized for Railway deployment with PostgreSQL and Redis
