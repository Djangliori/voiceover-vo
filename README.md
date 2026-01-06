# Georgian Voiceover App

![CI Status](https://github.com/speudoname/georgian-voiceover-app/workflows/CI%20-%20Tests%20%26%20Quality%20Checks/badge.svg)
![Deploy Status](https://github.com/speudoname/georgian-voiceover-app/workflows/CD%20-%20Deploy%20to%20Production/badge.svg)
![Code Coverage](https://codecov.io/gh/speudoname/georgian-voiceover-app/branch/main/graph/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

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

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test types
make test-unit         # Unit tests only
make test-integration  # Integration tests only
```

See [TESTING_SETUP.md](TESTING_SETUP.md) for comprehensive testing documentation.

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Type checking
make type-check

# Security scan
make security

# Run all checks (CI simulation)
make ci
```

### CI/CD

This project uses GitHub Actions for continuous integration and deployment:

- **CI**: Automated tests, linting, and security checks on every PR
- **CD**: Automated deployment to production on merge to main
- **Code Quality**: Weekly code analysis and dependency audits
- **Dependabot**: Automated dependency updates

See [CI_CD_SETUP.md](CI_CD_SETUP.md) for complete CI/CD documentation.

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes and add tests
4. Run tests: `make test`
5. Commit: `git commit -m "feat: Add my feature"`
6. Push: `git push origin feat/my-feature`
7. Create a Pull Request

## License

MIT License - see LICENSE file for details.

---

Enjoy translating videos to Georgian! 🇬🇪
