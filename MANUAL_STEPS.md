# Manual Setup Steps - VoYouTube

## ✅ Already Done by Me
- All Railway environment variables (11/11)
- Cloudflare R2 bucket created
- Cloudflare DNS configured: `voyoutube.com` → `lw37d1ti.up.railway.app`
- Railway domain generated

---

## 📋 Step 1: Create Cloudflare R2 API Token

### Why this can't be automated:
Cloudflare's REST API does not have an endpoint for creating R2 API tokens. When I tried, the API returned:
```
{"code":10015,"message":"No route matches this url."}
```

### Exact Steps:

1. **Open Cloudflare Dashboard**
   - Go to: https://dash.cloudflare.com
   - You should already be logged in as `levan@sarke.ge`

2. **Navigate to R2**
   - In the left sidebar, click **R2**
   - You'll see your bucket: `voyoutube-videos`

3. **Go to API Tokens**
   - Click **Manage R2 API Tokens** (button on the right side)

4. **Create New Token**
   - Click the blue **Create API Token** button

5. **Configure the Token**
   Fill in these exact values:

   | Field | Value |
   |-------|-------|
   | **Token name** | `voyoutube-app` |
   | **Permissions** | Select **Object Read & Write** |
   | **Apply to specific buckets only** | Toggle ON |
   | **Bucket** | Select `voyoutube-videos` from dropdown |
   | **TTL (Time to Live)** | Leave as default (forever) |

6. **Create the Token**
   - Click **Create API Token** button at the bottom

7. **SAVE THE CREDENTIALS** ⚠️ IMPORTANT

   You'll see a screen showing:
   ```
   Access Key ID: XXXXXXXXXXXXXXXXXXXX
   Secret Access Key: YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
   ```

   **Copy both values immediately - they won't be shown again!**

   - Copy the **Access Key ID**
   - Copy the **Secret Access Key**
   - Keep them somewhere safe temporarily (we'll add them to Railway next)

8. **Click "I have copied my credentials"**

---

## 📋 Step 2: Add R2 Credentials to Railway

You have TWO options:

### Option A: I Add Them via API (Faster)

Just paste the two values from Step 1 here in the chat:
```
Access Key ID: [paste here]
Secret Access Key: [paste here]
```

I'll add all 3 required variables to Railway automatically via API:
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_PUBLIC_URL=https://voyoutube.com/videos`

### Option B: Manual Setup in Railway Dashboard

1. **Open Railway Project**
   - Go to: https://railway.app/project/bd7d8d73-c874-4145-a4ef-a27bf5f3efe3
   - Click on the **georgian-voiceover-app** service (the one with the GitHub icon)

2. **Open Variables Tab**
   - Click the **Variables** tab at the top

3. **Add First Variable**
   - Click **New Variable** button
   - **Variable name**: `R2_ACCESS_KEY_ID`
   - **Value**: [paste the Access Key ID from Step 1]
   - Press Enter or click outside to save

4. **Add Second Variable**
   - Click **New Variable** button again
   - **Variable name**: `R2_SECRET_ACCESS_KEY`
   - **Value**: [paste the Secret Access Key from Step 1]
   - Press Enter or click outside to save

5. **Add Third Variable**
   - Click **New Variable** button again
   - **Variable name**: `R2_PUBLIC_URL`
   - **Value**: `https://voyoutube.com/videos`
   - Press Enter or click outside to save

6. **Verify**
   - You should now see 14 total variables
   - Railway will automatically redeploy your service

---

## 🎯 That's It!

Once Step 1 and Step 2 are complete:

1. **Wait 2-3 minutes** for Railway to redeploy with new R2 credentials
2. **Wait 5-10 minutes** for DNS to fully propagate
3. **Test your app**:
   - Open: https://voyoutube.com
   - Or try directly: https://voyoutube.com/watch?v=dQw4w9WgXcQ

---

## 🔍 How to Verify Everything Works

### Check 1: DNS is working
```bash
dig voyoutube.com
```
Should show CNAME pointing to `lw37d1ti.up.railway.app`

### Check 2: Website loads
Open https://voyoutube.com - should show the landing page

### Check 3: Video processing works
1. Take any YouTube URL: `https://www.youtube.com/watch?v=VIDEO_ID`
2. Replace with: `https://voyoutube.com/watch?v=VIDEO_ID`
3. Should start processing with progress bar
4. When complete, video plays with Georgian voiceover

### Check 4: R2 storage works
After processing a video, check:
- Railway logs should show "Uploading to R2..."
- Video should be accessible at the R2 URL
- Database should cache the video (reloading same video ID is instant)

---

## 📊 Final Checklist

- [x] Railway environment variables (11/11) - **Done by me**
- [x] Cloudflare R2 bucket created - **Done by me**
- [x] Cloudflare DNS configured - **Done by me**
- [x] Railway domain generated - **Done by me**
- [ ] **R2 API token created - Step 1 above**
- [ ] **R2 credentials in Railway - Step 2 above**

Once all checked, you're live! 🚀

---

## 💬 Quick Summary

**What you need to do manually:**
1. Create R2 API token in Cloudflare Dashboard (5 minutes)
2. Either:
   - Give me the credentials and I'll add them via API (30 seconds), OR
   - Add them to Railway yourself (2 minutes)

**Total time:** ~7 minutes

**Why manual:** API endpoints don't exist for R2 token creation
