# GeYouTube Deployment Guide

## ✅ What's Already Done

1. **Code Complete** - All features implemented:
   - YouTube-style URL routing (`geyoutube.com/watch?v=VIDEO_ID`)
   - Cloudflare R2 storage integration
   - PostgreSQL database for video tracking
   - Real-time progress updates
   - Video player with streaming
   - Production-ready with Gunicorn

2. **GitHub Repository** - Code pushed to:
   - https://github.com/speudoname/georgian-voiceover-app

3. **Railway Project Created**:
   - Project ID: `bd7d8d73-c874-4145-a4ef-a27bf5f3efe3`
   - Project Name: `geyoutube`

---

## 🔧 Remaining Steps (Manual)

### Step 1: Complete Railway Deployment

1. Go to https://railway.app/dashboard
2. Find the project "geyoutube"
3. Click "+ New" → "GitHub Repo"
4. Select `speudoname/georgian-voiceover-app`
5. Railway will auto-detect the Procfile and nixpacks.toml

### Step 2: Add PostgreSQL Database

1. In the Railway project, click "+ New" → "Database" → "PostgreSQL"
2. Railway will automatically set the `DATABASE_URL` environment variable

### Step 3: Set Environment Variables

Go to your service → Variables and add:

```
# Voicegain API (for transcription)
VOICEGAIN_API_KEY=[YOUR_VOICEGAIN_JWT_TOKEN]

# OpenAI API (for translation)
OPENAI_API_KEY=[YOUR_OPENAI_API_KEY]

# Google Cloud TTS (Gemini) - Required for voiceover
GOOGLE_APPLICATION_CREDENTIALS_JSON=[YOUR_JSON_CREDENTIALS]

# App Configuration
FLASK_PORT=5001
MAX_VIDEO_LENGTH=1800
OUTPUT_DIR=output
TEMP_DIR=temp

# Audio Settings
ORIGINAL_AUDIO_VOLUME=0.05
VOICEOVER_VOLUME=1.0

# Whisper Model
WHISPER_MODEL=base

# Cloudflare R2 (Add after Step 4)
CLOUDFLARE_ACCOUNT_ID=[YOUR_ACCOUNT_ID]
R2_ACCESS_KEY_ID=[FROM_STEP_4]
R2_SECRET_ACCESS_KEY=[FROM_STEP_4]
R2_BUCKET_NAME=geyoutube-videos
R2_PUBLIC_URL=https://videos.geyoutube.com
```

### Step 4: Set Up Cloudflare R2

#### A. Get Your Account ID
1. Log in to Cloudflare Dashboard: https://dash.cloudflare.com
2. Select any domain (like geyoutube.com)
3. Scroll down on Overview page - you'll see "Account ID" on the right
4. Copy the Account ID

#### B. Create R2 Bucket
1. In Cloudflare Dashboard, go to R2 (left sidebar)
2. Click "Create bucket"
3. Name: `geyoutube-videos`
4. Location: Automatic
5. Click "Create bucket"

#### C. Create R2 API Tokens
1. In R2, go to "Manage R2 API Tokens"
2. Click "Create API token"
3. Token name: `geyoutube-app`
4. Permissions: "Object Read & Write"
5. Bucket(s): `geyoutube-videos`
6. Click "Create API Token"
7. **Save these values** (shown only once):
   - Access Key ID
   - Secret Access Key

#### D. Set Up Public Access (Optional - for streaming)
1. Go to your bucket → Settings
2. Under "Public access", click "Allow Access"
3. Add custom domain: `videos.geyoutube.com`
4. Follow the DNS instructions Cloudflare provides

### Step 5: Configure Cloudflare DNS for geyoutube.com

1. Go to Cloudflare Dashboard → DNS → Records
2. Get your Railway app URL from Railway dashboard (looks like: `geyoutube-production.up.railway.app`)
3. Add DNS record:
   - **Type**: CNAME
   - **Name**: @  (or leave blank for root domain)
   - **Target**: [your-railway-url].railway.app
   - **Proxy status**: Proxied (orange cloud)
   - **TTL**: Auto

4. Add DNS record for video subdomain (if using R2 public domain):
   - **Type**: CNAME
   - **Name**: videos
   - **Target**: [from R2 custom domain setup]
   - **Proxy status**: Proxied
   - **TTL**: Auto

5. SSL/TLS Settings:
   - Go to SSL/TLS → Overview
   - Set to "Full" or "Full (strict)"

---

## 🧪 Testing

Once deployed:

1. **Test the main site**:
   - Go to https://geyoutube.com
   - You should see the landing page

2. **Test video processing**:
   - Get any YouTube URL, e.g.: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
   - Replace `youtube.com` with `geyoutube.com`
   - Go to: `https://geyoutube.com/watch?v=dQw4w9WgXcQ`
   - Should start processing automatically

3. **Check progress**:
   - Progress bar should update every 500ms
   - You'll see status messages

4. **Watch video**:
   - When complete, video player loads automatically
   - Video should play with Georgian voiceover

---

## 📊 Monitoring

- **Railway Logs**: Check deployment logs in Railway dashboard
- **Build Status**: Ensure nixpacks successfully installed ffmpeg
- **Database**: Check PostgreSQL service is running
- **Environment Variables**: Verify all are set correctly

---

## 🐛 Troubleshooting

### App won't start
- Check Railway logs for errors
- Verify all environment variables are set
- Ensure PostgreSQL database is running

### Videos not uploading to R2
- Check R2 credentials are correct
- Verify bucket name matches
- Check account ID is correct
- App will fall back to local storage if R2 not configured

### DNS not resolving
- Wait 5-10 minutes for DNS propagation
- Check CNAME record points to correct Railway URL
- Ensure proxy (orange cloud) is enabled

### Video processing fails
- Check API keys (Voicegain, OpenAI, Google Cloud) are valid
- Check Railway has enough resources
- Look for errors in Railway logs

---

## 💰 Cost Estimation

**Monthly costs (estimated for moderate usage)**:

- **Railway**: $5-20 (Hobby plan, depends on usage)
- **PostgreSQL**: Included in Railway plan
- **Cloudflare R2**: ~$0-5 (10GB free, then $0.015/GB)
- **Voicegain**: Based on usage (~$0.004/min)
- **Google Cloud TTS**: Based on usage
- **OpenAI GPT-4**: Based on your usage

**Total**: ~$10-30/month (excluding API usage costs)

---

## 🎯 Current Status

- ✅ Code complete and pushed to GitHub
- ✅ Railway project created
- ⏳ Need to connect GitHub repo in Railway dashboard
- ⏳ Need to add PostgreSQL database
- ⏳ Need to set environment variables
- ⏳ Need to create R2 bucket and get credentials
- ⏳ Need to configure DNS

---

## 📝 Notes

- The app works without R2 (uses local storage as fallback)
- Videos are cached in database to avoid reprocessing
- Progress updates work in real-time
- SSL automatically handled by Cloudflare
- Railway auto-deploys on git push to main branch

---

## 🆘 Need Help?

If you encounter issues:
1. Check Railway deployment logs
2. Verify all environment variables
3. Check Cloudflare DNS settings
4. Ensure API keys are valid
5. Monitor Railway resource usage

Good luck with the deployment! 🚀
