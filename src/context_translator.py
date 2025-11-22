"""
Context-Aware Translation Module
Translates paragraphs with conversation context and speaker awareness
Maintains natural flow and coherence across multi-speaker dialogue
"""

import os
import time
import json
from typing import List, Dict, Optional, Tuple
import openai
from src.config import Config
from src.segment_merger import SegmentMerger
from src.logging_config import get_logger

logger = get_logger(__name__)


class ContextAwareTranslator:
    """Translates with conversation context and speaker awareness"""

    def __init__(self):
        """Initialize context-aware translator"""
        # Set OpenAI API key for v0.28.1 compatibility
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        openai.api_key = api_key

        # Initialize segment merger
        self.merger = SegmentMerger()

        # Translation cache for consistency
        self.translation_cache = {}
        self.speaker_styles = {}

    def translate_conversation(
        self,
        segments: List[Dict],
        speakers: Optional[List[Dict]] = None,
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Translate entire conversation with context awareness

        Args:
            segments: List of transcription segments
            speakers: Optional speaker information
            progress_callback: Progress callback function

        Returns:
            List of translated segments
        """
        logger.info("="*60)
        logger.info("TRANSLATION PROCESS START")
        logger.info(f"Input: {len(segments)} segments, {len(speakers) if speakers else 0} speakers")

        # Log input segments
        for i, seg in enumerate(segments[:3]):
            logger.info(f"Segment {i}: Speaker={seg.get('speaker')}, Time=[{seg.get('start', 0):.1f}-{seg.get('end', 0):.1f}s]")
            logger.info(f"  English: {seg.get('text', '')[:100]}...")

        if progress_callback:
            progress_callback("Preparing segments for translation...")

        # Step 1: Merge segments into paragraphs
        paragraphs = self.merger.merge_segments_to_paragraphs(segments, speakers)
        logger.info(f"Merged {len(segments)} segments into {len(paragraphs)} paragraphs")

        # Step 2: Analyze speaker styles if available
        if speakers and len(speakers) > 1:
            self._analyze_speaker_styles(paragraphs, speakers)

        # Step 3: Translate paragraphs with context
        translated_paragraphs = []
        total_paragraphs = len(paragraphs)

        for i, paragraph in enumerate(paragraphs):
            if progress_callback:
                progress = int((i / total_paragraphs) * 100)
                speaker_info = f" [{paragraph.get('speaker_label', 'Speaker')}]" if 'speaker' in paragraph else ""
                progress_callback(f"Translating paragraph {i+1}/{total_paragraphs}{speaker_info} ({progress}%)")

            # Get context for this paragraph
            context = self.merger.calculate_translation_context(paragraphs, i)

            # Translate with context
            translated = self._translate_paragraph_with_context(
                paragraph,
                context,
                translated_paragraphs  # Previously translated for consistency
            )

            # Log translation result
            logger.info(f"Translated paragraph {i+1}:")
            logger.info(f"  English: {paragraph.get('text', '')[:100]}...")
            logger.info(f"  Georgian: {translated.get('translated_text', '')[:100]}...")

            translated_paragraphs.append(translated)

            # Small delay to avoid rate limiting
            if i < total_paragraphs - 1:
                time.sleep(0.5)

        # Step 4: Split paragraphs back to original timing if needed
        final_segments = self._restore_original_timing(
            translated_paragraphs,
            segments,
            progress_callback
        )

        if progress_callback:
            progress_callback(f"Translation complete: {len(final_segments)} segments")

        return final_segments

    def _analyze_speaker_styles(self, paragraphs: List[Dict], speakers: List[Dict]):
        """
        Analyze speaking styles for each speaker to maintain consistency

        Args:
            paragraphs: List of paragraphs with speaker info
            speakers: Speaker profiles
        """
        for speaker in speakers:
            speaker_id = speaker['id']

            # Collect all text from this speaker
            speaker_texts = [
                p['text'] for p in paragraphs
                if p.get('speaker') == speaker_id
            ]

            if speaker_texts:
                # Analyze speaking style
                style = {
                    'formal': self._is_formal_speech(speaker_texts),
                    'avg_sentence_length': self._avg_sentence_length(speaker_texts),
                    'uses_questions': self._uses_questions(speaker_texts),
                    'label': speaker.get('label', f'Speaker {speaker_id}')
                }

                self.speaker_styles[speaker_id] = style
                logger.info(f"Analyzed style for {style['label']}: formal={style['formal']}")

    def _translate_paragraph_with_context(
        self,
        paragraph: Dict,
        context: Dict,
        previous_translations: List[Dict]
    ) -> Dict:
        """
        Translate a paragraph with full context

        Args:
            paragraph: Paragraph to translate
            context: Context information
            previous_translations: Previously translated paragraphs

        Returns:
            Translated paragraph
        """
        # Build context-aware prompt
        prompt = self._build_translation_prompt(
            paragraph,
            context,
            previous_translations
        )

        # Check cache for repeated phrases
        cache_key = self._get_cache_key(paragraph['text'])
        if cache_key in self.translation_cache:
            logger.debug(f"Using cached translation for repeated phrase")
            translation = self.translation_cache[cache_key]
        else:
            # Call GPT-4 for translation
            translation = self._call_gpt4_translation(prompt, paragraph)
            # Cache common phrases
            if len(paragraph['text'].split()) <= 10:
                self.translation_cache[cache_key] = translation

        # Create translated paragraph
        translated = paragraph.copy()
        translated['original_text'] = paragraph['text']
        translated['text'] = translation
        translated['translated'] = True

        return translated

    def _build_translation_prompt(
        self,
        paragraph: Dict,
        context: Dict,
        previous_translations: List[Dict]
    ) -> str:
        """
        Build a context-aware translation prompt

        Args:
            paragraph: Current paragraph to translate
            context: Context information
            previous_translations: Previous translations

        Returns:
            Prompt for GPT-4
        """
        prompt_parts = []

        # System instruction
        prompt_parts.append(
            "You are translating a conversation from English to Georgian. "
            "Maintain natural conversation flow and speaker consistency."
        )

        # Add speaker context if available
        if 'speaker' in paragraph:
            speaker_id = paragraph['speaker']
            speaker_label = paragraph.get('speaker_label', f'Speaker {speaker_id}')

            prompt_parts.append(f"\nCurrent speaker: {speaker_label}")

            # Add speaker style if analyzed
            if speaker_id in self.speaker_styles:
                style = self.speaker_styles[speaker_id]
                if style['formal']:
                    prompt_parts.append("This speaker uses formal language.")
                else:
                    prompt_parts.append("This speaker uses casual language.")

        # Add conversation flow context
        if context['conversation_flow']:
            flow_type = context['conversation_flow'][0]
            if flow_type == 'responding_to_question':
                prompt_parts.append("\nThis is a response to a question.")
            elif flow_type == 'dialogue':
                prompt_parts.append("\nThis is part of a dialogue between multiple speakers.")

        # Add previous context (last 2 exchanges)
        if context['previous']:
            prompt_parts.append("\n\nPrevious context:")
            for prev in context['previous'][-2:]:  # Last 2 paragraphs
                speaker_info = f"[{prev.get('speaker_label', 'Speaker')}] " if 'speaker' in prev else ""
                # Find the translation if available
                prev_translation = None
                for trans in previous_translations:
                    if trans.get('start') == prev.get('start'):
                        prev_translation = trans.get('text')
                        break

                if prev_translation:
                    prompt_parts.append(f"{speaker_info}English: {prev['text']}")
                    prompt_parts.append(f"{speaker_info}Georgian: {prev_translation}")

        # Add current text to translate
        prompt_parts.append(f"\n\nTranslate to Georgian:\n{paragraph['text']}")

        # Special instructions
        prompt_parts.append(
            "\n\nInstructions:\n"
            "1. Maintain the conversational tone\n"
            "2. Keep consistency with previous translations\n"
            "3. Preserve any emphasis or emotion\n"
            "4. If this is a response, make it flow naturally from the previous question\n"
            "5. Return ONLY the Georgian translation, no explanations"
        )

        return '\n'.join(prompt_parts)

    def _call_gpt4_translation(self, prompt: str, paragraph: Dict) -> str:
        """
        Call GPT-4 API for translation

        Args:
            prompt: Translation prompt
            paragraph: Paragraph being translated

        Returns:
            Translated text
        """
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # Use OpenAI v0.28.1 API
                response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional English to Georgian translator specializing in natural conversation."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Lower temperature for consistency
                    max_tokens=500,
                    timeout=Config.OPENAI_TIMEOUT
                )

                translation = response['choices'][0]['message']['content'].strip()

                # Validate translation (should contain Georgian characters)
                if self._is_valid_georgian(translation):
                    return translation
                else:
                    logger.warning("Translation doesn't contain Georgian characters, retrying...")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    continue

            except Exception as e:
                logger.error(f"Translation API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    # Return original as fallback
                    logger.error("Translation failed, returning original text")
                    return paragraph['text']

        return paragraph['text']  # Fallback

    def _restore_original_timing(
        self,
        translated_paragraphs: List[Dict],
        original_segments: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Split translated paragraphs back to match original segment timing

        Args:
            translated_paragraphs: Translated paragraph-level text
            original_segments: Original segments with timing
            progress_callback: Progress callback

        Returns:
            Segments with original timing and translated text
        """
        if progress_callback:
            progress_callback("Restoring original timing...")

        result_segments = []

        for para in translated_paragraphs:
            # Find original segments that belong to this paragraph
            para_segments = [
                seg for seg in original_segments
                if seg['start'] >= para['start'] and seg['end'] <= para['end']
            ]

            if not para_segments:
                # Paragraph doesn't match original segments exactly
                # Use paragraph as-is but ensure translated_text is set
                para_copy = para.copy()
                para_copy['translated_text'] = para.get('text', '')
                result_segments.append(para_copy)
                continue

            # Split translated text proportionally
            translated_text = para['text']
            translated_words = translated_text.split()

            # Calculate word distribution
            total_original_words = sum(len(seg['text'].split()) for seg in para_segments)
            if total_original_words == 0:
                total_original_words = 1

            word_index = 0
            for seg in para_segments:
                # Calculate proportion of words for this segment
                original_words = len(seg['text'].split())
                proportion = original_words / total_original_words
                segment_word_count = int(len(translated_words) * proportion)

                # Extract words for this segment
                if word_index < len(translated_words):
                    if seg == para_segments[-1]:  # Last segment gets remaining words
                        segment_words = translated_words[word_index:]
                    else:
                        segment_words = translated_words[word_index:word_index + segment_word_count]

                    segment_text = ' '.join(segment_words)
                    word_index += len(segment_words)
                else:
                    segment_text = ""

                # Create result segment
                result_seg = seg.copy()
                result_seg['original_text'] = seg['text']
                result_seg['text'] = segment_text
                result_seg['translated_text'] = segment_text  # TTS looks for this field
                result_seg['translated'] = True
                if 'speaker' in para:
                    result_seg['speaker'] = para['speaker']
                    result_seg['speaker_label'] = para.get('speaker_label')

                result_segments.append(result_seg)

        logger.info(f"Restored {len(result_segments)} segments with translated text")

        return result_segments

    def _is_formal_speech(self, texts: List[str]) -> bool:
        """Detect if speaker uses formal language"""
        formal_indicators = [
            'therefore', 'furthermore', 'however', 'moreover',
            'consequently', 'nevertheless', 'accordingly'
        ]
        text_combined = ' '.join(texts).lower()
        formal_count = sum(1 for word in formal_indicators if word in text_combined)
        return formal_count >= 2

    def _avg_sentence_length(self, texts: List[str]) -> float:
        """Calculate average sentence length"""
        import re
        all_text = ' '.join(texts)
        sentences = re.split(r'[.!?]+', all_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0
        total_words = sum(len(s.split()) for s in sentences)
        return total_words / len(sentences)

    def _uses_questions(self, texts: List[str]) -> bool:
        """Check if speaker frequently asks questions"""
        text_combined = ' '.join(texts)
        question_count = text_combined.count('?')
        return question_count >= 2

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for translation"""
        # Normalize text for caching
        normalized = text.lower().strip()
        # Only cache short phrases
        if len(normalized.split()) <= 10:
            return normalized
        return None

    def _is_valid_georgian(self, text: str) -> bool:
        """Check if text contains Georgian characters"""
        georgian_range = range(0x10A0, 0x10FF)
        return any(ord(char) in georgian_range for char in text)