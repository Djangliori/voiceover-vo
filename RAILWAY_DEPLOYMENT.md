# Railway Deployment Instructions

## AssemblyAI Integration Setup

### 1. Add Environment Variable via Railway Dashboard

Since we couldn't set it via CLI, please add the AssemblyAI API key manually:

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Navigate to your **voyoutube** project
3. Click on the service (likely named "web" or similar)
4. Go to the **Variables** tab
5. Click **Add Variable**
6. Add the following variable:
   ```
   ASSEMBLYAI_API_KEY = ef78c7fc96e5459aa5435cac694bee3c
   ```

### 2. Additional Configuration Variables (Optional)

While you're in the Variables tab, you can also add these optional configuration variables:

```bash
# Transcription Provider (assemblyai or whisper)
TRANSCRIPTION_PROVIDER = assemblyai

# Enable speaker diarization
ENABLE_SPEAKER_DIARIZATION = true

# Maximum speakers to detect (2-10)
MAX_SPEAKERS = 10

# Pause threshold for merging segments (seconds)
SPEAKER_MERGE_PAUSE = 1.5

# AssemblyAI timeout (seconds)
ASSEMBLYAI_TIMEOUT = 300
```

### 3. Deploy Changes

After adding the environment variables:

1. Push your code changes to GitHub:
   ```bash
   git add .
   git commit -m "Add AssemblyAI integration with speaker diarization"
   git push
   ```

2. Railway will automatically detect the push and redeploy your application

### 4. Verify Deployment

Once deployed, you can verify the integration:

1. Check the Railway logs for successful initialization:
   - Look for: "AssemblyAI transcriber initialized successfully"

2. Test the API endpoint with a YouTube video
3. Monitor logs for "Using AssemblyAI for transcription with speaker diarization"

## Fallback Behavior

The system is configured with automatic fallback:

- **Primary**: AssemblyAI (with speaker diarization)
- **Fallback**: OpenAI Whisper (if AssemblyAI fails or is not configured)

This ensures your service remains operational even if AssemblyAI encounters issues.

## Testing Locally First

Before deploying, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the test script
python test_assemblyai.py
```

## Monitoring

Watch for these log messages in Railway:

- ✅ Success: "Using AssemblyAI for transcription with speaker diarization"
- ⚠️ Fallback: "AssemblyAI transcription failed, falling back to Whisper"
- ❌ Error: "Failed to initialize AssemblyAI"

## Support

If you encounter issues:

1. Check that ASSEMBLYAI_API_KEY is set correctly
2. Verify the API key is valid and has sufficient credits
3. Check Railway logs for specific error messages
4. The system will automatically fallback to Whisper if needed