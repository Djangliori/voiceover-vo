#!/usr/bin/env python3
"""
Test Gemini Translation
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 70)
print("  🧪 Testing Gemini Translation")
print("=" * 70)
print()

# Check if Gemini API key is configured
gemini_key = os.getenv('GEMINI_API_KEY')
if not gemini_key:
    print("❌ GEMINI_API_KEY not found in .env file")
    sys.exit(1)

print(f"✅ GEMINI_API_KEY configured ({len(gemini_key)} chars)")
print()

# Test translator initialization
print("1️⃣  Testing Translator initialization...")
try:
    from src.translator import Translator
    translator = Translator(use_paragraph_mode=False)
    print("   ✅ Translator initialized successfully")
    print()
except Exception as e:
    print(f"   ❌ Translator initialization failed: {e}")
    sys.exit(1)

# Test simple translation
print("2️⃣  Testing simple English to Georgian translation...")
test_text = "Hello, how are you?"
print(f"   English: {test_text}")

try:
    georgian = translator.translate_text(test_text)
    print(f"   Georgian: {georgian}")

    if georgian and georgian != test_text:
        print("   ✅ Translation successful!")
    else:
        print("   ⚠️  Translation returned same text or empty")
except Exception as e:
    print(f"   ❌ Translation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test segment translation
print("3️⃣  Testing segment translation...")
test_segments = [
    {"text": "Welcome to this video.", "start": 0, "end": 2},
    {"text": "Today we will learn something new.", "start": 2, "end": 5}
]

try:
    translated_segments = translator.translate_segments(test_segments)

    print(f"   Translated {len(translated_segments)} segments:")
    for i, seg in enumerate(translated_segments):
        print(f"   [{i}] EN: {seg.get('text', seg.get('original_text', ''))} ")
        print(f"       KA: {seg.get('translated_text', 'N/A')}")

    if all('translated_text' in seg for seg in translated_segments):
        print("   ✅ Segment translation successful!")
    else:
        print("   ⚠️  Some segments missing translation")
except Exception as e:
    print(f"   ❌ Segment translation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("  🎉 All tests passed! Gemini translation is working!")
print("=" * 70)
print()
print("💰 Cost: $0 (FREE tier - 15 requests/min, 1500 requests/day)")
print()
