# Deployment Guide: Minesweeper Multiplayer

## Overview
This guide explains how to deploy the Minesweeper multiplayer server to Render.

## Prerequisites
- GitHub account with repository access
- Render account (free tier available at https://render.com)

## Step 1: Prepare Repository
The code is already on GitHub at: https://github.com/tysonsiruno/minesweeper-multiplayer

## Step 2: Deploy to Render

### Option A: Using Render Dashboard

1. **Go to Render Dashboard**
   - Visit https://dashboard.render.com
   - Click "New +" → "Web Service"

2. **Connect GitHub Repository**
   - Select "Connect account" if not already connected
   - Choose repository: `tysonsiruno/minesweeper-multiplayer`

3. **Configure Web Service**
   - **Name**: `minesweeper-server` (or your preferred name)
   - **Region**: Oregon (or closest to you)
   - **Branch**: `main`
   - **Root Directory**: `server`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --worker-class eventlet -w 1 app:app`

4. **Environment Variables**
   - Click "Advanced" → "Add Environment Variable"
   - Add: `SECRET_KEY` → (Render can auto-generate this)
   - Add: `PORT` → `10000` (Render default)

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Your server URL will be: `https://minesweeper-server.onrender.com` (or similar)

### Option B: Using render.yaml (Automatic)

1. Render will detect the `server/render.yaml` file automatically
2. Just click "Apply" when prompted

## Step 3: Update Client Configuration

After deployment, update the client to use your server:

```bash
cd ~/minesweeper-python
export SERVER_URL=https://your-server-name.onrender.com
python3 minesweeper_multiplayer.py
```

Or set it permanently in the code at line 47:
```python
SERVER_URL = "https://your-server-name.onrender.com"
```

## Step 4: Test Multiplayer

1. **Start the client** (on your local machine):
   ```bash
   python3 minesweeper_multiplayer.py
   ```

2. **Create a room**:
   - Enter username
   - Choose "Multiplayer"
   - Click "Create Room"
   - Share the room code with friends

3. **Join from another machine**:
   - Enter username
   - Choose "Multiplayer"
   - Click "Join Room"
   - Enter the room code

## Server Endpoints

Once deployed, your server will have these endpoints:

- `GET /health` - Health check
- `GET /api/rooms/list` - List active rooms
- `GET /api/leaderboard/global?difficulty=Medium` - Get leaderboard
- `POST /api/leaderboard/submit` - Submit score

WebSocket events are handled at the root URL.

## Database (Optional - Future Enhancement)

Currently using in-memory storage. To add PostgreSQL:

1. In Render dashboard, add PostgreSQL database
2. Update `server/app.py` to use the database URL
3. Implement SQLAlchemy models from `MULTIPLAYER_PLAN.md`

## Troubleshooting

### Server won't start
- Check logs in Render dashboard
- Verify all dependencies in `requirements.txt`
- Ensure `PORT` environment variable is set

### Can't connect from client
- Verify server URL in client code
- Check firewall/network settings
- Ensure server is running (green status in Render)

### Room creation fails
- Check server logs for errors
- Verify WebSocket connection is established
- Try refreshing and reconnecting

## Monitoring

- **Render Dashboard**: View logs, metrics, and status
- **Health Check**: Visit `https://your-server.onrender.com/health`
- **Active Rooms**: Visit `https://your-server.onrender.com/api/rooms/list`

## Free Tier Limitations

Render free tier:
- Server spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds
- 750 hours/month of runtime
- Sufficient for development and testing

## Upgrading

To update the server:
1. Push changes to GitHub
2. Render will auto-deploy (if enabled)
3. Or manually trigger deploy from Render dashboard

---

**Server Repository**: https://github.com/tysonsiruno/minesweeper-multiplayer
**Render**: https://render.com
**Support**: Check MULTIPLAYER_PLAN.md for architecture details
