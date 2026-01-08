# Speaker Detection Service

Docker container that runs **pyannote.audio** for speaker diarization (detecting who is speaking when).

## Features

- 🎯 Detects multiple speakers in audio
- 🔊 Assigns speaker labels (SPEAKER_00, SPEAKER_01, etc.)
- 🎭 Maps speakers to voice genders (male/female)
- 🐳 Runs in isolated Docker container (no version conflicts)
- 🚀 REST API for easy integration

## Quick Start

### 1. Build and Run Container

```bash
# From project root
docker-compose up -d speaker-detection
```

### 2. Check Service Health

```bash
curl http://localhost:5002/health
```

Response:
```json
{
  "status": "healthy",
  "service": "speaker-detection",
  "device": "cpu"
}
```

### 3. Detect Speakers

```bash
curl -X POST http://localhost:5002/detect-speakers \
  -H "Content-Type: application/json" \
  -d '{"audio_path": "/app/temp/audio.wav"}'
```

Response:
```json
{
  "speakers": [
    {"start": 0.5, "end": 10.2, "speaker": "SPEAKER_00"},
    {"start": 10.5, "end": 25.3, "speaker": "SPEAKER_01"},
    {"start": 25.8, "end": 40.1, "speaker": "SPEAKER_00"}
  ],
  "num_speakers": 2,
  "speaker_labels": ["SPEAKER_00", "SPEAKER_01"]
}
```

## Integration with Main App

The Flask app automatically uses speaker detection if available:

```python
from src.speaker_detector import SpeakerDetector

# Initialize
detector = SpeakerDetector()

# Detect speakers in audio
speaker_result = detector.detect_speakers("temp/audio.wav")

# Assign voices to transcription segments
segments_with_voices = detector.assign_voices_to_segments(
    transcription_segments=transcription_segments,
    speaker_segments=speaker_result['speakers'],
    voice_mapping={
        'SPEAKER_00': 'male',
        'SPEAKER_01': 'female'
    }
)

# TTS will use the 'voice' field automatically
tts.generate_voiceover(segments_with_voices)
```

## Environment Variables

### Optional: Hugging Face Token

For better models, add your Hugging Face token to `.env`:

```bash
HUGGING_FACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
```

Get token: https://huggingface.co/settings/tokens

### Configure Service URL

In main app's `.env`:

```bash
SPEAKER_DETECTION_URL=http://localhost:5002
```

## How It Works

```
Audio File
    ↓
pyannote.audio (Docker Container)
    ↓
Speaker Segments: [
    {start: 0, end: 10, speaker: "SPEAKER_00"},
    {start: 10, end: 20, speaker: "SPEAKER_01"}
]
    ↓
Voice Mapping: {
    "SPEAKER_00": "male",   → Giorgi (Georgian)
    "SPEAKER_01": "female"  → Eka (Georgian)
}
    ↓
Edge TTS with Multiple Voices
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs voyoutube-speaker-detection

# Rebuild
docker-compose build --no-cache speaker-detection
docker-compose up -d speaker-detection
```

### Out of Memory

pyannote.audio is memory-intensive. For long audio files:

```bash
# Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory: 4GB+
```

### Service Not Detected

If Flask app doesn't detect the service:

1. Check service is running: `docker ps`
2. Check health: `curl http://localhost:5002/health`
3. Check environment: `SPEAKER_DETECTION_URL=http://localhost:5002` in `.env`

## Performance

- **CPU**: ~10-30 seconds per minute of audio
- **GPU**: ~2-5 seconds per minute of audio (with CUDA)
- **Memory**: 2-4GB RAM

## Limitations

- Works best with clear audio (minimal background noise)
- Minimum speaker duration: ~1 second
- Best for 2-4 speakers (accuracy decreases with more)

## Alternative: Disable Speaker Detection

If you don't need multi-speaker support:

```bash
# Stop the service
docker-compose stop speaker-detection

# Flask app will fall back to single voice mode
```
