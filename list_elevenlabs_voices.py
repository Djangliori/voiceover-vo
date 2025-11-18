"""
List all available voices from ElevenLabs and find Georgian-compatible ones
"""

import os
from elevenlabs import ElevenLabs

# Load API key
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('ELEVENLABS_API_KEY')
client = ElevenLabs(api_key=api_key)

print("Fetching all available voices from ElevenLabs...")
print("=" * 80)

try:
    # Get all voices
    voices = client.voices.get_all()

    print(f"\nFound {len(voices.voices)} voices\n")

    # List all voices with their details
    for voice in voices.voices:
        print(f"Name: {voice.name}")
        print(f"Voice ID: {voice.voice_id}")
        print(f"Category: {voice.category if hasattr(voice, 'category') else 'N/A'}")
        if hasattr(voice, 'labels') and voice.labels:
            print(f"Labels: {voice.labels}")
        if hasattr(voice, 'description') and voice.description:
            print(f"Description: {voice.description}")
        print("-" * 80)

except Exception as e:
    print(f"Error: {e}")
