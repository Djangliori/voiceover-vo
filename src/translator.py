"""
Translation Module
Translates text to Georgian using Gemini (FREE) or OpenAI GPT-4
Supports both segment-level and paragraph-level translation modes
"""

import os
from typing import List, Dict, Optional
from src.config import Config
from src.logging_config import get_logger

logger = get_logger(__name__)


class Translator:
    def __init__(self, use_paragraph_mode: bool = True):
        """
        Initialize translator (Gemini or OpenAI)

        Args:
            use_paragraph_mode: Whether to use context-aware paragraph translation
        """
        # Try Gemini first (FREE), fallback to OpenAI
        gemini_key = os.getenv('GEMINI_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')

        if gemini_key:
            # Use Gemini (FREE!)
            try:
                from src.gemini_translator import GeminiTranslator
                self.backend = GeminiTranslator()
                logger.info("Using Gemini API for translation (FREE)")
            except Exception as e:
                logger.error(f"Gemini initialization failed: {e}")
                if openai_key:
                    self._init_openai(openai_key)
                else:
                    raise ValueError("No translation API configured (Gemini or OpenAI)")
        elif openai_key:
            # Fallback to OpenAI
            self._init_openai(openai_key)
        else:
            raise ValueError("Neither GEMINI_API_KEY nor OPENAI_API_KEY found in environment variables")

        self.target_language = 'Georgian'
        self.use_paragraph_mode = use_paragraph_mode
        self.context_translator = None

        # Initialize context-aware translator if in paragraph mode
        if self.use_paragraph_mode:
            try:
                from src.context_translator import ContextAwareTranslator
                self.context_translator = ContextAwareTranslator()
                logger.info("Initialized context-aware paragraph translation mode")
            except ImportError as e:
                logger.warning(f"Could not initialize paragraph mode, falling back to segment mode: {e}")
                self.use_paragraph_mode = False

    def _init_openai(self, api_key: str):
        """Initialize OpenAI backend"""
        import openai
        openai.api_key = api_key
        self.backend = None  # Will use _translate_single and _translate_segment_mode
        logger.info("Using OpenAI API for translation")

    def translate_segments(self, segments, progress_callback=None, speakers=None):
        """
        Translate text segments to Georgian

        Args:
            segments: List of segments with 'text', 'start', 'end'
            progress_callback: Optional callback for progress updates
            speakers: Optional speaker information for context-aware translation

        Returns:
            List of segments with translated text added as 'translated_text'
        """
        # If using Gemini backend, delegate to it
        if self.backend:
            return self.backend.translate_segments(segments, progress_callback)

        # Use paragraph mode if available and segments have speaker info
        if self.use_paragraph_mode and self.context_translator:
            has_speakers = any('speaker' in seg for seg in segments) or speakers is not None
            if has_speakers:
                logger.info("Using context-aware paragraph translation mode")
                return self._translate_with_context(segments, speakers, progress_callback)

        # Fall back to original segment-based translation
        logger.info("Using segment-based translation mode")
        return self._translate_segment_mode(segments, progress_callback)

    def _translate_with_context(
        self,
        segments: List[Dict],
        speakers: Optional[List[Dict]],
        progress_callback: Optional[callable]
    ) -> List[Dict]:
        """
        Translate using context-aware paragraph mode

        Args:
            segments: List of segments
            speakers: Optional speaker information
            progress_callback: Progress callback

        Returns:
            Translated segments with context awareness
        """
        try:
            # Use context translator for paragraph-level translation
            translated = self.context_translator.translate_conversation(
                segments,
                speakers,
                progress_callback
            )

            # Ensure backward compatibility - add 'translated_text' field
            for seg in translated:
                if 'text' in seg and seg.get('translated', False):
                    seg['translated_text'] = seg['text']
                    seg['text'] = seg.get('original_text', seg['text'])

            return translated

        except Exception as e:
            logger.error(f"Context translation failed, falling back to segment mode: {e}")
            return self._translate_segment_mode(segments, progress_callback)

    def _translate_segment_mode(self, segments, progress_callback=None):
        """
        Original segment-based translation (backward compatible)

        Args:
            segments: List of segments
            progress_callback: Progress callback

        Returns:
            Translated segments
        """
        if progress_callback:
            progress_callback(f"AI translating {len(segments)} segments to Georgian...")

        # Combine all segments into one request for better context
        full_text = "\n\n".join([f"[{i}] {seg['text']}" for i, seg in enumerate(segments)])

        if progress_callback:
            progress_callback("Sending to GPT-4 for context-aware translation...")

        # Use GPT-4 for high-quality translation
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",  # Latest GPT-4 model
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert translator specializing in English to Georgian translation.
Your translations must be:
1. Natural and fluent in Georgian, not word-for-word mechanical translations
2. Contextually appropriate with proper Georgian grammar
3. Suitable for voiceover narration (spoken language, not overly formal)
4. Culturally appropriate for Georgian speakers
5. Maintain the meaning and tone of the original

Translate each numbered segment below into Georgian. Keep the same numbering format [0], [1], etc.
Do not add any explanations, just provide the translations."""
                    },
                    {
                        "role": "user",
                        "content": f"Translate these segments to Georgian:\n\n{full_text}"
                    }
                ],
                temperature=0.3  # Lower temperature for more consistent translations
            )

            # Parse the response
            translated_full = response['choices'][0]['message']['content']

            # Split back into segments
            translated_lines = translated_full.strip().split('\n\n')

            translated_segments = []
            for i, segment in enumerate(segments):
                # Find the corresponding translation
                translation = None
                for line in translated_lines:
                    if line.startswith(f"[{i}]"):
                        translation = line[len(f"[{i}]"):].strip()
                        break

                if not translation:
                    # Fallback: translate individually if batch failed
                    translation = self._translate_single(segment['text'])

                translated_segment = segment.copy()
                translated_segment['translated_text'] = translation
                translated_segment['original_text'] = segment['text']
                translated_segments.append(translated_segment)

                if progress_callback and (i + 1) % 10 == 0:
                    progress_callback(f"Processed {i + 1}/{len(segments)} translations")

        except Exception as e:
            # Log the error properly instead of silently ignoring
            logger.error("batch_translation_failed", error=str(e), exc_info=True)

            # Fallback: translate segments individually
            if progress_callback:
                progress_callback(f"Batch translation failed, translating individually...")

            translated_segments = []
            for i, segment in enumerate(segments):
                translation = self._translate_single(segment['text'])

                translated_segment = segment.copy()
                translated_segment['translated_text'] = translation
                translated_segment['original_text'] = segment['text']
                translated_segments.append(translated_segment)

                if progress_callback and (i + 1) % 5 == 0:
                    progress_callback(f"Translated {i + 1}/{len(segments)} segments")

        if progress_callback:
            progress_callback(f"AI translation complete: {len(translated_segments)} segments")

        return translated_segments

    def _translate_single(self, text):
        """
        Translate a single text segment to Georgian

        Args:
            text: Text to translate

        Returns:
            Translated text
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert translator specializing in English to Georgian translation.
Provide natural, fluent Georgian translations suitable for voiceover narration.
Use proper Georgian grammar and culturally appropriate expressions.
Only respond with the translation, no explanations."""
                    },
                    {
                        "role": "user",
                        "content": f"Translate to Georgian: {text}"
                    }
                ],
                temperature=0.3
            )

            return response['choices'][0]['message']['content'].strip()

        except Exception as e:
            # Log error properly instead of using print
            logger.error("single_translation_failed", error=str(e), text=text[:100])
            # Ultimate fallback: return original text with error marker
            return f"[Translation Error] {text}"

    def translate_text(self, text):
        """
        Translate a single text string to Georgian

        Args:
            text: Text to translate

        Returns:
            Translated text
        """
        # If using Gemini backend, delegate to it
        if self.backend:
            return self.backend.translate_text(text)

        return self._translate_single(text)
