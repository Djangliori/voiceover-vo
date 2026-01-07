# Celery Worker Setup on Railway

## Current Status

A `celery-worker` service has been created in your Railway project but needs to be connected to the GitHub repository.

**Service ID**: `9037b92e-21a8-40cd-8e33-92161c46f74c`
**Project**: voyoutube
**Dashboard**: https://railway.app/project/bd7d8d73-c874-4145-a4ef-a27bf5f3efe3

---

## Quick Setup Steps

### 1. Open Railway Dashboard
Go to: https://railway.app/project/bd7d8d73-c874-4145-a4ef-a27bf5f3efe3

### 2. Find the "celery-worker" service
You should see it in your project alongside:
- georgian-voiceover-app (main web service)
- Redis
- Postgres

### 3. Click on the celery-worker service

### 4. Connect to GitHub Repository
- Click on "Settings" tab
- Under "Source" section, click "Connect Repo"
- Select repository: **lashajincharadze/georgian-voiceover-app**
- Branch: **main**
- Root Directory: **(leave empty)**

### 5. Configure the Start Command
- Still in "Settings" tab
- Under "Deploy" section
- Find "Start Command"
- Enter: `celery -A celery_app worker --loglevel=info --concurrency=2`

**OR** you can use the Procfile:
- Set "Procfile Path" to: `Procfile.worker`
- Railway will automatically use the worker command from that file

### 6. Verify Environment Variables
- Go to "Variables" tab
- Ensure these variables are present (should be shared automatically):
  - `REDIS_URL` ← **Most important!**
  - `OPENAI_API_KEY`
  - `ELEVEN_LABS_API_KEY`
  - `DATABASE_URL`
  - All other environment variables from main service

### 7. Deploy
- Click "Deploy" button
- Or just save the settings, Railway will auto-deploy

### 8. Monitor the Logs
After deployment starts, check the logs. You should see:

```
 -------------- celery@railway v5.x.x (...)
---- **** -----
--- * ***  * -- Darwin-25.1.0-arm64 2025-11-19 XX:XX:XX
-- * - **** ---
- ** ---------- [config]
- ** ---------- .> app:         celery_app:0x...
- ** ---------- .> transport:   redis://...
- ** ---------- .> results:     disabled://
- *** --- * --- .> concurrency: 2 (prefork)
-- ******* ---- .> task events: OFF
--- ***** -----
 -------------- [queues]
                .> celery           exchange=celery(direct) key=celery

[tasks]
  . src.tasks.process_video_task

[2025-11-19 XX:XX:XX,XXX: INFO/MainProcess] Connected to redis://...
[2025-11-19 XX:XX:XX,XXX: INFO/MainProcess] mingle: searching for neighbors
[2025-11-19 XX:XX:XX,XXX: INFO/MainProcess] mingle: all alone
[2025-11-19 XX:XX:XX,XXX: INFO/MainProcess] celery@... ready.
```

---

## How It Works

### Architecture
```
User Request → Flask App → Celery Task Queue (Redis) → Celery Worker → Processing
                     ↓                                        ↓
                  Database ←──────────── Status Updates ──────┘
```

### Task Flow
1. User submits YouTube URL through voyoutube.com
2. Flask app creates task in Redis queue
3. Celery worker picks up task from queue
4. Worker processes video (download → transcribe → translate → TTS → mix → upload)
5. Worker updates database with progress and results
6. User sees real-time progress updates

### Why Separate Worker?
- **Scalability**: Workers can scale independently from web app
- **Reliability**: Long-running video processing doesn't block web requests
- **Resource Management**: Heavy CPU/memory tasks isolated from web server
- **Concurrent Processing**: Multiple videos can be processed simultaneously

---

## Troubleshooting

### Worker Won't Start
- Check that `REDIS_URL` environment variable is set
- Verify the repository is connected
- Check start command is correct
- Look for errors in deployment logs

### Worker Starts But Doesn't Process Tasks
- Confirm Redis is running (check Redis service status)
- Verify REDIS_URL points to correct Redis instance
- Check that main app is using same REDIS_URL
- Look for connection errors in worker logs

### Tasks Fail During Processing
- Check all API keys are set (OPENAI_API_KEY, ELEVEN_LABS_API_KEY)
- Verify DATABASE_URL is correct
- Check file permissions and temp directory access
- Monitor worker logs for specific error messages

---

## Testing the Setup

After deployment, test the worker:

1. Go to https://voyoutube.com
2. Enter a YouTube URL (preferably a SHORT video for testing)
3. Click "Translate to Georgian"
4. Watch the progress bar and status updates
5. Check worker logs in Railway dashboard

You should see the worker picking up and processing the task in real-time.

---

## What's Already Configured

✅ Redis database added to Railway
✅ Celery worker service created
✅ App code configured to use Celery (with Redis fallback)
✅ Procfile.worker exists with correct command
✅ Main app updated to detect and use Redis

⚠️ **Still Needed**: Connect worker service to GitHub repo and deploy

---

## Next Steps After Worker is Running

1. Test video processing end-to-end
2. Monitor worker performance and resource usage
3. Adjust concurrency if needed (currently set to 2)
4. Consider adding worker health checks
5. Set up monitoring/alerting for task failures

---

**Created**: 2025-11-19
**Status**: Service created, awaiting GitHub connection
