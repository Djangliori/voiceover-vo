"""
Test script to list available Georgian voices in Google Cloud TTS
"""

import os
from google.cloud import texttospeech

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-credentials.json'

# Create client
client = texttospeech.TextToSpeechClient()

# List all voices
voices = client.list_voices()

# Filter for Georgian voices
print("Available Georgian (ka) voices:")
print("-" * 50)

georgian_voices = []
for voice in voices.voices:
    for language_code in voice.language_codes:
        if language_code.startswith('ka'):
            georgian_voices.append(voice)
            print(f"Name: {voice.name}")
            print(f"Language: {language_code}")
            print(f"Gender: {texttospeech.SsmlVoiceGender(voice.ssml_gender).name}")
            print("-" * 50)

if not georgian_voices:
    print("No Georgian voices found!")
    print("\nShowing all available languages:")
    languages = set()
    for voice in voices.voices:
        for lang in voice.language_codes:
            languages.add(lang)

    for lang in sorted(languages):
        print(f"  {lang}")
