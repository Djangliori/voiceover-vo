#!/usr/bin/env python3
"""
Test Google Cloud TTS
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 70)
print("  🧪 Testing Google Cloud TTS")
print("=" * 70)
print()

# Check credentials
google_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
print(f"1️⃣  GOOGLE_APPLICATION_CREDENTIALS: {google_creds}")

if google_creds:
    import os.path
    if os.path.exists(google_creds):
        print(f"   ✅ File exists: {google_creds}")
    else:
        print(f"   ❌ File NOT found: {google_creds}")
        sys.exit(1)
else:
    print("   ❌ Environment variable not set")
    sys.exit(1)

print()

# Test TTS initialization
print("2️⃣  Testing TTS initialization...")
try:
    from src.tts_gemini import GeminiTextToSpeech
    tts = GeminiTextToSpeech()
    print(f"   ✅ TTS initialized successfully!")
    print(f"   Model: {tts.model_name}")
    print(f"   Voice: {tts.voice_name}")
    print(f"   Language: {tts.language_code}")
except Exception as e:
    print(f"   ❌ TTS initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test simple TTS generation
print("3️⃣  Testing simple TTS generation...")
test_segments = [
    {
        'translated_text': 'გამარჯობა',
        'start': 0,
        'end': 1
    }
]

try:
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        result = tts.generate_voiceover(test_segments, temp_dir=temp_dir)

        if result and len(result) > 0:
            audio_path = result[0].get('audio_path')
            if audio_path and os.path.exists(audio_path):
                print(f"   ✅ TTS generation successful!")
                print(f"   Audio file: {audio_path}")
                print(f"   File size: {os.path.getsize(audio_path)} bytes")
            else:
                print(f"   ❌ Audio file not generated")
                sys.exit(1)
        else:
            print(f"   ❌ No result returned")
            sys.exit(1)
except Exception as e:
    print(f"   ❌ TTS generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("  🎉 All TTS tests passed!")
print("=" * 70)
print()
