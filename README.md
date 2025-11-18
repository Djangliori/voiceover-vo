# Georgian Voiceover App

Translate YouTube videos to Georgian with natural voiceover overlay (traditional documentary-style dubbing).

## Features

- Downloads YouTube videos
- Transcribes speech with timestamps using Google Cloud Speech-to-Text
- Translates to Georgian using Google Cloud Translation API
- Generates Georgian voiceover using Google Cloud Text-to-Speech
- Mixes voiceover with lowered original audio
- Creates final video with Georgian overdub
- Simple web interface

## Requirements

- Python 3.9+
- ffmpeg
- Google Cloud Platform account with enabled APIs

## Installation

Already done! The app is ready to use.

## Running the App

1. Open Terminal
2. Navigate to the app directory:
   ```bash
   cd ~/georgian-voiceover-app
   ```

3. Start the server:
   ```bash
   python3 app.py
   ```

4. Open your browser to: **http://localhost:5000**

5. Paste a YouTube URL and click "Translate to Georgian"

## How It Works

1. **Download**: Video is downloaded from YouTube
2. **Transcribe**: Speech is transcribed with precise timestamps
3. **Translate**: Text is translated to Georgian
4. **Generate**: Georgian voiceover is synthesized
5. **Mix**: Original audio is lowered to 30% and mixed with voiceover
6. **Combine**: Final video is created with Georgian overdub

## Processing Time

- Short video (2-5 min): ~3-5 minutes
- Medium video (10-15 min): ~8-12 minutes
- Long video (30+ min): ~20-30 minutes

## Cost

With $300 Google Cloud free credit:
- ~$0.35 per 10-minute video
- Can process ~850 videos before paying

## Configuration

Edit `.env` file to customize:
- `ORIGINAL_AUDIO_VOLUME`: Volume of original audio (default: 0.3)
- `VOICEOVER_VOLUME`: Volume of Georgian voiceover (default: 1.0)
- `WHISPER_MODEL`: Transcription model (tiny/base/small/medium/large)

## Troubleshooting

**Error: "Google credentials not found"**
- Make sure `google-credentials.json` is in the app directory
- Check that APIs are enabled in Google Cloud Console

**Error: "ffmpeg not found"**
- Run: `brew install ffmpeg`

**Processing is slow**
- Normal! Video processing takes time
- Larger videos take longer
- Don't close the browser during processing

## Output

Processed videos are saved in the `output/` directory.

## Support

If you encounter issues:
1. Check the terminal for error messages
2. Verify Google Cloud APIs are enabled
3. Ensure you have enough free credits

## What's Next?

Possible enhancements:
- Batch processing multiple videos
- Voice gender/speed selection
- Multiple language support
- Preview before download
- Progress percentage improvements

Enjoy translating videos to Georgian! 🇬🇪
