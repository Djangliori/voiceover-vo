#!/usr/bin/env python3
"""
Test script for AssemblyAI integration
Tests transcription with speaker diarization
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.transcriber import Transcriber
from src.assemblyai_transcriber import AssemblyAITranscriber
from src.config import Config
from src.logging_config import get_logger

logger = get_logger(__name__)


def test_direct_assemblyai():
    """Test AssemblyAI directly"""
    print("\n=== Testing Direct AssemblyAI ===")

    # Check API key
    api_key = Config.ASSEMBLYAI_API_KEY
    if not api_key:
        print("❌ ASSEMBLYAI_API_KEY not configured")
        return False

    print(f"✓ AssemblyAI API key configured")

    try:
        # Initialize AssemblyAI transcriber
        transcriber = AssemblyAITranscriber(api_key)
        print("✓ AssemblyAI transcriber initialized")

        # Find a test audio file
        test_files = [
            "temp/test_audio.wav",
            "output/test.wav",
            "test.wav"
        ]

        test_audio = None
        for file in test_files:
            if os.path.exists(file):
                test_audio = file
                break

        if not test_audio:
            print("⚠️  No test audio file found. Creating sample...")
            # You can download a sample or use existing audio
            print("   Please provide a test audio file at temp/test_audio.wav")
            return False

        print(f"✓ Using test audio: {test_audio}")

        # Test transcription with speaker diarization
        def progress_callback(msg):
            print(f"   {msg}")

        print("\n📝 Starting transcription with speaker diarization...")
        segments, speakers = transcriber.transcribe_with_speakers(
            test_audio,
            progress_callback=progress_callback,
            speaker_count=None  # Auto-detect speakers
        )

        print(f"\n✓ Transcription complete!")
        print(f"   - {len(segments)} segments found")
        print(f"   - {len(speakers)} speakers detected")

        # Display speaker info
        if speakers:
            print("\n👥 Speaker Information:")
            for speaker in speakers:
                print(f"   - {speaker['label']}: {speaker['utterance_count']} utterances, "
                      f"{speaker['total_duration']:.1f}s total")

        # Display sample segments
        if segments:
            print("\n📄 Sample Segments (first 3):")
            for i, seg in enumerate(segments[:3]):
                speaker = seg.get('speaker', 'Unknown')
                print(f"   [{speaker}] {seg['start']:.1f}s - {seg['end']:.1f}s: {seg['text'][:50]}...")

        return True

    except Exception as e:
        print(f"❌ AssemblyAI test failed: {e}")
        logger.error(f"AssemblyAI test error: {e}", exc_info=True)
        return False


def test_transcriber_integration():
    """Test the main Transcriber with AssemblyAI integration"""
    print("\n=== Testing Transcriber Integration ===")

    try:
        # Check configuration
        provider = Config.TRANSCRIPTION_PROVIDER
        print(f"✓ Transcription provider: {provider}")
        print(f"✓ Speaker diarization: {Config.ENABLE_SPEAKER_DIARIZATION}")

        # Initialize transcriber
        transcriber = Transcriber()
        print(f"✓ Transcriber initialized with provider: {transcriber.provider}")

        # Find test audio
        test_audio = None
        for file in ["temp/test_audio.wav", "output/test.wav", "test.wav"]:
            if os.path.exists(file):
                test_audio = file
                break

        if not test_audio:
            print("⚠️  No test audio file found")
            return False

        print(f"✓ Using test audio: {test_audio}")

        # Test transcription
        def progress_callback(msg):
            print(f"   {msg}")

        print("\n📝 Starting transcription...")
        segments = transcriber.transcribe(
            test_audio,
            progress_callback=progress_callback
        )

        print(f"\n✓ Transcription complete!")
        print(f"   - {len(segments)} segments")
        print(f"   - Has speaker info: {transcriber.has_speaker_diarization()}")

        # Check speaker information
        if transcriber.has_speaker_diarization():
            speakers = transcriber.get_speakers()
            print(f"   - {len(speakers)} speakers detected")

            print("\n👥 Speaker Information:")
            for speaker in speakers:
                print(f"   - {speaker['label']}: {speaker['utterance_count']} utterances")

        # Show sample segments
        if segments:
            print("\n📄 Sample Segments (first 3):")
            for seg in segments[:3]:
                speaker = seg.get('speaker', 'N/A')
                print(f"   [Speaker {speaker}] {seg['start']:.1f}s: {seg['text'][:60]}...")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        logger.error(f"Integration test error: {e}", exc_info=True)
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("AssemblyAI Integration Test Suite")
    print("=" * 60)

    # Check environment
    print("\n📋 Environment Check:")
    print(f"   - ASSEMBLYAI_API_KEY: {'✓ Set' if Config.ASSEMBLYAI_API_KEY else '❌ Not set'}")
    print(f"   - OPENAI_API_KEY: {'✓ Set' if Config.OPENAI_API_KEY else '❌ Not set'}")
    print(f"   - Provider: {Config.TRANSCRIPTION_PROVIDER}")
    print(f"   - Diarization: {Config.ENABLE_SPEAKER_DIARIZATION}")

    # Run tests
    results = []

    # Test 1: Direct AssemblyAI
    if Config.ASSEMBLYAI_API_KEY:
        results.append(("Direct AssemblyAI", test_direct_assemblyai()))
    else:
        print("\n⚠️  Skipping direct AssemblyAI test (no API key)")

    # Test 2: Integration
    results.append(("Transcriber Integration", test_transcriber_integration()))

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
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Please check the logs.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())