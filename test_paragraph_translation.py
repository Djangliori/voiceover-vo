#!/usr/bin/env python3
"""
Test script for Paragraph-Level Translation (Phase 2)
Tests context-aware translation with speaker diarization
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.translator import Translator
from src.context_translator import ContextAwareTranslator
from src.segment_merger import SegmentMerger
from src.conversation_flow import ConversationFlowManager
from src.config import Config
from src.logging_config import get_logger

logger = get_logger(__name__)


def create_test_segments():
    """Create test segments simulating a dialogue"""
    segments = [
        # Speaker A introduces topic
        {
            'text': "Hello everyone, today we're discussing climate change.",
            'start': 0.0,
            'end': 3.5,
            'speaker': 'A'
        },
        {
            'text': "It's one of the most pressing issues of our time.",
            'start': 3.7,
            'end': 6.2,
            'speaker': 'A'
        },
        # Speaker B asks question
        {
            'text': "What are the main causes of climate change?",
            'start': 7.0,
            'end': 9.5,
            'speaker': 'B'
        },
        # Speaker A responds
        {
            'text': "Well, the primary cause is greenhouse gas emissions.",
            'start': 10.0,
            'end': 13.0,
            'speaker': 'A'
        },
        {
            'text': "These come from burning fossil fuels, deforestation, and industrial processes.",
            'start': 13.2,
            'end': 17.5,
            'speaker': 'A'
        },
        # Speaker B follows up
        {
            'text': "How can individuals help reduce their impact?",
            'start': 18.0,
            'end': 20.5,
            'speaker': 'B'
        },
        # Speaker A answers
        {
            'text': "There are many ways. Using renewable energy is important.",
            'start': 21.0,
            'end': 24.0,
            'speaker': 'A'
        },
        {
            'text': "Also, reducing consumption and supporting sustainable practices.",
            'start': 24.2,
            'end': 27.5,
            'speaker': 'A'
        }
    ]

    speakers = [
        {
            'id': 'A',
            'label': 'Speaker 1 (Host)',
            'utterance_count': 5,
            'total_duration': 17.3
        },
        {
            'id': 'B',
            'label': 'Speaker 2 (Guest)',
            'utterance_count': 2,
            'total_duration': 5.0
        }
    ]

    return segments, speakers


def test_segment_merger():
    """Test segment merging into paragraphs"""
    print("\n=== Testing Segment Merger ===")

    segments, speakers = create_test_segments()
    merger = SegmentMerger()

    # Test merging
    paragraphs = merger.merge_segments_to_paragraphs(segments, speakers)

    print(f"✓ Merged {len(segments)} segments into {len(paragraphs)} paragraphs")

    # Show paragraphs
    print("\n📝 Paragraphs:")
    for i, para in enumerate(paragraphs):
        speaker = para.get('speaker_label', para.get('speaker', 'Unknown'))
        duration = para['end'] - para['start']
        words = len(para['text'].split())
        print(f"   {i+1}. [{speaker}] {duration:.1f}s, {words} words")
        print(f"      \"{para['text'][:60]}...\"")

    # Test conversation turns
    turns = merger.group_by_conversation_turn(paragraphs)
    print(f"\n✓ Grouped into {len(turns)} conversation turns")

    return True


def test_conversation_flow():
    """Test conversation flow analysis"""
    print("\n=== Testing Conversation Flow Manager ===")

    segments, speakers = create_test_segments()
    flow_manager = ConversationFlowManager()

    # Analyze conversation
    analysis = flow_manager.analyze_conversation(segments, speakers)

    print("✓ Conversation Analysis:")
    print(f"   - Type: {analysis['type'].value}")
    print(f"   - Speakers: {analysis['speaker_count']}")
    print(f"   - Turns: {analysis['turn_count']}")
    print(f"   - Q&A Pairs: {analysis['question_answer_pairs']}")
    print(f"   - Pace: {analysis['dialogue_pace']}")

    # Show turns
    print("\n💬 Conversation Turns:")
    for i, turn in enumerate(flow_manager.turns):
        type_info = ""
        if turn.is_question:
            type_info = " [Question]"
        elif turn.is_response:
            type_info = " [Response]"

        print(f"   {i+1}. {turn.speaker_label}{type_info}")
        print(f"      Duration: {turn.end_time - turn.start_time:.1f}s")
        print(f"      Emotion: {turn.emotion}")

    return True


def test_context_translation():
    """Test context-aware translation"""
    print("\n=== Testing Context-Aware Translation ===")

    # Check if API key is available
    if not Config.OPENAI_API_KEY:
        print("⚠️  OPENAI_API_KEY not set, skipping translation test")
        return False

    segments, speakers = create_test_segments()

    try:
        # Initialize translator in paragraph mode
        translator = Translator(use_paragraph_mode=True)
        print("✓ Initialized translator in paragraph mode")

        # Progress callback
        def progress_callback(msg):
            print(f"   {msg}")

        # Translate with context
        print("\n🌐 Starting context-aware translation...")
        translated = translator.translate_segments(
            segments,
            progress_callback=progress_callback,
            speakers=speakers
        )

        print(f"\n✓ Translation complete: {len(translated)} segments")

        # Show sample translations
        print("\n📄 Sample Translations:")
        for i, seg in enumerate(translated[:3]):
            original = seg.get('original_text', seg.get('text', ''))
            translation = seg.get('translated_text', '')
            speaker = seg.get('speaker_label', seg.get('speaker', 'Unknown'))

            print(f"\n   {i+1}. [{speaker}]")
            print(f"      EN: {original[:60]}...")
            print(f"      GE: {translation[:60]}...")

        # Verify Georgian characters
        georgian_chars = 0
        for seg in translated:
            text = seg.get('translated_text', '')
            georgian_chars += sum(1 for c in text if 0x10A0 <= ord(c) <= 0x10FF)

        if georgian_chars > 0:
            print(f"\n✓ Verified Georgian text: {georgian_chars} Georgian characters found")
        else:
            print("\n⚠️  Warning: No Georgian characters detected in translation")

        return True

    except Exception as e:
        print(f"❌ Translation test failed: {e}")
        logger.error(f"Translation test error: {e}", exc_info=True)
        return False


def test_integration():
    """Test full integration of Phase 2 components"""
    print("\n=== Testing Full Integration ===")

    segments, speakers = create_test_segments()

    try:
        # 1. Merge segments
        merger = SegmentMerger()
        paragraphs = merger.merge_segments_to_paragraphs(segments, speakers)
        print(f"✓ Merged into {len(paragraphs)} paragraphs")

        # 2. Analyze flow
        flow_manager = ConversationFlowManager()
        analysis = flow_manager.analyze_conversation(segments, speakers)
        print(f"✓ Analyzed as {analysis['type'].value}")

        # 3. Translate (if API key available)
        if Config.OPENAI_API_KEY:
            translator = Translator(use_paragraph_mode=True)
            translated = translator.translate_segments(segments, speakers=speakers)
            print(f"✓ Translated {len(translated)} segments")

            # 4. Optimize for voiceover
            optimized = flow_manager.optimize_for_voiceover(translated)
            print(f"✓ Optimized for voiceover")

            # Check for pause hints
            pauses_added = sum(1 for seg in optimized if 'pause_before' in seg)
            print(f"   - Added pause hints to {pauses_added} segments")

            # Check for emotion hints
            emotions_added = sum(1 for seg in optimized if 'emotion_hint' in seg)
            print(f"   - Added emotion hints to {emotions_added} segments")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        logger.error(f"Integration test error: {e}", exc_info=True)
        return False


def main():
    """Run all Phase 2 tests"""
    print("=" * 60)
    print("Phase 2: Paragraph-Level Translation Test Suite")
    print("=" * 60)

    # Check environment
    print("\n📋 Environment Check:")
    print(f"   - OPENAI_API_KEY: {'✓ Set' if Config.OPENAI_API_KEY else '❌ Not set'}")
    print(f"   - ASSEMBLYAI_API_KEY: {'✓ Set' if Config.ASSEMBLYAI_API_KEY else '❌ Not set'}")

    # Run tests
    results = []

    # Test 1: Segment Merger
    results.append(("Segment Merger", test_segment_merger()))

    # Test 2: Conversation Flow
    results.append(("Conversation Flow", test_conversation_flow()))

    # Test 3: Context Translation
    if Config.OPENAI_API_KEY:
        results.append(("Context Translation", test_context_translation()))
    else:
        print("\n⚠️  Skipping translation test (no API key)")

    # Test 4: Integration
    results.append(("Integration", test_integration()))

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
        print("\n🎉 All Phase 2 tests passed!")
        print("\nNext steps:")
        print("1. Deploy and test with real videos")
        print("2. Monitor translation quality with speaker context")
        print("3. Proceed to Phase 3: Multi-Voice Support")
    else:
        print("\n⚠️  Some tests failed. Please check the logs.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())