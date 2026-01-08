# Speaker Detection Setup Guide

## გამოყენება (How to Use)

### 1. Docker Container-ის გაშვება (Start Docker Container)

```bash
# Build and start speaker detection service
docker-compose up -d speaker-detection

# Check status
docker ps
```

### 2. Flask App-ის კონფიგურაცია (Configure Flask App)

დაამატეთ `.env` ფაილში:

```bash
# Enable speaker detection
SPEAKER_DETECTION_URL=http://localhost:5002

# Optional: Enable speaker detection by default
USE_SPEAKER_DETECTION=true
```

### 3. ვიდეოს თარგმნა Multi-Speaker მხარდაჭერით

**ავტომატური რეჟიმი** (Flask app automatically detects speakers):

```bash
# Just process video normally - speaker detection happens automatically
# if SPEAKER_DETECTION_URL is configured
```

**Manual Voice Mapping** (თუ გინდათ კონკრეტული speaker-ებისთვის ხმების მითითება):

```python
# In your code or config
voice_mapping = {
    'SPEAKER_00': 'male',    # First speaker = Giorgi (male)
    'SPEAKER_01': 'female',  # Second speaker = Eka (female)
    'SPEAKER_02': 'male',    # Third speaker = Giorgi (male)
}
```

## როგორ მუშაობს (How It Works)

```
1. YouTube Video Download
       ↓
2. Audio Extraction → temp/audio.wav
       ↓
3. Speaker Detection Service (Docker)
   - pyannote.audio analyzes audio
   - Returns: [
       {start: 0, end: 10, speaker: "SPEAKER_00"},
       {start: 10, end: 20, speaker: "SPEAKER_01"}
     ]
       ↓
4. Transcription (Whisper)
   - Segments: [
       {start: 0, end: 5, text: "Hello"},
       {start: 5, end: 10, text: "world"}
     ]
       ↓
5. Voice Assignment
   - Match transcription segments with speaker segments
   - Result: [
       {start: 0, end: 5, text: "Hello", speaker: "SPEAKER_00", voice: "male"},
       {start: 5, end: 10, text: "world", speaker: "SPEAKER_00", voice: "male"}
     ]
       ↓
6. Translation (Gemini)
   - Translated: [
       {start: 0, end: 5, translated_text: "გამარჯობა", voice: "male"},
       {start: 5, end: 10, translated_text: "სამყარო", voice: "male"}
     ]
       ↓
7. TTS (Edge TTS)
   - Segment 0: "გამარჯობა" → Giorgi voice (male)
   - Segment 1: "სამყარო" → Giorgi voice (male)
       ↓
8. Audio Mixing + Video Output
```

## მაგალითები (Examples)

### Example 1: Interview (2 Speakers)

```
Original Audio:
- 0-30s: Interviewer (male)
- 30-60s: Guest (female)
- 60-90s: Interviewer (male)
- 90-120s: Guest (female)

Speaker Detection Result:
- SPEAKER_00 = Interviewer
- SPEAKER_01 = Guest

Voice Mapping:
- SPEAKER_00 → male → Giorgi
- SPEAKER_01 → female → Eka

Output:
- 0-30s: Georgian voiceover by Giorgi (male)
- 30-60s: Georgian voiceover by Eka (female)
- 60-90s: Georgian voiceover by Giorgi (male)
- 90-120s: Georgian voiceover by Eka (female)
```

### Example 2: Podcast (3+ Speakers)

```
Voice Mapping (alternating):
- SPEAKER_00 → male
- SPEAKER_01 → female
- SPEAKER_02 → male
- SPEAKER_03 → female
```

## Troubleshooting

### Speaker Detection Service არ მუშაობს

```bash
# Check if container is running
docker ps | grep speaker-detection

# Check logs
docker logs voyoutube-speaker-detection

# Restart service
docker-compose restart speaker-detection
```

### Wrong Speaker Detection

Speaker detection accuracy depends on:
- Audio quality (clear voices)
- Speaker distinctiveness (different voices)
- Background noise (less is better)

**გამოსავალი (Solution):**
1. Use higher quality audio
2. Manually specify voice mapping in config
3. Disable speaker detection for single-speaker videos

### Performance Issues

pyannote.audio არის memory-intensive:

```bash
# Check Docker resources
docker stats voyoutube-speaker-detection

# Increase memory in Docker Desktop:
# Settings → Resources → Memory: 4GB+
```

## Configuration Options

### .env Variables

```bash
# Speaker Detection Service
SPEAKER_DETECTION_URL=http://localhost:5002

# Enable/disable by default
USE_SPEAKER_DETECTION=true

# Hugging Face token (optional, for better models)
HUGGING_FACE_TOKEN=hf_xxxxxxxxxxxx

# Default voice if no speaker detection
EDGE_TTS_VOICE=male
```

### Voice Mapping Strategies

**Strategy 1: Simple Alternating**
```python
{
    'SPEAKER_00': 'male',
    'SPEAKER_01': 'female',
    'SPEAKER_02': 'male',
    'SPEAKER_03': 'female'
}
```

**Strategy 2: All Same Voice** (disable multi-voice)
```python
{
    'SPEAKER_00': 'male',
    'SPEAKER_01': 'male',
    'SPEAKER_02': 'male'
}
```

**Strategy 3: Custom Per Video** (future feature)
```python
{
    'VIDEO_ID': {
        'SPEAKER_00': 'female',  # Host is female
        'SPEAKER_01': 'male'     # Guest is male
    }
}
```

## Performance Benchmarks

| Audio Length | CPU Time | GPU Time | Memory |
|--------------|----------|----------|--------|
| 1 minute     | ~15s     | ~3s      | 2GB    |
| 5 minutes    | ~75s     | ~15s     | 3GB    |
| 10 minutes   | ~150s    | ~30s     | 4GB    |

## Disable Speaker Detection

თუ არ გჭირდებათ multi-speaker support:

```bash
# Stop the service
docker-compose stop speaker-detection

# Or remove from .env
# SPEAKER_DETECTION_URL=  (leave empty)
```

Flask app will automatically fall back to single-voice mode.
