"""
Speaker Detection Microservice
Uses pyannote.audio to detect who is speaking when
"""

import os
import json
from pathlib import Path
from flask import Flask, request, jsonify
from pyannote.audio import Pipeline
import torch

app = Flask(__name__)

# Load speaker diarization pipeline
print("Loading pyannote.audio speaker diarization pipeline...")
HUGGING_FACE_TOKEN = os.getenv('HUGGING_FACE_TOKEN')

if not HUGGING_FACE_TOKEN:
    print("WARNING: HUGGING_FACE_TOKEN not set - using default pipeline")
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=False
    )
else:
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=HUGGING_FACE_TOKEN
    )

# Use GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
pipeline = pipeline.to(device)
print(f"Pipeline loaded on device: {device}")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'speaker-detection',
        'device': str(device)
    })


@app.route('/detect-speakers', methods=['POST'])
def detect_speakers():
    """
    Detect speakers in audio file

    Request JSON:
    {
        "audio_path": "/path/to/audio.wav"
    }

    Response JSON:
    {
        "speakers": [
            {
                "start": 0.5,
                "end": 10.2,
                "speaker": "SPEAKER_00"
            },
            ...
        ],
        "num_speakers": 2
    }
    """
    try:
        data = request.json
        audio_path = data.get('audio_path')

        if not audio_path:
            return jsonify({'error': 'audio_path is required'}), 400

        if not os.path.exists(audio_path):
            return jsonify({'error': f'Audio file not found: {audio_path}'}), 404

        print(f"Processing: {audio_path}")

        # Run speaker diarization
        diarization = pipeline(audio_path)

        # Convert to list of segments
        speakers = []
        speaker_set = set()

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speakers.append({
                'start': float(turn.start),
                'end': float(turn.end),
                'speaker': speaker
            })
            speaker_set.add(speaker)

        result = {
            'speakers': speakers,
            'num_speakers': len(speaker_set),
            'speaker_labels': sorted(list(speaker_set))
        }

        print(f"Detected {len(speaker_set)} speakers in {len(speakers)} segments")

        return jsonify(result)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/assign-voices', methods=['POST'])
def assign_voices():
    """
    Assign voice gender to speaker segments

    Request JSON:
    {
        "speaker_segments": [...],  // from /detect-speakers
        "voice_mapping": {
            "SPEAKER_00": "male",
            "SPEAKER_01": "female"
        }
    }

    Response JSON:
    {
        "segments": [
            {
                "start": 0.5,
                "end": 10.2,
                "speaker": "SPEAKER_00",
                "voice": "male"
            }
        ]
    }
    """
    try:
        data = request.json
        speaker_segments = data.get('speaker_segments', [])
        voice_mapping = data.get('voice_mapping', {})

        # Default mapping: alternate male/female
        if not voice_mapping:
            voice_mapping = {
                'SPEAKER_00': 'male',
                'SPEAKER_01': 'female',
                'SPEAKER_02': 'male',
                'SPEAKER_03': 'female',
            }

        # Assign voices
        segments = []
        for seg in speaker_segments:
            speaker = seg.get('speaker')
            voice = voice_mapping.get(speaker, 'male')  # Default to male

            segments.append({
                'start': seg['start'],
                'end': seg['end'],
                'speaker': speaker,
                'voice': voice
            })

        return jsonify({'segments': segments})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("  Speaker Detection Service")
    print("  Port: 5002")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5002, debug=False)
