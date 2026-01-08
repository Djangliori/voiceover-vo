# 🎭 Speaker Detection დაყენდა! (Ready!)

## რა გაკეთდა? (What Was Done?)

✅ **Docker Container** - pyannote.audio speaker detection service
✅ **REST API** - მარტივი API speaker detection-სთვის
✅ **Integration** - Flask app ავტომატურად იყენებს service-ს თუ ხელმისაწვდომია
✅ **Multi-Voice Support** - Edge TTS-მა მხარს უჭერს სხვადასხვა ხმებს per segment
✅ **Setup Script** - `setup_speaker_detection.bat` ავტომატური დაყენებისთვის

---

## როგორ გავუშვა? (How to Start?)

### გზა 1: ავტომატური (Recommended)

```bash
# Run setup script
setup_speaker_detection.bat
```

ეს script:
1. ✅ Build-ს Docker container-ს
2. ✅ აწყობს speaker detection service-ს
3. ✅ ამოწმებს რომ მუშაობს
4. ✅ გიჩვენებთ next steps

### გზა 2: Manual

```bash
# Build container
docker-compose build speaker-detection

# Start service
docker-compose up -d speaker-detection

# Check health
curl http://localhost:5002/health
```

---

## კონფიგურაცია (Configuration)

დაამატეთ `.env` ფაილში:

```bash
# Enable speaker detection
SPEAKER_DETECTION_URL=http://localhost:5002

# Optional: Hugging Face token for better models
HUGGING_FACE_TOKEN=hf_xxxxxxxxxxxxx
```

**რესტარტი Flask App-ის:**
```bash
# Stop current Flask (Ctrl+C)
# Then restart:
python app.py
```

Flask app ავტომატურად დააკონექტდება speaker detection service-ს.

---

## როგორ მუშაობს? (How Does It Work?)

### Without Speaker Detection (ახლანდელი)
```
Video → Transcription → Translation → Edge TTS (1 voice) → Output
                                          ↓
                                   Giorgi (male) for ALL
```

### With Speaker Detection (ახალი!)
```
Video → Audio Extraction
          ↓
      Speaker Detection Service (Docker)
          ↓
      [SPEAKER_00: 0-30s, SPEAKER_01: 30-60s]
          ↓
      Transcription + Voice Assignment
          ↓
      [Segment 1: "Hello" - SPEAKER_00 - male]
      [Segment 2: "Hi" - SPEAKER_01 - female]
          ↓
      Translation
          ↓
      [Segment 1: "გამარჯობა" - male]
      [Segment 2: "გამარჯობა" - female]
          ↓
      Edge TTS (Multi-Voice)
          ↓
      [Segment 1: Giorgi voice]
      [Segment 2: Eka voice]
          ↓
      Audio Mixing → Output
```

---

## მაგალითი (Example)

### Video: Interview

**Original:**
- 0-30s: Host (male speaking English)
- 30-60s: Guest (female speaking English)
- 60-90s: Host (male speaking English)

**After Translation:**
- 0-30s: Host ქართულად - Giorgi-ს ხმით (male)
- 30-60s: Guest ქართულად - Eka-ს ხმით (female)
- 60-90s: Host ქართულად - Giorgi-ს ხმით (male)

---

## როდის გამოვიყენო? (When to Use?)

### ✅ გამოიყენეთ Speaker Detection თუ:
- Interview/Podcast (2+ speakers)
- Dialogue/Conversation
- Panel Discussion
- Q&A Sessions

### ❌ არ გამოიყენოთ თუ:
- Single speaker (monologue, presentation)
- Documentary narration
- Music videos
- Short clips (<30 seconds)

**რატომ?**
- Speaker detection არის slow (~10-30 seconds per minute of audio)
- არ არის საჭირო 1 მოლაპარაკისთვის
- Best quality with 2-3 distinct speakers

---

## Performance

| Mode | Speed | Quality |
|------|-------|---------|
| **No Speaker Detection** | ⚡ Fast | Single voice |
| **With Speaker Detection** | 🐢 Slower (+ ~30s per minute) | Multi-voice |

---

## Troubleshooting

### Service არ იწყება
```bash
# Check Docker is running
docker ps

# View logs
docker logs voyoutube-speaker-detection

# Rebuild
docker-compose build --no-cache speaker-detection
docker-compose up -d speaker-detection
```

### Flask App ვერ აღმოაჩენს Service-ს
```bash
# 1. Check service health
curl http://localhost:5002/health

# 2. Check .env file
echo SPEAKER_DETECTION_URL=http://localhost:5002

# 3. Restart Flask app
```

### Low Accuracy (ცუდი speaker detection)
- Audio quality დაბალია
- Speakers ძალიან მსგავსი ხმებით
- Background noise ბევრია

**გამოსავალი:**
- გამოიყენეთ უკეთესი audio quality
- ან manually მიუთითეთ voices config-ში

---

## Commands

```bash
# Start service
docker-compose up -d speaker-detection

# Stop service
docker-compose stop speaker-detection

# View logs
docker logs -f voyoutube-speaker-detection

# Check status
docker ps | grep speaker-detection

# Test API
curl http://localhost:5002/health
```

---

## შემდეგი ნაბიჯები (Next Steps)

1. **Run Setup:**
   ```bash
   setup_speaker_detection.bat
   ```

2. **დაამატეთ .env-ში:**
   ```
   SPEAKER_DETECTION_URL=http://localhost:5002
   ```

3. **Restart Flask App**

4. **Test with Multi-Speaker Video:**
   - Find an interview or podcast on YouTube
   - Process it normally
   - Check if different voices are used!

---

## დამატებითი ინფორმაცია

📖 Full Guide: `SPEAKER_DETECTION_GUIDE.md`
🐳 Docker Setup: `docker/speaker-detection/README.md`
🔧 API Details: `docker/speaker-detection/speaker_service.py`

---

## არის კითხვები? (Questions?)

- Docker container რას აკეთებს? → pyannote.audio speaker diarization
- რამდენი ხმაა? → 2 (Giorgi-male, Eka-female)
- გჭირდება internet? → არა, ყველაფერი local-ზე მუშაობს
- რამდენი დრო სჭირდება? → +10-30 seconds per minute of audio
- ვერ დავაყენე pyannote.audio-ს Windows-ზე? → Docker-ში არის, version conflicts-ის გარეშე!

---

**ყველაფერი მზადაა! Ready to test! 🎉**
