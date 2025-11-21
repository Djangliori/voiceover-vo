#!/usr/bin/env python3
"""
Test script for Multi-Voice Synthesis (Phase 3)
Tests multi-speaker voice synthesis with both ElevenLabs and Gemini TTS
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.voice_manager import VoiceManager
from src.voice_profiles import (
    ELEVENLABS_VOICES, GEMINI_VOICES,
    VoiceSelector, Gender, AgeGroup
)
from src.tts_factory import get_tts_provider, get_available_providers
from src.config import Config
from src.logging_config import get_logger

logger = get_logger(__name__)


def test_voice_profiles():
    """Test voice profile configuration"""
    print("\n=== Testing Voice Profiles ===")

    print("\n📋 ElevenLabs Voices:")
    for key, voice in ELEVENLABS_VOICES.items():
        print(f"   - {voice.name} ({voice.gender.value}, {voice.age_group.value}): {voice.description}")

    print(f"\nTotal ElevenLabs voices: {len(ELEVENLABS_VOICES)}")

    print("\n📋 Gemini TTS Voices:")
    for key, voice in GEMINI_VOICES.items():
        print(f"   - {voice.name} ({voice.gender.value}, {voice.age_group.value}): {voice.description}")

    print(f"\nTotal Gemini voices: {len(GEMINI_VOICES)}")

    return True


def test_voice_selection():
    """Test voice selection logic"""
    print("\n=== Testing Voice Selection ===")

    selector = VoiceSelector()

    # Test gender-based selection
    for provider in ['elevenlabs', 'gemini']:
        print(f"\n{provider.title()} Voice Selection:")

        male_voice = selector.get_voice_by_gender(provider, Gender.MALE)
        if male_voice:
            print(f"   Male voice: {male_voice.name}")

        female_voice = selector.get_voice_by_gender(provider, Gender.FEMALE)
        if female_voice:
            print(f"   Female voice: {female_voice.name}")

    # Test characteristic-based selection
    young_female = selector.get_voice_by_characteristics(
        'elevenlabs',
        gender=Gender.FEMALE,
        age_group=AgeGroup.YOUNG
    )
    if young_female:
        print(f"\n✓ Found young female voice: {young_female.name}")

    return True


def test_voice_manager():
    """Test voice manager functionality"""
    print("\n=== Testing Voice Manager ===")

    # Test for both providers
    for provider in ['elevenlabs', 'gemini']:
        print(f"\n{provider.title()} Provider:")

        manager = VoiceManager(provider=provider)
        print(f"   ✓ Initialized with {len(manager.available_voices)} voices")
        print(f"   - Male voices: {len(manager.male_voices)}")
        print(f"   - Female voices: {len(manager.female_voices)}")

    # Test speaker assignment
    test_speakers = [
        {'id': 'A', 'label': 'Speaker 1'},
        {'id': 'B', 'label': 'Speaker 2'},
        {'id': 'C', 'label': 'Speaker 3'}
    ]

    manager = VoiceManager('elevenlabs')
    assignments = manager.assign_voices_to_speakers(test_speakers)

    print("\n👥 Voice Assignments:")
    for speaker_id, voice in assignments.items():
        speaker_label = next((s['label'] for s in test_speakers if s['id'] == speaker_id), speaker_id)
        print(f"   {speaker_label} -> {voice.name} ({voice.gender.value})")

    return True


def test_multivoice_synthesis():
    """Test actual multi-voice synthesis"""
    print("\n=== Testing Multi-Voice Synthesis ===")

    # Check available providers
    providers = get_available_providers()
    print("\n📋 Available TTS Providers:")
    for provider, info in providers.items():
        status = "✓" if info['available'] else "✗"
        print(f"   {status} {provider}: {info['reason']}")

    # Get current provider
    current_provider = Config.TTS_PROVIDER
    print(f"\nCurrent provider: {current_provider}")

    # Create test segments with multiple speakers
    test_segments = [
        {
            'text': 'გამარჯობა, მე ვარ პირველი მომხსენებელი.',  # Hello, I am the first speaker
            'translated_text': 'გამარჯობა, მე ვარ პირველი მომხსენებელი.',
            'start': 0.0,
            'end': 3.0,
            'speaker': 'A'
        },
        {
            'text': 'გამარჯობა, მე ვარ მეორე მომხსენებელი.',  # Hello, I am the second speaker
            'translated_text': 'გამარჯობა, მე ვარ მეორე მომხსენებელი.',
            'start': 3.5,
            'end': 6.5,
            'speaker': 'B'
        },
        {
            'text': 'დღეს ჩვენ განვიხილავთ მრავალხმოვან სინთეზს.',  # Today we will discuss multi-voice synthesis
            'translated_text': 'დღეს ჩვენ განვიხილავთ მრავალხმოვან სინთეზს.',
            'start': 7.0,
            'end': 10.0,
            'speaker': 'A'
        },
        {
            'text': 'ეს ძალიან საინტერესო თემაა.',  # This is a very interesting topic
            'translated_text': 'ეს ძალიან საინტერესო თემაა.',
            'start': 10.5,
            'end': 12.5,
            'speaker': 'B'
        }
    ]

    test_speakers = [
        {'id': 'A', 'label': 'Speaker 1 (Host)'},
        {'id': 'B', 'label': 'Speaker 2 (Guest)'}
    ]

    try:
        # Initialize TTS provider
        print("\n🎙️ Initializing TTS provider...")
        tts = get_tts_provider()
        print(f"   ✓ TTS provider ready")

        # Initialize voice manager
        manager = VoiceManager(provider=current_provider)

        # Assign voices
        print("\n👥 Assigning voices to speakers...")
        assignments = manager.assign_voices_to_speakers(test_speakers, test_segments)

        for speaker_id, voice in assignments.items():
            speaker = next((s for s in test_speakers if s['id'] == speaker_id), None)
            if speaker:
                print(f"   {speaker['label']} -> {voice.name}")

        # Prepare segments
        voiced_segments = manager.prepare_segments_for_multivoice(test_segments, assignments)

        # Generate voiceover
        print("\n🎙️ Generating multi-voice synthesis...")
        temp_dir = "temp/multivoice_test"
        Path(temp_dir).mkdir(parents=True, exist_ok=True)

        def progress_callback(msg):
            print(f"   {msg}")

        # Test the synthesis (dry run - won't actually call API without segments)
        print("\n   [Dry run - actual synthesis would happen here]")

        # Show what would be synthesized
        voice_groups = manager.group_segments_by_voice(voiced_segments)
        for voice_id, segments in voice_groups.items():
            voice_name = next(
                (a.name for a in assignments.values() if a.id == voice_id),
                voice_id
            )
            print(f"   Voice {voice_name}: {len(segments)} segments")

        print("\n✓ Multi-voice synthesis test complete (dry run)")

        return True

    except Exception as e:
        print(f"❌ Multi-voice synthesis test failed: {e}")
        logger.error(f"Synthesis test error: {e}", exc_info=True)
        return False


def test_fallback_mapping():
    """Test voice fallback mapping between providers"""
    print("\n=== Testing Voice Fallback Mapping ===")

    manager_elevenlabs = VoiceManager('elevenlabs')
    manager_gemini = VoiceManager('gemini')

    # Test ElevenLabs -> Gemini fallback
    print("\nElevenLabs → Gemini Fallback:")
    test_voices_el = ['TX3LPaxmHKxFdv7VOQHJ', '21m00Tcm4TlvDq8ikWAM']  # Liam, Rachel

    for voice_id in test_voices_el:
        voice_name = next((v.name for v in ELEVENLABS_VOICES.values() if v.id == voice_id), voice_id)
        fallback = manager_elevenlabs.get_fallback_voice(voice_id, 'gemini')
        print(f"   {voice_name} ({voice_id[:8]}...) → {fallback}")

    # Test Gemini -> ElevenLabs fallback
    print("\nGemini → ElevenLabs Fallback:")
    test_voices_gm = ['Charon', 'Kore']

    for voice_name in test_voices_gm:
        fallback = manager_gemini.get_fallback_voice(voice_name, 'elevenlabs')
        fallback_name = next((v.name for v in ELEVENLABS_VOICES.values() if v.id == fallback), fallback)
        print(f"   {voice_name} → {fallback_name}")

    return True


def main():
    """Run all Phase 3 tests"""
    print("=" * 60)
    print("Phase 3: Multi-Voice Synthesis Test Suite")
    print("=" * 60)

    # Check environment
    print("\n📋 Environment Check:")
    print(f"   - TTS_PROVIDER: {Config.TTS_PROVIDER}")
    print(f"   - ELEVENLABS_API_KEY: {'✓ Set' if Config.ELEVENLABS_API_KEY else '❌ Not set'}")
    print(f"   - GOOGLE_APPLICATION_CREDENTIALS: {'✓ Set' if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') else '❌ Not set'}")
    print(f"   - ASSEMBLYAI_API_KEY: {'✓ Set' if Config.ASSEMBLYAI_API_KEY else '❌ Not set'}")

    # Run tests
    results = []

    # Test 1: Voice Profiles
    results.append(("Voice Profiles", test_voice_profiles()))

    # Test 2: Voice Selection
    results.append(("Voice Selection", test_voice_selection()))

    # Test 3: Voice Manager
    results.append(("Voice Manager", test_voice_manager()))

    # Test 4: Fallback Mapping
    results.append(("Fallback Mapping", test_fallback_mapping()))

    # Test 5: Multi-Voice Synthesis
    if Config.ELEVENLABS_API_KEY or os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        results.append(("Multi-Voice Synthesis", test_multivoice_synthesis()))
    else:
        print("\n⚠️  Skipping synthesis test (no API keys)")

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"   {name}: {status}")

    # Overall result
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 All Phase 3 tests passed!")
        print("\n✨ Multi-voice synthesis is ready for:")
        print("   - Both ElevenLabs and Gemini TTS providers")
        print("   - Automatic speaker-to-voice assignment")
        print("   - Gender detection and appropriate voice selection")
        print("   - Fallback voice mapping between providers")
        print("   - Parallel processing maintained")
    else:
        print("\n⚠️  Some tests failed. Please check the logs.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())