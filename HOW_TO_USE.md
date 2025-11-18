# How to Use the Georgian Voiceover App

## Your App is Ready!

The server is currently running at: **http://localhost:5001**

---

## Quick Start

### Step 1: Open the App
Open your web browser and go to:
```
http://localhost:5001
```

### Step 2: Paste a YouTube URL
- Find a YouTube video you want to translate
- Copy the URL (e.g., `https://www.youtube.com/watch?v=dQw4w9WgXcQ`)
- Paste it into the input field

### Step 3: Click "Translate to Georgian"
- The app will start processing
- You'll see a progress bar and status updates
- Processing takes 5-15 minutes depending on video length

### Step 4: Download Your Video
- When complete, click "Download Video"
- The video will have Georgian voiceover with lowered original audio

---

## Starting the App (Future Sessions)

1. Open Terminal
2. Run:
   ```bash
   cd ~/georgian-voiceover-app
   python3 app.py
   ```
3. Open browser to: http://localhost:5001

---

## Stopping the App

In the Terminal where the app is running:
- Press `CTRL + C`

---

## What Happens During Processing

1. **Download (10%)**: Video is downloaded from YouTube
2. **Transcribe (25-40%)**: Audio is transcribed with timestamps
3. **Translate (45-55%)**: English text translated to Georgian
4. **TTS (60-75%)**: Georgian voiceover is generated
5. **Mix (80-90%)**: Audio tracks are mixed
6. **Finalize (95-100%)**: Final video is created

---

## Tips

### For Best Results:
- Use videos with clear speech
- Shorter videos process faster (start with 2-5 minutes)
- Don't close browser during processing
- Check Terminal for detailed progress

### If Something Goes Wrong:
- Check the Terminal for error messages
- Make sure you have internet connection
- Verify Google Cloud APIs are working
- Try a different video

---

## Example Videos to Try

Start with short, clear videos:
- TED Talks (2-5 minutes)
- News clips
- Tutorial videos
- Short documentaries

Avoid:
- Very long videos (start small)
- Videos with music-only (no speech)
- Live streams

---

## Where Are My Videos?

Processed videos are saved in:
```
~/georgian-voiceover-app/output/
```

---

## Customization

Edit the `.env` file to change settings:

```bash
# Make original audio quieter/louder
ORIGINAL_AUDIO_VOLUME=0.3  # (0.0 to 1.0)

# Make voiceover quieter/louder
VOICEOVER_VOLUME=1.0  # (0.0 to 1.0)

# Use different transcription quality
WHISPER_MODEL=base  # tiny, base, small, medium, large
```

After changing settings, restart the app.

---

## Cost Tracking

Monitor your Google Cloud usage:
https://console.cloud.google.com/billing

With $300 free credit:
- Each 10-min video costs ~$0.35
- You can process ~850 videos

---

## Troubleshooting

### "Connection Error"
- Check if server is running in Terminal
- Make sure you're using http://localhost:5001

### "Google API Error"
- Check credentials file exists
- Verify APIs are enabled in Google Cloud Console
- Check you have remaining credits

### "Processing Stuck"
- Check Terminal for errors
- Refresh the browser page
- Restart the server

### "ffmpeg Error"
- Run: `brew install ffmpeg`
- Restart the app

---

## Ready to Test?

1. Make sure the server is running (check Terminal)
2. Open: http://localhost:5001
3. Paste a short YouTube URL
4. Watch the magic happen!

Enjoy translating videos to Georgian! 🇬🇪
