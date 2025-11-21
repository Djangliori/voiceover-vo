# Georgian Voiceover App - Enhancement Plan
## Multi-Speaker Support & Natural Synchronization

**Last Updated**: November 2024
**Current Status**: Phase 3 Complete, Phase 4 Starting

---

## 🎯 Progress Summary

### ✅ Completed Features
1. **AssemblyAI Integration** - Speaker diarization with fallback to Whisper
2. **Paragraph-Level Translation** - Context-aware translation with conversation flow
3. **Multi-Voice Support** - Dynamic voice assignment for both ElevenLabs and Gemini TTS

### 🔄 In Progress
- **Phase 4**: Dynamic Synchronization with subtitle-style overflow

### ⏳ Remaining
- **Phase 5**: Testing & Optimization

### 🚀 Key Achievements
- **Dual TTS Provider Support**: Both ElevenLabs and Google Gemini TTS
- **Parallel Processing**: Maintained speed with concurrent API calls
- **28 Gemini Voices**: Full support for all celestial-themed voices
- **9 ElevenLabs Voices**: Curated selection for Georgian
- **Automatic Fallback**: Seamless provider switching on failure
- **Context-Aware Translation**: Paragraph grouping with speaker context

### 📝 Implementation Notes
**Additions Beyond Original Plan:**
- **Google Gemini TTS Integration**: Added as alternative to ElevenLabs (not in original spec)
- **Provider Fallback System**: Automatic switching between TTS providers
- **Concurrent Request Optimization**: Both TTS providers now use ThreadPoolExecutor
- **Voice Equivalence Mapping**: Cross-provider voice mapping for seamless fallback

**Technical Improvements:**
- Maintained OpenAI v0.28.1 compatibility (avoided breaking production)
- Added comprehensive logging throughout
- Resource management with proper session handling
- Thread-safe processing status tracking

---

## 📋 Executive Summary

This plan outlines the transformation of the Georgian Voiceover App from a single-voice, rigid-timing system to a professional multi-speaker dubbing platform with natural synchronization and conversation flow.

### Current Limitations
- ❌ No speaker detection or differentiation
- ❌ Single voice for all content
- ❌ Rigid time-code matching causing unnatural pauses
- ❌ Sentences cut mid-thought due to segment boundaries
- ❌ No context awareness in translation

### Proposed Solution
- ✅ AssemblyAI for speaker diarization
- ✅ Multiple ElevenLabs voices mapped to speakers
- ✅ Paragraph-level translation for natural flow
- ✅ Dynamic synchronization with overflow support
- ✅ Professional dubbing quality output

### Expected Outcomes
- 95%+ speaker identification accuracy
- 4 distinct voices per video
- Natural Georgian speech rhythm
- 30% improvement in translation quality
- Professional documentary-quality output

---

## 🗓️ Implementation Timeline

### Total Duration: 6 Weeks

| Phase | Duration | Focus Area | Status |
|-------|----------|------------|---------|
| Phase 1 | Weeks 1-2 | AssemblyAI Integration | ✅ COMPLETED |
| Phase 2 | Weeks 2-3 | Paragraph-Level Translation | ✅ COMPLETED |
| Phase 3 | Weeks 3-4 | Multi-Voice Support | ✅ COMPLETED |
| Phase 4 | Weeks 4-5 | Dynamic Synchronization | 🔄 IN PROGRESS |
| Phase 5 | Weeks 5-6 | Testing & Optimization | ⏳ PENDING |

---

## 📊 Phase 1: AssemblyAI Integration (Weeks 1-2)

### 1.1 Overview
Replace OpenAI Whisper with AssemblyAI to gain speaker diarization capabilities while maintaining transcription quality.

### 1.2 Technical Implementation

#### New File: `src/assemblyai_transcriber.py`
```python
"""
AssemblyAI Transcription with Speaker Diarization
Provides speaker-aware transcription with timestamp preservation
"""

import assemblyai as aai
from typing import List, Dict
import os

class AssemblyAITranscriber:
    def __init__(self):
        aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

    def transcribe_with_speakers(self, audio_path: str) -> List[Dict]:
        """
        Transcribe audio with speaker diarization

        Returns:
            [
                {
                    "text": "Hello, how are you?",
                    "start": 0.0,
                    "end": 2.5,
                    "speaker": "A",
                    "confidence": 0.95
                },
                ...
            ]
        """
        config = aai.TranscriptionConfig(
            speaker_labels=True,
            speakers_expected=None,  # Auto-detect number
            language_code="en",
            punctuate=True,
            format_text=True
        )

        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_path)

        return self._parse_segments(transcript)
```

#### Configuration Updates: `src/config.py`
```python
# AssemblyAI Configuration
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
USE_ASSEMBLYAI = os.getenv('USE_ASSEMBLYAI', 'false').lower() == 'true'
SPEAKER_DETECTION_ENABLED = os.getenv('SPEAKER_DETECTION_ENABLED', 'true').lower() == 'true'
MAX_SPEAKERS = int(os.getenv('MAX_SPEAKERS', 4))
SPEAKER_CONFIDENCE_THRESHOLD = float(os.getenv('SPEAKER_CONFIDENCE_THRESHOLD', 0.7))
```

### 1.3 API Integration

#### AssemblyAI Features to Utilize
- **Speaker Diarization**: Identify different speakers
- **Auto Punctuation**: Improve sentence detection
- **Confidence Scores**: Filter low-quality segments
- **Word-Level Timestamps**: Fine-grained timing control

### 1.4 Fallback Strategy
```python
def transcribe(self, audio_path: str):
    try:
        if Config.USE_ASSEMBLYAI:
            return self.assemblyai_transcribe(audio_path)
    except Exception as e:
        logger.warning(f"AssemblyAI failed: {e}, falling back to Whisper")

    return self.whisper_transcribe(audio_path)  # Existing method
```

### 1.5 Cost Analysis
- **AssemblyAI**: $0.00025 per second ($0.90/hour)
- **10-minute video**: $0.15
- **Monthly estimate (100 videos)**: $15
- **ROI**: Speaker detection adds significant value

---

## 📝 Phase 2: Paragraph-Level Translation (Weeks 2-3)

### 2.1 Overview
Group related segments into paragraphs for contextually aware translation, eliminating mid-sentence cuts.

### 2.2 Technical Implementation

#### New File: `src/segment_merger.py`
```python
"""
Intelligent Segment Merging for Paragraph-Level Translation
Groups segments by speaker and semantic boundaries
"""

class SegmentMerger:
    def __init__(self,
                 max_paragraph_duration: float = 15.0,
                 min_paragraph_duration: float = 5.0):
        self.max_duration = max_paragraph_duration
        self.min_duration = min_paragraph_duration

    def merge_to_paragraphs(self, segments: List[Dict]) -> List[Dict]:
        """
        Merge segments into paragraph-level chunks

        Strategy:
        1. Group consecutive segments by same speaker
        2. Detect sentence boundaries (., !, ?)
        3. Respect max duration limits
        4. Preserve natural speech breaks
        """
        paragraphs = []
        current_paragraph = {
            'segments': [],
            'speaker': None,
            'start': None,
            'end': None,
            'text': ''
        }

        for segment in segments:
            # Check if we should start new paragraph
            should_break = (
                self._is_sentence_end(segment['text']) or
                self._speaker_changed(current_paragraph, segment) or
                self._duration_exceeded(current_paragraph, segment)
            )

            if should_break and current_paragraph['segments']:
                paragraphs.append(self._finalize_paragraph(current_paragraph))
                current_paragraph = self._new_paragraph()

            # Add segment to current paragraph
            self._add_segment(current_paragraph, segment)

        return paragraphs

    def _is_sentence_end(self, text: str) -> bool:
        """Detect natural sentence boundaries"""
        endings = ['.', '!', '?', '."', '!"', '?"']
        return any(text.strip().endswith(e) for e in endings)
```

### 2.3 Translation Enhancement

#### Modified: `src/translator.py`
```python
def translate_paragraphs(self, paragraphs: List[Dict]) -> List[Dict]:
    """
    Translate paragraph-level text with context awareness
    """
    system_prompt = """You are translating a conversation to Georgian.
    Maintain:
    1. Speaker tone and personality
    2. Contextual references between sentences
    3. Natural conversation flow
    4. Appropriate formality levels

    The text contains multiple speakers marked as [Speaker A], [Speaker B], etc.
    Preserve these markers in your translation."""

    for paragraph in paragraphs:
        # Include speaker context in translation
        context = f"[Speaker {paragraph['speaker']}]: {paragraph['text']}"
        translation = self._translate_with_context(context, system_prompt)
        paragraph['translated_text'] = translation

    return paragraphs
```

### 2.4 Benefits
- **Context Preservation**: Related ideas stay together
- **Natural Flow**: No mid-thought interruptions
- **Better Translation**: GPT-4 has full context
- **Reduced API Calls**: Batch processing efficiency

---

## 🎭 Phase 3: Multi-Voice Support (Weeks 3-4)

### 3.1 Overview
Implement intelligent voice mapping to assign different ElevenLabs voices to detected speakers.

### 3.2 Voice Pool Configuration

#### New File: `config/voices.json`
```json
{
  "voice_pools": {
    "male": [
      {
        "id": "TX3LPaxmHKxFdv7VOQHJ",
        "name": "Liam",
        "language": "Georgian",
        "characteristics": "deep, authoritative"
      },
      {
        "id": "MALE_VOICE_2_ID",
        "name": "Giorgi",
        "language": "Georgian",
        "characteristics": "warm, friendly"
      }
    ],
    "female": [
      {
        "id": "FEMALE_VOICE_1_ID",
        "name": "Nino",
        "language": "Georgian",
        "characteristics": "clear, professional"
      },
      {
        "id": "FEMALE_VOICE_2_ID",
        "name": "Mariam",
        "language": "Georgian",
        "characteristics": "gentle, expressive"
      }
    ],
    "neutral": [
      {
        "id": "NARRATOR_VOICE_ID",
        "name": "Narrator",
        "language": "Georgian",
        "characteristics": "neutral, documentary"
      }
    ]
  },
  "assignment_rules": {
    "max_speakers": 4,
    "primary_speaker_voice": "best_quality",
    "fallback_voice": "TX3LPaxmHKxFdv7VOQHJ"
  }
}
```

### 3.3 Voice Manager Implementation

#### New File: `src/voice_manager.py`
```python
"""
Intelligent Voice Assignment and Management
Maps speakers to appropriate voices based on various factors
"""

class VoiceManager:
    def __init__(self):
        self.voice_config = self._load_voice_config()
        self.assignments = {}

    def assign_voices(self, speaker_analysis: Dict) -> Dict[str, str]:
        """
        Assign voices to speakers based on:
        1. Number of speakers
        2. Speaking time (primary speaker gets best voice)
        3. Gender hints (if detectable)
        4. User preferences
        """
        speakers_ranked = self._rank_speakers_by_time(speaker_analysis)

        for rank, speaker in enumerate(speakers_ranked):
            if rank == 0:
                # Primary speaker gets the best voice
                voice_id = self._get_primary_voice()
            elif rank < len(self.voice_config['voice_pools']['male']):
                # Assign from appropriate pool
                voice_id = self._get_voice_for_rank(rank)
            else:
                # Fallback for too many speakers
                voice_id = self.voice_config['assignment_rules']['fallback_voice']

            self.assignments[speaker] = voice_id

        return self.assignments

    def get_voice_for_segment(self, segment: Dict) -> str:
        """Get appropriate voice ID for a segment"""
        speaker = segment.get('speaker', 'default')
        return self.assignments.get(speaker, self._get_fallback_voice())
```

### 3.4 TTS Enhancement

#### Modified: `src/tts.py`
```python
def generate_voiceover_multi(self, segments: List[Dict], voice_manager: VoiceManager):
    """
    Generate voiceover with multiple voices
    """
    for segment in segments:
        voice_id = voice_manager.get_voice_for_segment(segment)

        # Cache voice settings per speaker for consistency
        voice_settings = self._get_cached_settings(voice_id)

        audio = self.client.generate(
            text=segment['translated_text'],
            voice=voice_id,
            model="eleven_turbo_v2",  # Fast model for Georgian
            voice_settings=voice_settings
        )

        segment['audio_path'] = self._save_audio(audio, segment)
        segment['voice_id'] = voice_id
```

### 3.5 Voice Consistency Rules
- **Same speaker** = Same voice throughout video
- **Primary speaker** = Highest quality voice
- **Gender matching** = When detectable (future enhancement)
- **Max 4 voices** = Avoid confusion

---

## 🎵 Phase 4: Dynamic Synchronization (Weeks 4-5)

### 4.1 Overview
Implement sophisticated audio mixing that allows natural Georgian speech flow while maintaining video sync.

### 4.2 Dynamic Mixer Implementation

#### New File: `src/dynamic_mixer.py`
```python
"""
Advanced Audio Mixing with Dynamic Synchronization
Allows Georgian overflow with intelligent original audio ducking
"""

class DynamicMixer:
    def __init__(self):
        self.overflow_allowed = Config.SUBTITLE_OVERFLOW_ALLOWED
        self.duck_factor = Config.DYNAMIC_DUCK_FACTOR

    def mix_with_overflow(self, original_audio, voiceover_segments, video_duration):
        """
        Advanced mixing strategy:
        1. Allow Georgian to overflow segment boundaries
        2. Dynamically duck original audio during speech
        3. Smooth crossfades between speakers
        4. Preserve important original audio
        """

        # Build envelope for dynamic ducking
        duck_envelope = self._build_duck_envelope(voiceover_segments, video_duration)

        # Apply envelope to original audio
        original_ducked = self._apply_envelope(original_audio, duck_envelope)

        # Mix voiceover with natural timing
        mixed = self._mix_natural_timing(original_ducked, voiceover_segments)

        return mixed

    def _build_duck_envelope(self, segments, duration):
        """
        Create volume envelope that:
        - Ducks during Georgian speech
        - Gradual fade in/out (no harsh cuts)
        - Preserves music/effects between speech
        """
        envelope = np.ones(int(duration * 44100))  # Full volume baseline

        for segment in segments:
            # Calculate actual voiceover duration (may exceed segment boundary)
            vo_duration = self._get_actual_duration(segment['audio_path'])

            # Duck original audio during voiceover + padding
            start_sample = int(segment['start'] * 44100)
            end_sample = int((segment['start'] + vo_duration) * 44100)

            # Smooth fade
            fade_samples = int(0.1 * 44100)  # 100ms fade

            # Apply ducking with fade
            self._apply_fade(envelope, start_sample, end_sample, fade_samples)

        return envelope
```

### 4.3 Synchronization Strategies

#### Strategy 1: Subtitle-Style Overflow
```python
def subtitle_style_sync(self, segments):
    """
    Allow Georgian to complete naturally, even if it extends past segment boundary
    Similar to how subtitles can appear before/after actual speech
    """
    for i, segment in enumerate(segments):
        # Check if Georgian is longer than original
        original_duration = segment['end'] - segment['start']
        georgian_duration = self._measure_tts_duration(segment['translated_text'])

        if georgian_duration > original_duration:
            # Allow overflow, but check for conflicts
            if i < len(segments) - 1:
                next_start = segments[i + 1]['start']
                max_overflow = next_start - segment['end'] - 0.2  # 200ms buffer

                if georgian_duration - original_duration <= max_overflow:
                    segment['allow_overflow'] = True
                else:
                    # Need to compress speech rate slightly
                    segment['speed_factor'] = original_duration / georgian_duration
```

#### Strategy 2: Dynamic Speech Rate
```python
def adjust_speech_rate(self, segment, target_duration):
    """
    Slightly adjust TTS speed to fit timing when necessary
    Range: 0.9x to 1.1x to maintain naturalness
    """
    current_duration = self._get_segment_duration(segment)

    if current_duration > target_duration * 1.1:
        # Too long, speed up slightly
        return self._adjust_tempo(segment, min(1.1, target_duration / current_duration))
    elif current_duration < target_duration * 0.9:
        # Too short, slow down slightly
        return self._adjust_tempo(segment, max(0.9, target_duration / current_duration))

    return segment  # No adjustment needed
```

### 4.4 Quality Assurance

#### Sync Validation
```python
def validate_synchronization(self, segments):
    """
    Check for:
    1. Overlapping segments
    2. Excessive gaps
    3. Sync drift over time
    """
    issues = []

    for i in range(len(segments) - 1):
        current_end = segments[i]['end'] + segments[i].get('overflow', 0)
        next_start = segments[i + 1]['start']

        if current_end > next_start + 0.1:  # 100ms tolerance
            issues.append({
                'type': 'overlap',
                'segments': [i, i + 1],
                'overlap_duration': current_end - next_start
            })

        gap = next_start - current_end
        if gap > 5.0:  # 5 second gap
            issues.append({
                'type': 'long_gap',
                'segments': [i, i + 1],
                'gap_duration': gap
            })

    return issues
```

---

## 🧪 Phase 5: Testing & Optimization (Weeks 5-6)

### 5.1 Test Scenarios

#### Scenario Matrix
| Content Type | Speakers | Duration | Expected Challenge |
|-------------|----------|----------|-------------------|
| News Report | 1 | 5 min | Formal tone preservation |
| Interview | 2 | 10 min | Speaker distinction |
| Panel Discussion | 4+ | 15 min | Voice management |
| Documentary | Mixed | 20 min | Narrator vs. subjects |
| Tutorial | 1 | 30 min | Technical terminology |

### 5.2 Performance Metrics

#### Quantitative Metrics
```python
class PerformanceMonitor:
    def measure_quality(self, original, processed):
        return {
            'speaker_accuracy': self._measure_speaker_accuracy(),
            'sync_quality': self._measure_sync_quality(),
            'translation_accuracy': self._measure_translation_quality(),
            'processing_speed': self._measure_processing_time(),
            'cost_per_minute': self._calculate_cost()
        }

    def _measure_sync_quality(self):
        """
        Calculate percentage of segments within acceptable sync range
        Acceptable: Georgian starts within 500ms of original
        """
        in_sync = 0
        total = len(self.segments)

        for segment in self.segments:
            offset = abs(segment['georgian_start'] - segment['original_start'])
            if offset <= 0.5:  # 500ms tolerance
                in_sync += 1

        return (in_sync / total) * 100
```

#### Qualitative Metrics
- User satisfaction surveys
- A/B testing against current system
- Professional translator review
- Native Georgian speaker feedback

### 5.3 Optimization Targets

#### Performance Goals
- **Processing Speed**: < 2x real-time
- **Memory Usage**: < 2GB per video
- **API Efficiency**: Batch where possible
- **Cache Hit Rate**: > 80% for common phrases

#### Quality Goals
- **Speaker ID Accuracy**: > 95%
- **Translation Quality**: > 4.5/5 rating
- **Sync Accuracy**: > 90% within 500ms
- **Voice Consistency**: 100% same speaker = same voice

---

## 💾 Database Schema Updates

### New Tables

```sql
-- Speaker tracking table
CREATE TABLE speakers (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(20) NOT NULL,
    speaker_label VARCHAR(10) NOT NULL,
    voice_id VARCHAR(100),
    total_duration FLOAT,
    segment_count INTEGER,
    first_appearance FLOAT,
    characteristics JSON,
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);

-- Voice assignment history
CREATE TABLE voice_assignments (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(20) NOT NULL,
    speaker_label VARCHAR(10) NOT NULL,
    voice_id VARCHAR(100) NOT NULL,
    assignment_reason VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);

-- Processing metrics
CREATE TABLE processing_metrics (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(20) NOT NULL,
    metric_type VARCHAR(50),
    metric_value FLOAT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (video_id) REFERENCES videos(video_id)
);
```

### Updated Videos Table

```sql
ALTER TABLE videos ADD COLUMN speaker_count INTEGER DEFAULT 1;
ALTER TABLE videos ADD COLUMN transcription_service VARCHAR(20) DEFAULT 'whisper';
ALTER TABLE videos ADD COLUMN voice_mapping JSON;
ALTER TABLE videos ADD COLUMN sync_quality_score FLOAT;
ALTER TABLE videos ADD COLUMN processing_version VARCHAR(10) DEFAULT 'v1';
```

---

## 📦 Dependencies & Configuration

### New Requirements

```txt
# Add to requirements.txt
assemblyai==0.33.0      # Speaker diarization
numpy==1.24.3           # Audio processing
scipy==1.11.4           # Signal processing
librosa==0.10.1         # Audio analysis
webrtcvad==2.0.10       # Voice activity detection
```

### Environment Variables

```bash
# Add to .env

# AssemblyAI
ASSEMBLYAI_API_KEY=your_api_key_here
USE_ASSEMBLYAI=true
SPEAKER_DETECTION_ENABLED=true
MAX_SPEAKERS=4
SPEAKER_CONFIDENCE_THRESHOLD=0.7

# Translation
PARAGRAPH_MODE_ENABLED=true
MAX_PARAGRAPH_DURATION=15
MIN_PARAGRAPH_DURATION=5
PRESERVE_SPEAKER_CONTEXT=true

# Voice Management
MULTI_VOICE_ENABLED=true
VOICE_ASSIGNMENT_MODE=automatic
PRIMARY_SPEAKER_VOICE_PRIORITY=true
VOICE_CONSISTENCY_ENFORCED=true

# Synchronization
SUBTITLE_OVERFLOW_ALLOWED=true
DYNAMIC_DUCKING_ENABLED=true
DUCK_FACTOR=0.15
MAX_SPEECH_RATE_ADJUSTMENT=1.1
MIN_SPEECH_RATE_ADJUSTMENT=0.9

# Quality Control
SYNC_TOLERANCE_MS=500
MAX_GAP_DURATION=5.0
MIN_GAP_DURATION=0.2
```

---

## 💰 Cost Analysis

### Current System (Per 10-min Video)
| Service | Cost | Notes |
|---------|------|-------|
| OpenAI Whisper | $0.10 | Transcription only |
| GPT-4 Translation | $0.05 | Segment-level |
| ElevenLabs TTS | $0.35 | Single voice |
| **Total** | **$0.50** | |

### Enhanced System (Per 10-min Video)
| Service | Cost | Notes |
|---------|------|-------|
| AssemblyAI | $0.15 | With speaker diarization |
| GPT-4 Translation | $0.04 | Batch paragraph processing |
| ElevenLabs TTS | $0.35 | Multiple voices, same cost |
| **Total** | **$0.54** | |

### Monthly Projections (100 videos)
- **Current**: $50/month
- **Enhanced**: $54/month
- **Additional Cost**: $4/month (+8%)
- **Value Added**: Professional multi-speaker dubbing

---

## 🚀 Deployment Strategy

### Phase Rollout

#### Week 1-2: Alpha Testing
- Deploy to staging environment
- Test with 10 sample videos
- Gather initial metrics
- Fix critical issues

#### Week 3-4: Beta Testing
- Enable for 10% of users
- A/B testing framework
- Collect feedback
- Performance optimization

#### Week 5-6: Production Rollout
- Gradual rollout to all users
- Monitor metrics closely
- Quick rollback capability
- Documentation update

### Feature Flags

```python
FEATURE_FLAGS = {
    'assemblyai_enabled': False,  # Start disabled
    'paragraph_translation': False,
    'multi_voice': False,
    'dynamic_sync': False,
    'rollout_percentage': 0  # Gradual increase
}

def should_use_new_pipeline(video_id):
    """Determine if video should use new pipeline"""
    if FEATURE_FLAGS['rollout_percentage'] == 100:
        return True

    # Use hash of video_id for consistent assignment
    import hashlib
    hash_value = int(hashlib.md5(video_id.encode()).hexdigest()[:8], 16)
    threshold = FEATURE_FLAGS['rollout_percentage'] * (2**32 - 1) / 100

    return hash_value < threshold
```

### Monitoring & Alerts

```python
class PipelineMonitor:
    def __init__(self):
        self.metrics = {
            'processing_time': [],
            'api_errors': [],
            'sync_quality': [],
            'user_feedback': []
        }

    def alert_on_degradation(self):
        """Alert if quality drops below threshold"""
        if self.get_average_sync_quality() < 85:
            self.send_alert("Sync quality degradation detected")

        if self.get_error_rate() > 5:
            self.send_alert("High error rate in new pipeline")
```

---

## 📚 Documentation Updates

### User Documentation
1. **Feature Guide**: How multi-voice works
2. **Quality Settings**: Adjusting sync preferences
3. **Troubleshooting**: Common issues and solutions
4. **API Updates**: New endpoints and parameters

### Developer Documentation
1. **Architecture Overview**: New components and flow
2. **API Reference**: AssemblyAI and voice management
3. **Configuration Guide**: All new settings explained
4. **Testing Guide**: How to test each component

---

## ✅ Success Criteria

### Must Have
- ✅ Speaker detection working (>90% accuracy)
- ✅ Multiple voices assigned correctly
- ✅ No overlapping audio segments
- ✅ Backward compatibility maintained
- ✅ Cost increase < 20%

### Should Have
- ✅ Natural conversation flow
- ✅ Sync within 500ms tolerance
- ✅ Processing time < 2x video duration
- ✅ User satisfaction improved

### Nice to Have
- Gender detection for voice matching
- Custom voice training
- Real-time preview
- Manual voice override UI

---

## 🎯 Next Steps

### Immediate Actions (This Week)
1. **Obtain AssemblyAI API key**
   - Sign up at assemblyai.com
   - Test basic transcription
   - Verify Georgian language support

2. **Test ElevenLabs Georgian voices**
   - Identify all available Georgian voices
   - Test quality and characteristics
   - Create voice profiles

3. **Set up development environment**
   - Create feature branch: `feature/multi-speaker-support`
   - Install new dependencies
   - Configure feature flags

### Development Priorities (Week 1)
1. Implement AssemblyAI transcriber
2. Create fallback mechanism
3. Test speaker detection accuracy
4. Build segment merger logic

### Testing Priorities (Week 2)
1. Create test video dataset
2. Measure baseline metrics
3. Implement A/B testing framework
4. Set up monitoring dashboard

---

## 🎉 Conclusion

This enhancement plan transforms the Georgian Voiceover App into a professional-grade dubbing system. By implementing speaker diarization, multi-voice support, paragraph-level translation, and dynamic synchronization, we'll deliver:

1. **Natural Conversations**: Multiple speakers with distinct voices
2. **Contextual Translation**: Better understanding through paragraph grouping
3. **Professional Quality**: Comparable to commercial dubbing services
4. **Flexible Synchronization**: Natural Georgian flow without rigid constraints
5. **Scalable Architecture**: Ready for future enhancements

The phased approach ensures safe deployment with minimal risk. Feature flags allow gradual rollout and quick rollback if needed. The modest cost increase (8%) is justified by the significant quality improvement.

Most importantly, this plan maintains the core mission: making English content accessible to Georgian speakers with high-quality, natural-sounding translations.

---

## 📎 Appendix

### A. Sample Code Structure

```
src/
├── transcription/
│   ├── base_transcriber.py      # Abstract base class
│   ├── whisper_transcriber.py   # OpenAI Whisper (current)
│   └── assemblyai_transcriber.py # AssemblyAI (new)
├── translation/
│   ├── translator.py            # Enhanced with paragraph mode
│   └── segment_merger.py        # New merger logic
├── tts/
│   ├── tts.py                  # Enhanced multi-voice
│   └── voice_manager.py        # New voice assignment
├── audio/
│   ├── audio_mixer.py          # Current mixer
│   └── dynamic_mixer.py        # New advanced mixer
└── utils/
    ├── config.py               # Central configuration
    └── monitoring.py           # Performance tracking
```

### B. API Response Examples

#### AssemblyAI Response
```json
{
  "utterances": [
    {
      "speaker": "A",
      "text": "Hello everyone, welcome to our discussion.",
      "start": 0,
      "end": 3500,
      "confidence": 0.97
    },
    {
      "speaker": "B",
      "text": "Thank you for having me.",
      "start": 3600,
      "end": 5200,
      "confidence": 0.95
    }
  ]
}
```

#### Voice Assignment
```json
{
  "speaker_mapping": {
    "A": "TX3LPaxmHKxFdv7VOQHJ",
    "B": "FEMALE_VOICE_ID",
    "C": "NARRATOR_VOICE_ID"
  },
  "assignment_reason": "automatic_by_speaking_time"
}
```

### C. Configuration Examples

#### Minimal Config (Current behavior)
```env
USE_ASSEMBLYAI=false
MULTI_VOICE_ENABLED=false
PARAGRAPH_MODE_ENABLED=false
```

#### Full Enhancement Config
```env
USE_ASSEMBLYAI=true
SPEAKER_DETECTION_ENABLED=true
PARAGRAPH_MODE_ENABLED=true
MULTI_VOICE_ENABLED=true
SUBTITLE_OVERFLOW_ALLOWED=true
DYNAMIC_DUCKING_ENABLED=true
```

---

**Document Version**: 1.0.0
**Last Updated**: November 2024
**Author**: Claude (with requirements from user)
**Status**: Ready for Implementation