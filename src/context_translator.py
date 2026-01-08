"""
Context-Aware Translation Module
Translates paragraphs with conversation context and speaker awareness
Maintains natural flow and coherence across multi-speaker dialogue
"""

import os
import time
import json
from typing import List, Dict, Optional, Tuple
from src.config import Config
from src.segment_merger import SegmentMerger
from src.logging_config import get_logger

logger = get_logger(__name__)


class ContextAwareTranslator:
    """Translates with conversation context and speaker awareness"""

    def __init__(self):
        """Initialize context-aware translator"""
        # Try Gemini first (FREE), fallback to OpenAI
        gemini_key = os.getenv('GEMINI_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')

        if gemini_key:
            # Use Gemini (FREE!)
            from google import genai
            self.client = genai.Client(api_key=gemini_key)
            self.model_name = 'models/gemini-2.5-flash'
            self.backend = 'gemini'
            logger.info("Using Gemini API for context-aware translation (FREE)")
        elif openai_key:
            # Fallback to OpenAI
            import openai
            openai.api_key = openai_key
            self.model = None
            self.backend = 'openai'
            logger.info("Using OpenAI API for context-aware translation")
        else:
            raise ValueError("Neither GEMINI_API_KEY nor OPENAI_API_KEY found in environment variables")

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
            progress_callback("Translating segments...")

        # SIMPLIFIED: Translate each segment directly (no paragraph merging)
        # This is more reliable and preserves original timing
        translated_segments = []
        total_segments = len(segments)

        for i, segment in enumerate(segments):
            if progress_callback:
                progress = int((i / total_segments) * 100)
                progress_callback(f"Translating segment {i+1}/{total_segments} ({progress}%)")

            # Get the English text
            english_text = segment.get('text', '').strip()

            if not english_text:
                logger.warning(f"Segment {i} has no text, skipping")
                continue

            # Translate directly
            try:
                georgian_text = self._translate_text(english_text)
            except Exception as e:
                logger.error(f"Translation failed for segment {i}: {e}")
                georgian_text = ""

            # Create translated segment with original timing
            translated_seg = segment.copy()
            translated_seg['original_text'] = english_text
            translated_seg['text'] = georgian_text
            translated_seg['translated_text'] = georgian_text
            translated_seg['translated'] = True

            logger.info(f"Segment {i}: [{segment.get('start', 0):.1f}s-{segment.get('end', 0):.1f}s]")
            logger.info(f"  EN: {english_text[:60]}...")
            logger.info(f"  KA: {georgian_text[:60]}...")

            translated_segments.append(translated_seg)

            # Small delay to avoid rate limiting
            if i < total_segments - 1:
                time.sleep(0.3)

        if progress_callback:
            progress_callback(f"Translation complete: {len(translated_segments)} segments")

        logger.info(f"Translated {len(translated_segments)} segments")
        return translated_segments

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

    def _translate_text(self, english_text: str) -> str:
        """
        Translate English to Georgian with natural, conversational style.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.backend == 'gemini':
                    # Use Gemini
                    prompt = f"""You are an expert English to Georgian translator specializing in natural, spoken Georgian.

Your translations must be:
1. NATURAL and FLUENT Georgian - NOT word-for-word mechanical translations
2. Adjusted to Georgian grammar, word order, and sentence structure
3. Using natural Georgian expressions and idioms where appropriate
4. Suitable for voiceover/dubbing (spoken language, conversational tone)
5. Culturally appropriate for Georgian speakers
6. Preserving the original meaning, emotion, and tone

IMPORTANT: Georgian has different sentence structure than English. Rearrange words naturally.
Return ONLY the Georgian translation, nothing else.

Translate to natural Georgian:

{english_text}"""

                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt
                    )
                    translation = response.text.strip()
                    if translation:
                        return translation
                else:
                    # Use OpenAI
                    import openai
                    response = openai.ChatCompletion.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "system",
                                "content": """You are an expert English to Georgian translator specializing in natural, spoken Georgian.

Your translations must be:
1. NATURAL and FLUENT Georgian - NOT word-for-word mechanical translations
2. Adjusted to Georgian grammar, word order, and sentence structure
3. Using natural Georgian expressions and idioms where appropriate
4. Suitable for voiceover/dubbing (spoken language, conversational tone)
5. Culturally appropriate for Georgian speakers
6. Preserving the original meaning, emotion, and tone

IMPORTANT: Georgian has different sentence structure than English. Rearrange words naturally.
Return ONLY the Georgian translation, nothing else."""
                            },
                            {
                                "role": "user",
                                "content": f"Translate to natural Georgian:\n\n{english_text}"
                            }
                        ],
                        temperature=0.4,
                        max_tokens=500,
                        timeout=30
                    )
                    translation = response['choices'][0]['message']['content'].strip()
                    if translation:
                        return translation
            except Exception as e:
                logger.error(f"Translation error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)

        return ""

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
        used_segments = set()  # Track which segments have been processed

        for para_idx, para in enumerate(translated_paragraphs):
            # Find original segments that overlap with this paragraph
            # Use overlap matching (not strict containment) for robustness
            para_segments = [
                seg for seg in original_segments
                if seg['start'] < para['end'] and seg['end'] > para['start']  # Overlaps
                and id(seg) not in used_segments  # Not already used
            ]

            logger.info(f"Para {para_idx} [{para.get('start', 0):.1f}s-{para.get('end', 0):.1f}s]: matched {len(para_segments)} segments")

            if not para_segments:
                # Paragraph doesn't match original segments exactly
                # Use paragraph as-is but ensure translated_text is set
                para_copy = para.copy()
                para_copy['translated_text'] = para.get('text', '')
                result_segments.append(para_copy)
                logger.info(f"  -> Using paragraph as segment (no matching original segments)")
                continue

            # Mark segments as used
            for seg in para_segments:
                used_segments.add(id(seg))

            # Put all translated text in the first segment of the paragraph
            # This is simpler and more reliable than proportional splitting
            translated_text = para.get('text', '')
            logger.info(f"  -> Text ({len(translated_text)} chars): {translated_text[:80]}...")

            for i, seg in enumerate(para_segments):
                result_seg = seg.copy()
                result_seg['original_text'] = seg['text']

                if i == 0:
                    # First segment gets all the translated text
                    result_seg['text'] = translated_text
                    result_seg['translated_text'] = translated_text
                else:
                    # Other segments in this paragraph get empty (will be skipped by TTS)
                    result_seg['text'] = ""
                    result_seg['translated_text'] = ""

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